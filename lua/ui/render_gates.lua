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
local cachedFinishSegments = nil
local cachedFinishOuter1 = nil
local cachedFinishOuter2 = nil
local cachedFinishPylons = nil
local cachedFinishOverhead = nil
local cachedStopBoxCorners = nil
local cachedStopBoxPerimeter = nil
local cachedStopBoxPylons = nil
local cachedStopBoxHatch1 = nil
local cachedStopBoxHatch2 = nil
local cachedGuideLine = nil

local okUtils, Utils = pcall(require, "engine/utils")
if not okUtils or not Utils then
    Utils = require("utils")
end

local toVec3 = Utils.toVec3

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
    cachedFinishSegments = nil
    cachedFinishOuter1 = nil
    cachedFinishOuter2 = nil
    cachedFinishPylons = nil
    cachedFinishOverhead = nil
    cachedStopBoxCorners = nil
    cachedStopBoxPerimeter = nil
    cachedStopBoxPylons = nil
    cachedStopBoxHatch1 = nil
    cachedStopBoxHatch2 = nil
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
        local p1 = toVec3(timing.finish_gate.p1)
        local p2 = toVec3(timing.finish_gate.p2)
        cachedFinishPoints = { p1 = p1, p2 = p2 }

        local gateWidth = (p2 - p1):length()
        if gateWidth >= 0.1 then
            local gateDir = (p2 - p1):normalize()
            local gateNormal = gateDir:cross(vec3(0, 1, 0)):normalize()

            -- Pre-cache chequered ribbon segments to avoid per-frame table allocations
            cachedFinishSegments = {}
            local numSegments = math.max(6, math.floor(gateWidth / 1.0))
            local step = (p2 - p1) / numSegments

            for seg = 0, numSegments - 1 do
                local segA = p1 + step * seg
                local segB = p1 + step * (seg + 1)
                local isWhite = (seg % 2 == 0)
                local segCol = isWhite and rgbm(1.0, 1.0, 1.0, 0.9) or rgbm(0.1, 0.1, 0.1, 0.9)
                table.insert(cachedFinishSegments, {
                    pts = {
                        segA + vec3(0, 0.05, 0),
                        segB + vec3(0, 0.05, 0),
                    },
                    color = segCol,
                })
            end

            -- Pre-cache outer glowing polylines
            cachedFinishOuter1 = {
                p1 - gateNormal * 0.5 + vec3(0, 0.06, 0),
                p2 - gateNormal * 0.5 + vec3(0, 0.06, 0),
            }
            cachedFinishOuter2 = {
                p1 + gateNormal * 0.5 + vec3(0, 0.06, 0),
                p2 + gateNormal * 0.5 + vec3(0, 0.06, 0),
            }

            -- Pre-cache vertical beam pillars & overhead banner
            local pylonHeight = vec3(0, 3.8, 0)
            cachedFinishPylons = {
                p1 = p1,
                top1 = p1 + pylonHeight,
                p2 = p2,
                top2 = p2 + pylonHeight,
            }
            cachedFinishOverhead = {
                p1 + pylonHeight,
                p2 + pylonHeight,
            }
        end
    end

    if timing.stop_box and timing.stop_box.center then
        local center = toVec3(timing.stop_box.center)
        local size = timing.stop_box.size or { 4.5, 14.0, 1.0 }
        local rot = timing.stop_box.rotation_deg or 0
        local corners = computeStopBoxCorners(center, size, rot)
        cachedStopBoxCorners = corners

        cachedStopBoxPerimeter = {
            corners[1],
            corners[2],
            corners[3],
            corners[4],
            corners[1],
        }

        local cornerHeight = vec3(0, 1.2, 0)
        cachedStopBoxPylons = {}
        for i = 1, 4 do
            cachedStopBoxPylons[i] = {
                base = corners[i],
                top = corners[i] + cornerHeight,
            }
        end

        cachedStopBoxHatch1 = { corners[1], corners[3] }
        cachedStopBoxHatch2 = { corners[2], corners[4] }
    end

    -- Precompute guide line points only if explicit guide spline waypoints exist
    if testConfig.guide_spline and #testConfig.guide_spline >= 2 then
        cachedGuideLine = {}
        for _, pt in ipairs(testConfig.guide_spline) do
            table.insert(cachedGuideLine, toVec3(pt))
        end
    end
