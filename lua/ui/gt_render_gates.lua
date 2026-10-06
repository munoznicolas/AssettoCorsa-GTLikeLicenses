--[[
    Gran Turismo-style 3D Gates & World Visualizer for Assetto Corsa Licenses Mod
    Uses CSP's render.drawRibbon() and render.polyline() API.
    Renders:
    1. Glowing neon start line ribbon and vertical laser gate
    2. Chequered finish line ribbon and finish banner
    3. Stop-box glowing perimeter boundary with dynamic status feedback
    4. Ideal guide line trajectory ribbon
]]

local GTRenderGates = {}

-- Ensure render.drawRibbon and render.polyline exist in CSP runtime
if render then
    if render.drawRibbon == nil then
        --- Polyfill for render.drawRibbon if not natively provided by CSP build
        --- Draws a 3D strip/ribbon along a series of points or between two endpoints
        --- @param points vec3[] Sequence of 3D center points
        --- @param width number Ribbon width in meters
        --- @param color rgbm Color with alpha
        --- @param uvScale number? Texture/pattern repeat scale
        render.drawRibbon = function(points, width, color, uvScale)
            if not points or #points < 2 then return end
            local halfW = (width or 1.0) * 0.5
            local col = color or rgbm(0, 1, 1, 0.8)

            render.setBlendMode(render.BlendMode.AlphaBlend)
            render.setCullMode(render.CullMode.None)
            render.setDepthMode(render.DepthMode.ReadOnly)

            for i = 1, #points - 1 do
                local pA = points[i]
                local pB = points[i + 1]
                local fwd = (pB - pA):normalize()
                local up = vec3(0, 1, 0)
                local side = fwd:cross(up):normalize() * halfW

                local v1 = pA - side
                local v2 = pA + side
                local v3 = pB + side
                local v4 = pB - side

                if render.quad then
                    render.quad(v1, v2, v3, v4, col)
                elseif render.glBegin and render.GLPrimitiveType and render.GLPrimitiveType.Quads then
                    render.glBegin(render.GLPrimitiveType.Quads)
                    render.glSetColor(col)
                    render.glVertex(v1)
                    render.glVertex(v2)
                    render.glVertex(v3)
                    render.glVertex(v4)
                    render.glEnd()
                else
                    render.debugLine(v1, v2, col, col)
                    render.debugLine(v2, v3, col, col)
                    render.debugLine(v3, v4, col, col)
                    render.debugLine(v4, v1, col, col)
                end
            end
        end
    end

    if render.polyline == nil then
        --- Polyfill for render.polyline if not natively provided by CSP build
        --- Draws connected 3D lines across a sequence of vertices
        --- @param points vec3[] Sequence of 3D vertices
        --- @param color rgbm Color with alpha
        --- @param thickness number? Line thickness in meters
        render.polyline = function(points, color, thickness)
            if not points or #points < 2 then return end
            local col = color or rgbm(1, 1, 1, 1)

            render.setBlendMode(render.BlendMode.AlphaBlend)
            render.setDepthMode(render.DepthMode.ReadOnly)

            for i = 1, #points - 1 do
                local p1 = points[i]
                local p2 = points[i + 1]
                render.debugLine(p1, p2, col, col)
            end
        end
    end
end

-- State variables
local currentConfig = nil
local animTimer = 0
local cachedStartPoints = nil
local cachedFinishPoints = nil
local cachedStopBoxCorners = nil
local cachedGuideLine = nil

local function safeRequire(name)
    local ok, mod = pcall(require, name)
    if ok then return mod end
    ok, mod = pcall(require, "engine/" .. name)
    if ok then return mod end
    ok, mod = pcall(require, "lua/engine/" .. name)
    if ok then return mod end
    return nil
end

local GTUtils = safeRequire("gt_utils")

--- Helper to safely convert array {x, y, z} or vec3 into a vec3 object
local function toVec3(p)
    if GTUtils and GTUtils.toVec3 then return GTUtils.toVec3(p) end
    if not p then return vec3(0, 0, 0) end
    if type(p.x) == "number" and type(p.y) == "number" and type(p.z) == "number" then
        return vec3(p.x, p.y, p.z)
    end
    if type(p[1]) == "number" and type(p[2]) == "number" and type(p[3]) == "number" then
        return vec3(p[1], p[2], p[3])
    end
    return vec3(0, 0, 0)
