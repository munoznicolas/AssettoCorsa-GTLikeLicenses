-- ==============================================================================
-- Gran Turismo License Engine - Test Configuration Loader
-- File: lua/engine/config_loader.lua
-- Description: Dynamic test JSON definition resolver and INI parser.
--              Queries race.ini via CSP ac.INIConfig, locates JSON files using
--              dynamic ac.FolderID anchors, and provides authoritative fallbacks.
-- ==============================================================================

local function safeRequire(name)
  local ok, mod = pcall(require, name)
  if ok then return mod end
  ok, mod = pcall(require, "engine/" .. name)
  if ok then return mod end
  ok, mod = pcall(require, "lua/engine/" .. name)
  if ok then return mod end
  local legacy = name:match("^gt_(.+)$") or ("gt_" .. name)
  ok, mod = pcall(require, legacy)
  if ok then return mod end
  ok, mod = pcall(require, "engine/" .. legacy)
  if ok then return mod end
  ok, mod = pcall(require, "lua/engine/" .. legacy)
  if ok then return mod end
  error(string.format("config_loader: Failed to require '%s': %s", name, tostring(mod)))
end

local Utils = safeRequire("utils")

local ConfigLoader = {}

-- Default fallback test configuration (used if no JSON file is found)
ConfigLoader.DEFAULT_TEST_CONFIG = {
  test_id = "B-1",
  tier = "National B",
  title = "Starting & Stopping: 1000m Acceleration & Braking",
  description = "Launch cleanly and bring the car to a full stop inside the marked grid box.",
  lesson_objective = "Straight-line threshold braking without locking wheels.",
  car_id = "abarth500",
  track_id = "magione",
  track_layout = "",
  start_mode = "STANDING",
  spawn = {
    position = { 0.0, 0.5, 0.0 },
    forward_vector = { 0.0, 0.0, 1.0 },
    initial_speed_kmh = 0
  },
  timing = {
    start_gate = {
      p1 = { -10.0, 0.0, 0.0 },
      p2 = { 10.0, 0.0, 0.0 }
    },
    finish_gate = {
      p1 = { -10.0, 0.0, 1000.0 },
      p2 = { 10.0, 0.0, 1000.0 }
    },
    stop_box = {
      center = { 0.0, 0.0, 1025.0 },
      size = { 12.0, 4.0, 50.0 },
      rotation_deg = 0
    }
  },
  fail_rules = {
    max_wheels_off = 2,
    wall_collision_threshold_n = 1500,
    max_yaw_angle_deg = 90,
    stop_box_overshoot_fail = true
  },
  targets = {
    gold_seconds = 26.500,
    silver_seconds = 28.000,
    bronze_seconds = 31.000
  }
}

---Extracts the active test identifier from race configuration using a prioritized resolution pipeline.
---@param race table? @INIConfig instance
---@return string? testId
function ConfigLoader.resolveActiveTestId(race)
  if not race then return nil end

  -- 1. Dedicated license test ID keys
  local testId = race:get("GTLICENSE", "TEST_ID", "")
  if testId and #testId > 0 then return testId end

  testId = race:get("RACE", "TEST_ID", "")
  if testId and #testId > 0 then return testId end

  -- 2. Session name extraction (e.g. "B-1: Straight Braking" -> "B-1")
  local sName = race:get("SESSION_0", "NAME", "")
  if sName and #sName > 0 then
    local matched = sName:match("([%a]+%-%d+)") or sName:match("^([%w%-]+):")
    if matched then return matched end
  end

  -- 3. Career Event name extraction
  local eventName = race:get("EVENT", "NAME", "")
  if eventName and #eventName > 0 then
    local matched = eventName:match("([%a]+%-%d+)") or eventName:match("^([%w%-]+):")
    if matched then return matched end
  end

  -- 4. Race name fallback
  local raceName = race:get("RACE", "NAME", "")
  if raceName and #raceName > 0 then
    local matched = raceName:match("([%a]+%-%d+)")
    if matched then return matched end
  end

  return nil
end

