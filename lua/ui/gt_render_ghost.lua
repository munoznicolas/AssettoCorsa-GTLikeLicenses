-- ==============================================================================
-- Gran Turismo License Engine for Assetto Corsa (CSP)
-- File: lua/ui/gt_render_ghost.lua
-- Description: 3D world visualizer for Gold Ghost Car & Pace Car.
--              Renders 3D translucent vehicle wireframe, dynamic brake lights,
--              overhead 3D pacer chevron, and trailing guidance line.
-- ==============================================================================

local GTRenderGhost = {}

-- Visual Palette
local COLOR_GHOST_BODY   = rgbm and rgbm(0.2, 0.7, 1.0, 0.45) or { 0.2, 0.7, 1.0, 0.45 }
local COLOR_GHOST_ROOF   = rgbm and rgbm(0.3, 0.85, 1.0, 0.60) or { 0.3, 0.85, 1.0, 0.60 }
local COLOR_BRAKE_ON     = rgbm and rgbm(1.0, 0.08, 0.08, 0.95) or { 1.0, 0.08, 0.08, 0.95 }
local COLOR_BRAKE_OFF    = rgbm and rgbm(0.2, 0.8, 1.0, 0.25) or { 0.2, 0.8, 1.0, 0.25 }
local COLOR_PACER_GOLD   = rgbm and rgbm(1.0, 0.84, 0.0, 0.90) or { 1.0, 0.84, 0.0, 0.90 }
local COLOR_TRAIL_RIBBON = rgbm and rgbm(1.0, 0.85, 0.2, 0.35) or { 1.0, 0.85, 0.2, 0.35 }

-- Trail History buffer
local trailHistory = {}
local MAX_TRAIL_POINTS = 25
local trailTimer = 0.0

---Helper to construct vec3 safely across CSP environments.
local function toVec3(p)
  if vec3 and vec3.new then
    return vec3(p[1], p[2], p[3])
  end
  return { x = p[1], y = p[2], z = p[3] }
end

---Draws a 3D line segment using render.drawLine or polyline fallback.
local function draw3DLine(p1, p2, color, thickness)
  thickness = thickness or 2.0
  if render and render.drawLine then
    render.drawLine(p1, p2, color, thickness)
  elseif render and render.polyline then
    render.polyline({ p1, p2 }, color, thickness)
  end
end

---Resets trail history (called on session reset).
function GTRenderGhost.reset()
  trailHistory = {}
  trailTimer = 0.0
end

