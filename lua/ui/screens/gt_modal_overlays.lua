--[[
    Gran Turismo Fullscreen Modal Overlays Subsystem
    Renders event overlays:
    1. 3-2-1-START! animated countdown
    2. Deep crimson DISQUALIFIED banner with interactive Retry button
    3. Celebratory Results Screen with medal awards card and action buttons
]]

local Theme = require("ui/common/gt_ui_theme")

local GTModalOverlays = {}

--------------------------------------------------------------------------------
-- 1. CENTER COUNTDOWN (3 - 2 - 1 - START!)
--------------------------------------------------------------------------------
function GTModalOverlays.drawCountdown(screenW, screenH, timer, isGo)
    local centerX = screenW * 0.5
    local centerY = screenH * 0.42

    local displayText = ""
    local isText = false
    if isGo then
        displayText = "START!"
        isText = true
    elseif timer > 2.0 then
        displayText = "3"
    elseif timer > 1.0 then
        displayText = "2"
    elseif timer > 0.0 then
        displayText = "1"
    end

    if displayText == "" then return end

    local glowW = isGo and 400 or 240
    local glowH = 120
    local p1 = vec2(centerX - glowW * 0.5, centerY - glowH * 0.5)
    local p2 = vec2(centerX + glowW * 0.5, centerY + glowH * 0.5)

    local hAlign = (ui and ui.Alignment and ui.Alignment.Center) or 0
    local vAlign = (ui and ui.Alignment and ui.Alignment.Center) or 0

    if isText then
        Theme.drawGTTextClipped(displayText, 64, p1, p2, hAlign, vAlign, Theme.COLORS.WHITE, "Regular")
    else
        Theme.drawTimingTextClipped(displayText, 76, p1, p2, hAlign, vAlign, Theme.COLORS.WHITE, 1.0)
    end
end

--------------------------------------------------------------------------------
-- 2. PROMINENT RED 'DISQUALIFIED' BANNER
--------------------------------------------------------------------------------
function GTModalOverlays.drawDisqualifiedBanner(screenW, screenH, failReason, callbacks, animTimer)
    local bannerH = 180
    local p1 = vec2(0, (screenH - bannerH) * 0.45)
    local p2 = vec2(screenW, p1.y + bannerH)

    -- Full-width deep crimson backdrop with dark shadows
    if ui and ui.drawRectFilled then
        ui.drawRectFilled(p1, p2, Theme.COLORS.FAIL_BG, 0)

        -- Hazard warning border lines top and bottom
        local pulse = 0.5 + 0.5 * math.sin((animTimer or 0) * 6.0)
        local borderCol = rgbm(1.0, 0.2 + 0.3 * pulse, 0.2, 1.0)
        ui.drawRectFilled(p1, vec2(screenW, p1.y + 6), borderCol, 0)
        ui.drawRectFilled(vec2(0, p2.y - 6), p2, borderCol, 0)
    end

    local hAlign = (ui and ui.Alignment and ui.Alignment.Center) or 0
    local vAlign = (ui and ui.Alignment and ui.Alignment.Center) or 0

    -- Primary Warning Title
    Theme.drawGTTextClipped("DISQUALIFIED", 32, p1 + vec2(0, 16), vec2(screenW, p1.y + 64), hAlign, vAlign, Theme.COLORS.WHITE, "Regular")

    -- Failure Reason Subtitle
    local reasonText = string.upper(failReason or "FAILED CRITERIA")
    Theme.drawGTTextClipped(reasonText, 17, p1 + vec2(0, 68), vec2(screenW, p1.y + 104), hAlign, vAlign, Theme.COLORS.OFF_WHITE, "Regular")

    -- Interactive Retry Button
    local btnW = 200
    local btnH = 36
    local btnX = (screenW - btnW) * 0.5
    local btnY = p1.y + 110
    local btnP1 = vec2(btnX, btnY)
    local btnP2 = btnP1 + vec2(btnW, btnH)

    -- Click Detection for interactive mouse control
    local uiState = ac and ac.getUI and ac.getUI()
    local isHovered = false
    if uiState and uiState.mousePos then
        local mPos = uiState.mousePos
        if mPos.x >= btnP1.x and mPos.x <= btnP2.x and mPos.y >= btnP1.y and mPos.y <= btnP2.y then
            isHovered = true
            if uiState.isMouseLeftKeyClicked and callbacks and callbacks.onRestart then
                callbacks.onRestart()
            end
        end
    end

    if ui and ui.drawRectFilled then
        local btnBg = isHovered and rgbm(0.35, 0.10, 0.10, 0.95) or rgbm(0.20, 0.06, 0.06, 0.85)
        local btnBorder = isHovered and rgbm(1.0, 0.4, 0.4, 1.0) or Theme.COLORS.BORDER_GREY
        ui.drawRectFilled(btnP1, btnP2, btnBg, 4)
        if ui.drawRect and ui.CornerFlags then
            ui.drawRect(btnP1, btnP2, btnBorder, 4, ui.CornerFlags.All, 1.2)
        end
    end

    Theme.drawGTTextClipped("RETRY  (R)", 15, btnP1, btnP2, hAlign, vAlign, Theme.COLORS.WHITE, "Regular")

    -- Prompt to Retry via Hotkey / Gamepad
    Theme.drawGTTextClipped("PRESS  [ R ],  [ ENTER ],  [ SPACE ]  OR  CLICK  TO  RETRY", 13, p1 + vec2(0, 152), vec2(screenW, p1.y + 174), hAlign, vAlign, Theme.COLORS.OFF_WHITE, "Regular")
