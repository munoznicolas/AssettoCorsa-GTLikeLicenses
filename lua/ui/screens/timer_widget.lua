--[[
    Gran Turismo Stopwatch & Live Target Delta Widget
    Renders high-precision digital lap timer and real-time medal delta comparisons.
    Supports both fixed-screen placement and draggable AC Lua App window rendering.
]]

local Theme = require("ui/common/ui_theme")

local GTTimerWidget = {}

--- Render Stopwatch in Fixed Screen Coordinates (Default GT7 layout)
--- @param screenW number Screen width
--- @param sessionTime number Elapsed session time in seconds
--- @param targets table? Targets table { gold_seconds, silver_seconds, bronze_seconds }
--- @param currentState integer? State enum (1=COUNTDOWN, 2=RUNNING, 3=PASSED, 4=FAILED)
function GTTimerWidget.drawFixed(screenW, sessionTime, targets, currentState)
    local posX = screenW - 280
    local posY = 88

    -- Header label: "TIME"
    Theme.drawGTText("TIME", 12, vec2(posX, posY), Theme.COLORS.WHITE, "Regular")

    -- Digital Clock Display: 34px font size ensures full 0'00.000 (254px) fits within 280px margin
    local timeText = Theme.formatTime(sessionTime)
    local clockCol = (currentState == 4) and Theme.COLORS.FAIL_RED or Theme.COLORS.WHITE
    Theme.drawTimingText(timeText, 34, vec2(posX, posY + 16), clockCol)

    -- Dynamic Target Display: live target threshold indicator beneath clock if targets provided
    if currentState and currentState > 0 then
        local targetLabel, targetCol = Theme.getTargetDisplay(sessionTime, targets)
        if targetLabel then
            Theme.drawGTText(targetLabel, 11, vec2(posX, posY + 54), targetCol, "Regular")
        end
    end
end

--- Render Stopwatch relative to an AC UI App Window (Movable Mode)
--- @param sessionTime number Elapsed session time
--- @param targets table? Targets table
--- @param currentState integer? State enum
--- @param scaleVal number? Optional scaling multiplier
function GTTimerWidget.drawWindow(sessionTime, targets, currentState, scaleVal)
    local s = scaleVal or 1.0
    local originX = 8 * s
    local originY = 8 * s

    local labelSize = math.max(10, math.floor(12 * s))
    local timingSize = math.max(16, math.floor(34 * s))
    local targetSize = math.max(9, math.floor(11 * s))
    local gap = math.max(3, math.floor(timingSize * 0.1))

    -- Header label: "TIME"
    Theme.drawGTText("TIME", labelSize, vec2(originX, originY), Theme.COLORS.WHITE, "Regular")

    -- Digital Clock Display
    local timeText = Theme.formatTime(sessionTime)
    local clockCol = (currentState == 4) and Theme.COLORS.FAIL_RED or Theme.COLORS.WHITE
    Theme.drawTimingText(timeText, timingSize, vec2(originX, originY + labelSize + gap), clockCol)

    -- Dynamic Target Display
    if currentState and currentState > 0 then
        local targetLabel, targetCol = Theme.getTargetDisplay(sessionTime, targets)
        if targetLabel then
            local targetY = originY + labelSize + gap + timingSize + gap
            Theme.drawGTText(targetLabel, targetSize, vec2(originX, targetY), targetCol, "Regular")
        end
    end
end

return GTTimerWidget

