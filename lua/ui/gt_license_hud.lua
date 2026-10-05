--[[
    Gran Turismo-style Vector Canvas HUD for Assetto Corsa Licenses Mod
    Renders responsive, resolution-independent vector UI using CSP's ui.* API.
    
    Components:
    1. Top Banner: Test title, lesson objective, target medal times (Gold, Silver, Bronze)
    2. Real-Time Stopwatch: Classic GT typography and precision session timer
    3. Speed Indicator: Digital speedometer readout and dynamic bar gauge
    4. Live Medal Target Delta: Real-time delta comparison against target thresholds
    5. Center Countdown: 3-2-1-GO animated countdown
    6. Prominent Disqualification Banner: Deep crimson banner with failure reason
    7. Celebratory Results Screen: Medal awarded card, target comparisons, and action controls
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

-- Color Palette (Gran Turismo aesthetic)
local COLORS = {
    BG_DARK       = rgbm(0.04, 0.06, 0.09, 0.88),
    BG_CARD       = rgbm(0.07, 0.09, 0.14, 0.94),
    ACCENT_BLUE   = rgbm(0.08, 0.55, 0.95, 1.00),
    ACCENT_CYAN   = rgbm(0.10, 0.85, 0.95, 1.00),
    WHITE         = rgbm(1.00, 1.00, 1.00, 1.00),
    OFF_WHITE     = rgbm(0.90, 0.92, 0.95, 0.95),
    GREY_TEXT     = rgbm(0.65, 0.68, 0.74, 0.85),
    BORDER_GREY   = rgbm(0.25, 0.28, 0.35, 0.60),

    -- Medal Colors
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
-- 1. TOP HEADER BANNER
--------------------------------------------------------------------------------
local function drawTopBanner(screenW, config, targets)
    local bannerH = 68
    local bannerW = math.min(screenW - 40, 1600)
    local bannerX = (screenW - bannerW) * 0.5
    local p1 = vec2(bannerX, 16)
    local p2 = vec2(bannerX + bannerW, 16 + bannerH)

    -- Background Bar with Glassmorphic Gradient
    ui.drawRectFilled(p1, p2, COLORS.BG_DARK, 6)
    -- Bottom Accent Pinstripe
    ui.drawRectFilled(vec2(bannerX, 16 + bannerH - 3), p2, COLORS.ACCENT_BLUE, 2)
    -- Sleek Border Outline
    ui.drawRect(p1, p2, COLORS.BORDER_GREY, 6, ui.CornerFlags.All, 1)

    -- Left: Test ID Badge & Title
    local testCode = config.test_id or "TEST"
    local badgeW = 75
    local badgeP1 = p1 + vec2(12, 10)
    local badgeP2 = badgeP1 + vec2(badgeW, bannerH - 24)

    ui.drawRectFilled(badgeP1, badgeP2, COLORS.ACCENT_BLUE, 4)
    ui.pushFont(ui.Font.Title)
    ui.drawTextClipped(testCode, badgeP1, badgeP2, COLORS.WHITE, vec2(0.5, 0.5))
    ui.popFont()

    -- Title & Lesson Objective
    local titleX = badgeP2.x + 14
    local titleY = p1.y + 10
    ui.pushFont(ui.Font.Title)
    ui.drawText(config.title or "License Examination", vec2(titleX, titleY), COLORS.WHITE)
    ui.popFont()

    if config.lesson_objective and config.lesson_objective ~= "" then
        ui.pushFont(ui.Font.Small)
        ui.drawText(config.lesson_objective, vec2(titleX, titleY + 24), COLORS.GREY_TEXT)
        ui.popFont()
    end

    -- Right: Target Medal Times (Gold, Silver, Bronze)
    if targets then
        local rightPad = p2.x - 14
        local cardW = 125
        local cardH = bannerH - 22
        local cardY = p1.y + 11

        local medals = {
            { label = "BRONZE", time = targets.bronze_seconds, col = COLORS.BRONZE, bg = COLORS.BRONZE_BG },
            { label = "SILVER", time = targets.silver_seconds, col = COLORS.SILVER, bg = COLORS.SILVER_BG },
            { label = "GOLD",   time = targets.gold_seconds,   col = COLORS.GOLD,   bg = COLORS.GOLD_BG },
        }

        for i, m in ipairs(medals) do
            local cX = rightPad - (i * (cardW + 10))
            local cP1 = vec2(cX, cardY)
            local cP2 = cP1 + vec2(cardW, cardH)

            ui.drawRectFilled(cP1, cP2, m.bg, 4)
            ui.drawRect(cP1, cP2, m.col, 4, ui.CornerFlags.All, 1)

            -- Medal Label
            ui.pushFont(ui.Font.Tiny)
            ui.drawTextClipped(m.label, cP1 + vec2(6, 4), cP1 + vec2(cardW - 6, 16), m.col, vec2(0.0, 0.5))
            ui.popFont()

            -- Medal Time
            ui.pushFont(ui.Font.Main)
            local timeStr = m.time and formatTime(m.time) or "--'--.---"
            ui.drawTextClipped(timeStr, cP1 + vec2(6, 16), cP2 - vec2(6, 4), COLORS.WHITE, vec2(1.0, 0.5))
            ui.popFont()
        end
    end
end

--------------------------------------------------------------------------------
-- 2. STOPWATCH & LIVE MEDAL DELTA CLUSTER
--------------------------------------------------------------------------------
local function drawStopwatchCluster(screenW, sessionTime, targets, currentState)
    local boxW = 280
    local boxH = 92
    local boxX = screenW - boxW - 30
    local boxY = 96
    local p1 = vec2(boxX, boxY)
    local p2 = p1 + vec2(boxW, boxH)

    ui.drawRectFilled(p1, p2, COLORS.BG_CARD, 6)
    ui.drawRect(p1, p2, COLORS.BORDER_GREY, 6, ui.CornerFlags.All, 1)

    -- Header label
    ui.pushFont(ui.Font.Small)
    ui.drawText("TIME", p1 + vec2(14, 8), COLORS.GREY_TEXT)
    ui.popFont()

    -- Digital Clock Display
    ui.pushFont(ui.Font.Huge)
    local timeCol = COLORS.WHITE
    if currentState == GTLicenseHUD.STATE.PASSED then
        timeCol = COLORS.SUCCESS_GREEN
    elseif currentState == GTLicenseHUD.STATE.FAILED then
        timeCol = COLORS.FAIL_RED
    end
    local timeText = formatTime(sessionTime)
    ui.drawText(timeText, p1 + vec2(14, 26), timeCol)
    ui.popFont()

    -- 3. Live Medal Target Delta Pill
    if targets and targets.gold_seconds and currentState == GTLicenseHUD.STATE.RUNNING then
        local deltaText = ""
        local deltaCol = COLORS.ACCENT_CYAN
        local targetLabel = "GOLD"

        if sessionTime < targets.gold_seconds then
            local delta = sessionTime - targets.gold_seconds
            deltaText = string.format("GOLD %s", formatDelta(delta))
            deltaCol = COLORS.ACCENT_CYAN
        elseif targets.silver_seconds and sessionTime < targets.silver_seconds then
            local delta = sessionTime - targets.silver_seconds
            deltaText = string.format("SILVER %s", formatDelta(delta))
            deltaCol = COLORS.WARN_AMBER
        elseif targets.bronze_seconds and sessionTime < targets.bronze_seconds then
            local delta = sessionTime - targets.bronze_seconds
            deltaText = string.format("BRONZE %s", formatDelta(delta))
            deltaCol = COLORS.BRONZE
        else
            local delta = sessionTime - (targets.bronze_seconds or 0)
            deltaText = string.format("LIMIT %s", formatDelta(delta))
            deltaCol = COLORS.FAIL_RED
        end

        local pillP1 = p1 + vec2(14, 66)
        local pillP2 = p1 + vec2(boxW - 14, 86)
        ui.drawRectFilled(pillP1, pillP2, rgbm(0, 0, 0, 0.4), 3)
        ui.pushFont(ui.Font.Small)
        ui.drawTextClipped(deltaText, pillP1, pillP2, deltaCol, vec2(0.5, 0.5))
        ui.popFont()
    end
end

--------------------------------------------------------------------------------
-- 4. SPEED INDICATOR & TACHOMETER BAR
--------------------------------------------------------------------------------
local function drawSpeedIndicator(screenW, screenH, speedKmh)
    local boxW = 220
    local boxH = 64
    local boxX = screenW - boxW - 30
    local boxY = screenH - boxH - 30
    local p1 = vec2(boxX, boxY)
    local p2 = p1 + vec2(boxW, boxH)

    ui.drawRectFilled(p1, p2, COLORS.BG_CARD, 6)
    ui.drawRect(p1, p2, COLORS.BORDER_GREY, 6, ui.CornerFlags.All, 1)

    local spd = math.floor(math.max(0, speedKmh or 0))
    ui.pushFont(ui.Font.Huge)
    ui.drawText(tostring(spd), p1 + vec2(14, 10), COLORS.WHITE)
    ui.popFont()

    ui.pushFont(ui.Font.Small)
    ui.drawText("KM/H", p1 + vec2(140, 26), COLORS.GREY_TEXT)
    ui.popFont()

    -- Dynamic Speed Bar Gauge
    local barP1 = p1 + vec2(14, 50)
    local barP2 = p1 + vec2(boxW - 14, 56)
    local maxDisplaySpeed = 240.0
    local fillFrac = math.min(1.0, math.max(0.0, spd / maxDisplaySpeed))

    ui.drawRectFilled(barP1, barP2, rgbm(0.15, 0.17, 0.22, 0.8), 2)
    if fillFrac > 0 then
        local fillP2 = vec2(barP1.x + (barP2.x - barP1.x) * fillFrac, barP2.y)
        local barColor = COLORS.ACCENT_CYAN
        if spd > 140 then
            barColor = COLORS.WARN_AMBER
        elseif spd > 200 then
            barColor = COLORS.FAIL_RED
        end
        ui.drawRectFilled(barP1, fillP2, barColor, 2)
    end
end

--------------------------------------------------------------------------------
-- 5. CENTER COUNTDOWN (3 - 2 - 1 - GO!)
--------------------------------------------------------------------------------
local function drawCountdown(screenW, screenH, timer, isGo)
    local centerX = screenW * 0.5
    local centerY = screenH * 0.42

    local displayText = ""
    local textColor = COLORS.WHITE
    local scale = 1.0

    if isGo then
        displayText = "START!"
        textColor = COLORS.SUCCESS_GREEN
    elseif timer > 2.0 then
        displayText = "3"
        textColor = COLORS.WARN_AMBER
        scale = 1.0 + 0.3 * (timer - 2.0)
    elseif timer > 1.0 then
        displayText = "2"
        textColor = COLORS.WARN_AMBER
        scale = 1.0 + 0.3 * (timer - 1.0)
    elseif timer > 0.0 then
        displayText = "1"
        textColor = COLORS.WARN_AMBER
        scale = 1.0 + 0.3 * timer
    end

    if displayText == "" then return end

    -- Central Backing Glow Pill
    local glowW = isGo and 360 or 220
    local glowH = 110
    local p1 = vec2(centerX - glowW * 0.5, centerY - glowH * 0.5)
    local p2 = vec2(centerX + glowW * 0.5, centerY + glowH * 0.5)

    ui.drawRectFilled(p1, p2, rgbm(0, 0, 0, 0.75), 12)
    ui.drawRect(p1, p2, textColor, 12, ui.CornerFlags.All, 2)

    ui.pushFont(ui.Font.Huge)
    ui.drawTextClipped(displayText, p1, p2, textColor, vec2(0.5, 0.5))
    ui.popFont()
end

--------------------------------------------------------------------------------
-- 6. PROMINENT RED 'DISQUALIFIED' BANNER
--------------------------------------------------------------------------------
local function drawDisqualifiedBanner(screenW, screenH, failReason)
    local bannerH = 160
    local p1 = vec2(0, (screenH - bannerH) * 0.45)
    local p2 = vec2(screenW, p1.y + bannerH)

    -- Full-width deep crimson backdrop with dark shadows
    ui.drawRectFilled(p1, p2, COLORS.FAIL_BG, 0)

    -- Hazard warning border lines top and bottom
    local pulse = 0.5 + 0.5 * math.sin(animTimer * 6.0)
    local borderCol = rgbm(1.0, 0.2 + 0.3 * pulse, 0.2, 1.0)
    ui.drawRectFilled(p1, vec2(screenW, p1.y + 6), borderCol, 0)
    ui.drawRectFilled(vec2(0, p2.y - 6), p2, borderCol, 0)

    -- Primary Warning Title
    ui.pushFont(ui.Font.Huge)
    ui.drawTextClipped("DISQUALIFIED", p1 + vec2(0, 16), vec2(screenW, p1.y + 70), COLORS.WHITE, vec2(0.5, 0.5))
    ui.popFont()

    -- Failure Reason Subtitle
    local reasonText = string.upper(failReason or "FAILED CRITERIA")
    ui.pushFont(ui.Font.Title)
    ui.drawTextClipped(reasonText, p1 + vec2(0, 72), vec2(screenW, p1.y + 112), rgbm(1, 0.85, 0.85, 0.95), vec2(0.5, 0.5))
    ui.popFont()

    -- Prompt to Retry
    ui.pushFont(ui.Font.Main)
    ui.drawTextClipped("PRESS  [ R ]  OR  [ RESET ]  TO RETRY", p1 + vec2(0, 116), vec2(screenW, p1.y + 146), COLORS.OFF_WHITE, vec2(0.5, 0.5))
    ui.popFont()
end

--------------------------------------------------------------------------------
-- 7. CELEBRATORY RESULTS SCREEN
--------------------------------------------------------------------------------
local function drawResultsScreen(screenW, screenH, finalTime, targets, medalAchieved, callbacks)
    local cardW = 620
    local cardH = 460
    local p1 = vec2((screenW - cardW) * 0.5, (screenH - cardH) * 0.45)
    local p2 = p1 + vec2(cardW, cardH)

    -- Translucent Brushed Glass Card
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
        headerCol = COLORS.ACCENT_CYAN
        medalTitle = "TEST COMPLETED"
    end

    ui.drawRectFilled(ribbonP1, ribbonP2, rgbm(headerCol.r * 0.35, headerCol.g * 0.35, headerCol.b * 0.35, 0.9), 12, ui.CornerFlags.Top)
    ui.drawRectFilled(vec2(ribbonP1.x, ribbonP2.y - 3), ribbonP2, headerCol, 0)

    ui.pushFont(ui.Font.Title)
    ui.drawTextClipped(medalTitle, ribbonP1, ribbonP2, COLORS.WHITE, vec2(0.5, 0.5))
    ui.popFont()

    -- Final Recorded Time Box
    local timeBoxP1 = p1 + vec2(30, 88)
    local timeBoxP2 = p1 + vec2(cardW - 30, 160)
    ui.drawRectFilled(timeBoxP1, timeBoxP2, rgbm(0, 0, 0, 0.4), 6)

    ui.pushFont(ui.Font.Small)
    ui.drawText("RECORDED TIME", timeBoxP1 + vec2(16, 10), COLORS.GREY_TEXT)
    ui.popFont()

    ui.pushFont(ui.Font.Huge)
    ui.drawTextClipped(formatTime(finalTime), timeBoxP1, timeBoxP2, COLORS.WHITE, vec2(0.5, 0.65))
    ui.popFont()

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

            ui.drawRectFilled(rP1, rP2, rgbm(0.1, 0.12, 0.16, 0.5), 4)

            -- Medal Name with color dot
            ui.drawCircleFilled(rP1 + vec2(14, 15), 5, row.col)
            ui.pushFont(ui.Font.Main)
            ui.drawText(row.name, rP1 + vec2(28, 6), COLORS.WHITE)

            -- Target Time
            local targetStr = row.target and formatTime(row.target) or "--'--.---"
            ui.drawTextClipped(targetStr, rP1, rP2 - vec2(100, 0), COLORS.GREY_TEXT, vec2(1.0, 0.5))

            -- Delta / Status
            if row.target and finalTime then
                local delta = finalTime - row.target
                local deltaStr = formatDelta(delta)
                local dCol = delta <= 0 and COLORS.SUCCESS_GREEN or COLORS.FAIL_RED
                ui.drawTextClipped(deltaStr, rP1, rP2 - vec2(14, 0), dCol, vec2(1.0, 0.5))
            end
            ui.popFont()
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
    ui.drawRectFilled(b1P1, b1P2, rgbm(0.2, 0.24, 0.3, 0.8), 4)
    ui.drawRect(b1P1, b1P2, COLORS.BORDER_GREY, 4, ui.CornerFlags.All, 1)
    ui.pushFont(ui.Font.Main)
    ui.drawTextClipped("RESTART (R)", b1P1, b1P2, COLORS.WHITE, vec2(0.5, 0.5))

    -- Next Event Button
    local b2P1 = vec2(startBtnX + btnW + btnSpacing, btnY)
    local b2P2 = b2P1 + vec2(btnW, btnH)
    ui.drawRectFilled(b2P1, b2P2, COLORS.ACCENT_BLUE, 4)
    ui.drawTextClipped("NEXT EVENT", b2P1, b2P2, COLORS.WHITE, vec2(0.5, 0.5))

    -- Exit Button
    local b3P1 = vec2(startBtnX + (btnW + btnSpacing) * 2, btnY)
    local b3P2 = b3P1 + vec2(btnW, btnH)
    ui.drawRectFilled(b3P1, b3P2, rgbm(0.18, 0.20, 0.24, 0.8), 4)
    ui.drawRect(b3P1, b3P2, COLORS.BORDER_GREY, 4, ui.CornerFlags.All, 1)
    ui.drawTextClipped("EXIT (ESC)", b3P1, b3P2, COLORS.GREY_TEXT, vec2(0.5, 0.5))
    ui.popFont()

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
function GTLicenseHUD.draw(sessionTime, targetsOrConfig, currentState, failReason, speedKmh, medalAchieved, callbacks)
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

    -- 1. Top Banner (visible in all states)
    drawTopBanner(screenW, config, targets)

    -- 2. Stopwatch and Live Target Delta
    drawStopwatchCluster(screenW, sessionTime, targets, currentState)

    -- 3. Speed Indicator (visible during Countdown and Running)
    if currentState == GTLicenseHUD.STATE.COUNTDOWN or currentState == GTLicenseHUD.STATE.RUNNING then
        drawSpeedIndicator(screenW, screenH, speedKmh)
    end

    -- 4. Countdown 3-2-1-GO
    if currentState == GTLicenseHUD.STATE.COUNTDOWN then
        drawCountdown(screenW, screenH, countdownTimer, false)
    elseif goDisplayTimer > 0 then
        drawCountdown(screenW, screenH, 0, true)
    end

    -- 5. Disqualification Banner
    if currentState == GTLicenseHUD.STATE.FAILED then
        drawDisqualifiedBanner(screenW, screenH, failReason)
    end

    -- 6. Results Screen
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
        opts.callbacks
    )
end

return GTLicenseHUD