end

--------------------------------------------------------------------------------
-- 3. CELEBRATORY RESULTS SCREEN
--------------------------------------------------------------------------------
function GTModalOverlays.drawResultsScreen(screenW, screenH, finalTime, targets, medalAchieved, callbacks)
    local cardW = 620
    local cardH = 460
    local p1 = vec2((screenW - cardW) * 0.5, (screenH - cardH) * 0.45)
    local p2 = p1 + vec2(cardW, cardH)

    -- Translucent Dark Glass Card
    if ui and ui.drawRectFilled then
        ui.drawRectFilled(p1, p2, Theme.COLORS.BG_CARD, 12)
        if ui.drawRect and ui.CornerFlags then
            ui.drawRect(p1, p2, Theme.COLORS.BORDER_GREY, 12, ui.CornerFlags.All, 1.5)
        end
    end

    -- Top Header Ribbon
    local ribbonP1 = p1
    local ribbonP2 = p1 + vec2(cardW, 70)
    local medal = medalAchieved or "bronze"

    local headerCol = Theme.COLORS.BRONZE
    local medalTitle = "BRONZE MEDAL"
    if medal == "gold" then
        headerCol = Theme.COLORS.GOLD
        medalTitle = "★ GOLD MEDAL AWARDED ★"
    elseif medal == "silver" then
        headerCol = Theme.COLORS.SILVER
        medalTitle = "★ SILVER MEDAL AWARDED ★"
    elseif medal == "bronze" then
        headerCol = Theme.COLORS.BRONZE
        medalTitle = "★ BRONZE MEDAL AWARDED ★"
    else
        headerCol = Theme.COLORS.WHITE
        medalTitle = "TEST COMPLETED"
    end

    if ui and ui.drawRectFilled and ui.CornerFlags then
        ui.drawRectFilled(ribbonP1, ribbonP2, rgbm(headerCol.r * 0.25, headerCol.g * 0.25, headerCol.b * 0.25, 0.95), 12, ui.CornerFlags.Top)
        ui.drawRectFilled(vec2(ribbonP1.x, ribbonP2.y - 3), ribbonP2, headerCol, 0)
    end

    local hCenter = (ui and ui.Alignment and ui.Alignment.Center) or 0
    local vCenter = (ui and ui.Alignment and ui.Alignment.Center) or 0
    local hEnd = (ui and ui.Alignment and ui.Alignment.End) or 1

    Theme.drawGTTextClipped(medalTitle, 22, ribbonP1, ribbonP2, hCenter, vCenter, Theme.COLORS.WHITE, "Regular")

    -- Final Recorded Time Box
    local timeBoxP1 = p1 + vec2(30, 88)
    local timeBoxP2 = p1 + vec2(cardW - 30, 160)
    if ui and ui.drawRectFilled then
        ui.drawRectFilled(timeBoxP1, timeBoxP2, rgbm(0, 0, 0, 0.5), 6)
    end

    Theme.drawGTText("RECORDED TIME", 13, timeBoxP1 + vec2(16, 10), Theme.COLORS.WHITE, "Regular")
    Theme.drawTimingTextClipped(Theme.formatTime(finalTime), 46, timeBoxP1, timeBoxP2, hCenter, vCenter, Theme.COLORS.WHITE)

    -- Target Times Breakdown Table
    if targets then
        local tableY = p1.y + 175
        local rows = {
            { name = "Gold Target",   target = targets.gold_seconds,   col = Theme.COLORS.GOLD },
            { name = "Silver Target", target = targets.silver_seconds, col = Theme.COLORS.SILVER },
            { name = "Bronze Target", target = targets.bronze_seconds, col = Theme.COLORS.BRONZE },
        }

        for i, row in ipairs(rows) do
            local rowY = tableY + (i - 1) * 36
            local rP1 = vec2(p1.x + 30, rowY)
            local rP2 = vec2(p1.x + cardW - 30, rowY + 30)

            if ui and ui.drawRectFilled then
                ui.drawRectFilled(rP1, rP2, rgbm(0.1, 0.1, 0.1, 0.5), 4)
                if ui.drawCircleFilled then
                    ui.drawCircleFilled(rP1 + vec2(14, 15), 5, row.col)
                end
            end

            Theme.drawGTText(row.name, 14, rP1 + vec2(28, 6), Theme.COLORS.WHITE, "Regular")

            local targetStr = row.target and Theme.formatTime(row.target) or "--'--.---"
            Theme.drawTimingTextClipped(targetStr, 18, rP1, rP2 - vec2(100, 0), hEnd, vCenter, Theme.COLORS.WHITE)

            if row.target and finalTime then
                local delta = finalTime - row.target
                local deltaStr = Theme.formatDelta(delta)
                local dCol = delta <= 0 and Theme.COLORS.SUCCESS_GREEN or Theme.COLORS.FAIL_RED
                Theme.drawGTTextClipped(deltaStr, 15, rP1, rP2 - vec2(14, 0), hEnd, vCenter, dCol, "Regular")
            end
        end
    end

    -- Action Buttons (Restart, Exit)
    local btnW = 180
    local btnH = 40
    local btnY = p1.y + cardH - 60
    local btnSpacing = 30
    local totalBtnsW = (btnW * 2) + btnSpacing
    local startBtnX = p1.x + (cardW - totalBtnsW) * 0.5

    -- Restart Button
    local b1P1 = vec2(startBtnX, btnY)
    local b1P2 = b1P1 + vec2(btnW, btnH)

    -- Exit Button
    local b2P1 = vec2(startBtnX + btnW + btnSpacing, btnY)
    local b2P2 = b2P1 + vec2(btnW, btnH)

    -- Mouse Hover Detection
    local uiState = ac and ac.getUI and ac.getUI()
    local mPos = uiState and uiState.mousePos
    local isB1Hovered = mPos and (mPos.x >= b1P1.x and mPos.x <= b1P2.x and mPos.y >= b1P1.y and mPos.y <= b1P2.y)
    local isB2Hovered = mPos and (mPos.x >= b2P1.x and mPos.x <= b2P2.x and mPos.y >= b2P1.y and mPos.y <= b2P2.y)

    if ui and ui.drawRectFilled and ui.CornerFlags then
        local b1Bg = isB1Hovered and rgbm(0.28, 0.28, 0.28, 0.95) or rgbm(0.18, 0.18, 0.18, 0.8)
        local b1Border = isB1Hovered and rgbm(0.9, 0.9, 0.9, 1.0) or Theme.COLORS.BORDER_GREY
        ui.drawRectFilled(b1P1, b1P2, b1Bg, 4)
        ui.drawRect(b1P1, b1P2, b1Border, 4, ui.CornerFlags.All, 1)

        local b2Bg = isB2Hovered and rgbm(0.25, 0.25, 0.25, 0.95) or rgbm(0.15, 0.15, 0.15, 0.8)
        local b2Border = isB2Hovered and rgbm(0.9, 0.9, 0.9, 1.0) or Theme.COLORS.BORDER_GREY
        ui.drawRectFilled(b2P1, b2P2, b2Bg, 4)
        ui.drawRect(b2P1, b2P2, b2Border, 4, ui.CornerFlags.All, 1)
    end

    Theme.drawGTTextClipped("RESTART (R)", 14, b1P1, b1P2, hCenter, vCenter, Theme.COLORS.WHITE, "Regular")
    Theme.drawGTTextClipped("EXIT (ESC)", 14, b2P1, b2P2, hCenter, vCenter, Theme.COLORS.WHITE, "Regular")

    -- Click Detection for interactive mouse control
    if uiState and uiState.isMouseLeftKeyClicked and callbacks then
        if isB1Hovered and callbacks.onRestart then
            callbacks.onRestart()
        elseif isB2Hovered and callbacks.onExit then
            callbacks.onExit()
        end
    end
end

return GTModalOverlays

