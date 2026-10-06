-- ==============================================================================
-- Gran Turismo License Engine for Assetto Corsa (CSP)
-- File: lua/engine/gt_license_engine.lua
-- Description: Master scenario coordinator managing the state machine
--              (COUNTDOWN -> RUNNING -> PASSED / FAILED -> RESULTS),
--              loading the active test JSON definition, and driving
--              physics hooks and adjudication.
-- ==============================================================================

local function safeRequire(name)
  local ok, mod = pcall(require, name)
  if ok then return mod end
  ok, mod = pcall(require, "engine/" .. name)
  if ok then return mod end
  ok, mod = pcall(require, "lua/engine/" .. name)
  if ok then return mod end
  error(string.format("gt_license_engine: Failed to require '%s': %s", name, tostring(mod)))
end

local GTUtils        = safeRequire("gt_utils")
local GTPhysicsHooks = safeRequire("gt_physics_hooks")
local GTAdjudicator  = safeRequire("gt_adjudicator")
local GTSessionReset = safeRequire("gt_session_reset")
local GTGhostManager = safeRequire("gt_ghost_manager")

local function tryRequireEngine(name)
  local ok, mod = pcall(require, name)
  if ok then return mod end
  ok, mod = pcall(require, "engine/" .. name)
  if ok then return mod end
  ok, mod = pcall(require, "lua/engine/" .. name)
  if ok then return mod end
  return nil
end

local GTAICoordinator = tryRequireEngine("gt_ai_coordinator")

local function tryRequireUI(name)
  local ok, mod = pcall(require, name)
  if ok then return mod end
  ok, mod = pcall(require, "ui/" .. name)
  if ok then return mod end
  ok, mod = pcall(require, "lua/ui/" .. name)
  if ok then return mod end
  return nil
end

local GTLicenseHUD   = tryRequireUI("gt_license_hud")
local GTRenderGates  = tryRequireUI("gt_render_gates")
local GTRenderGhost  = tryRequireUI("gt_render_ghost")
local GTAudioManager = tryRequireUI("gt_audio_manager")

local GTLicenseEngine = {}

-- Engine Lifecycle States
GTLicenseEngine.STATE = {
  INITIALIZING = "INITIALIZING",
  COUNTDOWN    = "COUNTDOWN",
  RUNNING      = "RUNNING",
  PASSED       = "PASSED",
  FAILED       = "FAILED",
  RESULTS      = "RESULTS"
}