---Builds dynamic search directories for License resources without machine-specific hardcoded paths.
---@return string[] searchFolders
function ConfigLoader.getSearchFolders()
  local folders = {}
  local added = {}

  local function addFolder(path)
    if path and #path > 0 and not added[path] then
      added[path] = true
      table.insert(folders, path)
    end
  end

  -- CSP FolderID anchors
  if ac and ac.getFolder and ac.FolderID then
    if ac.FolderID.ScriptOrigin then
      local origin = ac.getFolder(ac.FolderID.ScriptOrigin)
      if origin and #origin > 0 and not origin:find("AppData") then
        addFolder(origin)
      end
    end
    if ac.FolderID.Root then
      local root = ac.getFolder(ac.FolderID.Root)
      if root and #root > 0 then
        addFolder(root .. "/extension/lua/new-modes/gt-license")
      end
    end
    if ac.FolderID.ExtLua then
      local extLua = ac.getFolder(ac.FolderID.ExtLua)
      if extLua and #extLua > 0 then
        addFolder(extLua .. "/new-modes/gt-license")
      end
    end
  end

  -- Relative script origin detection
  local srcInfo = debug.getinfo(1, "S")
  if srcInfo and srcInfo.source and srcInfo.source:sub(1, 1) == "@" then
    local scriptDir = srcInfo.source:sub(2):match("^(.*)[/\\].-$")
    if scriptDir then
      -- If inside lua/engine, parent is lua/
      local parentDir = scriptDir:match("^(.*)[/\\].-$")
      if parentDir then
        addFolder(parentDir)
      end
      addFolder(scriptDir)
    end
  end

  return folders
end

---Loads a JSON test definition file from disk or resolves via CSP race.ini.
---@param filepath string? @Optional path to test JSON file
---@return table testConfig
function ConfigLoader.loadTestConfig(filepath)
  local content = nil

  if filepath then
    if io.load then
      content = io.load(filepath)
    end
    if not content then
      local f = io.open(filepath, "r")
      if f then
        content = f:read("*all")
        f:close()
      end
    end
  end

  -- Search standard CSP directory locations if no content yet
  if not content then
    local race = nil
    if ac and ac.INIConfig and ac.INIConfig.raceConfig then
      local ok, r = pcall(ac.INIConfig.raceConfig)
      if ok then race = r end
    end

    local testId = ConfigLoader.resolveActiveTestId(race)

    if ac and ac.log then
      ac.log(string.format("[GTLicense] loadTestConfig: detected testId='%s'", tostring(testId)))
    end

    if testId == "AI_TELEMETRY_RECORDER" then
      return {
        test_id = "AI_TELEMETRY_RECORDER",
        is_telemetry_recording = true,
        title = "100% AI Telemetry Lap Profiler",
        start_mode = "FLYING_LAP",
      }
    end

    local searchFolders = ConfigLoader.getSearchFolders()
    local candidates = {}
    local relFile = (testId and #testId > 0) and Utils.getTestFilePath(testId) or nil

    for _, baseFolder in ipairs(searchFolders) do
      if relFile then
        table.insert(candidates, baseFolder .. "/data/tests/" .. relFile)
        table.insert(candidates, baseFolder .. "/data/" .. relFile)
        table.insert(candidates, baseFolder .. "/" .. relFile)
      end
      table.insert(candidates, baseFolder .. "/active_test.json")
      table.insert(candidates, baseFolder .. "/data/active_test.json")
      table.insert(candidates, baseFolder .. "/data/tests/active_test.json")
    end

    for _, path in ipairs(candidates) do
      if io.load then
        content = io.load(path)
      end
      if not content then
        local f = io.open(path, "r")
        if f then
          content = f:read("*all")
          f:close()
        end
      end
      if content and #content > 0 then
        if ac and ac.log then
          ac.log(string.format("[GTLicense] loadTestConfig: successfully loaded JSON from '%s' (%d bytes)", path, #content))
        end
        break
      end
    end
  end

  if content and #content > 0 then
    local parsed = Utils.parseJSONSafe(content)
    if parsed and parsed.test_id then
      return parsed
    end
  end

  return ConfigLoader.DEFAULT_TEST_CONFIG
end

-- Backward compatibility alias
ConfigLoader.GTConfigLoader = ConfigLoader

return ConfigLoader

