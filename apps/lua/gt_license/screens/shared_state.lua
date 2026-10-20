--[[
    Gran Turismo UI App Shared State Client
    Connects to the New Mode simulation engine via CSP's `ac.connect()`.
    Falls back gracefully to native car and session telemetry when running outside New Mode.
]]

local SharedStateClient = {}

local con = nil

local function buildLayout()
    if not (ac and ac.StructItem) then return nil end
    return {
        ac.StructItem.key('app.GTLicense.sharedState'),
        isActive          = ac.StructItem.boolean(),
        uiAppActive       = ac.StructItem.boolean(),
        lastAppHeartbeat  = ac.StructItem.double(),
        sessionTime       = ac.StructItem.double(),
        currentState      = ac.StructItem.int32(),
        countdownTimer    = ac.StructItem.float(),
        isGo              = ac.StructItem.boolean(),
        failReason        = ac.StructItem.string(64),
        testId            = ac.StructItem.string(32),
        testTitle         = ac.StructItem.string(64),
        lessonObjective   = ac.StructItem.string(128),
        tierName          = ac.StructItem.string(32),
        goldTime          = ac.StructItem.double(),
        silverTime        = ac.StructItem.double(),
        bronzeTime        = ac.StructItem.double(),
        speedKmh          = ac.StructItem.double(),
        gear              = ac.StructItem.int32(),
        rpm               = ac.StructItem.float(),
        medalAchieved     = ac.StructItem.string(16),
        requestRestart    = ac.StructItem.boolean(),
        requestNext       = ac.StructItem.boolean(),
        requestExit       = ac.StructItem.boolean(),
    }
end

local function getConnection()
    if con and con.isActive then return con end
    if ac and ac.connect and ac.StructItem then
        local layout = buildLayout()
        if layout then
            local ns = (ac.SharedNamespace and ac.SharedNamespace.Shared) or 'shared'
            local ok, res = pcall(ac.connect, layout, true, ns)
            if ok and res then
                con = res
                return con
            end
        end
    end
    return con
end

--- Retrieves current license state
--- @return table State dictionary
function SharedStateClient.get()
    local c = getConnection()
    if c and c.isActive then
        c.uiAppActive = true
        local sim = ac and ac.getSim and ac.getSim()
        c.lastAppHeartbeat = (sim and sim.currentSessionTime and (sim.currentSessionTime / 1000)) or (os and os.clock and os.clock()) or 0.0

        return {
            isModeActive    = true,
            sessionTime     = tonumber(c.sessionTime) or 0.0,
            currentState    = tonumber(c.currentState) or 2,
            countdownTimer  = tonumber(c.countdownTimer) or 0.0,
            isGo            = c.isGo == true,
            failReason      = tostring(c.failReason or ""),
            testId          = tostring(c.testId or "TEST"),
            testTitle       = tostring(c.testTitle or "License Examination"),
            lessonObjective = tostring(c.lessonObjective or ""),
            targets         = {
                gold_seconds   = (c.goldTime and c.goldTime > 0) and tonumber(c.goldTime) or nil,
                silver_seconds = (c.silverTime and c.silverTime > 0) and tonumber(c.silverTime) or nil,
                bronze_seconds = (c.bronzeTime and c.bronzeTime > 0) and tonumber(c.bronzeTime) or nil,
            },
            speedKmh        = tonumber(c.speedKmh) or 0.0,
            gear            = tonumber(c.gear) or 0,
            medalAchieved   = tostring(c.medalAchieved or ""),
            rawConnection   = c,
        }
    end

    -- Fallback: native Assetto Corsa session
    local car = ac and ac.getCar and ac.getCar(0)
    local sim = ac and ac.getSim and ac.getSim()
    local lapTimeSec = (car and car.lapTimeMs and car.lapTimeMs > 0) and (car.lapTimeMs / 1000) or 0.0
    local speed = car and car.speedKmh or 0.0
    local gear = car and car.gear or 0

    return {
        isModeActive    = false,
        sessionTime     = lapTimeSec,
        currentState    = 2, -- Running
        countdownTimer  = 0.0,
        isGo            = false,
        failReason      = "",
        testId          = "AC",
        testTitle       = (sim and sim.trackConfiguration) or "Free Practice",
        lessonObjective = "Track Day / Open Practice Session",
        targets         = nil,
        speedKmh        = speed,
        gear            = gear,
        medalAchieved   = "",
        rawConnection   = nil,
    }
end

--- Triggers restart in the master simulation engine
function SharedStateClient.requestRestart()
    local c = getConnection()
    if c then c.requestRestart = true end
end

--- Triggers next event in the master simulation engine
function SharedStateClient.requestNext()
    local c = getConnection()
    if c then c.requestNext = true end
end

return SharedStateClient

