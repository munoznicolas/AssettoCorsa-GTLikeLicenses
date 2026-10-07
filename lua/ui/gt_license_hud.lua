--[[
    Gran Turismo-style Vector Canvas HUD for Assetto Corsa Licenses Mod
    Renders responsive, resolution-independent vector UI using CSP's DirectWrite (DWrite) & ui.* API.
    
    Components:
    1. Top Banner: Test title, lesson objective, target medal times (Gold, Silver, Bronze)
    2. Real-Time Stopwatch: Classic GT7 typography (MyTimingFont & MyTimingFontOutline)
    3. Live Medal Target Delta: Real-time delta comparison against target thresholds
    4. Center Countdown: 3-2-1-GO animated countdown
    5. Prominent Disqualification Banner: Deep crimson banner with failure reason
    6. Celebratory Results Screen: Medal awarded card, target comparisons, and action controls
]]

local GTLicenseHUD = {}

-- State Enumeration
GTLicenseHUD.STATE = {
    PREPARE   = 0,
    COUNTDOWN = 1,
    RUNNING   = 2,
    PASSED    = 3,
    FAILED    = 4,
}

-- Color Palette (Gran Turismo aesthetic: White typography with black edges, neutral backdrop)
local COLORS = {
    BG_DARK       = rgbm(0.04, 0.04, 0.04, 0.85),
    BG_CARD       = rgbm(0.06, 0.06, 0.06, 0.94),
    WHITE         = rgbm(1.00, 1.00, 1.00, 1.00),
    BLACK         = rgbm(0.00, 0.00, 0.00, 1.00),
    OFF_WHITE     = rgbm(0.92, 0.92, 0.92, 0.95),
    GREY_TEXT     = rgbm(0.70, 0.70, 0.70, 0.85),
    BORDER_GREY   = rgbm(0.25, 0.25, 0.25, 0.60),

    -- Medal Colors (Accents for icons / indicators)
    GOLD          = rgbm(1.00, 0.84, 0.00, 1.00),
    GOLD_BG       = rgbm(0.35, 0.28, 0.02, 0.85),
    SILVER        = rgbm(0.85, 0.88, 0.92, 1.00),
    SILVER_BG     = rgbm(0.25, 0.27, 0.30, 0.85),
    BRONZE        = rgbm(0.80, 0.50, 0.20, 1.00),
    BRONZE_BG     = rgbm(0.30, 0.18, 0.08, 0.85),

    -- Status & Alerts
    FAIL_RED      = rgbm(0.90, 0.12, 0.12, 0.96),
    FAIL_BG       = rgbm(0.50, 0.05, 0.05, 0.92),
    SUCCESS_GREEN = rgbm(0.15, 0.90, 0.35, 1.00),
    WARN_AMBER    = rgbm(1.00, 0.70, 0.10, 1.00),
}

-- Local internal state
local currentConfig = nil
local countdownTimer = 3.0
local goDisplayTimer = 0.0
local animTimer = 0.0
local lastState = GTLicenseHUD.STATE.PREPARE
local cachedMedalAchieved = nil

-- Check if CSP DirectWrite font subsystem is available
local hasDWrite = (ui ~= nil and ui.pushDWriteFont ~= nil and ui.dwriteDrawText ~= nil)

--- Helper to format seconds into classic GT laptime format: M'SS.mmm
local function formatTime(seconds)
    if not seconds or seconds < 0 then seconds = 0 end
    local minutes = math.floor(seconds / 60)
    local remainder = seconds % 60
    local secs = math.floor(remainder)
    local millis = math.floor((remainder - secs) * 1000)
    return string.format("%d'%02d.%03d", minutes, secs, millis)
end

--- Helper to format delta times: +0.123 or -1.456
local function formatDelta(delta)
    local sign = delta >= 0 and "+" or "-"
    local absVal = math.abs(delta)
    local secs = math.floor(absVal)
    local millis = math.floor((absVal - secs) * 1000)
    return string.format("%s%d.%03d", sign, secs, millis)
end

--------------------------------------------------------------------------------
-- TYPOGRAPHY SUBSYSTEM: GT7 DirectWrite Paired Outlines & Weight Layering
--------------------------------------------------------------------------------

