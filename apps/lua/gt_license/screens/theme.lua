--[[
    Gran Turismo UI App Typography & DirectWrite Theme Subsystem
    Provides authentic GT7 typography, paired outlines, and color definitions for AC Lua Apps.
]]

local Theme = {}

Theme.COLORS = {
    BG_DARK       = (rgbm and rgbm(0.04, 0.04, 0.04, 0.85)) or nil,
    BG_CARD       = (rgbm and rgbm(0.06, 0.06, 0.06, 0.94)) or nil,
    WHITE         = (rgbm and rgbm(1.00, 1.00, 1.00, 1.00)) or nil,
    BLACK         = (rgbm and rgbm(0.00, 0.00, 0.00, 1.00)) or nil,
    OFF_WHITE     = (rgbm and rgbm(0.92, 0.92, 0.92, 0.95)) or nil,
    GREY_TEXT     = (rgbm and rgbm(0.70, 0.70, 0.70, 0.85)) or nil,
    BORDER_GREY   = (rgbm and rgbm(0.25, 0.25, 0.25, 0.60)) or nil,

    GOLD          = (rgbm and rgbm(1.00, 0.84, 0.00, 1.00)) or nil,
    SILVER        = (rgbm and rgbm(0.85, 0.88, 0.92, 1.00)) or nil,
    BRONZE        = (rgbm and rgbm(0.80, 0.50, 0.20, 1.00)) or nil,

    FAIL_RED      = (rgbm and rgbm(0.90, 0.12, 0.12, 0.96)) or nil,
    SUCCESS_GREEN = (rgbm and rgbm(0.15, 0.90, 0.35, 1.00)) or nil,
}

local hasDWrite = (ui ~= nil and ui.pushDWriteFont ~= nil and ui.dwriteDrawText ~= nil)

function Theme.formatTime(seconds)
    if not seconds or seconds < 0 then seconds = 0 end
    local minutes = math.floor(seconds / 60)
    local remainder = seconds % 60
    local secs = math.floor(remainder)
    local millis = math.floor((remainder - secs) * 1000)
    return string.format("%d'%02d.%03d", minutes, secs, millis)
end

function Theme.formatDelta(delta)
    local sign = delta >= 0 and "+" or "-"
    local absVal = math.abs(delta)
    local secs = math.floor(absVal)
    local millis = math.floor((absVal - secs) * 1000)
    return string.format("%s%d.%03d", sign, secs, millis)
end

function Theme.drawTimingText(text, fontSize, pos, textColor)
    if not text or text == "" or not ui then return end
    textColor = textColor or Theme.COLORS.WHITE

    if hasDWrite then
        ui.pushDWriteFont("MyTimingFontOutline:fonts")
        ui.dwriteDrawText(text, fontSize, pos, rgbm(0, 0, 0, 0.95))
        ui.popDWriteFont()

        ui.pushDWriteFont("MyTimingFont:fonts")
        ui.dwriteDrawText(text, fontSize, pos, textColor)
        ui.popDWriteFont()
    else
        if ui.pushFont and ui.Font and ui.Font.Huge then ui.pushFont(ui.Font.Huge) end
        ui.drawText(text, pos, textColor)
        if ui.popFont and ui.Font and ui.Font.Huge then ui.popFont() end
    end
end

function Theme.drawTimingTextClipped(text, fontSize, posMin, posMax, hAlign, vAlign, textColor)
    if not text or text == "" or not ui then return end
    textColor = textColor or Theme.COLORS.WHITE
    hAlign = hAlign or (ui.Alignment and ui.Alignment.Center or 0)
    vAlign = vAlign or (ui.Alignment and ui.Alignment.Center or 0)

    if hasDWrite then
        ui.pushDWriteFont("MyTimingFontOutline:fonts")
        ui.dwriteDrawTextClipped(text, fontSize, posMin, posMax, hAlign, vAlign, false, rgbm(0, 0, 0, 0.95))
        ui.popDWriteFont()

        ui.pushDWriteFont("MyTimingFont:fonts")
        ui.dwriteDrawTextClipped(text, fontSize, posMin, posMax, hAlign, vAlign, false, textColor)
        ui.popDWriteFont()
    else
        if ui.pushFont and ui.Font and ui.Font.Huge then ui.pushFont(ui.Font.Huge) end
        ui.drawTextClipped(text, posMin, posMax, textColor, vec2(0.5, 0.5))
        if ui.popFont and ui.Font and ui.Font.Huge then ui.popFont() end
    end
end

function Theme.drawGTText(text, fontSize, pos, textColor, weight)
    if not text or text == "" or not ui then return end
    textColor = textColor or Theme.COLORS.WHITE
    weight = weight or "Regular"

    if hasDWrite then
        ui.pushDWriteFont(string.format("MyFont:fonts;Weight=%s", weight))
        local outlineCol = rgbm(0, 0, 0, 0.92)
        ui.dwriteDrawText(text, fontSize, vec2(pos.x - 1, pos.y), outlineCol)
        ui.dwriteDrawText(text, fontSize, vec2(pos.x + 1, pos.y), outlineCol)
        ui.dwriteDrawText(text, fontSize, vec2(pos.x, pos.y - 1), outlineCol)
        ui.dwriteDrawText(text, fontSize, vec2(pos.x, pos.y + 1), outlineCol)
        ui.dwriteDrawText(text, fontSize, pos, textColor)
        ui.popDWriteFont()
    else
        if ui.pushFont and ui.Font and ui.Font.Main then ui.pushFont(ui.Font.Main) end
        local oCol = rgbm and rgbm(0, 0, 0, 0.92) or nil
        if oCol then
            ui.drawText(text, vec2(pos.x - 1, pos.y), oCol)
            ui.drawText(text, vec2(pos.x + 1, pos.y), oCol)
            ui.drawText(text, vec2(pos.x, pos.y - 1), oCol)
            ui.drawText(text, vec2(pos.x, pos.y + 1), oCol)
        end
        ui.drawText(text, pos, textColor)
        if ui.popFont and ui.Font and ui.Font.Main then ui.popFont() end
    end
end

function Theme.drawGTTextClipped(text, fontSize, posMin, posMax, hAlign, vAlign, textColor, weight)
    if not text or text == "" or not ui then return end
    textColor = textColor or Theme.COLORS.WHITE
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
        ui.drawTextClipped(text, posMin, posMax, textColor, vec2(0.5, 0.5))
        if ui.popFont and ui.Font and ui.Font.Main then ui.popFont() end
    end
end

return Theme

