--[[
    Gran Turismo UI App Shared State Client
    Connects to the New Mode simulation engine via CSP's `ac.connect()`.
    Falls back gracefully to native car and session telemetry when running outside New Mode.
]]

local SharedStateClient = {}

local SHARED_LAYOUT = {
    ac and ac.StructItem and ac.StructItem.key('app.GTLicense.sharedState'),
    isActive        = ac and ac.StructItem and ac.StructItem.boolean(),
    uiAppActive     = ac and ac.StructItem and ac.StructItem.boolean(),
    sessionTime     = ac and ac.StructItem and ac.StructItem.double(),
    currentState    = ac and ac.StructItem and ac.StructItem.int32(),
    countdownTimer  = ac and ac.StructItem and ac.StructItem.float(),
    isGo            = ac and ac.StructItem and ac.StructItem.boolean(),
    failReason      = ac and ac.StructItem and ac.StructItem.string(64),
    testId          = ac and ac.StructItem and ac.StructItem.string(32),
    testTitle       = ac and ac.StructItem and ac.StructItem.string(64),
    lessonObjective = ac and ac.StructItem and ac.StructItem.string(128),
    tierName        = ac and ac.StructItem and ac.StructItem.string(32),
    goldTime        = ac and ac.StructItem and ac.StructItem.double(),
    silverTime      = ac and ac.StructItem and ac.StructItem.double(),
    bronzeTime      = ac and ac.StructItem and ac.StructItem.double(),
    speedKmh        = ac and ac.StructItem and ac.StructItem.double(),
    gear            = ac and ac.StructItem and ac.StructItem.int32(),
    rpm             = ac and ac.StructItem and ac.StructItem.float(),
    medalAchieved   = ac and ac.StructItem and ac.StructItem.string(16),
    ghostDelta      = ac and ac.StructItem and ac.StructItem.double(),
    ghostActive     = ac and ac.StructItem and ac.StructItem.boolean(),
    ghostMode       = ac and ac.StructItem and ac.StructItem.int32(),
    ghostOSD        = ac and ac.StructItem and ac.StructItem.string(64),
    requestRestart  = ac and ac.StructItem and ac.StructItem.boolean(),
    requestNext     = ac and ac.StructItem and ac.StructItem.boolean(),
    requestExit     = ac and ac.StructItem and ac.StructItem.boolean(),
}

local con = nil
if ac and ac.connect and ac.StructItem then
    local ok, res = pcall(ac.connect, SHARED_LAYOUT, false)
    if ok and res then con = res end
end

--- Retrieves current license state
--- @return table State dictionary
function SharedStateClient.get()
    if con and con.isActive then
        con.uiAppActive = true
        return {
            isModeActive    = true,
            sessionTime     = con.sessionTime or 0.0,
            currentState    = con.currentState or 2,
            countdownTimer  = con.countdownTimer or 0.0,
            isGo            = con.isGo or false,
            failReason      = con.failReason or "",
            testId          = con.testId or "TEST",
            testTitle       = con.testTitle or "License Examination",
            lessonObjective = con.lessonObjective or "",
            targets         = {
                gold_seconds   = con.goldTime > 0 and con.goldTime or nil,
                silver_seconds = con.silverTime > 0 and con.silverTime or nil,
                bronze_seconds = con.bronzeTime > 0 and con.bronzeTime or nil,
            },
            speedKmh        = con.speedKmh or 0.0,
            gear            = con.gear or 0,
            medalAchieved   = con.medalAchieved or "",
            ghostState      = {
                active      = con.ghostActive,
                delta       = con.ghostDelta,
                mode        = con.ghostMode,
                osd_message = con.ghostOSD,
            },
            rawConnection   = con,
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
        ghostState      = nil,
        rawConnection   = nil,
    }
end

--- Triggers restart in the master simulation engine
function SharedStateClient.requestRestart()
    if con then con.requestRestart = true end
end

--- Triggers next event in the master simulation engine
function SharedStateClient.requestNext()
    if con then con.requestNext = true end
end

return SharedStateClient

