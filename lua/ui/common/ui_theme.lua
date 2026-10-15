--[[
    Gran Turismo UI Theme & DirectWrite Typography Subsystem
    Provides color palettes, DirectWrite font layering, outline fallbacks,
    and precision time formatting across both New Mode HUD and AC Lua Apps.
]]

local GTTheme = {}

-- Clean color constructor helper
local function color(r, g, b, a)
    return (rgbm and rgbm(r, g, b, a)) or nil
end

-- Color Palette (Gran Turismo aesthetic: White typography with black edges, neutral backdrop)
GTTheme.COLORS = {
    BG_DARK       = color(0.04, 0.04, 0.04, 0.85),
    BG_CARD       = color(0.06, 0.06, 0.06, 0.94),
    WHITE         = color(1.00, 1.00, 1.00, 1.00),
    BLACK         = color(0.00, 0.00, 0.00, 1.00),
    OFF_WHITE     = color(0.92, 0.92, 0.92, 0.95),
    GREY_TEXT     = color(0.70, 0.70, 0.70, 0.85),
    BORDER_GREY   = color(0.25, 0.25, 0.25, 0.60),

    -- Medal Colors (Accents for icons / indicators)
    GOLD          = color(1.00, 0.84, 0.00, 1.00),
    GOLD_BG       = color(0.35, 0.28, 0.02, 0.85),
    SILVER        = color(0.85, 0.88, 0.92, 1.00),
    SILVER_BG     = color(0.25, 0.27, 0.30, 0.85),
    BRONZE        = color(0.80, 0.50, 0.20, 1.00),
    BRONZE_BG     = color(0.30, 0.18, 0.08, 0.85),

    -- Status & Alerts
    FAIL_RED      = color(0.90, 0.12, 0.12, 0.96),
    FAIL_BG       = color(0.50, 0.05, 0.05, 0.92),
    SUCCESS_GREEN = color(0.15, 0.90, 0.35, 1.00),
    WARN_AMBER    = color(1.00, 0.70, 0.10, 1.00),
}

-- Check if CSP DirectWrite font subsystem is available
local hasDWrite = (ui ~= nil and ui.pushDWriteFont ~= nil and ui.dwriteDrawText ~= nil)
GTTheme.hasDWrite = hasDWrite

--- Helper to format seconds into classic GT laptime format: M'SS.mmm
function GTTheme.formatTime(seconds)
    if not seconds or seconds < 0 then seconds = 0 end
    local minutes = math.floor(seconds / 60)
    local remainder = seconds % 60
    local secs = math.floor(remainder)
    local millis = math.floor((remainder - secs) * 1000)
    return string.format("%d'%02d.%03d", minutes, secs, millis)
end

--- Helper to format delta times: +0.123 or -1.456
function GTTheme.formatDelta(delta)
    local sign = delta >= 0 and "+" or "-"
    local absVal = math.abs(delta)
    local secs = math.floor(absVal)
    local millis = math.floor((absVal - secs) * 1000)
    return string.format("%s%d.%03d", sign, secs, millis)
end

--- Determine which medal a time achieved
--- @param time number Lap time in seconds
--- @param targets table { gold_seconds, silver_seconds, bronze_seconds }
--- @return string|nil 'gold'|'silver'|'bronze'|nil
function GTTheme.evaluateMedal(time, targets)
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

--- Determine the active target threshold label and accent color for the stopwatch
--- @param sessionTime number Elapsed session time in seconds
--- @param targets table? Targets table { gold_seconds, silver_seconds, bronze_seconds }
--- @return string|nil label, rgbm|nil color
function GTTheme.getTargetDisplay(sessionTime, targets)
    if not targets or not targets.gold_seconds then return nil, nil end

    local time = sessionTime or 0
    if time <= targets.gold_seconds then
        return "TARGET (GOLD)  " .. GTTheme.formatTime(targets.gold_seconds), GTTheme.COLORS.GOLD
    elseif targets.silver_seconds and time <= targets.silver_seconds then
        return "TARGET (SILVER)  " .. GTTheme.formatTime(targets.silver_seconds), GTTheme.COLORS.SILVER
    elseif targets.bronze_seconds and time <= targets.bronze_seconds then
        return "TARGET (BRONZE)  " .. GTTheme.formatTime(targets.bronze_seconds), GTTheme.COLORS.BRONZE
    else
        return "OVER TARGET TIME", GTTheme.COLORS.FAIL_RED
    end
end

--- Fallback: 4-cardinal ImGui outline (optimized from 8-directional to cut draw calls by 50%)
function GTTheme.drawTextOutlinedFallback(text, pos, textColor, outlineColor, thickness)
    if not text or text == "" or not ui then return end
    local col = textColor or GTTheme.COLORS.WHITE
    local oCol = outlineColor or GTTheme.COLORS.BLACK
    local t = thickness or 1.5

    ui.drawText(text, vec2(pos.x - t, pos.y), oCol)
    ui.drawText(text, vec2(pos.x + t, pos.y), oCol)
    ui.drawText(text, vec2(pos.x, pos.y - t), oCol)
    ui.drawText(text, vec2(pos.x, pos.y + t), oCol)
    ui.drawText(text, pos, col)
end

