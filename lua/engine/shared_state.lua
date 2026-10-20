--[[
    License Shared State Subsystem
    Exposes high-speed, zero-copy shared memory via CSP's `ac.connect()`
    between the CSP New Mode simulation engine and the movable AC Lua Apps.
]]

local SharedState = {}

-- Schema layout for inter-process / inter-script communication
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

--- Create fallback table for standalone or test environments
local function createFallback()
    return {
        isActive          = true,
        uiAppActive       = false,
        lastAppHeartbeat  = 0.0,
        sessionTime       = 0.0,
        currentState      = 0,
        countdownTimer    = 3.0,
        isGo              = false,
        failReason        = "",
        testId            = "",
        testTitle         = "",
        lessonObjective   = "",
        tierName          = "",
        goldTime          = 0.0,
        silverTime        = 0.0,
        bronzeTime        = 0.0,
        speedKmh          = 0.0,
        gear              = 0,
        rpm               = 0.0,
        medalAchieved     = "",
        requestRestart    = false,
        requestNext       = false,
        requestExit       = false,
    }
end

local connectionInstance = nil

--- Connect to the shared memory block
--- @return table Connected shared memory structure or fallback table
function SharedState.connect()
    if connectionInstance and connectionInstance.isActive ~= nil then return connectionInstance end

    if ac and ac.connect and ac.StructItem then
        local layout = buildLayout()
        if layout then
            local ns = (ac.SharedNamespace and ac.SharedNamespace.Shared) or 'shared'
            local ok, res = pcall(ac.connect, layout, true, ns)
            if ok and res then
                connectionInstance = res
                connectionInstance.isActive = true
                return connectionInstance
            end
        end
    end

    connectionInstance = createFallback()
    connectionInstance.isActive = true
    return connectionInstance
end

return SharedState