end

--- Calculate 4 ground corners of an oriented stop box
local function computeStopBoxCorners(center, size, rotationDeg)
    local cx, cy, cz = center.x, center.y + 0.05, center.z
    local halfW = (size.x or size[1] or 4.0) * 0.5
    local halfL = (size.z or size[3] or size.y or size[2] or 12.0) * 0.5

    local rad = math.rad(rotationDeg or 0)
    local cosA = math.cos(rad)
    local sinA = math.sin(rad)

    local localCorners = {
        { x = -halfW, z = -halfL },
        { x =  halfW, z = -halfL },
        { x =  halfW, z =  halfL },
        { x = -halfW, z =  halfL },
    }

    local corners = {}
    for i, c in ipairs(localCorners) do
        local rx = c.x * cosA - c.z * sinA
        local rz = c.x * sinA + c.z * cosA
        corners[i] = vec3(cx + rx, cy, cz + rz)
    end
    return corners
end

--- Initialize or update gate geometries from active test configuration
--- @param testConfig table Test JSON definition adhering to schema
function GTRenderGates.init(testConfig)
    currentConfig = testConfig
    cachedStartPoints = nil
    cachedFinishPoints = nil
    cachedStopBoxCorners = nil
    cachedGuideLine = nil
    animTimer = 0

    if not testConfig or not testConfig.timing then
        return
    end

    local timing = testConfig.timing
    if timing.start_gate then
        cachedStartPoints = {
            p1 = toVec3(timing.start_gate.p1),
            p2 = toVec3(timing.start_gate.p2),
        }
    end

    if timing.finish_gate then
        cachedFinishPoints = {
            p1 = toVec3(timing.finish_gate.p1),
            p2 = toVec3(timing.finish_gate.p2),
        }
    end

    if timing.stop_box and timing.stop_box.center then
        local center = toVec3(timing.stop_box.center)
        local size = timing.stop_box.size or { 4.5, 14.0, 1.0 }
        local rot = timing.stop_box.rotation_deg or 0
        cachedStopBoxCorners = computeStopBoxCorners(center, size, rot)
    end

    -- Precompute guide line points if waypoints exist or interpolate
    if testConfig.guide_spline and #testConfig.guide_spline >= 2 then
        cachedGuideLine = {}
        for _, pt in ipairs(testConfig.guide_spline) do
            table.insert(cachedGuideLine, toVec3(pt))
        end
    elseif cachedStartPoints and cachedFinishPoints then
        -- Generate smooth reference line between start and finish gates
        local startMid = (cachedStartPoints.p1 + cachedStartPoints.p2) * 0.5
        local finishMid = (cachedFinishPoints.p1 + cachedFinishPoints.p2) * 0.5
        cachedGuideLine = { startMid, finishMid }
    end
end

