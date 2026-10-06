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
  if JSON and JSON.parse then
    return JSON.parse(str)
  end
  -- If JSON is not present, return default
  return nil
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
    local scriptFolder = ac.getFolder(ac.FolderID.ExtScript)
    local candidates = {
      scriptFolder .. "/active_test.json",
      scriptFolder .. "/data/active_test.json",
      scriptFolder .. "/data/tests/active_test.json"
    }
    for _, path in ipairs(candidates) do
      if io.load then
        content = io.load(path)
      end
      if content and #content > 0 then break end
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

  -- 2. State machine evaluation
  if self.state == GTLicenseEngine.STATE.COUNTDOWN then
    self.countdownTimer = self.countdownTimer - dt
    local currentStep = math.ceil(self.countdownTimer)

    if currentStep >= 1 and currentStep < self.countdownLastStep then
      self.countdownLastStep = currentStep
      dispatchEvent(self, "countdownTick", currentStep)
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
    end

  elseif self.state == GTLicenseEngine.STATE.RUNNING then
    self.sessionTime = self.sessionTime + dt

    -- Adjudicate failure conditions and finish gate/stop box completion
    local adjResult = self.adjudicator:adjudicate(dt, self.sessionTime, car)

    if adjResult.status == "FAILED" then
      self.failReason = adjResult.reason or "Disqualified"
      self:setState(GTLicenseEngine.STATE.FAILED)
      dispatchEvent(self, "testFailed", self.failReason)
      self.sessionReset:scheduleAutoReset(2.0)

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
  local activeEngine = nil

  function script.init()
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