--- Fallback: 8-directional ImGui outline
local function drawTextOutlinedFallback(text, pos, textColor, outlineColor, thickness)
    if not text or text == "" then return end
    local col = textColor or COLORS.WHITE
    local oCol = outlineColor or COLORS.BLACK
    local t = thickness or 1.5

    ui.drawText(text, vec2(pos.x - t, pos.y), oCol)
    ui.drawText(text, vec2(pos.x + t, pos.y), oCol)
    ui.drawText(text, vec2(pos.x, pos.y - t), oCol)
    ui.drawText(text, vec2(pos.x, pos.y + t), oCol)
    ui.drawText(text, vec2(pos.x - t, pos.y - t), oCol)
    ui.drawText(text, vec2(pos.x + t, pos.y - t), oCol)
    ui.drawText(text, vec2(pos.x - t, pos.y + t), oCol)
    ui.drawText(text, vec2(pos.x + t, pos.y + t), oCol)
    ui.drawText(text, pos, col)
end

--- Fallback: 8-directional ImGui clipped outline
local function drawTextClippedOutlinedFallback(text, posMin, posMax, textColor, alignment, outlineColor, thickness)
    if not text or text == "" then return end
    local col = textColor or COLORS.WHITE
    local oCol = outlineColor or COLORS.BLACK
    local t = thickness or 1.5
    local align = alignment or vec2(0, 0)

    ui.drawTextClipped(text, posMin + vec2(-t, 0), posMax + vec2(-t, 0), oCol, align)
    ui.drawTextClipped(text, posMin + vec2(t, 0), posMax + vec2(t, 0), oCol, align)
    ui.drawTextClipped(text, posMin + vec2(0, -t), posMax + vec2(0, -t), oCol, align)
    ui.drawTextClipped(text, posMin + vec2(0, t), posMax + vec2(0, t), oCol, align)
    ui.drawTextClipped(text, posMin + vec2(-t, -t), posMax + vec2(-t, -t), oCol, align)
    ui.drawTextClipped(text, posMin + vec2(t, -t), posMax + vec2(t, -t), oCol, align)
    ui.drawTextClipped(text, posMin + vec2(-t, t), posMax + vec2(-t, t), oCol, align)
    ui.drawTextClipped(text, posMin + vec2(t, t), posMax + vec2(t, t), oCol, align)
    ui.drawTextClipped(text, posMin, posMax, col, align)
end

--- Draw GT7 digital timing text using paired MyTimingFontOutline + MyTimingFont
local function drawTimingText(text, fontSize, pos, textColor, outlineAlpha)
    if not text or text == "" then return end
    textColor = textColor or COLORS.WHITE
    outlineAlpha = outlineAlpha or 0.95

    if hasDWrite then
        -- 1. Black outline layer using MyTimingFontOutline
        ui.pushDWriteFont("MyTimingFontOutline:fonts")
        ui.dwriteDrawText(text, fontSize, pos, rgbm(0, 0, 0, outlineAlpha))
        ui.popDWriteFont()

        -- 2. Foreground timing layer using MyTimingFont
        ui.pushDWriteFont("MyTimingFont:fonts")
        ui.dwriteDrawText(text, fontSize, pos, textColor)
        ui.popDWriteFont()
    else
        ui.pushFont(ui.Font.Huge)
        drawTextOutlinedFallback(text, pos, textColor, COLORS.BLACK, 2.0)
        ui.popFont()
    end
end

--- Draw GT7 clipped digital timing text using paired MyTimingFontOutline + MyTimingFont
local function drawTimingTextClipped(text, fontSize, posMin, posMax, hAlign, vAlign, textColor, outlineAlpha)
    if not text or text == "" then return end
    textColor = textColor or COLORS.WHITE
    outlineAlpha = outlineAlpha or 0.95
    hAlign = hAlign or (ui.Alignment and ui.Alignment.Center or 0)
    vAlign = vAlign or (ui.Alignment and ui.Alignment.Center or 0)

    if hasDWrite then
        ui.pushDWriteFont("MyTimingFontOutline:fonts")
        ui.dwriteDrawTextClipped(text, fontSize, posMin, posMax, hAlign, vAlign, false, rgbm(0, 0, 0, outlineAlpha))
        ui.popDWriteFont()

        ui.pushDWriteFont("MyTimingFont:fonts")
        ui.dwriteDrawTextClipped(text, fontSize, posMin, posMax, hAlign, vAlign, false, textColor)
        ui.popDWriteFont()
    else
        ui.pushFont(ui.Font.Huge)
        local ax = (hAlign == 1) and 1.0 or ((hAlign == -1) and 0.0 or 0.5)
        local ay = (vAlign == 1) and 1.0 or ((vAlign == -1) and 0.0 or 0.5)
        drawTextClippedOutlinedFallback(text, posMin, posMax, textColor, vec2(ax, ay), COLORS.BLACK, 2.0)
        ui.popFont()
    end
