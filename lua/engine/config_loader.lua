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

-- Deprecated fallback alias kept as nil; engine reports explicit errors instead of loading random defaults
ConfigLoader.DEFAULT_TEST_CONFIG = nil

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
local function isValidTestConfig(cfg)
  if not cfg or type(cfg) ~= "table" then return false end
  if not cfg.test_id or #tostring(cfg.test_id) == 0 then return false end
  if not cfg.spawn or type(cfg.spawn) ~= "table" then return false end
  local pos = cfg.spawn.position
  if not pos or type(pos) ~= "table" then return false end
  if (pos[1] == nil and pos.x == nil) or (pos[2] == nil and pos.y == nil) or (pos[3] == nil and pos.z == nil) then
    return false
  end
  return true
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
    if content and #content > 0 then
      local parsed = Utils.parseJSONSafe(content)
      if isValidTestConfig(parsed) then
        return parsed
      end
    end
  end

  -- Search standard CSP directory locations if no content yet
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
    local fileContent = nil
    if io.load then
      fileContent = io.load(path)
    end
    if not fileContent then
      local f = io.open(path, "r")
      if f then
        fileContent = f:read("*all")
        f:close()
      end
    end
    if fileContent and #fileContent > 0 then
      local parsed = Utils.parseJSONSafe(fileContent)
      if isValidTestConfig(parsed) then
        if ac and ac.log then
          ac.log(string.format("[GTLicense] loadTestConfig: valid test JSON loaded from '%s' (%d bytes)", path, #fileContent))
        end
        return parsed
      elseif parsed and parsed.test_id then
        if ac and ac.log then
          ac.log(string.format("[GTLicense] loadTestConfig: skipping incomplete candidate '%s' (missing spawn.position)", path))
        end
      end
    end
  end

  local err = string.format("Failed to find or load valid test configuration for '%s'", tostring(testId or filepath or "unknown session"))
  if ac and ac.log then
    ac.log(string.format("[GTLicense] loadTestConfig ERROR: %s", err))
  end
  return nil, err
end

-- Backward compatibility alias
ConfigLoader.GTConfigLoader = ConfigLoader

return ConfigLoader

