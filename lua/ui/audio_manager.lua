--[[
    Gran Turismo-style Audio Cue Manager for Assetto Corsa Licenses Mod
    Handles triggering countdown beeps (3, 2, 1), high GO chime, failure buzzer,
    pass fanfare, and gold victory fanfare using CSP's ui.playSound() API.
]]

local GTAudioManager = {}

-- Sound file names matching assets/audio/ spec
GTAudioManager.SOUNDS = {
    COUNTDOWN_BEEP = "countdown_beep.wav",
    COUNTDOWN_GO   = "countdown_go.wav",
    FAIL_BUZZER    = "fail_buzzer.wav",
    PASS_FANFARE   = "pass_fanfare.wav",
    GOLD_FANFARE   = "gold_fanfare.wav",
}

local masterVolume = 1.0
local audioBasePath = ""
local soundCache = {}
local audioEventCache = {}

-- Debounce tracking to prevent repeated audio spamming
local lastState = nil
local lastPlayedBeep = nil
local hasPlayedPass = false
local hasPlayedFail = false

--- Play or trigger an AudioEvent from file with event caching
local function playAudioEvent(path, volume, pitch)
    local ev = audioEventCache[path]
    if not ev and ac and ac.AudioEvent and ac.AudioEvent.fromFile then
        local ok, res = pcall(function()
            return ac.AudioEvent.fromFile({ filename = path, use3D = false, loop = false })
        end)
        if ok and res then
            ev = res
            audioEventCache[path] = ev
        end
    end

    if ev then
        if ev.setVolume then ev:setVolume(volume) end
        if ev.setPitch then ev:setPitch(pitch) end
        ev:start()
        return true
    end
    return false
end

-- Polyfill ui.playSound if not natively exposed by current CSP build
if ui and ui.playSound == nil then
    ui.playSound = function(filepath, volume, pitch)
        playAudioEvent(filepath, volume or 1.0, pitch or 1.0)
    end
end

--- Resolve absolute or relative path to sound asset
local function resolveSoundPath(filename)
    if soundCache[filename] then
        return soundCache[filename]
    end

    local candidates = {
        audioBasePath .. "/" .. filename,
        audioBasePath .. "/assets/audio/" .. filename,
        "assets/audio/" .. filename,
    }

    if ac and ac.getFolder and ac.FolderID then
        if ac.FolderID.ScriptOrigin then
            local scriptOrigin = ac.getFolder(ac.FolderID.ScriptOrigin)
            table.insert(candidates, scriptOrigin .. "/assets/audio/" .. filename)
            table.insert(candidates, scriptOrigin .. "/audio/" .. filename)
        end
        if ac.FolderID.Root then
            local acRoot = ac.getFolder(ac.FolderID.Root)
            table.insert(candidates, acRoot .. "/extension/lua/new-modes/gt-license/assets/audio/" .. filename)
            table.insert(candidates, acRoot .. "/content/tracks/common/audio/" .. filename)
        end
    end

    -- Default fallback is the configured base path or relative asset path
    local resolved = candidates[1]
    if io and io.exists then
        for _, path in ipairs(candidates) do
            if io.exists(path) then
                resolved = path
                break
            end
        end
    end

    soundCache[filename] = resolved
    return resolved
end

--- Internal playback wrapper invoking ui.playSound() or AudioEvent cache
local function play(soundName, volume, pitch)
    local path = resolveSoundPath(soundName)
    local finalVol = (volume or 1.0) * masterVolume
    local finalPitch = pitch or 1.0

    if ui and type(ui.playSound) == "function" then
        local success, err = pcall(ui.playSound, path, finalVol, finalPitch)
        if not success and ac and ac.log then
            ac.log("GTAudioManager ui.playSound failed: " .. tostring(err))
        end
    elseif ac and ac.AudioEvent and ac.AudioEvent.fromFile then
        playAudioEvent(path, finalVol, finalPitch)
    end
end

