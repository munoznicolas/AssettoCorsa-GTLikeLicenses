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

  -- Fallback for legacy gt_ prefixed module names
  local legacy = name:match("^gt_(.+)$") or ("gt_" .. name)
  local legacyCandidates = {
    legacy,
    "engine/" .. legacy,
    "lua/engine/" .. legacy
  }
  for _, path in ipairs(legacyCandidates) do
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

-- Backward compatibility alias
Utils.GTUtils = Utils

return Utils

