--[[
    Gran Turismo Top Test Banner App Window Screen
    Handles script.bannerHUD(dt) callback for the movable AC Lua App.
]]

local Theme       = require("screens/theme")
local SharedState = require("screens/shared_state")

local BASE_WIDTH  = 860
local BASE_HEIGHT = 75

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

        -- Medal Label
        Theme.drawGTText(m.label, math.floor(12 * s), vec2(medalBlockX + 16 * s, rowY + 2 * s), Theme.COLORS.WHITE, "Regular")

        -- Medal Time
        local timeStr = m.time and Theme.formatTime(m.time) or "--'--.---"
        local pMin = vec2(medalBlockX + 65 * s, rowY)
        local pMax = vec2(rightPad, rowY + 18 * s)
        Theme.drawTimingTextClipped(timeStr, math.floor(17 * s), pMin, pMax, hEnd, vCenter, Theme.COLORS.WHITE)
    end
end

local function renderBannerContent(origin, scale, bannerWidth)
    local state = SharedState.get()
    local s = scale or 1.0
    local ox = origin.x
    local oy = origin.y
    local bw = bannerWidth or (820 * s)

    local testCode = state.testId or "TEST"
    local titleText = state.testTitle or "License Examination"
    local headerText = string.format("%s   %s", testCode, titleText)

    Theme.drawGTText(headerText, math.floor(20 * s), vec2(ox, oy), Theme.COLORS.WHITE, "Regular")

    if state.lessonObjective and state.lessonObjective ~= "" then
        Theme.drawGTText(state.lessonObjective, math.floor(13 * s), vec2(ox, oy + 26 * s), Theme.COLORS.OFF_WHITE, "Regular")
    end

    if state.targets then
        local rightPad = ox + bw
        local medalBlockW = 195 * s
        local medalBlockX = rightPad - medalBlockW
        drawMedalTargets(rightPad, medalBlockX, oy, 20 * s, state.targets, s)
    end
end

function script.bannerHUD(dt)
    -- Individual widget scaling driven by native window dimensions
    local curW = (ui and ui.windowWidth and ui.windowWidth()) or BASE_WIDTH
    local curH = (ui and ui.windowHeight and ui.windowHeight()) or BASE_HEIGHT
    local s = math.max(0.35, math.min(curW / BASE_WIDTH, curH / BASE_HEIGHT))
    local bannerW = math.max(300 * s, curW - (16 * s))

    renderBannerContent(vec2(8 * s, 6 * s), s, bannerW)
end