end

--- Draw Glowing Start Line Ribbon (Retained for API contract; start line visuals are handled via spawn & countdown HUD)
function GTRenderGates.drawStartGate(pulse)
    -- Start gate visual wireframe intentionally omitted per Gran Turismo presentation standards;
    -- vehicle spawn orientation and the countdown sequence define the start.
    return
end

--- Draw Chequered Finish Line Ribbon and Finish Banner
function GTRenderGates.drawFinishGate(pulse)
    if not cachedFinishSegments or not cachedFinishPylons then return end

    -- Pre-cached chequered finish ribbon on road surface (zero allocations per frame)
    for _, seg in ipairs(cachedFinishSegments) do
        render.drawRibbon(seg.pts, 1.0, seg.color)
    end

    -- Bright neon red/gold finish line outer boundary
    local finishGlow = rgbm(1.0, 0.2, 0.2, 0.7 + 0.25 * pulse)
    if cachedFinishOuter1 and cachedFinishOuter2 then
        render.polyline(cachedFinishOuter1, finishGlow, 0.06)
        render.polyline(cachedFinishOuter2, finishGlow, 0.06)
    end

    -- Vertical finish beam pillars
    local pylons = cachedFinishPylons
    render.debugLine(pylons.p1, pylons.top1, rgbm(1, 0.3, 0.3, 1), rgbm(1, 1, 1, 1))
    render.debugLine(pylons.p2, pylons.top2, rgbm(1, 0.3, 0.3, 1), rgbm(1, 1, 1, 1))
    render.debugSphere(pylons.top1, 0.25, finishGlow)
    render.debugSphere(pylons.top2, 0.25, finishGlow)

    -- Overhead ribbon connecting finish pylons
    if cachedFinishOverhead then
        render.drawRibbon(cachedFinishOverhead, 0.5, rgbm(1.0, 0.15, 0.15, 0.85))
    end
end

--- Draw Stop-Box Perimeter Boundary with Dynamic State Feedback
--- @param pulse number Oscillating pulse factor
--- @param carPos vec3? Player car position
--- @param carSpeedKmh number? Player car speed in km/h
--- @param isDisqualified boolean?
function GTRenderGates.drawStopBox(pulse, carPos, carSpeedKmh, isDisqualified)
    if not cachedStopBoxCorners or not cachedStopBoxPerimeter then return end

    -- Dynamic feedback colors:
    -- Default/Approaching: Amber / High-contrast caution yellow
    -- Stopped cleanly inside: Emerald green
    -- Disqualified / overshoot: Crimson red
    local boxColor = rgbm(1.0, 0.85, 0.15, 0.8 + 0.15 * pulse)
    local isInside = false

    if carPos and currentConfig and currentConfig.timing and currentConfig.timing.stop_box then
        local sb = currentConfig.timing.stop_box

        -- Authoritative 2D rotated OBB containment check matching physics adjudication
        if Utils.isInsideStopBox(carPos, sb) then
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
    render.polyline(cachedStopBoxPerimeter, boxColor, 0.1)

    -- Draw corner markers (neon vertical pylons)
    if cachedStopBoxPylons then
        for i = 1, 4 do
            local p = cachedStopBoxPylons[i]
            render.debugLine(p.base, p.top, boxColor, boxColor)
            render.debugSphere(p.top, 0.12, boxColor)
        end
    end

    -- Diagonal caution warning stripes inside the stop box
    if cachedStopBoxHatch1 and cachedStopBoxHatch2 then
        local hatchCol = rgbm(boxColor.r, boxColor.g, boxColor.b, 0.35)
        render.polyline(cachedStopBoxHatch1, hatchCol, 0.05)
        render.polyline(cachedStopBoxHatch2, hatchCol, 0.05)
    end
end

--- Draw Ideal Racing Guide Line Ribbon on Track Surface
function GTRenderGates.drawGuideLine(pulse)
    if not cachedGuideLine or #cachedGuideLine < 2 then return end

    -- Render smooth trajectory ribbon
    local guideColor = rgbm(0.2, 0.85, 1.0, 0.35 + 0.1 * pulse)
    render.drawRibbon(cachedGuideLine, 0.35, guideColor)
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
