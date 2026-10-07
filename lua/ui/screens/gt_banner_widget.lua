--[[
    Gran Turismo Top Test Banner Widget
    Renders test code, test title, lesson objective, and medal target thresholds.
    Supports both fixed-screen placement and draggable AC Lua App window rendering.
]]

local Theme = require("ui/common/gt_ui_theme")

local GTBannerWidget = {}

--- Helper to draw the vertically aligned medal targets stack
local function drawMedalTargets(rightPad, medalBlockX, startY, rowH, targets, s)
    s = s or 1.0
    local medals = {
        { label = "GOLD",   time = targets.gold_seconds,   col = Theme.COLORS.GOLD },
        { label = "SILVER", time = targets.silver_seconds, col = Theme.COLORS.SILVER },
        { label = "BRONZE", time = targets.bronze_seconds, col = Theme.COLORS.BRONZE },
    }

    local hEnd = (ui and ui.Alignment and ui.Alignment.End) or 1
    local vCenter = (ui and ui.Alignment and ui.Alignment.Center) or 0

    for i, m in ipairs(medals) do
        local rowY = startY + (i - 1) * rowH

        -- Medal indicator dot
        if ui and ui.drawCircleFilled then
            ui.drawCircleFilled(vec2(medalBlockX + 5 * s, rowY + 9 * s), 3.5 * s, m.col)
        end

        -- Medal Label (GT7 Clean Typography)
        Theme.drawGTText(m.label, math.floor(12 * s), vec2(medalBlockX + 16 * s, rowY + 2 * s), Theme.COLORS.WHITE, "Regular")

        -- Medal Time (GT7 Timing Font: Vertically aligned flush right)
        local timeStr = m.time and Theme.formatTime(m.time) or "--'--.---"
        local pMin = vec2(medalBlockX + 65 * s, rowY)
        local pMax = vec2(rightPad, rowY + 18 * s)
        Theme.drawTimingTextClipped(timeStr, math.floor(17 * s), pMin, pMax, hEnd, vCenter, Theme.COLORS.WHITE)
    end
end

--- Render Top Header Banner in Fixed Screen Coordinates (Default GT7 layout)
--- @param screenW number Screen width
--- @param config table Test configuration table
--- @param targets table Targets table { gold_seconds, silver_seconds, bronze_seconds }
function GTBannerWidget.drawFixed(screenW, config, targets)
    local bannerW = math.min(screenW - 80, 1600)
    local bannerX = (screenW - bannerW) * 0.5

    -- Left: Test ID and Lesson Title
    local testCode = (config and config.test_id) or "TEST"
    local titleText = (config and config.title) or "License Examination"
    local headerText = string.format("%s   %s", testCode, titleText)

    Theme.drawGTText(headerText, 22, vec2(bannerX, 18), Theme.COLORS.WHITE, "Regular")

    if config and config.lesson_objective and config.lesson_objective ~= "" then
        Theme.drawGTText(config.lesson_objective, 14, vec2(bannerX, 44), Theme.COLORS.OFF_WHITE, "Regular")
    end

    -- Right: Target Medal Times
    if targets then
        local rightPad = bannerX + bannerW
        local medalBlockW = 195
        local medalBlockX = rightPad - medalBlockW
        drawMedalTargets(rightPad, medalBlockX, 16, 22, targets, 1.0)
    end
end

--- Render Top Header Banner relative to an AC UI App Window (Movable Mode)
--- @param config table Test configuration table
--- @param targets table Targets table
--- @param scaleVal number? Optional scaling multiplier
function GTBannerWidget.drawWindow(config, targets, scaleVal)
    local s = scaleVal or 1.0
    local originX = 10 * s
    local originY = 5 * s

    local testCode = (config and config.test_id) or "TEST"
    local titleText = (config and config.title) or "License Examination"
    local headerText = string.format("%s   %s", testCode, titleText)

    Theme.drawGTText(headerText, math.floor(20 * s), vec2(originX, originY), Theme.COLORS.WHITE, "Regular")

    if config and config.lesson_objective and config.lesson_objective ~= "" then
        Theme.drawGTText(config.lesson_objective, math.floor(13 * s), vec2(originX, originY + 26 * s), Theme.COLORS.OFF_WHITE, "Regular")
    end

    -- Right: Target Medal Times Stack
    if targets then
        local totalW = 820 * s
        local rightPad = originX + totalW
        local medalBlockW = 195 * s
        local medalBlockX = rightPad - medalBlockW
        drawMedalTargets(rightPad, medalBlockX, originY, 20 * s, targets, s)
    end
end

return GTBannerWidget