-- Default fallback test configuration (used if no JSON file is found)
local DEFAULT_TEST_CONFIG = {
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

---Simple JSON parser fallback for standalone test harnesses without CSP JSON global.
local function parseJSONSafe(str)
  if GTUtils and GTUtils.parseJSONSafe then
    return GTUtils.parseJSONSafe(str)
  end
  if JSON and JSON.parse then
    return JSON.parse(str)
  end
  return nil
end

local function getTestFilePath(testId)
  if GTUtils and GTUtils.getTestFilePath then
    return GTUtils.getTestFilePath(testId)
  end
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

---Loads a JSON test definition file from disk.
---@param filepath string? @Path to test JSON file
---@return table testConfig
function GTLicenseEngine.loadTestConfig(filepath)
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

    local candidates = {}
    local relFile = (testId and #testId > 0) and getTestFilePath(testId) or nil

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
    local parsed = parseJSONSafe(content)
    if parsed and parsed.test_id then
      return parsed
    end
  end

  return DEFAULT_TEST_CONFIG
end

---Creates and initializes the master license engine coordinator.
---@param testDefinition table|string? @Test config table or path to test JSON
---@return table GTLicenseEngine instance
function GTLicenseEngine.new(testDefinition)
  local self = setmetatable({}, { __index = GTLicenseEngine })

  -- Event listeners
  self.listeners = {
    stateChanged = {},
    countdownTick = {},
    go = {},
    testPassed = {},
    testFailed = {},
    resultsShown = {},
    reset = {}
  }

  -- Initialize Session Reset Controller
  self.sessionReset = GTSessionReset.new({
    autoResetDelay = 1.8
  })
  self.sessionReset:onReset(function(reason)
    self:onSessionResetTriggered(reason)
  end)

  -- Load test definition
  if type(testDefinition) == "table" then
    self.testConfig = testDefinition
  elseif type(testDefinition) == "string" then
    self.testConfig = GTLicenseEngine.loadTestConfig(testDefinition)
  else
    self.testConfig = GTLicenseEngine.loadTestConfig(nil)
  end

  local initSpeed = (self.testConfig.spawn and self.testConfig.spawn.initial_speed_kmh) or 0
  if ac and ac.log then
    ac.log(string.format("[GTLicense] Initialized engine for test '%s' (%s) | Start Mode: %s | Initial Speed: %.1f km/h",
      tostring(self.testConfig.test_id),
      tostring(self.testConfig.title),
      tostring(self.testConfig.start_mode),
      tonumber(initSpeed) or 0))
  end

  -- State machine variables
  self.state = GTLicenseEngine.STATE.INITIALIZING
  self.sessionTime = 0
  self.countdownTimer = 3.0
  self.countdownLastStep = 4
  self.failReason = nil
  self.achievedMedal = nil
  self.resultsTimer = 0
  self.results = {}

  -- Initialize Adjudicator
  self.adjudicator = GTAdjudicator.new(self.testConfig)

  -- Initialize Ghost & Pace Car Manager
  local ghostTrajectory = nil
  if self.testConfig.ghost and self.testConfig.ghost.trajectory then
    ghostTrajectory = self.testConfig.ghost.trajectory
  end
  self.ghostManager = GTGhostManager.new(self.testConfig, ghostTrajectory)

  -- Initialize AI & Rolling Start Coordinator
  if GTAICoordinator then
    self.aiCoordinator = GTAICoordinator.new(self.testConfig)
  end

  -- Begin countdown immediately upon creation
  self:startCountdown()

  return self
end

---Registers an event callback for state changes.
---@param fn fun(newState: string, oldState: string)
function GTLicenseEngine:onStateChanged(fn)
  table.insert(self.listeners.stateChanged, fn)
end

---Registers an event callback for countdown ticks (3, 2, 1).
---@param fn fun(tick: integer)
function GTLicenseEngine:onCountdownTick(fn)
  table.insert(self.listeners.countdownTick, fn)
end

---Registers an event callback for the "GO!" signal.
---@param fn fun()
function GTLicenseEngine:onGo(fn)
  table.insert(self.listeners.go, fn)
end

---Registers an event callback for test completion (pass).
---@param fn fun(results: table)
function GTLicenseEngine:onTestPassed(fn)
  table.insert(self.listeners.testPassed, fn)
end

---Registers an event callback for test failure (disqualification).
---@param fn fun(reason: string)
function GTLicenseEngine:onTestFailed(fn)
  table.insert(self.listeners.testFailed, fn)
end

---Registers an event callback for results screen presentation.
---@param fn fun(results: table)
function GTLicenseEngine:onResultsShown(fn)
  table.insert(self.listeners.resultsShown, fn)
end

---Registers an event callback for session resets.
---@param fn fun(reason: string)
function GTLicenseEngine:onReset(fn)
  table.insert(self.listeners.reset, fn)
end

---Dispatches an event to all registered listeners.
---@param eventName string
---@param ... any
local function dispatchEvent(self, eventName, ...)
  local list = self.listeners[eventName]
  if list then
    for i = 1, #list do
      pcall(list[i], ...)
    end
  end
end

---Changes the current state and notifies listeners.
---@param newState string
function GTLicenseEngine:setState(newState)
  if self.state ~= newState then
    local oldState = self.state
    self.state = newState
    dispatchEvent(self, "stateChanged", newState, oldState)
  end
end

---Starts or restarts the 3-2-1 countdown sequence.
function GTLicenseEngine:startCountdown()
  self:setState(GTLicenseEngine.STATE.COUNTDOWN)
  self.sessionTime = 0
  self.countdownTimer = 3.0
  self.countdownLastStep = 4
  self.failReason = nil
  self.achievedMedal = nil
  self.results = {}
  self.sessionReset:cancelAutoReset()

  -- Reinitialize Adjudicator with current test config
  self.adjudicator:init(self.testConfig)

  -- Teleport car to spawn coordinates and impart rolling launch velocity if configured
  local isStanding = (self.testConfig.start_mode == "STANDING")
  GTPhysicsHooks.setupSpawn(self.testConfig, 0)

  -- Lock controls during countdown
  GTPhysicsHooks.lockControls(3.0, isStanding)

  if ac and ac.log then
    ac.log(string.format("[GTLicense] Countdown started | start_mode=%s | isStanding=%s | initial_speed=%.1f km/h",
      tostring(self.testConfig.start_mode), tostring(isStanding),
      tonumber(self.testConfig.spawn and self.testConfig.spawn.initial_speed_kmh or 0) or 0))
  end
end

---Evaluates medal rank based on achieved session time.
---@param timeSeconds number
---@return string medal ("GOLD" | "SILVER" | "BRONZE" | "NONE")
function GTLicenseEngine:evaluateMedal(timeSeconds)
  local targets = self.testConfig.targets or {}
  local gold = tonumber(targets.gold_seconds) or 999
  local silver = tonumber(targets.silver_seconds) or 999
  local bronze = tonumber(targets.bronze_seconds) or 999

  if timeSeconds <= gold then
    return "GOLD"
  elseif timeSeconds <= silver then
    return "SILVER"
  elseif timeSeconds <= bronze then
    return "BRONZE"
  else
    return "NONE"
  end
end

---Builds the results report table.
---@return table results
function GTLicenseEngine:compileResults()
  local targets = self.testConfig.targets or {}
  local gold = tonumber(targets.gold_seconds) or 0
  local silver = tonumber(targets.silver_seconds) or 0
  local bronze = tonumber(targets.bronze_seconds) or 0

  return {
    test_id = self.testConfig.test_id,
    title = self.testConfig.title,
    time = self.sessionTime,
    medal = self.achievedMedal or "NONE",
    target_gold = gold,
    target_silver = silver,
    target_bronze = bronze,
    delta_gold = self.sessionTime - gold,
    delta_silver = self.sessionTime - silver,
    delta_bronze = self.sessionTime - bronze,
    passed = (self.achievedMedal ~= nil and self.achievedMedal ~= "NONE"),
    fail_reason = self.failReason
  }
end

---Called when GTSessionReset fires a reset.
---@param reason string
function GTLicenseEngine:onSessionResetTriggered(reason)
  if self.ghostManager then
    self.ghostManager:reset()
  end
  if GTRenderGhost and GTRenderGhost.reset then
    GTRenderGhost.reset()
  end
  dispatchEvent(self, "reset", reason)
  self:startCountdown()
end

---Triggers manual session restart immediately.
function GTLicenseEngine:restart()
  self.sessionReset:executeReset("MANUAL_CALL")
end

---Main per-frame simulation update step.
---@param dt number @Frame delta time in seconds
function GTLicenseEngine:update(dt)
  -- 1. Check restart inputs and auto-reset countdown
  self.sessionReset:update(dt)

  local car = ac and ac.getCar and ac.getCar(0)

  -- Ensure car is properly spawned and oriented on the first live simulation frame
  if not self.spawnInitialized and car then
    self.spawnInitialized = true
    GTPhysicsHooks.setupSpawn(self.testConfig, 0)
    local isStanding = (self.testConfig.start_mode == "STANDING")
    GTPhysicsHooks.lockControls(3.0, isStanding)
    if ac and ac.log then
      ac.log(string.format("[GTLicense] First live frame spawn applied: pos=(%.2f, %.2f, %.2f), look=(%.2f, %.2f, %.2f), speed=%.2f km/h",
        car.position.x, car.position.y, car.position.z,
        car.look.x, car.look.y, car.look.z, car.speedKmh))
    end
  end

  -- 2. State machine evaluation
  if self.state == GTLicenseEngine.STATE.COUNTDOWN then
    self.countdownTimer = self.countdownTimer - dt
    local currentStep = math.ceil(self.countdownTimer)

    if currentStep >= 1 and currentStep < self.countdownLastStep then
      self.countdownLastStep = currentStep
      dispatchEvent(self, "countdownTick", currentStep)
      if ac and ac.log then
        local spd = car and car.speedKmh or 0
        local gear = car and car.gear or 0
        local lx = car and car.look and car.look.x or 0
        local lz = car and car.look and car.look.z or 0
        ac.log(string.format("[GTLicense] Countdown Tick %d | Mode=%s | Speed=%.2f km/h | Gear=%d | Look=(%.2f, %.2f)",
          currentStep, tostring(self.testConfig.start_mode), spd, gear, lx, lz))
      end
    end

    -- Maintain spawn position and rolling velocity vector during countdown
    if self.testConfig and self.testConfig.spawn then
      local initialSpeed = tonumber(self.testConfig.spawn.initial_speed_kmh) or 0
      if initialSpeed > 0 then
        GTPhysicsHooks.maintainRollingVelocity(0, self.testConfig.spawn.forward_vector, initialSpeed)
      end
    end

    if self.countdownTimer <= 0 then
      -- Release control locks and launch test
      GTPhysicsHooks.unlockControls()
      if self.aiCoordinator then
        self.aiCoordinator:triggerGreenFlag()
      end
      dispatchEvent(self, "go")
      self:setState(GTLicenseEngine.STATE.RUNNING)
      if ac and ac.log then
        local spd = car and car.speedKmh or 0
        local gear = car and car.gear or 0
        ac.log(string.format("[GTLicense] Countdown GO! | Mode=%s | Telemetry: Speed=%.2f km/h, Gear=%d",
          tostring(self.testConfig.start_mode), spd, gear))
      end
    end

    -- Periodic telemetry sampling
    if not self.telemetrySamples then
      self.telemetrySamples = {}
      self.lastTelemetrySampleTime = 0
    end
    self.lastTelemetrySampleTime = (self.lastTelemetrySampleTime or 0) + dt
    if self.lastTelemetrySampleTime >= 0.25 then
      self.lastTelemetrySampleTime = 0
      if car then
        table.insert(self.telemetrySamples, {
          t = self.sessionTime,
          countdown = self.countdownTimer,
          state = self.state,
          speedKmh = car.speedKmh,
          posX = car.position.x,
          posY = car.position.y,
          posZ = car.position.z,
          velX = car.velocity.x,
          velY = car.velocity.y,
          velZ = car.velocity.z,
          gear = car.gear,
          rpm = car.rpm
        })
        if io and io.save and JSON and JSON.stringify then
          local dump = {
            test_id = self.testConfig.test_id,
            start_mode = self.testConfig.start_mode,
            initial_speed_kmh = (self.testConfig.spawn and self.testConfig.spawn.initial_speed_kmh) or 0,
            samples = self.telemetrySamples
          }
          local scriptFolder = ac and ac.getFolder and ac.getFolder(ac.FolderID.ExtScript)
          if scriptFolder then
            io.save(scriptFolder .. "/data/telemetry_eval.json", JSON.stringify(dump))
          end
        end
      end
    end

  elseif self.state == GTLicenseEngine.STATE.RUNNING then
    self.sessionTime = self.sessionTime + dt

    -- Adjudicate failure conditions and finish gate/stop box completion
    local adjResult = self.adjudicator:adjudicate(dt, self.sessionTime, car)

    if adjResult.status == "FAILED" then
      self.failReason = adjResult.reason or "Disqualified"
      self:setState(GTLicenseEngine.STATE.FAILED)
      dispatchEvent(self, "testFailed", self.failReason)
      -- Do NOT auto restart on timer; wait for user input (hotkey, gamepad, or UI retry)
      self.sessionReset:cancelAutoReset()

    elseif adjResult.status == "PASSED" then
      self.achievedMedal = self:evaluateMedal(self.sessionTime)
      self.results = self:compileResults()
      self:setState(GTLicenseEngine.STATE.PASSED)
      dispatchEvent(self, "testPassed", self.results)
      self.resultsTimer = 1.2
    end

  elseif self.state == GTLicenseEngine.STATE.PASSED then
    -- Brief celebration delay before showing results dialog
    self.resultsTimer = self.resultsTimer - dt
    if self.resultsTimer <= 0 then
      self:setState(GTLicenseEngine.STATE.RESULTS)
      dispatchEvent(self, "resultsShown", self.results)
    end

  elseif self.state == GTLicenseEngine.STATE.FAILED then
    -- Fail banner active, waiting for auto-reset timer or manual 'R' keypress
    -- Handled via sessionReset:update(dt)

  elseif self.state == GTLicenseEngine.STATE.RESULTS then
    -- Results modal active, waiting for player to retry or exit
    -- Handled via UI input
  end

  -- 3. Update AI Traffic & Pace Car Coordinator
  if self.aiCoordinator then
    self.aiCoordinator:update(dt, self.sessionTime)
  end

  -- 4. Update Ghost & Pace Car Manager
  if self.ghostManager then
    local carPos = nil
    if car and car.position then
      carPos = { car.position.x, car.position.y, car.position.z }
    end
    local gTime = (self.state == GTLicenseEngine.STATE.RUNNING) and self.sessionTime or 0.0
    self.ghostManager:update(dt, gTime, carPos)
  end

  -- 4. Update audio cues if audio manager is loaded
  if GTAudioManager and GTAudioManager.update then
    GTAudioManager.update(dt, self:getNumericState(), self.countdownTimer, self.achievedMedal)
  end
end

-- ==============================================================================
-- Public Getters for HUD, 3D Rendering & Audio Subsystems
-- ==============================================================================

function GTLicenseEngine:getState()
  return self.state
end

function GTLicenseEngine:getSessionTime()
  return self.sessionTime
end

function GTLicenseEngine:getCountdownTimer()
  return math.max(0, self.countdownTimer)
end

function GTLicenseEngine:getCountdownStep()
  if self.countdownTimer > 0 then
    return math.ceil(self.countdownTimer)
  else
    return 0 -- GO
  end
end

function GTLicenseEngine:getFailReason()
  return self.failReason
end

function GTLicenseEngine:getMedal()
  return self.achievedMedal
end

function GTLicenseEngine:getResults()
  return self.results
end

function GTLicenseEngine:getActiveTest()
  return self.testConfig
end

function GTLicenseEngine:getNumericState()
  if self.state == GTLicenseEngine.STATE.COUNTDOWN then
    return 1
  elseif self.state == GTLicenseEngine.STATE.RUNNING then
    return 2
  elseif self.state == GTLicenseEngine.STATE.PASSED or self.state == GTLicenseEngine.STATE.RESULTS then
    return 3
  elseif self.state == GTLicenseEngine.STATE.FAILED then
    return 4
  else
    return 0
  end
end

function GTLicenseEngine:draw3D(dt)
  if GTRenderGates and GTRenderGates.draw3D then
    local car = ac and ac.getCar and ac.getCar(0)
    local carPos = car and car.position
    local speedKmh = car and car.speedKmh
    GTRenderGates.draw3D(dt, carPos, self:getNumericState(), speedKmh)
  end

  if GTRenderGhost and GTRenderGhost.render and self.ghostManager then
    GTRenderGhost.render(self.ghostManager:getState(), dt)
  end
end

function GTLicenseEngine:drawUI()
  if GTLicenseHUD and GTLicenseHUD.draw then
    local car = ac and ac.getCar and ac.getCar(0)
    local speedKmh = car and car.speedKmh or 0
    local callbacks = {
      onRestart = function() self:restart() end
    }
    local ghostState = self.ghostManager and self.ghostManager:getState() or nil
    GTLicenseHUD.draw(
      self.sessionTime,
      self.testConfig,
      self:getNumericState(),
      self.failReason,
      speedKmh,
      self.achievedMedal,
      callbacks,
      ghostState
    )
  end
end

function GTLicenseEngine:getGhostState()
  return self.ghostManager and self.ghostManager:getState() or nil
end

-- ==============================================================================
-- CSP Global Script Hooks Integration
-- ==============================================================================
-- If executed as the top-level CSP scenario script, wire directly into script.*
if script ~= nil then
  local activeEngine = GTLicenseEngine.new(nil)
  if GTLicenseHUD and GTLicenseHUD.init then
    GTLicenseHUD.init(activeEngine:getActiveTest())
  end
  if GTRenderGates and GTRenderGates.init then
    GTRenderGates.init(activeEngine:getActiveTest())
  end
  if GTAudioManager and GTAudioManager.init then
    GTAudioManager.init()
  end

  function script.init()
    if not activeEngine then
      activeEngine = GTLicenseEngine.new(nil)
      if GTLicenseHUD and GTLicenseHUD.init then
        GTLicenseHUD.init(activeEngine:getActiveTest())
      end
      if GTRenderGates and GTRenderGates.init then
        GTRenderGates.init(activeEngine:getActiveTest())
      end
      if GTAudioManager and GTAudioManager.init then
        GTAudioManager.init()
      end
    end
  end

  function script.update(dt)
    if activeEngine then
      activeEngine:update(dt)
    end
  end

  function script.draw3D(dt)
    if activeEngine then
      activeEngine:draw3D(dt)
    end
  end

  function script.drawUI()
    if activeEngine then
      activeEngine:drawUI()
    end
  end
end

return GTLicenseEngine

