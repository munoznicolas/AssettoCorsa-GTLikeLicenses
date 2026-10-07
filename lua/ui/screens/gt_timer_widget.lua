--[[
    Gran Turismo Stopwatch & Live Target Delta Widget
    Renders high-precision digital lap timer and real-time medal delta comparisons.
    Supports both fixed-screen placement and draggable AC Lua App window rendering.
]]

local Theme = require("ui/common/gt_ui_theme")

local GTTimerWidget = {}

--- Format delta string for medal targets
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

--- Render Stopwatch & Delta in Fixed Screen Coordinates (Default GT7 layout)
--- @param screenW number Screen width
--- @param sessionTime number Elapsed session time in seconds
--- @param targets table Targets table { gold_seconds, silver_seconds, bronze_seconds }
--- @param currentState integer State enum (2 = RUNNING)
function GTTimerWidget.drawFixed(screenW, sessionTime, targets, currentState)
    local posX = screenW - 270
    local posY = 88

    -- Header label: "TIME"
    Theme.drawGTText("TIME", 13, vec2(posX, posY), Theme.COLORS.WHITE, "Regular")

    -- Digital Clock Display (Official GT7 Paired Outline & Digit Font)
    local timeText = Theme.formatTime(sessionTime)
    Theme.drawTimingText(timeText, 40, vec2(posX, posY + 16), Theme.COLORS.WHITE)

    -- Live Medal Target Delta
    local deltaText = getDeltaText(sessionTime, targets, currentState)
    if deltaText then
        Theme.drawGTText(deltaText, 17, vec2(posX, posY + 66), Theme.COLORS.WHITE, "Regular")
    end
end

--- Render Stopwatch & Delta relative to an AC UI App Window (Movable Mode)
--- @param sessionTime number Elapsed session time
--- @param targets table Targets table
--- @param currentState integer State enum
--- @param scaleVal number? Optional scaling multiplier
function GTTimerWidget.drawWindow(sessionTime, targets, currentState, scaleVal)
    local s = scaleVal or 1.0
    local originX = 10 * s
    local originY = 5 * s

    -- Header label: "TIME"
    Theme.drawGTText("TIME", math.floor(13 * s), vec2(originX, originY), Theme.COLORS.WHITE, "Regular")

    -- Digital Clock Display
    local timeText = Theme.formatTime(sessionTime)
    Theme.drawTimingText(timeText, math.floor(40 * s), vec2(originX, originY + 16 * s), Theme.COLORS.WHITE)

    -- Live Medal Target Delta
    local deltaText = getDeltaText(sessionTime, targets, currentState)
    if deltaText then
        Theme.drawGTText(deltaText, math.floor(17 * s), vec2(originX, originY + 66 * s), Theme.COLORS.WHITE, "Regular")
    end
end

return GTTimerWidget

