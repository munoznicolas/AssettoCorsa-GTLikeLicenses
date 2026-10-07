--[[
    Gran Turismo Speedometer App Window Screen
    Handles script.speedoHUD(dt) callback for the movable AC Lua App.
]]

local Theme       = require("screens/theme")
local SharedState = require("screens/shared_state")

local BASE_WIDTH  = 220
local BASE_HEIGHT = 75

local function formatGear(gear)
    if not gear or gear == 0 then return "N" end
    if gear < 0 then return "R" end
    return tostring(gear)
end

local function renderSpeedoContent(origin, scale)
    local state = SharedState.get()
    local s = scale or 1.0
    local ox = origin.x
    local oy = origin.y

    local speed = state.speedKmh or 0.0
    local speedStr = string.format("%d", math.floor(speed + 0.5))

    -- Speed Number (large GT7 timing font)
    Theme.drawTimingText(speedStr, math.floor(44 * s), vec2(ox, oy), Theme.COLORS.WHITE)

    -- Unit (always KM/H) and Gear
    Theme.drawGTText("KM/H", math.floor(13 * s), vec2(ox + 95 * s, oy + 8 * s), Theme.COLORS.GREY_TEXT, "Regular")
    Theme.drawGTText(string.format("GEAR %s", formatGear(state.gear)), math.floor(15 * s), vec2(ox + 95 * s, oy + 26 * s), Theme.COLORS.WHITE, "Bold")
end

function script.speedoHUD(dt)
    -- Individual widget scaling driven by native window dimensions
    local curW = (ui and ui.windowWidth and ui.windowWidth()) or BASE_WIDTH
    local curH = (ui and ui.windowHeight and ui.windowHeight()) or BASE_HEIGHT
    local s = math.max(0.35, math.min(curW / BASE_WIDTH, curH / BASE_HEIGHT))

    renderSpeedoContent(vec2(8 * s, 6 * s), s)
end