--- Initialize Audio Manager with optional custom base path
--- @param customBasePath string? Path to root mod or assets folder
function GTAudioManager.init(customBasePath)
    if customBasePath and customBasePath ~= "" then
        audioBasePath = customBasePath
    elseif ac and ac.getFolder and ac.FolderID and ac.FolderID.ScriptOrigin then
        audioBasePath = ac.getFolder(ac.FolderID.ScriptOrigin)
    else
        audioBasePath = "."
    end
    GTAudioManager.reset()
end

--- Set global master volume multiplier (0.0 to 1.0)
--- @param volume number
function GTAudioManager.setVolume(volume)
    masterVolume = math.max(0.0, math.min(1.0, volume or 1.0))
end

--- Reset trigger debounce state (e.g. upon test reset / retry)
function GTAudioManager.reset()
    lastState = nil
    lastPlayedBeep = nil
    hasPlayedPass = false
    hasPlayedFail = false
    soundCache = {}
end

--- Trigger standard countdown beep (counts: 3, 2, 1)
--- @param count integer? Current countdown second (3, 2, or 1)
function GTAudioManager.playCountdownBeep(count)
    if count and lastPlayedBeep == count then
        return -- Prevent duplicate beep for same second
    end
    lastPlayedBeep = count
    play(GTAudioManager.SOUNDS.COUNTDOWN_BEEP, 0.9, 1.0)
end

--- Trigger high-pitched GO start chime
function GTAudioManager.playCountdownGo()
    if lastPlayedBeep == "GO" then
        return
    end
    lastPlayedBeep = "GO"
    play(GTAudioManager.SOUNDS.COUNTDOWN_GO, 1.0, 1.0)
end

--- Trigger prominent failure/disqualification buzzer
function GTAudioManager.playFailBuzzer()
    if hasPlayedFail then
        return
    end
    hasPlayedFail = true
    play(GTAudioManager.SOUNDS.FAIL_BUZZER, 1.0, 1.0)
end

--- Trigger test pass fanfare (bronze / silver level)
function GTAudioManager.playPassFanfare()
    if hasPlayedPass then
        return
    end
    hasPlayedPass = true
    play(GTAudioManager.SOUNDS.PASS_FANFARE, 1.0, 1.0)
end

--- Trigger glorious gold medal victory fanfare
function GTAudioManager.playGoldFanfare()
    if hasPlayedPass then
        return
    end
    hasPlayedPass = true
    play(GTAudioManager.SOUNDS.GOLD_FANFARE, 1.0, 1.0)
end

--- Trigger appropriate victory fanfare based on medal earned
--- @param medal 'gold'|'silver'|'bronze'|nil
function GTAudioManager.playMedalFanfare(medal)
    if medal == "gold" or medal == "GOLD" then
        GTAudioManager.playGoldFanfare()
    else
        GTAudioManager.playPassFanfare()
    end
end

--- Update audio manager state machine transitions automatically
--- @param dt number Delta time in seconds
--- @param currentState integer Current simulation state
--- @param countdownTimer number? Remaining seconds in countdown (e.g. 3.0 down to 0.0)
--- @param medalAchieved string? 'gold', 'silver', 'bronze'
function GTAudioManager.update(dt, currentState, countdownTimer, medalAchieved)
    -- State definitions matching engine:
    -- 1 = COUNTDOWN, 2 = RUNNING, 3 = PASSED, 4 = FAILED
    if currentState == 1 and countdownTimer then
        local floorSec = math.ceil(countdownTimer)
        if floorSec >= 1 and floorSec <= 3 and lastPlayedBeep ~= floorSec then
            GTAudioManager.playCountdownBeep(floorSec)
        end
    end

    if lastState == 1 and currentState == 2 then
        GTAudioManager.playCountdownGo()
    end

    if currentState == 3 and not hasPlayedPass then
        GTAudioManager.playMedalFanfare(medalAchieved)
    end

    if currentState == 4 and not hasPlayedFail then
        GTAudioManager.playFailBuzzer()
    end

    lastState = currentState
end

return GTAudioManager