end

--- Draw GT7 UI text (Titles, subtitles, labels) using clean white typography with crisp 1px black edges
local function drawGTText(text, fontSize, pos, textColor, weight)
    if not text or text == "" then return end
    textColor = textColor or COLORS.WHITE
    weight = weight or "Regular"

    if hasDWrite then
        -- Use matching weight for both outline and text to preserve exact glyph geometry and spacing
        ui.pushDWriteFont(string.format("MyFont:fonts;Weight=%s", weight))
        local outlineCol = rgbm(0, 0, 0, 0.85)
        ui.dwriteDrawText(text, fontSize, vec2(pos.x - 1, pos.y), outlineCol)
        ui.dwriteDrawText(text, fontSize, vec2(pos.x + 1, pos.y), outlineCol)
        ui.dwriteDrawText(text, fontSize, vec2(pos.x, pos.y - 1), outlineCol)
        ui.dwriteDrawText(text, fontSize, vec2(pos.x, pos.y + 1), outlineCol)
        ui.dwriteDrawText(text, fontSize, pos, textColor)
        ui.popDWriteFont()
    else
        ui.pushFont(ui.Font.Title)
        drawTextOutlinedFallback(text, pos, textColor, COLORS.BLACK, 1.2)
        ui.popFont()
    end
end

--- Draw GT7 clipped UI text using clean white typography with crisp 1px black edges
local function drawGTTextClipped(text, fontSize, posMin, posMax, hAlign, vAlign, textColor, weight)
    if not text or text == "" then return end
    textColor = textColor or COLORS.WHITE
    weight = weight or "Regular"
    hAlign = hAlign or (ui.Alignment and ui.Alignment.Center or 0)
    vAlign = vAlign or (ui.Alignment and ui.Alignment.Center or 0)

    if hasDWrite then
        ui.pushDWriteFont(string.format("MyFont:fonts;Weight=%s", weight))
        local outlineCol = rgbm(0, 0, 0, 0.85)
        ui.dwriteDrawTextClipped(text, fontSize, posMin + vec2(-1, 0), posMax + vec2(-1, 0), hAlign, vAlign, false, outlineCol)
        ui.dwriteDrawTextClipped(text, fontSize, posMin + vec2(1, 0), posMax + vec2(1, 0), hAlign, vAlign, false, outlineCol)
        ui.dwriteDrawTextClipped(text, fontSize, posMin + vec2(0, -1), posMax + vec2(0, -1), hAlign, vAlign, false, outlineCol)
        ui.dwriteDrawTextClipped(text, fontSize, posMin + vec2(0, 1), posMax + vec2(0, 1), hAlign, vAlign, false, outlineCol)
        ui.dwriteDrawTextClipped(text, fontSize, posMin, posMax, hAlign, vAlign, false, textColor)
        ui.popDWriteFont()
    else
        ui.pushFont(ui.Font.Main)
        local ax = (hAlign == 1) and 1.0 or ((hAlign == -1) and 0.0 or 0.5)
        local ay = (vAlign == 1) and 1.0 or ((vAlign == -1) and 0.0 or 0.5)
        drawTextClippedOutlinedFallback(text, posMin, posMax, textColor, vec2(ax, ay), COLORS.BLACK, 1.2)
        ui.popFont()
    end
end

--- Initialize HUD with active test configuration
--- @param testConfig table Test definition JSON
function GTLicenseHUD.init(testConfig)
    currentConfig = testConfig or {}
    GTLicenseHUD.reset()
end

--- Reset HUD timers and animation state
function GTLicenseHUD.reset()
    countdownTimer = 3.0
    goDisplayTimer = 0.0
    animTimer = 0.0
    cachedMedalAchieved = nil
end

--- Determine which medal a time achieved
--- @param time number Lap time in seconds
--- @param targets table { gold_seconds, silver_seconds, bronze_seconds }
--- @return string|nil 'gold'|'silver'|'bronze'|nil
function GTLicenseHUD.evaluateMedal(time, targets)
    if not targets or not time or time <= 0 then return nil end
    if targets.gold_seconds and time <= targets.gold_seconds then
        return "gold"
    elseif targets.silver_seconds and time <= targets.silver_seconds then
        return "silver"
    elseif targets.bronze_seconds and time <= targets.bronze_seconds then
        return "bronze"
    end
    return nil
