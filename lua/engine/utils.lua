-- ==============================================================================
-- Gran Turismo License Engine for Assetto Corsa (CSP)
-- File: lua/engine/utils.lua
-- Description: Shared utilities, vector math helpers, module loaders, and
--              JSON / 3D rendering fallbacks for License subsystems.
-- ==============================================================================

local Utils = {}

---Converts an array {x, y, z}, table {x=..., y=..., z=...}, or vec3 to a valid vec3.
---@param v table|vec3|number[]|nil
---@return vec3
function Utils.toVec3(v)
  if v == nil then
    return vec3(0, 0, 0)
  end

  -- Already a vec3 or cdata object with x, y, z
  if type(v) == "cdata" or type(v) == "userdata" then
    return v
  end

  if type(v) == "table" then
    if v.x ~= nil and v.y ~= nil and v.z ~= nil then
      return vec3(tonumber(v.x) or 0, tonumber(v.y) or 0, tonumber(v.z) or 0)
    elseif v[1] ~= nil and v[2] ~= nil and v[3] ~= nil then
      return vec3(tonumber(v[1]) or 0, tonumber(v[2]) or 0, tonumber(v[3]) or 0)
    end
  end

  return vec3(0, 0, 0)
end

---Safely normalizes a 3D direction vector.
---@param dir vec3|table|number[]
---@return vec3
function Utils.safeNormalize(dir)
  local v = Utils.toVec3(dir)
  local len = math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
  if len > 0.0001 then
    return vec3(v.x / len, v.y / len, v.z / len)
  end
  return vec3(0, 0, 1) -- default forward facing vector
end

---Safely requires a module across potential relative package paths.
---@param name string @Module name or relative path
---@param errorOnFail boolean? @Whether to raise an error if require fails
---@return any module
function Utils.safeRequire(name, errorOnFail)
  local candidates = {
    name,
    "engine/" .. name,
    "lua/engine/" .. name,
    "ui/" .. name,
    "lua/ui/" .. name
  }

  for _, path in ipairs(candidates) do
    local ok, mod = pcall(require, path)
    if ok and mod ~= nil then
      return mod
    end
  end

  if errorOnFail then
    error(string.format("utils: Failed to require '%s' across search paths", name))
  end
  return nil
end

---Checks whether a keyboard key is pressed via CSP ui or ac bindings.
---@param keyIndex integer?
---@return boolean
function Utils.isKeyPressed(keyIndex)
  if not keyIndex then return false end
  if ui and ui.keyboardButtonPressed and ui.keyboardButtonPressed(keyIndex) then
    return true
  end
  if ac and ac.isKeyPressed and ac.isKeyPressed(keyIndex) then
    return true
  end
  return false
end

---2D Line-Segment Intersection test on the X-Z ground plane.
---Checks whether trajectory from p1 to p2 crosses gate segment p3 to p4.
---@param p1 table|vec3 @Previous position
---@param p2 table|vec3 @Current position
---@param p3 table|vec3|number[] @Gate point 1
---@param p4 table|vec3|number[] @Gate point 2
---@return boolean intersects
function Utils.segmentsIntersect2D(p1, p2, p3, p4)
  local x1, z1 = p1.x or p1[1], p1.z or p1[3]
  local x2, z2 = p2.x or p2[1], p2.z or p2[3]
  local x3, z3 = p3.x or p3[1], p3.z or p3[3]
  local x4, z4 = p4.x or p4[1], p4.z or p4[3]

  local function ccw(ax, az, bx, bz, cx, cz)
    return ((cz - az) * (bx - ax)) > ((bz - az) * (cx - ax))
  end

  local a = ccw(x1, z1, x3, z3, x4, z4)
  local b = ccw(x2, z2, x3, z3, x4, z4)
  local c = ccw(x1, z1, x2, z2, x3, z3)
  local d = ccw(x1, z1, x2, z2, x4, z4)

  return (a ~= b) and (c ~= d)
end

---Tests whether a 3D position is spatially contained inside an Oriented Bounding Box (OBB).
---@param pos table|vec3 @Vehicle world position
---@param stopBox table @{ center=[x,y,z], size=[sx,sy,sz], rotation_deg=deg }
---@return boolean isInside, number localX, number localZ
function Utils.isInsideStopBox(pos, stopBox)
  if not pos or not stopBox or not stopBox.center or not stopBox.size then
    return false, 0, 0
  end

  local px = pos.x or pos[1]
  local py = pos.y or pos[2]
  local pz = pos.z or pos[3]

  local center = stopBox.center
  local size = stopBox.size
  local cx = center.x or center[1]
  local cy = center.y or center[2]
  local cz = center.z or center[3]

  local sx = size.x or size[1] or 4.5
  local sy = size.y or size[2] or 2.0
  local sz = size.z or size[3] or size.y or size[2] or 14.0

  -- Height containment check (generous vertical window of +- 4m)
  if math.abs(py - cy) > (sy * 0.5 + 4.0) then
    return false, 0, 0
  end

  -- Translation relative to box center
  local dx = px - cx
  local dz = pz - cz

  -- 2D rotation around Y axis
  local rotDeg = stopBox.rotation_deg or 0
  local rad = math.rad(-rotDeg)
  local cosR = math.cos(rad)
  local sinR = math.sin(rad)

  local localX = dx * cosR - dz * sinR
  local localZ = dx * sinR + dz * cosR

  local halfX = sx * 0.5
  local halfZ = sz * 0.5

  local inside = (math.abs(localX) <= halfX) and (math.abs(localZ) <= halfZ)
  return inside, localX, localZ
end

---Safely parses a JSON string using CSP JSON global.
---@param str string
---@return table|nil
function Utils.parseJSONSafe(str)
  if not str or #str == 0 then return nil end
  if JSON and JSON.parse then
    local ok, res = pcall(JSON.parse, str)
    if ok and res then return res end
  end
  return nil
end

---Maps a test code (e.g. "B-3", "IA-12", "S-1") to its relative JSON path.
---@param testId string
---@return string|nil relativePath
function Utils.getTestFilePath(testId)
  if not testId or #testId == 0 then return nil end
  local prefix, numStr = testId:match("^([%a]+)%-(%d+)$")
  if not prefix or not numStr then return nil end
  local num = tonumber(numStr)
  if not num then return nil end
  prefix = string.upper(prefix)
  local numPadded = string.format("%02d", num)
  local tierFolder, filePrefix
  if prefix == "B" then
    tierFolder = "national_b"
    filePrefix = "b"
  elseif prefix == "A" then
    tierFolder = "national_a"
    filePrefix = "a"
  elseif prefix == "IB" then
    tierFolder = "international_b"
    filePrefix = "ib"
  elseif prefix == "IA" then
    tierFolder = "international_a"
    filePrefix = "ia"
  elseif prefix == "S" then
    tierFolder = "super_license"
    filePrefix = "s"
  else
    return nil
  end
  return string.format("%s/test_%s%s.json", tierFolder, filePrefix, numPadded)
end

---Draws a 3D line segment using render.drawLine or polyline fallback.
---@param p1 vec3|table
---@param p2 vec3|table
---@param color rgbm
---@param thickness number?
function Utils.draw3DLine(p1, p2, color, thickness)
  thickness = thickness or 2.0
  local v1 = Utils.toVec3(p1)
  local v2 = Utils.toVec3(p2)
  if render and render.drawLine then
    render.drawLine(v1, v2, color, thickness)
  elseif render and render.polyline then
    render.polyline({ v1, v2 }, color, thickness)
  end
end

return Utils