---Main 3D rendering call for Ghost Car.
---@param ghostState table @State table from GTGhostManager:getState()
---@param dt number|nil @Frame delta time
function GTRenderGhost.render(ghostState, dt)
  if not ghostState or not ghostState.active or not ghostState.pos then
    return
  end

  dt = dt or 0.016

  local cx = ghostState.pos[1]
  local cy = ghostState.pos[2] + 0.05 -- slight offset above road surface
  local cz = ghostState.pos[3]

  local fx = ghostState.heading[1] or 0.0
  local fy = ghostState.heading[2] or 0.0
  local fz = ghostState.heading[3] or 1.0
  local fLen = math.sqrt(fx * fx + fy * fy + fz * fz)
  if fLen > 1e-4 then
    fx, fy, fz = fx / fLen, fy / fLen, fz / fLen
  else
    fx, fy, fz = 0, 0, 1
  end

  -- Lateral right vector
  local rx = -fz
  local ry = 0
  local rz = fx
  local rLen = math.sqrt(rx * rx + rz * rz)
  if rLen > 1e-4 then
    rx, rz = rx / rLen, rz / rLen
  else
    rx, rz = 1, 0
  end

  -- Up vector
  local ux, uy, uz = 0, 1, 0

  -- Standard Vehicle Dimensions (in meters)
  local halfW = 0.90   -- Width 1.80m
  local halfL = 2.10   -- Length 4.20m
  local bodyH = 0.70   -- Beltline height
  local roofH = 1.30   -- Roof height
  local cabinShrink = 0.65 -- Cabin narrower than body

  -- Calculate 3D Box Vertices
  -- Base corners (Ground plane)
  local fl_b = toVec3({ cx + fx * halfL - rx * halfW, cy, cz + fz * halfL - rz * halfW })
  local fr_b = toVec3({ cx + fx * halfL + rx * halfW, cy, cz + fz * halfL + rz * halfW })
  local rl_b = toVec3({ cx - fx * halfL - rx * halfW, cy, cz - fz * halfL - rz * halfW })
  local rr_b = toVec3({ cx - fx * halfL + rx * halfW, cy, cz - fz * halfL + rz * halfW })

  -- Beltline corners
  local fl_m = toVec3({ cx + fx * halfL - rx * halfW, cy + bodyH, cz + fz * halfL - rz * halfW })
  local fr_m = toVec3({ cx + fx * halfL + rx * halfW, cy + bodyH, cz + fz * halfL + rz * halfW })
  local rl_m = toVec3({ cx - fx * halfL - rx * halfW, cy + bodyH, cz - fz * halfL - rz * halfW })
  local rr_m = toVec3({ cx - fx * halfL + rx * halfW, cy + bodyH, cz - fz * halfL + rz * halfW })

  -- Roof corners (Cabin)
  local fl_t = toVec3({ cx + fx * (halfL * 0.4) - rx * (halfW * cabinShrink), cy + roofH, cz + fz * (halfL * 0.4) - rz * (halfW * cabinShrink) })
  local fr_t = toVec3({ cx + fx * (halfL * 0.4) + rx * (halfW * cabinShrink), cy + roofH, cz + fz * (halfL * 0.4) + rz * (halfW * cabinShrink) })
  local rl_t = toVec3({ cx - fx * (halfL * 0.5) - rx * (halfW * cabinShrink), cy + roofH, cz - fz * (halfL * 0.5) - rz * (halfW * cabinShrink) })
  local rr_t = toVec3({ cx - fx * (halfL * 0.5) + rx * (halfW * cabinShrink), cy + roofH, cz - fz * (halfL * 0.5) + rz * (halfW * cabinShrink) })

  -- 1. Draw Lower Chassis Perimeter
  draw3DLine(fl_b, fr_b, COLOR_GHOST_BODY, 2.5)
  draw3DLine(fr_b, rr_b, COLOR_GHOST_BODY, 2.0)
  draw3DLine(rr_b, rl_b, COLOR_GHOST_BODY, 2.5)
  draw3DLine(rl_b, fl_b, COLOR_GHOST_BODY, 2.0)

  -- 2. Draw Beltline Perimeter
  draw3DLine(fl_m, fr_m, COLOR_GHOST_BODY, 2.0)
  draw3DLine(fr_m, rr_m, COLOR_GHOST_BODY, 1.8)
  draw3DLine(rr_m, rl_m, COLOR_GHOST_BODY, 2.0)
  draw3DLine(rl_m, fl_m, COLOR_GHOST_BODY, 1.8)

  -- 3. Draw Vertical Struts
  draw3DLine(fl_b, fl_m, COLOR_GHOST_BODY, 2.0)
  draw3DLine(fr_b, fr_m, COLOR_GHOST_BODY, 2.0)
  draw3DLine(rl_b, rl_m, COLOR_GHOST_BODY, 2.0)
  draw3DLine(rr_b, rr_m, COLOR_GHOST_BODY, 2.0)

  -- 4. Draw Greenhouse / Roof Pillars
  draw3DLine(fl_m, fl_t, COLOR_GHOST_ROOF, 2.0)
  draw3DLine(fr_m, fr_t, COLOR_GHOST_ROOF, 2.0)
  draw3DLine(rl_m, rl_t, COLOR_GHOST_ROOF, 2.0)
  draw3DLine(rr_m, rr_t, COLOR_GHOST_ROOF, 2.0)

  -- 5. Draw Roof Perimeter
  draw3DLine(fl_t, fr_t, COLOR_GHOST_ROOF, 2.5)
  draw3DLine(fr_t, rr_t, COLOR_GHOST_ROOF, 2.0)
  draw3DLine(rr_t, rl_t, COLOR_GHOST_ROOF, 2.5)
  draw3DLine(rl_t, fl_t, COLOR_GHOST_ROOF, 2.0)

  -- 6. Dynamic Brake Lights
  local brakeColor = ghostState.is_braking and COLOR_BRAKE_ON or COLOR_BRAKE_OFF
  local blWidth = 0.35
  local blLeft_p1 = toVec3({ cx - fx * (halfL + 0.02) - rx * (halfW * 0.85), cy + bodyH * 0.8, cz - fz * (halfL + 0.02) - rz * (halfW * 0.85) })
  local blLeft_p2 = toVec3({ cx - fx * (halfL + 0.02) - rx * (halfW * 0.85 - blWidth), cy + bodyH * 0.8, cz - fz * (halfL + 0.02) - rz * (halfW * 0.85 - blWidth) })
  local blRight_p1 = toVec3({ cx - fx * (halfL + 0.02) + rx * (halfW * 0.85), cy + bodyH * 0.8, cz - fz * (halfL + 0.02) + rz * (halfW * 0.85) })
  local blRight_p2 = toVec3({ cx - fx * (halfL + 0.02) + rx * (halfW * 0.85 - blWidth), cy + bodyH * 0.8, cz - fz * (halfL + 0.02) + rz * (halfW * 0.85 - blWidth) })

  draw3DLine(blLeft_p1, blLeft_p2, brakeColor, ghostState.is_braking and 6.0 or 3.0)
  draw3DLine(blRight_p1, blRight_p2, brakeColor, ghostState.is_braking and 6.0 or 3.0)

  -- 7. Overhead 3D Pacer Chevron
  local chevCenter = toVec3({ cx, cy + roofH + 0.85, cz })
  local chevTop    = toVec3({ cx, cy + roofH + 1.25, cz })
  local chevLeft   = toVec3({ cx - rx * 0.45, cy + roofH + 0.95, cz - rz * 0.45 })
  local chevRight  = toVec3({ cx + rx * 0.45, cy + roofH + 0.95, cz + rz * 0.45 })

  draw3DLine(chevTop, chevLeft, COLOR_PACER_GOLD, 3.5)
  draw3DLine(chevTop, chevRight, COLOR_PACER_GOLD, 3.5)
  draw3DLine(chevLeft, chevCenter, COLOR_PACER_GOLD, 2.5)
  draw3DLine(chevRight, chevCenter, COLOR_PACER_GOLD, 2.5)

  -- 8. Trailing Guide Ribbon
  trailTimer = trailTimer + dt
  if trailTimer > 0.08 then
    trailTimer = 0.0
    table.insert(trailHistory, 1, toVec3({ cx, cy + 0.04, cz }))
    if #trailHistory > MAX_TRAIL_POINTS then
      table.remove(trailHistory)
    end
  end

  if #trailHistory >= 2 and render and render.drawRibbon then
    local ribbonWidth = 1.6
    render.drawRibbon(trailHistory, COLOR_TRAIL_RIBBON, ribbonWidth)
  elseif #trailHistory >= 2 and render and render.polyline then
    render.polyline(trailHistory, COLOR_TRAIL_RIBBON, 3.0)
  end
end

return GTRenderGhost