end

--- Frame update for HUD timers and animations
--- @param dt number Delta time in seconds
--- @param currentState integer State from GTLicenseHUD.STATE
--- @param stateCountdownTimer number? External countdown timer from engine
function GTLicenseHUD.update(dt, currentState, stateCountdownTimer)
    animTimer = animTimer + (dt or 0.016)

    if currentState == GTLicenseHUD.STATE.COUNTDOWN then
        if stateCountdownTimer then
            countdownTimer = stateCountdownTimer
        else
            countdownTimer = math.max(0, countdownTimer - dt)
        end
    end

    -- Trigger "GO!" chime burst timer when transitioning from countdown to running
    if lastState == GTLicenseHUD.STATE.COUNTDOWN and currentState == GTLicenseHUD.STATE.RUNNING then
        goDisplayTimer = 0.85
    elseif goDisplayTimer > 0 then
        goDisplayTimer = math.max(0, goDisplayTimer - dt)
    end

    lastState = currentState
end

--------------------------------------------------------------------------------
-- 1. TOP HEADER BANNER (Clean floating GT7 typography, zero blue rectangles)
--------------------------------------------------------------------------------
local function drawTopBanner(screenW, config, targets)
    local bannerW = math.min(screenW - 80, 1600)
    local bannerX = (screenW - bannerW) * 0.5

    -- Left: Test ID and Lesson Title (Clean GT7 Typography)
    local testCode = config.test_id or "TEST"
    local titleText = config.title or "License Examination"
    local headerText = string.format("%s   %s", testCode, titleText)

    drawGTText(headerText, 22, vec2(bannerX, 18), COLORS.WHITE, "Regular")

    if config.lesson_objective and config.lesson_objective ~= "" then
        drawGTText(config.lesson_objective, 14, vec2(bannerX, 44), COLORS.OFF_WHITE, "Regular")
    end

    -- Right: Target Medal Times (Gold, Silver, Bronze - Vertically Aligned Stack)
    if targets then
        local rightPad = bannerX + bannerW
        local medalBlockW = 195
        local medalBlockX = rightPad - medalBlockW
        local startY = 16
        local rowH = 22

        local medals = {
            { label = "GOLD",   time = targets.gold_seconds,   col = COLORS.GOLD },
            { label = "SILVER", time = targets.silver_seconds, col = COLORS.SILVER },
            { label = "BRONZE", time = targets.bronze_seconds, col = COLORS.BRONZE },
        }

        local hEnd = ui.Alignment and ui.Alignment.End or 1
        local vCenter = ui.Alignment and ui.Alignment.Center or 0

        for i, m in ipairs(medals) do
            local rowY = startY + (i - 1) * rowH

            -- Medal indicator dot
            ui.drawCircleFilled(vec2(medalBlockX + 5, rowY + 9), 3.5, m.col)

            -- Medal Label (GT7 Clean Typography: White with black edges)
            drawGTText(m.label, 12, vec2(medalBlockX + 16, rowY + 2), COLORS.WHITE, "Regular")

            -- Medal Time (GT7 Timing Font: Vertically aligned flush right)
            local timeStr = m.time and formatTime(m.time) or "--'--.---"
            local pMin = vec2(medalBlockX + 65, rowY)
            local pMax = vec2(rightPad, rowY + 18)
            drawTimingTextClipped(timeStr, 17, pMin, pMax, hEnd, vCenter, COLORS.WHITE)
        end
    end
end

