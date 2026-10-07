--[[
    Gran Turismo Timer & Target Delta App Window Screen
    Handles script.timerHUD(dt) callback for the movable AC Lua App.
]]

local Theme       = require("screens/theme")
local SharedState = require("screens/shared_state")

local BASE_WIDTH  = 270
local BASE_HEIGHT = 95

local function getDeltaText(sessionTime, targets, currentState)
    if not targets or not targets.gold_seconds or currentState ~= 2 then
        return nil
    end

    if sessionTime < targets.gold_seconds then
        local delta = sessionTime - targets.gold_seconds
        return string.format("GOLD %s", Theme.formatDelta(delta))
    elseif targets.silver_seconds and sessionTime < targets.silver_seconds then
        local delta = sessionTime - targets.silver_seconds
        return string.format("SILVER %s", Theme.formatDelta(delta))
    elseif targets.bronze_seconds and sessionTime < targets.bronze_seconds then
        local delta = sessionTime - targets.bronze_seconds
        return string.format("BRONZE %s", Theme.formatDelta(delta))
    else
        local delta = sessionTime - (targets.bronze_seconds or 0)
        return string.format("LIMIT %s", Theme.formatDelta(delta))
    end
end

local function renderTimerContent(origin, scale)
    local state = SharedState.get()
    local s = scale or 1.0
    local ox = origin.x
    local oy = origin.y

    -- Header label: "TIME"
    Theme.drawGTText("TIME", math.floor(13 * s), vec2(ox, oy), Theme.COLORS.WHITE, "Regular")

    -- Digital Clock Display
    local timeText = Theme.formatTime(state.sessionTime)
    Theme.drawTimingText(timeText, math.floor(40 * s), vec2(ox, oy + 16 * s), Theme.COLORS.WHITE)

    -- Live Medal Target Delta
    local deltaText = getDeltaText(state.sessionTime, state.targets, state.currentState)
    if deltaText then
        Theme.drawGTText(deltaText, math.floor(17 * s), vec2(ox, oy + 66 * s), Theme.COLORS.WHITE, "Regular")
    end
end

function script.timerHUD(dt)
    -- Individual widget scaling driven by native window dimensions
    local curW = (ui and ui.windowWidth and ui.windowWidth()) or BASE_WIDTH
    local curH = (ui and ui.windowHeight and ui.windowHeight()) or BASE_HEIGHT
    local s = math.max(0.35, math.min(curW / BASE_WIDTH, curH / BASE_HEIGHT))

    renderTimerContent(vec2(8 * s, 6 * s), s)
end