--- Fallback: 4-cardinal ImGui clipped outline (optimized from 8-directional)
function GTTheme.drawTextClippedOutlinedFallback(text, posMin, posMax, textColor, alignment, outlineColor, thickness)
    if not text or text == "" or not ui then return end
    local col = textColor or GTTheme.COLORS.WHITE
    local oCol = outlineColor or GTTheme.COLORS.BLACK
    local t = thickness or 1.5
    local align = alignment or vec2(0, 0)

    ui.drawTextClipped(text, posMin + vec2(-t, 0), posMax + vec2(-t, 0), oCol, align)
    ui.drawTextClipped(text, posMin + vec2(t, 0), posMax + vec2(t, 0), oCol, align)
    ui.drawTextClipped(text, posMin + vec2(0, -t), posMax + vec2(0, -t), oCol, align)
    ui.drawTextClipped(text, posMin + vec2(0, t), posMax + vec2(0, t), oCol, align)
    ui.drawTextClipped(text, posMin, posMax, col, align)
end

--- Draw GT7 digital timing text using paired MyTimingFontOutline + MyTimingFont
function GTTheme.drawTimingText(text, fontSize, pos, textColor, outlineAlpha)
    if not text or text == "" or not ui then return end
    textColor = textColor or GTTheme.COLORS.WHITE
    outlineAlpha = outlineAlpha or 0.95

    if hasDWrite then
        ui.pushDWriteFont("MyTimingFontOutline:fonts")
        ui.dwriteDrawText(text, fontSize, pos, rgbm(0, 0, 0, outlineAlpha))
        ui.popDWriteFont()

        ui.pushDWriteFont("MyTimingFont:fonts")
        ui.dwriteDrawText(text, fontSize, pos, textColor)
        ui.popDWriteFont()
    else
        if ui.pushFont and ui.Font and ui.Font.Huge then ui.pushFont(ui.Font.Huge) end
        GTTheme.drawTextOutlinedFallback(text, pos, textColor, GTTheme.COLORS.BLACK, 2.0)
        if ui.popFont and ui.Font and ui.Font.Huge then ui.popFont() end
    end
end

--- Draw GT7 clipped digital timing text using paired MyTimingFontOutline + MyTimingFont
function GTTheme.drawTimingTextClipped(text, fontSize, posMin, posMax, hAlign, vAlign, textColor, outlineAlpha)
    if not text or text == "" or not ui then return end
    textColor = textColor or GTTheme.COLORS.WHITE
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
        if ui.pushFont and ui.Font and ui.Font.Huge then ui.pushFont(ui.Font.Huge) end
        local ax = (hAlign == 1) and 1.0 or ((hAlign == -1) and 0.0 or 0.5)
        local ay = (vAlign == 1) and 1.0 or ((vAlign == -1) and 0.0 or 0.5)
        GTTheme.drawTextClippedOutlinedFallback(text, posMin, posMax, textColor, vec2(ax, ay), GTTheme.COLORS.BLACK, 2.0)
        if ui.popFont and ui.Font and ui.Font.Huge then ui.popFont() end
    end
end

--- Draw GT7 UI text using clean white typography with crisp 1px black edges
function GTTheme.drawGTText(text, fontSize, pos, textColor, weight)
    if not text or text == "" or not ui then return end
    textColor = textColor or GTTheme.COLORS.WHITE
    weight = weight or "Regular"

    if hasDWrite then
        ui.pushDWriteFont(string.format("MyFont:fonts;Weight=%s", weight))
        local outlineCol = rgbm(0, 0, 0, 0.85)
        ui.dwriteDrawText(text, fontSize, vec2(pos.x - 1, pos.y), outlineCol)
        ui.dwriteDrawText(text, fontSize, vec2(pos.x + 1, pos.y), outlineCol)
        ui.dwriteDrawText(text, fontSize, vec2(pos.x, pos.y - 1), outlineCol)
        ui.dwriteDrawText(text, fontSize, vec2(pos.x, pos.y + 1), outlineCol)
        ui.dwriteDrawText(text, fontSize, pos, textColor)
        ui.popDWriteFont()
    else
        if ui.pushFont and ui.Font and ui.Font.Title then ui.pushFont(ui.Font.Title) end
        GTTheme.drawTextOutlinedFallback(text, pos, textColor, GTTheme.COLORS.BLACK, 1.2)
        if ui.popFont and ui.Font and ui.Font.Title then ui.popFont() end
    end
end

--- Draw GT7 clipped UI text using clean white typography with crisp 1px black edges
function GTTheme.drawGTTextClipped(text, fontSize, posMin, posMax, hAlign, vAlign, textColor, weight)
    if not text or text == "" or not ui then return end
    textColor = textColor or GTTheme.COLORS.WHITE
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
        if ui.pushFont and ui.Font and ui.Font.Main then ui.pushFont(ui.Font.Main) end
        local ax = (hAlign == 1) and 1.0 or ((hAlign == -1) and 0.0 or 0.5)
        local ay = (vAlign == 1) and 1.0 or ((vAlign == -1) and 0.0 or 0.5)
        GTTheme.drawTextClippedOutlinedFallback(text, posMin, posMax, textColor, vec2(ax, ay), GTTheme.COLORS.BLACK, 1.2)
        if ui.popFont and ui.Font and ui.Font.Main then ui.popFont() end
    end
end

return GTTheme

