--[[
    Gran Turismo Shared State Subsystem
    Exposes high-speed, zero-copy shared memory via CSP's `ac.connect()`
    between the CSP New Mode simulation engine and the movable AC Lua Apps.
]]

local GTLicenseShared = {}

-- Schema layout for inter-process / inter-script communication
local function buildLayout()
    if not (ac and ac.StructItem) then return nil end
    return {
        ac.StructItem.key('app.GTLicense.sharedState'),
        isActive        = ac.StructItem.boolean(),
        uiAppActive     = ac.StructItem.boolean(),
        sessionTime     = ac.StructItem.double(),
        currentState    = ac.StructItem.int32(),
        countdownTimer  = ac.StructItem.float(),
        isGo            = ac.StructItem.boolean(),
        failReason      = ac.StructItem.string(64),
        testId          = ac.StructItem.string(32),
        testTitle       = ac.StructItem.string(64),
        lessonObjective = ac.StructItem.string(128),
        tierName        = ac.StructItem.string(32),
        goldTime        = ac.StructItem.double(),
        silverTime      = ac.StructItem.double(),
        bronzeTime      = ac.StructItem.double(),
        speedKmh        = ac.StructItem.double(),
        gear            = ac.StructItem.int32(),
        rpm             = ac.StructItem.float(),
        medalAchieved   = ac.StructItem.string(16),
        ghostDelta      = ac.StructItem.double(),
        ghostActive     = ac.StructItem.boolean(),
        ghostMode       = ac.StructItem.int32(),
        ghostOSD        = ac.StructItem.string(64),
        requestRestart  = ac.StructItem.boolean(),
        requestNext     = ac.StructItem.boolean(),
        requestExit     = ac.StructItem.boolean(),
    }
end

--- Create fallback table for standalone or test environments
local function createFallback()
    return {
        isActive        = false,
        uiAppActive     = false,
        sessionTime     = 0.0,
        currentState    = 0,
        countdownTimer  = 3.0,
        isGo            = false,
        failReason      = "",
        testId          = "",
        testTitle       = "",
        lessonObjective = "",
        tierName        = "",
        goldTime        = 0.0,
        silverTime      = 0.0,
        bronzeTime      = 0.0,
        speedKmh        = 0.0,
        gear            = 0,
        rpm             = 0.0,
        medalAchieved   = "",
        ghostDelta      = 0.0,
        ghostActive     = false,
        ghostMode       = 1,
        ghostOSD        = "",
        requestRestart  = false,
        requestNext     = false,
        requestExit     = false,
    }
end

local connectionInstance = nil

--- Connect to the shared memory block
--- @return table Connected shared memory structure or fallback table
function GTLicenseShared.connect()
    if connectionInstance then return connectionInstance end

    if ac and ac.connect and ac.StructItem then
        local layout = buildLayout()
        if layout then
            local ok, res = pcall(ac.connect, layout, false)
            if ok and res then
                connectionInstance = res
                return connectionInstance
            end
        end
    end

    connectionInstance = createFallback()
    return connectionInstance
end

return GTLicenseShared

