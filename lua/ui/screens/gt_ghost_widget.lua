--[[
    Gran Turismo Ghost & Pacer Delta Widget
    Renders live delta against Ghost/Pace Car and hotkey feedback OSD.
    Supports both fixed-screen placement and draggable AC Lua App window rendering.
]]

local Theme = require("ui/common/gt_ui_theme")

local GTGhostWidget = {}

local function formatGhostText(ghostState)
    local delta = (ghostState and ghostState.delta) or 0.0
    local prefix = delta >= 0 and "+" or "-"
    local absD = math.abs(delta)
    local deltaStr = string.format("%s%.2fs", prefix, absD)
    local modeName = (ghostState and ghostState.mode == 2) and "PACER" or "GOLD"
    return string.format("GHOST [%s]: %s", modeName, deltaStr)
end

--- Render Ghost Delta in Fixed Screen Coordinates (Default GT7 layout)
--- @param screenW number Screen width
--- @param ghostState table Ghost state table { active, delta, mode, osd_message }
function GTGhostWidget.drawFixedDelta(screenW, ghostState)
    if not ghostState or not ghostState.active then return end
    local posX = screenW - 270
    local posY = 182
    local label = formatGhostText(ghostState)
    Theme.drawGTText(label, 14, vec2(posX, posY), Theme.COLORS.WHITE, "Regular")
end

--- Render Ghost Hotkey OSD notification in Fixed Coordinates
--- @param screenW number Screen width
--- @param screenH number Screen height
--- @param ghostState table Ghost state table
function GTGhostWidget.drawFixedOSD(screenW, screenH, ghostState)
    if not ghostState or not ghostState.osd_message then return end
    local bannerW = 420
    local bannerH = 36
    local p1 = vec2((screenW - bannerW) * 0.5, screenH - 120)
    local p2 = p1 + vec2(bannerW, bannerH)

    local hAlign = (ui and ui.Alignment and ui.Alignment.Center) or 0
    local vAlign = (ui and ui.Alignment and ui.Alignment.Center) or 0
    Theme.drawGTTextClipped(ghostState.osd_message, 16, p1, p2, hAlign, vAlign, Theme.COLORS.WHITE, "Regular")
end

--- Render Ghost Delta relative to an AC UI App Window (Movable Mode)
--- @param ghostState table Ghost state table
--- @param scaleVal number? Optional scaling multiplier
function GTGhostWidget.drawWindow(ghostState, scaleVal)
    local s = scaleVal or 1.0
    local originX = 10 * s
    local originY = 5 * s

    local label = (ghostState and ghostState.active) and formatGhostText(ghostState) or "GHOST: OFF [G to toggle]"
    Theme.drawGTText(label, math.floor(14 * s), vec2(originX, originY), Theme.COLORS.WHITE, "Regular")

    if ghostState and ghostState.osd_message and ghostState.osd_message ~= "" then
        Theme.drawGTText(ghostState.osd_message, math.floor(12 * s), vec2(originX, originY + 24 * s), Theme.COLORS.OFF_WHITE, "Regular")
    end
end

return GTGhostWidget

