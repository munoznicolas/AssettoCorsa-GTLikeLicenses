--[[
    Gran Turismo Ghost & Pacer Delta App Window Screen
    Handles script.ghostHUD(dt) callback for the movable AC Lua App.
]]

local Theme       = require("screens/theme")
local SharedState = require("screens/shared_state")

local BASE_WIDTH  = 260
local BASE_HEIGHT = 50

local function formatGhostText(ghostState)
    local delta = (ghostState and ghostState.delta) or 0.0
    local prefix = delta >= 0 and "+" or "-"
    local absD = math.abs(delta)
    local deltaStr = string.format("%s%.2fs", prefix, absD)
    local modeName = (ghostState and ghostState.mode == 2) and "PACER" or "GOLD"
    return string.format("GHOST [%s]: %s", modeName, deltaStr)
end

local function renderGhostContent(origin, scale)
    local state = SharedState.get()
    local s = scale or 1.0
    local ox = origin.x
    local oy = origin.y

    local ghostState = state.ghostState
    local label = (ghostState and ghostState.active) and formatGhostText(ghostState) or "GHOST: OFF [G to toggle]"
    Theme.drawGTText(label, math.floor(14 * s), vec2(ox, oy), Theme.COLORS.WHITE, "Regular")

    if ghostState and ghostState.osd_message and ghostState.osd_message ~= "" then
        Theme.drawGTText(ghostState.osd_message, math.floor(12 * s), vec2(ox, oy + 24 * s), Theme.COLORS.OFF_WHITE, "Regular")
    end
end

function script.ghostHUD(dt)
    -- Individual widget scaling driven by native window dimensions
    local curW = (ui and ui.windowWidth and ui.windowWidth()) or BASE_WIDTH
    local curH = (ui and ui.windowHeight and ui.windowHeight()) or BASE_HEIGHT
    local s = math.max(0.35, math.min(curW / BASE_WIDTH, curH / BASE_HEIGHT))

    renderGhostContent(vec2(8 * s, 6 * s), s)
end