--------------------------------------------------------------------------------
-- 2. STOPWATCH & LIVE MEDAL DELTA (GT7 Digital Stopwatch Typography)
--------------------------------------------------------------------------------
local function drawStopwatchCluster(screenW, sessionTime, targets, currentState)
    local posX = screenW - 270
    local posY = 88

    -- Header label: "TIME"
    drawGTText("TIME", 13, vec2(posX, posY), COLORS.WHITE, "Regular")

    -- Digital Clock Display (Official GT7 Paired Outline & Digit Font)
    local timeText = formatTime(sessionTime)
    drawTimingText(timeText, 40, vec2(posX, posY + 16), COLORS.WHITE)

    -- Live Medal Target Delta
    if targets and targets.gold_seconds and currentState == GTLicenseHUD.STATE.RUNNING then
        local deltaText = ""
        if sessionTime < targets.gold_seconds then
            local delta = sessionTime - targets.gold_seconds
            deltaText = string.format("GOLD %s", formatDelta(delta))
        elseif targets.silver_seconds and sessionTime < targets.silver_seconds then
            local delta = sessionTime - targets.silver_seconds
            deltaText = string.format("SILVER %s", formatDelta(delta))
        elseif targets.bronze_seconds and sessionTime < targets.bronze_seconds then
            local delta = sessionTime - targets.bronze_seconds
            deltaText = string.format("BRONZE %s", formatDelta(delta))
        else
            local delta = sessionTime - (targets.bronze_seconds or 0)
            deltaText = string.format("LIMIT %s", formatDelta(delta))
        end

        drawGTText(deltaText, 17, vec2(posX, posY + 66), COLORS.WHITE, "Regular")
    end
end

--------------------------------------------------------------------------------
-- 2.1 LIVE GHOST / PACER DELTA WIDGET
--------------------------------------------------------------------------------
local function drawGhostDelta(screenW, ghostState)
    if not ghostState or not ghostState.active then return end

    local posX = screenW - 270
    local posY = 182

    local delta = ghostState.delta or 0.0
    local prefix = delta >= 0 and "+" or "-"
    local absD = math.abs(delta)
    local deltaStr = string.format("%s%.2fs", prefix, absD)
    local label = string.format("GHOST [%s]: %s", ghostState.mode == 2 and "PACER" or "GOLD", deltaStr)

    drawGTText(label, 14, vec2(posX, posY), COLORS.WHITE, "Regular")
end

--------------------------------------------------------------------------------
-- 2.2 GHOST HOTKEY OSD BANNER
--------------------------------------------------------------------------------
local function drawGhostOSD(screenW, screenH, ghostState)
    if not ghostState or not ghostState.osd_message then return end

    local bannerW = 420
    local bannerH = 36
    local p1 = vec2((screenW - bannerW) * 0.5, screenH - 120)
    local p2 = p1 + vec2(bannerW, bannerH)

    local hAlign = ui.Alignment and ui.Alignment.Center or 0
    local vAlign = ui.Alignment and ui.Alignment.Center or 0
    drawGTTextClipped(ghostState.osd_message, 16, p1, p2, hAlign, vAlign, COLORS.WHITE, "Regular")
end

--------------------------------------------------------------------------------
-- 3. CENTER COUNTDOWN (3 - 2 - 1 - START! Authentic GT7 Countdown)
--------------------------------------------------------------------------------
local function drawCountdown(screenW, screenH, timer, isGo)
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

    local hAlign = ui.Alignment and ui.Alignment.Center or 0
    local vAlign = ui.Alignment and ui.Alignment.Center or 0

    if isText then
        -- START! using clean GT7 Regular typography
        drawGTTextClipped(displayText, 64, p1, p2, hAlign, vAlign, COLORS.WHITE, "Regular")
    else
        -- 3, 2, 1 using GT7 Timing paired outline font
        drawTimingTextClipped(displayText, 76, p1, p2, hAlign, vAlign, COLORS.WHITE, 1.0)
    end
end