--- Draw Glowing Start Line Ribbon and Laser Pylons
function GTRenderGates.drawStartGate(pulse)
    if not cachedStartPoints then return end
    local p1 = cachedStartPoints.p1
    local p2 = cachedStartPoints.p2
    local gateWidth = (p2 - p1):length()
    if gateWidth < 0.1 then return end

    local gateDir = (p2 - p1):normalize()
    local gateMid = (p1 + p2) * 0.5
    local gateNormal = gateDir:cross(vec3(0, 1, 0)):normalize()

    -- Glowing neon cyan ribbon on track surface
    local glowAlpha = 0.65 + 0.25 * pulse
    local ribbonColor = rgbm(0.1, 0.75, 1.0, glowAlpha)
    local ribbonPts = {
        p1 - gateNormal * 0.4 + vec3(0, 0.05, 0),
        p2 - gateNormal * 0.4 + vec3(0, 0.05, 0),
    }
    render.drawRibbon(ribbonPts, 0.8, ribbonColor)

    -- Vertical laser light curtain ribbon (2.5m tall)
    local curtainColor = rgbm(0.05, 0.6, 1.0, 0.25 + 0.15 * pulse)
    local curtainTopPts = {
        p1 + vec3(0, 2.5, 0),
        p2 + vec3(0, 2.5, 0),
    }
    render.drawRibbon({ (p1 + p2) * 0.5, (p1 + p2) * 0.5 + vec3(0, 2.5, 0) }, gateWidth, curtainColor)

    -- Start line perimeter border lines
    local borderCol = rgbm(0.8, 0.95, 1.0, 0.9)
    render.polyline({
        p1 + vec3(0, 0.08, 0),
        p2 + vec3(0, 0.08, 0),
    }, borderCol, 0.05)

    -- Neon gate endpoint pillars
    local pylonHeight = vec3(0, 3.2, 0)
    render.debugLine(p1, p1 + pylonHeight, borderCol, ribbonColor)
    render.debugLine(p2, p2 + pylonHeight, borderCol, ribbonColor)
    render.debugSphere(p1 + pylonHeight, 0.22, ribbonColor)
    render.debugSphere(p2 + pylonHeight, 0.22, ribbonColor)
end

--- Draw Chequered Finish Line Ribbon and Finish Banner
function GTRenderGates.drawFinishGate(pulse)
    if not cachedFinishPoints then return end
    local p1 = cachedFinishPoints.p1
    local p2 = cachedFinishPoints.p2
    local gateWidth = (p2 - p1):length()
    if gateWidth < 0.1 then return end

    local gateDir = (p2 - p1):normalize()
    local gateNormal = gateDir:cross(vec3(0, 1, 0)):normalize()

    -- Chequered finish ribbon on road surface
    local numSegments = math.max(6, math.floor(gateWidth / 1.0))
    local step = (p2 - p1) / numSegments

    for seg = 0, numSegments - 1 do
        local segA = p1 + step * seg
        local segB = p1 + step * (seg + 1)
        local isWhite = (seg % 2 == 0)
        local segCol = isWhite and rgbm(1.0, 1.0, 1.0, 0.9) or rgbm(0.1, 0.1, 0.1, 0.9)
        local segPts = {
            segA + vec3(0, 0.05, 0),
            segB + vec3(0, 0.05, 0),
        }
        render.drawRibbon(segPts, 1.0, segCol)
    end

    -- Bright neon red/gold finish line outer boundary
    local finishGlow = rgbm(1.0, 0.2, 0.2, 0.7 + 0.25 * pulse)
    render.polyline({
        p1 - gateNormal * 0.5 + vec3(0, 0.06, 0),
        p2 - gateNormal * 0.5 + vec3(0, 0.06, 0),
    }, finishGlow, 0.06)
    render.polyline({
        p1 + gateNormal * 0.5 + vec3(0, 0.06, 0),
        p2 + gateNormal * 0.5 + vec3(0, 0.06, 0),
    }, finishGlow, 0.06)

    -- Vertical finish beam pillars
    local pylonHeight = vec3(0, 3.8, 0)
    render.debugLine(p1, p1 + pylonHeight, rgbm(1, 0.3, 0.3, 1), rgbm(1, 1, 1, 1))
    render.debugLine(p2, p2 + pylonHeight, rgbm(1, 0.3, 0.3, 1), rgbm(1, 1, 1, 1))
    render.debugSphere(p1 + pylonHeight, 0.25, finishGlow)
    render.debugSphere(p2 + pylonHeight, 0.25, finishGlow)

    -- Overhead ribbon connecting finish pylons
    local overheadPts = {
        p1 + pylonHeight,
        p2 + pylonHeight,
    }
    render.drawRibbon(overheadPts, 0.5, rgbm(1.0, 0.15, 0.15, 0.85))
end

