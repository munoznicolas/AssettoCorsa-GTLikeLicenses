-- ==============================================================================
-- Gran Turismo License Engine - Test Configuration Loader
-- File: lua/engine/gt_config_loader.lua
-- Description: Dynamic test JSON definition resolver and INI parser.
--              Queries race.ini via CSP ac.INIConfig, locates JSON files using
--              ac.FolderID, and provides authoritative fallback configurations.
-- ==============================================================================

local function safeRequire(name)
  local ok, mod = pcall(require, name)
  if ok then return mod end
  ok, mod = pcall(require, "engine/" .. name)
  if ok then return mod end
  ok, mod = pcall(require, "lua/engine/" .. name)
  if ok then return mod end
  error(string.format("gt_config_loader: Failed to require '%s': %s", name, tostring(mod)))
end

local GTUtils = safeRequire("gt_utils")

local GTConfigLoader = {}

-- Default fallback test configuration (used if no JSON file is found)
GTConfigLoader.DEFAULT_TEST_CONFIG = {
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

---Loads a JSON test definition file from disk or resolves via CSP race.ini.
---@param filepath string? @Optional path to test JSON file
---@return table testConfig
function GTConfigLoader.loadTestConfig(filepath)
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
  if not content and ac and ac.getFolder then
    local scriptFolders = {}
    if ac.FolderID then
      if ac.FolderID.ScriptOrigin then
        local origin = ac.getFolder(ac.FolderID.ScriptOrigin)
        if origin and #origin > 0 and not origin:find("AppData") then
          table.insert(scriptFolders, origin)
        end
      end
      if ac.FolderID.Root then
        local root = ac.getFolder(ac.FolderID.Root)
        if root and #root > 0 then
          table.insert(scriptFolders, root .. "/extension/lua/new-modes/gt-license")
        end
      end
      if ac.FolderID.ExtLua then
        local extLua = ac.getFolder(ac.FolderID.ExtLua)
        if extLua and #extLua > 0 then
          table.insert(scriptFolders, extLua .. "/new-modes/gt-license")
        end
      end
    end
    table.insert(scriptFolders, "D:/SteamLibrary/steamapps/common/assettocorsa/extension/lua/new-modes/gt-license")

    -- Try to determine active test ID from race.ini
    local testId = nil
    if ac.INIConfig and ac.INIConfig.raceConfig then
      local ok, race = pcall(ac.INIConfig.raceConfig)
      if ok and race then
        testId = race:get("GTLICENSE", "TEST_ID", "")
        if not testId or #testId == 0 then
          testId = race:get("RACE", "TEST_ID", "")
        end
        if not testId or #testId == 0 then
          local sName = race:get("SESSION_0", "NAME", "")
          testId = sName:match("([%a]+%-%d+)") or sName:match("^([%w%-]+):")
        end
        if not testId or #testId == 0 then
          local eventName = race:get("EVENT", "NAME", "")
          testId = eventName:match("([%a]+%-%d+)") or eventName:match("^([%w%-]+):")
        end
        if not testId or #testId == 0 then
          local raceName = race:get("RACE", "NAME", "")
          testId = raceName:match("([%a]+%-%d+)")
        end
      end
    end

    if ac and ac.log then
      ac.log(string.format("[GTLicense] loadTestConfig: detected testId='%s'", tostring(testId)))
    end

    if testId == "AI_TELEMETRY_RECORDER" then
      return {
        test_id = "AI_TELEMETRY_RECORDER",
        is_telemetry_recording = true,
        title = "95% AI Telemetry Lap Profiler",
        start_mode = "FLYING_LAP",
      }
    end

    local candidates = {}
    local relFile = (testId and #testId > 0) and GTUtils.getTestFilePath(testId) or nil

    for _, baseFolder in ipairs(scriptFolders) do
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
    local parsed = GTUtils.parseJSONSafe(content)
    if parsed and parsed.test_id then
      return parsed
    end
  end

  return GTConfigLoader.DEFAULT_TEST_CONFIG
end

return GTConfigLoader

