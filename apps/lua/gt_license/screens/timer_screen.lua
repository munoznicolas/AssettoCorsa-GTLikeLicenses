--[[
    Gran Turismo Timer & Target Delta App Window Screen
    Handles script.timerHUD(dt) callback for the movable AC Lua App.
]]

local Theme       = require("screens/theme")
local SharedState = require("screens/shared_state")

local BASE_WIDTH  = 280
local BASE_HEIGHT = 75

local function renderTimerContent(curW, curH)
    local state = SharedState.get()

    -- Guaranteed edge padding to prevent window clipping boundaries from slicing font ascenders/outlines
    local padX = math.max(8, math.floor(curW * 0.04))
    local padY = math.max(10, math.floor(curH * 0.12))

    local availW = math.max(60, curW - (padX * 2))
    local availH = math.max(25, curH - (padY * 2))

    -- Text 0'00.000 is ~7.46x fontSize wide in MyTimingFont. Margin 7.8x prevents right-edge clipping.
    -- Total vertical stack is label (0.32x) + gap (0.10x) + clock (1.0x) = ~1.42x. Divisor 1.45 guarantees no vertical clipping.
    local sizeByWidth  = availW / 7.8
    local sizeByHeight = availH / 1.45

    local timingFontSize = math.floor(math.min(sizeByWidth, sizeByHeight))
    timingFontSize = math.max(16, math.min(timingFontSize, 60))

    -- Header label "TIME": guaranteed minimum 10px with safe top clearance
    local labelFontSize = math.max(10, math.floor(timingFontSize * 0.32))
    labelFontSize = math.min(labelFontSize, 18)

    local gap = math.max(3, math.floor(timingFontSize * 0.10))

    -- Header label: "TIME"
    Theme.drawGTText("TIME", labelFontSize, vec2(padX, padY), Theme.COLORS.WHITE, "Regular")

    -- Digital Clock Display: positioned with guaranteed clearance below header
    local timeText = Theme.formatTime(state.sessionTime)
    local clockY = padY + labelFontSize + gap
    Theme.drawTimingText(timeText, timingFontSize, vec2(padX, clockY), Theme.COLORS.WHITE)
end

function script.timerHUD(dt)
    -- Individual widget scaling driven by native window dimensions
    local curW = (ui and ui.windowWidth and ui.windowWidth()) or BASE_WIDTH
    local curH = (ui and ui.windowHeight and ui.windowHeight()) or BASE_HEIGHT

    renderTimerContent(curW, curH)
end