--- Draw Stop-Box Perimeter Boundary with Dynamic State Feedback
--- @param carPos vec3? Player car position
--- @param carSpeedKmh number? Player car speed in km/h
--- @param isDisqualified boolean?
function GTRenderGates.drawStopBox(pulse, carPos, carSpeedKmh, isDisqualified)
    if not cachedStopBoxCorners or #cachedStopBoxCorners < 4 then return end
    local corners = cachedStopBoxCorners

    -- Dynamic feedback colors:
    -- Default/Approaching: Amber / High-contrast caution yellow
    -- Stopped cleanly inside: Emerald green
    -- Disqualified / overshoot: Crimson red
    local boxColor = rgbm(1.0, 0.85, 0.15, 0.8 + 0.15 * pulse)
    local isInside = false

    if carPos and currentConfig and currentConfig.timing and currentConfig.timing.stop_box then
        local sb = currentConfig.timing.stop_box
        local center = toVec3(sb.center)
        local dist = (vec3(carPos.x, center.y, carPos.z) - center):length()
        local maxRadius = ((sb.size and (sb.size[1] or sb.size.x)) or 6.0) + ((sb.size and (sb.size[2] or sb.size.y)) or 14.0) * 0.5
        if dist < maxRadius then
            isInside = true
            if (carSpeedKmh or 0) < 0.5 then
                boxColor = rgbm(0.1, 1.0, 0.3, 0.95) -- Success green!
            else
                boxColor = rgbm(0.2, 0.8, 1.0, 0.9) -- Braking zone active cyan
            end
        end
    end

    if isDisqualified then
        boxColor = rgbm(1.0, 0.1, 0.1, 0.95)
    end

    -- Draw perimeter boundary using render.polyline
    local perimeter = {
        corners[1],
        corners[2],
        corners[3],
        corners[4],
        corners[1], -- Close the loop
    }
    render.polyline(perimeter, boxColor, 0.1)

    -- Draw corner markers (neon vertical pylons)
    local cornerHeight = vec3(0, 1.2, 0)
    for i = 1, 4 do
        local c = corners[i]
        render.debugLine(c, c + cornerHeight, boxColor, boxColor)
        render.debugSphere(c + cornerHeight, 0.12, boxColor)
    end

    -- Diagonal caution warning stripes inside the stop box
    local hatchPts1 = { corners[1], corners[3] }
    local hatchPts2 = { corners[2], corners[4] }
    local hatchCol = rgbm(boxColor.r, boxColor.g, boxColor.b, 0.35)
    render.polyline(hatchPts1, hatchCol, 0.05)
    render.polyline(hatchPts2, hatchCol, 0.05)
end

--- Draw Ideal Racing Guide Line Ribbon on Track Surface
function GTRenderGates.drawGuideLine(pulse)
    if not cachedGuideLine or #cachedGuideLine < 2 then return end

    -- Render smooth trajectory ribbon
    local guideColor = rgbm(0.2, 0.85, 1.0, 0.35 + 0.1 * pulse)
    render.drawRibbon(cachedGuideLine, 0.35, guideColor)

    -- Center laser thread line
    render.polyline(cachedGuideLine, rgbm(0.6, 0.95, 1.0, 0.6), 0.04)
end

--- Main 3D render hook, called inside script.draw3D(dt)
--- @param dt number Delta time in seconds
--- @param carPos vec3? Current player car position
--- @param currentState integer? 1=COUNTDOWN, 2=RUNNING, 3=PASSED, 4=FAILED
--- @param carSpeedKmh number?
function GTRenderGates.draw3D(dt, carPos, currentState, carSpeedKmh)
    if not currentConfig then return end
    animTimer = animTimer + (dt or 0.016)
    local pulse = math.sin(animTimer * 4.0)

    -- 1. Glowing start line ribbon
    GTRenderGates.drawStartGate(pulse)

    -- 2. Chequered finish line ribbon
    GTRenderGates.drawFinishGate(pulse)

    -- 3. Stop-box perimeter boundary
    local isFailed = (currentState == 4)
    GTRenderGates.drawStopBox(pulse, carPos, carSpeedKmh, isFailed)

    -- 4. Ideal guide line ribbon (visible during COUNTDOWN and RUNNING)
    if currentState == 1 or currentState == 2 then
        GTRenderGates.drawGuideLine(pulse)
    end
end

return GTRenderGates