--------------------------------------------------------------------------------
-- 4. PROMINENT RED 'DISQUALIFIED' BANNER
--------------------------------------------------------------------------------
local function drawDisqualifiedBanner(screenW, screenH, failReason, callbacks)
    local bannerH = 180
    local p1 = vec2(0, (screenH - bannerH) * 0.45)
    local p2 = vec2(screenW, p1.y + bannerH)

    -- Full-width deep crimson backdrop with dark shadows
    ui.drawRectFilled(p1, p2, COLORS.FAIL_BG, 0)

    -- Hazard warning border lines top and bottom
    local pulse = 0.5 + 0.5 * math.sin(animTimer * 6.0)
    local borderCol = rgbm(1.0, 0.2 + 0.3 * pulse, 0.2, 1.0)
    ui.drawRectFilled(p1, vec2(screenW, p1.y + 6), borderCol, 0)
    ui.drawRectFilled(vec2(0, p2.y - 6), p2, borderCol, 0)

    local hAlign = ui.Alignment and ui.Alignment.Center or 0
    local vAlign = ui.Alignment and ui.Alignment.Center or 0

    -- Primary Warning Title (Clean GT7 Typography)
    drawGTTextClipped("DISQUALIFIED", 32, p1 + vec2(0, 16), vec2(screenW, p1.y + 64), hAlign, vAlign, COLORS.WHITE, "Regular")

    -- Failure Reason Subtitle
    local reasonText = string.upper(failReason or "FAILED CRITERIA")
    drawGTTextClipped(reasonText, 17, p1 + vec2(0, 68), vec2(screenW, p1.y + 104), hAlign, vAlign, COLORS.OFF_WHITE, "Regular")

    -- Interactive Retry Button
    local btnW = 200
    local btnH = 36
    local btnX = (screenW - btnW) * 0.5
    local btnY = p1.y + 110
    local btnP1 = vec2(btnX, btnY)
    local btnP2 = btnP1 + vec2(btnW, btnH)

    -- Click Detection for interactive mouse control
    local uiState = ac.getUI and ac.getUI()
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

    local btnBg = isHovered and rgbm(0.35, 0.10, 0.10, 0.95) or rgbm(0.20, 0.06, 0.06, 0.85)
    local btnBorder = isHovered and rgbm(1.0, 0.4, 0.4, 1.0) or COLORS.BORDER_GREY
    ui.drawRectFilled(btnP1, btnP2, btnBg, 4)
    ui.drawRect(btnP1, btnP2, btnBorder, 4, ui.CornerFlags.All, 1.2)

    drawGTTextClipped("RETRY  (R)", 15, btnP1, btnP2, hAlign, vAlign, COLORS.WHITE, "Regular")

    -- Prompt to Retry via Hotkey / Gamepad
    drawGTTextClipped("PRESS  [ R ],  [ ENTER ],  [ SPACE ]  OR  CLICK  TO  RETRY", 13, p1 + vec2(0, 152), vec2(screenW, p1.y + 174), hAlign, vAlign, COLORS.OFF_WHITE, "Regular")
end

