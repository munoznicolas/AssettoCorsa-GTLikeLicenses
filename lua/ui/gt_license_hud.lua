--[[
    Gran Turismo Master HUD Coordinator for Assetto Corsa Licenses Mod
    Coordinates DirectWrite HUD rendering, widget modularity, and fullscreen modal overlays.
    Interfaces seamlessly with both CSP New Mode runtime and draggable AC Lua Apps.
    Modal Overlays: 3-2-1-START! countdown, DISQUALIFIED banner, and results screen.
]]

local Theme           = require("ui/common/gt_ui_theme")
local GTTimerWidget   = require("ui/screens/gt_timer_widget")
local GTModalOverlays = require("ui/screens/gt_modal_overlays")
local GTLicenseShared = nil
pcall(function() GTLicenseShared = require("engine/shared_state") end)
if not GTLicenseShared then
  pcall(function() GTLicenseShared = require("engine/gt_shared_state") end)
end
if not GTLicenseShared then
  pcall(function() GTLicenseShared = require("shared_state") end)
end

local GTLicenseHUD = {}

-- State Enumeration
GTLicenseHUD.STATE = {
    PREPARE   = 0,
    COUNTDOWN = 1,
    RUNNING   = 2,
    PASSED    = 3,
    FAILED    = 4,
}

-- Re-export Theme Colors for backward compatibility
GTLicenseHUD.COLORS = Theme.COLORS

-- Local internal state
local currentConfig = nil
local countdownTimer = 3.0
local goDisplayTimer = 0.0
local animTimer = 0.0
local lastState = GTLicenseHUD.STATE.PREPARE
local cachedMedalAchieved = nil

local sharedState = GTLicenseShared.connect()

local function isUIAppActive()
    if not sharedState or not sharedState.uiAppActive then return false end
    if sharedState.lastAppHeartbeat and sharedState.lastAppHeartbeat > 0 then
        local sim = ac and ac.getSim and ac.getSim()
        local now = (sim and sim.currentSessionTime and (sim.currentSessionTime / 1000)) or (os and os.clock and os.clock()) or 0
        if math.abs(now - sharedState.lastAppHeartbeat) > 0.5 then
            return false
        end
    end
    return true
end

-- Internal component functions retained for contract tests & legacy compatibility
local function drawStopwatchCluster(screenW, sessionTime, targets, currentState)
    GTTimerWidget.drawFixed(screenW, sessionTime, targets, currentState)
end

local function drawCountdown(screenW, screenH, timer, isGo)
    GTModalOverlays.drawCountdown(screenW, screenH, timer, isGo)
end

local function drawDisqualifiedBanner(screenW, screenH, failReason, callbacks)
    GTModalOverlays.drawDisqualifiedBanner(screenW, screenH, failReason, callbacks, animTimer)
end

local function drawResultsScreen(screenW, screenH, finalTime, targets, medalAchieved, callbacks)
    GTModalOverlays.drawResultsScreen(screenW, screenH, finalTime, targets, medalAchieved, callbacks)
end

--- Initialize HUD with active test configuration
--- @param testConfig table Test definition JSON
function GTLicenseHUD.init(testConfig)
    currentConfig = testConfig or {}
    GTLicenseHUD.reset()
end

--- Reset HUD timers and animation state
function GTLicenseHUD.reset()
    countdownTimer = 3.0
    goDisplayTimer = 0.0
    animTimer = 0.0
    cachedMedalAchieved = nil
end

--- Determine which medal a time achieved
--- @param time number Lap time in seconds
--- @param targets table { gold_seconds, silver_seconds, bronze_seconds }
--- @return string|nil 'gold'|'silver'|'bronze'|nil
function GTLicenseHUD.evaluateMedal(time, targets)
    return Theme.evaluateMedal(time, targets)
end

--- Frame update for HUD timers and animations
--- @param dt number Delta time in seconds
--- @param currentState integer State from GTLicenseHUD.STATE
--- @param stateCountdownTimer number? External countdown timer from engine
function GTLicenseHUD.update(dt, currentState, stateCountdownTimer)
    animTimer = animTimer + (dt or 0.016)

    if currentState == GTLicenseHUD.STATE.COUNTDOWN then
        if stateCountdownTimer then
            countdownTimer = stateCountdownTimer
        else
            countdownTimer = math.max(0, countdownTimer - dt)
        end
    end

    -- Trigger "GO!" chime burst timer when transitioning from countdown to running
    if lastState == GTLicenseHUD.STATE.COUNTDOWN and currentState == GTLicenseHUD.STATE.RUNNING then
        goDisplayTimer = 0.85
    elseif goDisplayTimer > 0 then
        goDisplayTimer = math.max(0, goDisplayTimer - dt)
    end

    lastState = currentState
end

--- Master HUD Drawing Hook
--- Invoked within script.drawUI()
function GTLicenseHUD.draw(sessionTime, targetsOrConfig, currentState, failReason, speedKmh, medalAchieved, callbacks)
    local uiState = ac and ac.getUI and ac.getUI()
    local screenW = (uiState and uiState.windowSize and uiState.windowSize.x) or 1920
    local screenH = (uiState and uiState.windowSize and uiState.windowSize.y) or 1080
    local dt = (uiState and uiState.dt) or 0.016

    local config = currentConfig
    local targets = (config and config.targets) or {}
    if type(targetsOrConfig) == "table" then
        if targetsOrConfig.targets then
            config = targetsOrConfig
            targets = targetsOrConfig.targets
        elseif targetsOrConfig.gold_seconds or targetsOrConfig.bronze_seconds then
            targets = targetsOrConfig
        end
    end

    GTLicenseHUD.update(dt, currentState)

    if currentState == GTLicenseHUD.STATE.PASSED and not cachedMedalAchieved then
        cachedMedalAchieved = medalAchieved or GTLicenseHUD.evaluateMedal(sessionTime, targets)
    end

    if not ui or not ui.beginTransparentWindow then return end

    ui.beginTransparentWindow("gtLicenseHudWindow", vec2(0, 0), vec2(screenW, screenH), false)

    -- If movable UI App is not active, render in-race HUD widgets directly as fallback
    if not isUIAppActive() then
        drawStopwatchCluster(screenW, sessionTime, targets, currentState)
    end

    -- Fullscreen Modal Overlays (Always rendered cleanly in script.drawUI)
    if currentState == GTLicenseHUD.STATE.COUNTDOWN then
        drawCountdown(screenW, screenH, countdownTimer, false)
    elseif goDisplayTimer > 0 then
        drawCountdown(screenW, screenH, 0, true)
    end

    if currentState == GTLicenseHUD.STATE.FAILED then
        drawDisqualifiedBanner(screenW, screenH, failReason, callbacks)
    end

    if currentState == GTLicenseHUD.STATE.PASSED then
        drawResultsScreen(screenW, screenH, sessionTime, targets, cachedMedalAchieved, callbacks)
    end

    ui.endTransparentWindow()
end

--- Convenience wrapper accepting single options table
function GTLicenseHUD.drawHUD(opts)
    if not opts then return end
    GTLicenseHUD.draw(
        opts.sessionTime or 0,
        opts.targets or opts.config,
        opts.currentState or GTLicenseHUD.STATE.RUNNING,
        opts.failReason,
        opts.speedKmh or 0,
        opts.medalAchieved,
        opts.callbacks
    )
end

return GTLicenseHUD
