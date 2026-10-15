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
    local sessionTime = state.sessionTime or 0.0
    local targets = state.targets
    local currentState = state.currentState or 2

    -- Guaranteed edge padding to prevent window clipping boundaries from slicing font ascenders/outlines
    local padX = math.max(6, math.floor(curW * 0.03))
    local padY = math.max(4, math.floor(curH * 0.06))

    local availW = math.max(60, curW - (padX * 2))
    local availH = math.max(25, curH - (padY * 2))

    -- Text 0'00.000 is ~7.46x fontSize wide in MyTimingFont. Margin 7.8x prevents right-edge clipping.
    -- Total vertical stack with target label is header (0.32x) + gap (0.08x) + clock (1.0x) + gap (0.08x) + target (0.32x) = ~1.80x.
    local sizeByWidth  = availW / 7.8
    local sizeByHeight = availH / 1.80

    local timingFontSize = math.floor(math.min(sizeByWidth, sizeByHeight))
    timingFontSize = math.max(14, math.min(timingFontSize, 60))

    -- Header label "TIME" and target font sizing
    local labelFontSize  = math.max(9, math.min(16, math.floor(timingFontSize * 0.32)))
    local targetFontSize = math.max(9, math.min(16, math.floor(timingFontSize * 0.32)))
    local gap = math.max(2, math.floor(timingFontSize * 0.08))

    local labelY  = padY
    local clockY  = labelY + labelFontSize + gap
    local targetY = clockY + timingFontSize + gap

    -- Header label: "TIME"
    Theme.drawGTText("TIME", labelFontSize, vec2(padX, labelY), Theme.COLORS.WHITE, "Regular")

    -- Digital Clock Display: red if disqualified (state 4), white otherwise
    local timeText = Theme.formatTime(sessionTime)
    local clockCol = (currentState == 4) and Theme.COLORS.FAIL_RED or Theme.COLORS.WHITE
    Theme.drawTimingText(timeText, timingFontSize, vec2(padX, clockY), clockCol)

    -- Dynamic Target Display: live achievable medal threshold indicator
    if currentState and currentState > 0 then
        local targetLabel, targetCol = Theme.getTargetDisplay(sessionTime, targets)
        if targetLabel then
            Theme.drawGTText(targetLabel, targetFontSize, vec2(padX, targetY), targetCol, "Regular")
        end
    end
end

function script.timerHUD(dt)
    -- Individual widget scaling driven by native window dimensions
    local curW = (ui and ui.windowWidth and ui.windowWidth()) or BASE_WIDTH
    local curH = (ui and ui.windowHeight and ui.windowHeight()) or BASE_HEIGHT

    renderTimerContent(curW, curH)
end