--------------------------------------------------------------------------------
-- 5. CELEBRATORY RESULTS SCREEN (Neutral dark backdrop, zero blue)
--------------------------------------------------------------------------------
local function drawResultsScreen(screenW, screenH, finalTime, targets, medalAchieved, callbacks)
    local cardW = 620
    local cardH = 460
    local p1 = vec2((screenW - cardW) * 0.5, (screenH - cardH) * 0.45)
    local p2 = p1 + vec2(cardW, cardH)

    -- Translucent Dark Glass Card (Neutral dark, no blue)
    ui.drawRectFilled(p1, p2, COLORS.BG_CARD, 12)
    ui.drawRect(p1, p2, COLORS.BORDER_GREY, 12, ui.CornerFlags.All, 1.5)

    -- Top Header Ribbon
    local ribbonP1 = p1
    local ribbonP2 = p1 + vec2(cardW, 70)
    local medal = medalAchieved or "bronze"

    local headerCol = COLORS.BRONZE
    local medalTitle = "BRONZE MEDAL"
    if medal == "gold" then
        headerCol = COLORS.GOLD
        medalTitle = "★ GOLD MEDAL AWARDED ★"
    elseif medal == "silver" then
        headerCol = COLORS.SILVER
        medalTitle = "★ SILVER MEDAL AWARDED ★"
    elseif medal == "bronze" then
        headerCol = COLORS.BRONZE
        medalTitle = "★ BRONZE MEDAL AWARDED ★"
    else
        headerCol = COLORS.WHITE
        medalTitle = "TEST COMPLETED"
    end

    ui.drawRectFilled(ribbonP1, ribbonP2, rgbm(headerCol.r * 0.25, headerCol.g * 0.25, headerCol.b * 0.25, 0.95), 12, ui.CornerFlags.Top)
    ui.drawRectFilled(vec2(ribbonP1.x, ribbonP2.y - 3), ribbonP2, headerCol, 0)

    local hCenter = ui.Alignment and ui.Alignment.Center or 0
    local vCenter = ui.Alignment and ui.Alignment.Center or 0
    local hEnd = ui.Alignment and ui.Alignment.End or 1

    drawGTTextClipped(medalTitle, 22, ribbonP1, ribbonP2, hCenter, vCenter, COLORS.WHITE, "Regular")

    -- Final Recorded Time Box
    local timeBoxP1 = p1 + vec2(30, 88)
    local timeBoxP2 = p1 + vec2(cardW - 30, 160)
    ui.drawRectFilled(timeBoxP1, timeBoxP2, rgbm(0, 0, 0, 0.5), 6)

    drawGTText("RECORDED TIME", 13, timeBoxP1 + vec2(16, 10), COLORS.WHITE, "Regular")
    drawTimingTextClipped(formatTime(finalTime), 46, timeBoxP1, timeBoxP2, hCenter, vCenter, COLORS.WHITE)

    -- Target Times Breakdown Table
    if targets then
        local tableY = p1.y + 175
        local rows = {
            { name = "Gold Target",   target = targets.gold_seconds,   col = COLORS.GOLD },
            { name = "Silver Target", target = targets.silver_seconds, col = COLORS.SILVER },
            { name = "Bronze Target", target = targets.bronze_seconds, col = COLORS.BRONZE },
        }

        for i, row in ipairs(rows) do
            local rowY = tableY + (i - 1) * 36
            local rP1 = vec2(p1.x + 30, rowY)
            local rP2 = vec2(p1.x + cardW - 30, rowY + 30)

            ui.drawRectFilled(rP1, rP2, rgbm(0.1, 0.1, 0.1, 0.5), 4)

            -- Medal color indicator dot
            ui.drawCircleFilled(rP1 + vec2(14, 15), 5, row.col)
            drawGTText(row.name, 14, rP1 + vec2(28, 6), COLORS.WHITE, "Regular")

            -- Target Time (GT7 Timing font)
            local targetStr = row.target and formatTime(row.target) or "--'--.---"
            drawTimingTextClipped(targetStr, 18, rP1, rP2 - vec2(100, 0), hEnd, vCenter, COLORS.WHITE)

            -- Delta / Status
            if row.target and finalTime then
                local delta = finalTime - row.target
                local deltaStr = formatDelta(delta)
                local dCol = delta <= 0 and COLORS.SUCCESS_GREEN or COLORS.FAIL_RED
                drawGTTextClipped(deltaStr, 15, rP1, rP2 - vec2(14, 0), hEnd, vCenter, dCol, "Regular")
            end
        end
    end

    -- Action Buttons (Retry, Next, Exit)
    local btnW = 160
    local btnH = 40
    local btnY = p1.y + cardH - 60
    local btnSpacing = 20
    local totalBtnsW = (btnW * 3) + (btnSpacing * 2)
    local startBtnX = p1.x + (cardW - totalBtnsW) * 0.5

    -- Restart Button
    local b1P1 = vec2(startBtnX, btnY)
    local b1P2 = b1P1 + vec2(btnW, btnH)
    ui.drawRectFilled(b1P1, b1P2, rgbm(0.18, 0.18, 0.18, 0.8), 4)
    ui.drawRect(b1P1, b1P2, COLORS.BORDER_GREY, 4, ui.CornerFlags.All, 1)
    drawGTTextClipped("RESTART (R)", 14, b1P1, b1P2, hCenter, vCenter, COLORS.WHITE, "Regular")

    -- Next Event Button (Neutral Dark with Highlight Border, NO BLUE)
    local b2P1 = vec2(startBtnX + btnW + btnSpacing, btnY)
    local b2P2 = b2P1 + vec2(btnW, btnH)
    ui.drawRectFilled(b2P1, b2P2, rgbm(0.25, 0.25, 0.25, 0.9), 4)
    ui.drawRect(b2P1, b2P2, rgbm(0.8, 0.8, 0.8, 0.8), 4, ui.CornerFlags.All, 1)
    drawGTTextClipped("NEXT EVENT", 14, b2P1, b2P2, hCenter, vCenter, COLORS.WHITE, "Regular")

    -- Exit Button
    local b3P1 = vec2(startBtnX + (btnW + btnSpacing) * 2, btnY)
    local b3P2 = b3P1 + vec2(btnW, btnH)
    ui.drawRectFilled(b3P1, b3P2, rgbm(0.15, 0.15, 0.15, 0.8), 4)
    ui.drawRect(b3P1, b3P2, COLORS.BORDER_GREY, 4, ui.CornerFlags.All, 1)
    drawGTTextClipped("EXIT (ESC)", 14, b3P1, b3P2, hCenter, vCenter, COLORS.WHITE, "Regular")

    -- Click Detection for interactive mouse control
    local uiState = ac.getUI and ac.getUI()
    if uiState and uiState.isMouseLeftKeyClicked and callbacks then
        local mPos = uiState.mousePos
        if mPos.x >= b1P1.x and mPos.x <= b1P2.x and mPos.y >= b1P1.y and mPos.y <= b1P2.y then
            if callbacks.onRestart then callbacks.onRestart() end
        elseif mPos.x >= b2P1.x and mPos.x <= b2P2.x and mPos.y >= b2P1.y and mPos.y <= b2P2.y then
            if callbacks.onNext then callbacks.onNext() end
        elseif mPos.x >= b3P1.x and mPos.x <= b3P2.x and mPos.y >= b3P1.y and mPos.y <= b3P2.y then
            if callbacks.onExit then callbacks.onExit() end
        end
    end
end

--------------------------------------------------------------------------------
-- MAIN DRAW HOOK: Invoked inside script.drawUI()
--------------------------------------------------------------------------------
--- @param sessionTime number Current test elapsed time
--- @param targetsOrConfig table Targets table or Full testConfig table
--- @param currentState integer State from GTLicenseHUD.STATE
--- @param failReason string? Reason for failure
--- @param speedKmh number? Current vehicle speed
--- @param medalAchieved string? 'gold'|'silver'|'bronze'
--- @param callbacks table? { onRestart = fn, onNext = fn, onExit = fn }
--- @param ghostState table? Ghost state from GTGhostManager:getState()
function GTLicenseHUD.draw(sessionTime, targetsOrConfig, currentState, failReason, speedKmh, medalAchieved, callbacks, ghostState)
    local uiState = ac.getUI and ac.getUI()
    local screenW = (uiState and uiState.windowSize and uiState.windowSize.x) or 1920
    local screenH = (uiState and uiState.windowSize and uiState.windowSize.y) or 1080
    local dt = (uiState and uiState.dt) or 0.016

    local config = currentConfig
    local targets = (config and config.targets) or {}
    if type(targetsOrConfig) == "table" then
        if targetsOrConfig.targets then
            config = targetsOrConfig
            targets = targetsOrConfig.targets
        elseif targetsOrConfig.gold_seconds or targetsOrConfig.bronze_seconds then
            targets = targetsOrConfig
        end
    end

    GTLicenseHUD.update(dt, currentState)

    if currentState == GTLicenseHUD.STATE.PASSED and not cachedMedalAchieved then
        cachedMedalAchieved = medalAchieved or GTLicenseHUD.evaluateMedal(sessionTime, targets)
    end

    -- Transparent window wrapper to ensure proper layering in CSP UI
    ui.beginTransparentWindow("gtLicenseHudWindow", vec2(0, 0), vec2(screenW, screenH), false)

    -- 1. Top Banner (visible in all states, floating GT7 typography)
    drawTopBanner(screenW, config, targets)

    -- 2. Stopwatch and Live Target Delta (floating GT7 typography)
    drawStopwatchCluster(screenW, sessionTime, targets, currentState)

    -- 2.1 Live Ghost / Pace Car Delta Widget
    if currentState == GTLicenseHUD.STATE.RUNNING and ghostState then
        drawGhostDelta(screenW, ghostState)
    end

    -- 2.2 Ghost Hotkey OSD Notification Banner
    if ghostState then
        drawGhostOSD(screenW, screenH, ghostState)
    end

    -- 3. Countdown 3-2-1-GO (huge floating GT7 typography)
    if currentState == GTLicenseHUD.STATE.COUNTDOWN then
        drawCountdown(screenW, screenH, countdownTimer, false)
    elseif goDisplayTimer > 0 then
        drawCountdown(screenW, screenH, 0, true)
    end

    -- 4. Disqualification Banner
    if currentState == GTLicenseHUD.STATE.FAILED then
        drawDisqualifiedBanner(screenW, screenH, failReason, callbacks)
    end

    -- 5. Results Screen
    if currentState == GTLicenseHUD.STATE.PASSED then
        drawResultsScreen(screenW, screenH, sessionTime, targets, cachedMedalAchieved, callbacks)
    end

    ui.endTransparentWindow()
end

--- Convenience wrapper accepting single options table
function GTLicenseHUD.drawHUD(opts)
    if not opts then return end
    GTLicenseHUD.draw(
        opts.sessionTime or 0,
        opts.targets or opts.config,
        opts.currentState or GTLicenseHUD.STATE.RUNNING,
        opts.failReason,
        opts.speedKmh or 0,
        opts.medalAchieved,
        opts.callbacks,
        opts.ghostState
    )
end

return GTLicenseHUD
