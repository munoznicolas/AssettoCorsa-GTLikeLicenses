-- ==============================================================================
-- Gran Turismo License Engine for Assetto Corsa (CSP)
-- File: lua/engine/license_engine.lua
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
  error(string.format("license_engine: Failed to require '%s': %s", name, tostring(mod)))
end

local PhysicsHooks  = safeRequire("physics_hooks")
local Adjudicator   = safeRequire("adjudicator")
local SessionReset  = safeRequire("session_reset")
local ConfigLoader  = safeRequire("config_loader")
local Results       = safeRequire("results")
local EngineRuntime = safeRequire("engine_runtime")

local function tryRequireEngine(name)
  local ok, mod = pcall(require, name)
  if ok then return mod end
  ok, mod = pcall(require, "engine/" .. name)
  if ok then return mod end
  ok, mod = pcall(require, "lua/engine/" .. name)
  if ok then return mod end
  return nil
end

local AICoordinator   = tryRequireEngine("ai_coordinator")
local TelemetryLogger = tryRequireEngine("telemetry_logger")

local function tryRequireUI(name)
  local ok, mod = pcall(require, name)
  if ok then return mod end
  ok, mod = pcall(require, "ui/" .. name)
  if ok then return mod end
  ok, mod = pcall(require, "lua/ui/" .. name)
  if ok then return mod end
  return nil
end

local GTLicenseHUD   = tryRequireUI("license_hud") or tryRequireUI("gt_license_hud")
local GTRenderGates  = tryRequireUI("render_gates") or tryRequireUI("gt_render_gates")
local GTAudioManager = tryRequireUI("audio_manager") or tryRequireUI("gt_audio_manager")

local LicenseShared = nil
pcall(function() LicenseShared = require("engine/shared_state") end)
if not LicenseShared then
  pcall(function() LicenseShared = require("shared_state") end)
end

local LicenseEngine = {}

-- Engine Lifecycle States
LicenseEngine.STATE = {
  INITIALIZING = "INITIALIZING",
  COUNTDOWN    = "COUNTDOWN",
  RUNNING      = "RUNNING",
  PASSED       = "PASSED",
  FAILED       = "FAILED",
  RESULTS      = "RESULTS"
}

-- Default fallback test configuration & loader delegation
LicenseEngine.DEFAULT_TEST_CONFIG = ConfigLoader.DEFAULT_TEST_CONFIG
LicenseEngine.loadTestConfig = ConfigLoader.loadTestConfig

local dispatchEvent = EngineRuntime.dispatchEvent
EngineRuntime.attachMethods(LicenseEngine)

---Creates and initializes the master license engine coordinator.
---@param testDefinition table|string? @Test config table or path to test JSON
---@return table LicenseEngine instance
function LicenseEngine.new(testDefinition)
  local self = setmetatable({}, { __index = LicenseEngine })

  self.listeners = {
    stateChanged = {},
    countdownTick = {},
    go = {},
    testPassed = {},
    testFailed = {},
    resultsShown = {},
    reset = {}
  }

  self.sessionReset = SessionReset.new({ autoResetDelay = 1.8 })
  self.sessionReset:onReset(function(reason)
    self:onSessionResetTriggered(reason)
  end)

  local cfg, loadErr = nil, nil
  if type(testDefinition) == "table" then
    cfg = testDefinition
  elseif type(testDefinition) == "string" then
    cfg, loadErr = LicenseEngine.loadTestConfig(testDefinition)
  else
    cfg, loadErr = LicenseEngine.loadTestConfig(nil)
  end

  if not cfg then
    local err = loadErr or string.format("No valid test configuration found for '%s'", tostring(testDefinition or "active session"))
    if ac and ac.log then
      ac.log(string.format("[GTLicense] FATAL CONFIG ERROR: %s", err))
    end
    self.loadError = err
    self.testConfig = {
      test_id = "ERROR",
      title = "Configuration Error",
      start_mode = "STANDING",
      spawn = { position = { 0, 0, 0 }, forward_vector = { 0, 0, 1 }, initial_speed_kmh = 0 },
      timing = {},
      fail_rules = {},
      targets = { gold_seconds = 0, silver_seconds = 0, bronze_seconds = 0 },
    }
  else
    self.testConfig = cfg
    self.loadError = nil
  end

  local initSpeed = (self.testConfig.spawn and self.testConfig.spawn.initial_speed_kmh) or 0
  if ac and ac.log then
    ac.log(string.format("[GTLicense] Initialized engine for test '%s' (%s) | Start Mode: %s | Initial Speed: %.1f km/h",
      tostring(self.testConfig.test_id),
      tostring(self.testConfig.title),
      tostring(self.testConfig.start_mode),
      tonumber(initSpeed) or 0))
  end

  if self.loadError then
    self.state = LicenseEngine.STATE.FAILED
    self.failReason = self.loadError
  else
    self.state = LicenseEngine.STATE.INITIALIZING
    self.failReason = nil
  end
  self.sessionTime = 0
  self.countdownTimer = 3.0
  self.countdownLastStep = 4
  self.achievedMedal = nil
  self.resultsTimer = 0
  self.results = {}

  self.adjudicator = Adjudicator.new(self.testConfig)
  EngineRuntime.loadRaceIniFlags(self)

  self.restartCount = 0
  self.telemetrySamples = {}

  if ac and ac.onSessionStart then
    ac.onSessionStart(function(sessionIndex, restarted)
      if ac and ac.log then
        ac.log(string.format("[GTLicense] ac.onSessionStart: sessionIndex=%d, restarted=%s", sessionIndex, tostring(restarted)))
      end
      if restarted then
        self.spawnInitialized = false
        self.gearOverrideReleased = false
        self.lastAIShiftTime = 0
        self.restartCount = (self.restartCount or 0) + 1
        self:startCountdown()
      end
    end)
  end

  if AICoordinator then
    self.aiCoordinator = AICoordinator.new(self.testConfig)
  end
  if TelemetryLogger then
    self.telemetryLogger = TelemetryLogger.new()
  end
  if LicenseShared and LicenseShared.connect then
    self.sharedState = LicenseShared.connect()
  end

  self:startCountdown()
  return self
end

---Returns true if the specified state requires vehicle braking (FAILED, PASSED, RESULTS).
---@param state string
---@return boolean
function LicenseEngine.isBrakingState(state)
  return state == LicenseEngine.STATE.FAILED
      or state == LicenseEngine.STATE.PASSED
      or state == LicenseEngine.STATE.RESULTS
end

---Changes the current state and notifies listeners.
---@param newState string
function LicenseEngine:setState(newState)
  if self.state ~= newState then
    local oldState = self.state
    self.state = newState

    local wasBraking = LicenseEngine.isBrakingState(oldState)
    local isBraking = LicenseEngine.isBrakingState(newState)

    if isBraking and not wasBraking then
      local enableAI = (newState == LicenseEngine.STATE.PASSED or newState == LicenseEngine.STATE.RESULTS)
      PhysicsHooks.applyFailureBraking(0, 0.5, enableAI)
      if ac and ac.log then
        if newState == LicenseEngine.STATE.FAILED then
          ac.log(string.format("[GTLicense] Failure triggered: reason='%s' | Deploying 50%% emergency braking", tostring(self.failReason)))
        else
          ac.log(string.format("[GTLicense] Test completed: medal='%s' | Deploying 50%% controlled braking with AI steering", tostring(self.achievedMedal or "NONE")))
        end
      end
    elseif wasBraking and not isBraking then
      PhysicsHooks.releaseFailureBraking(0)
      if ac and ac.log then
        ac.log("[GTLicense] Leaving completed/failed state | Releasing failure braking")
      end
    end

    dispatchEvent(self, "stateChanged", newState, oldState)
  end
end

function LicenseEngine:startCountdown()
  if self.loadError then
    self:setState(LicenseEngine.STATE.FAILED)
    self.failReason = self.loadError
    return
  end

  PhysicsHooks.releaseFailureBraking(0)

  if self.isTelemetryRecorder then
    self:setState(LicenseEngine.STATE.RUNNING)
    self.sessionTime = 0
    self.spawnInitialized = false
    self.countdownTimer = 0
    self.countdownLastStep = 0
    self.failReason = nil
    self.achievedMedal = nil
    self.results = {}
    self.sessionReset:cancelAutoReset()

    EngineRuntime.engageTelemetryRecorderAutopilot(self)
    if ac and ac.log then
      ac.log(string.format("[GTLicense] AI Telemetry Recorder: Hotlap start initialized, native AI autopilot engaged at %.0f%% AI level.", (self.aiLevel or 1.0) * 100))
    end
    dispatchEvent(self, "go")
    return
  end

  self:setState(LicenseEngine.STATE.COUNTDOWN)
  self.sessionTime = 0
  self.spawnInitialized = false
  self.countdownTimer = 3.0
  self.countdownLastStep = 4
  self.failReason = nil
  self.achievedMedal = nil
  self.results = {}
  self.sessionReset:cancelAutoReset()

  self.adjudicator:init(self.testConfig)
  self.adjudicator.isAITestMode = self.isAITestMode

  local isStanding = (self.testConfig.start_mode == "STANDING")
  local initialSpeed = tonumber(self.testConfig.spawn and self.testConfig.spawn.initial_speed_kmh or 0) or 0
  self.isAIRollingActive = (not isStanding) and (initialSpeed > 0)

  local targetGear = tonumber(self.testConfig.spawn and self.testConfig.spawn.gear)
  if not targetGear or targetGear <= 0 then
    targetGear = isStanding and 1 or PhysicsHooks.estimateStartingGear(initialSpeed)
  end
  local targetRPM = tonumber(self.testConfig.spawn and self.testConfig.spawn.rpm)
  if not targetRPM or targetRPM <= 0 then
    targetRPM = isStanding and 1000 or 3500
  end
  self.targetStartingGear = targetGear
  local spawnOk, spawnErr = PhysicsHooks.setupSpawn(self.testConfig, 0)
  if not spawnOk and ac and ac.log then
    ac.log(string.format("[GTLicense] WARNING: Initial setupSpawn noted: %s", tostring(spawnErr)))
  end

  PhysicsHooks.lockControls(3.0, isStanding, targetGear, targetRPM)

  if ac and ac.log then
    ac.log(string.format("[GTLicense] Countdown started | start_mode=%s | isStanding=%s | initial_speed=%.1f km/h | gear=%d | rpm=%d",
      tostring(self.testConfig.start_mode), tostring(isStanding),
      initialSpeed, targetGear, targetRPM))
  end
end

function LicenseEngine:evaluateMedal(timeSeconds)
  if self.isAITestMode then
    return "GOLD"
  end
  return Results.evaluateMedal(timeSeconds, self.testConfig and self.testConfig.targets)
end

function LicenseEngine:compileResults()
  return Results.compileResults(self.testConfig, self.sessionTime, self.achievedMedal, self.failReason)
end

function LicenseEngine:onSessionResetTriggered(reason)
  self.restartCount = (self.restartCount or 0) + 1
  self.gearOverrideReleased = false
  self.lastAIShiftTime = 0
  self.spawnInitialized = false
  PhysicsHooks.releaseFailureBraking(0)
  self.isAIRollingActive = false
  if self.telemetryLogger then
    self.telemetryLogger:reset()
  end
  dispatchEvent(self, "reset", reason)
  self:startCountdown()
end

function LicenseEngine:restart()
  self.sessionReset:executeReset("MANUAL_CALL")
end

function LicenseEngine:exitSession()
  if ac and ac.log then
    ac.log("[GTLicense] User requested session exit via Exit button or ESC")
  end
  if ac and ac.endSession then
    local medal = self.achievedMedal or "NONE"
    local passed = (self.state == LicenseEngine.STATE.PASSED or self.state == LicenseEngine.STATE.RESULTS)
    local resultsObj = nil
    if self.results and self.results.final_time then
      resultsObj = {
        summary = passed and ("Test Passed: " .. medal) or "Test Incomplete",
        message = string.format("Time: %.3fs", self.results.final_time)
      }
    end
    ac.endSession(passed and ("License Test Completed (" .. medal .. ")") or "License Test Exited", passed, resultsObj)
  end
end

function LicenseEngine:update(dt)
  if self.loadError then
    if self.state ~= LicenseEngine.STATE.FAILED then
      self:setState(LicenseEngine.STATE.FAILED)
      self.failReason = self.loadError
    end
    return
  end

  if EngineRuntime.checkSessionInterrupts(self, LicenseEngine.STATE) then
    return
  end

  self.sessionReset:update(dt)
  local car = ac and ac.getCar and ac.getCar(0)

  if not self.spawnInitialized and car then
    EngineRuntime.initializeFirstLiveFrame(self, car, LicenseEngine.STATE.FAILED)
    return
  end

  if self.state == LicenseEngine.STATE.COUNTDOWN then
    EngineRuntime.updateCountdown(self, dt, car, LicenseEngine.STATE.RUNNING)

  elseif self.state == LicenseEngine.STATE.RUNNING then
    self.sessionTime = self.sessionTime + dt

    if self.isAITestMode and self.aiCoordinator then
      self.aiCoordinator:maintainAutopilot(0, math.max(1.0, self.aiLevel or 1.0), self.isTelemetryRecorder)
    end
    if self.telemetryLogger then
      self.telemetryLogger:logLiveTrack(car, self.sessionTime)
    end

    EngineRuntime.updateRunningHandover(self, car)

    if not self.isTelemetryRecorder then
      local adjResult = self.adjudicator:adjudicate(dt, self.sessionTime, car)

      if adjResult.status == "FAILED" then
        self.failReason = adjResult.reason or "Disqualified"
        self:setState(LicenseEngine.STATE.FAILED)
        dispatchEvent(self, "testFailed", self.failReason)
        self.sessionReset:cancelAutoReset()

      elseif adjResult.status == "PASSED" then
        self.achievedMedal = self:evaluateMedal(self.sessionTime)
        self.results = self:compileResults()
        self:setState(LicenseEngine.STATE.PASSED)
        dispatchEvent(self, "testPassed", self.results)
        self.resultsTimer = 1.2
      end
    end

  elseif LicenseEngine.isBrakingState(self.state) then
    local enableAI = (self.state == LicenseEngine.STATE.PASSED or self.state == LicenseEngine.STATE.RESULTS)
    PhysicsHooks.applyFailureBraking(0, 0.5, enableAI)

    if self.state == LicenseEngine.STATE.PASSED then
      self.resultsTimer = self.resultsTimer - dt
      if self.resultsTimer <= 0 then
        self:setState(LicenseEngine.STATE.RESULTS)
        dispatchEvent(self, "resultsShown", self.results)
      end
    end
  end

  if self.aiCoordinator then
    self.aiCoordinator:update(dt, self.sessionTime)
  end
  if GTAudioManager and GTAudioManager.update then
    GTAudioManager.update(dt, self:getNumericState(), self.countdownTimer, self.achievedMedal)
  end

  EngineRuntime.syncSharedState(self, car, LicenseEngine.STATE.RUNNING)

  if self.telemetryLogger then
    self.telemetryLogger:recordSample(
      car, self.sessionTime, dt, self.state, self.countdownTimer,
      self.testConfig, self.targetStartingGear, self.restartCount
    )
  end
end

function LicenseEngine:draw3D(dt)
  if GTRenderGates and GTRenderGates.draw3D then
    local car = ac and ac.getCar and ac.getCar(0)
    local carPos = car and car.position
    local speedKmh = car and car.speedKmh
    GTRenderGates.draw3D(dt, carPos, self:getNumericState(), speedKmh)
  end
end

function LicenseEngine:drawUI()
  if GTLicenseHUD and GTLicenseHUD.draw then
    local car = ac and ac.getCar and ac.getCar(0)
    local speedKmh = car and car.speedKmh or 0
    local callbacks = {
      onRestart = function() self:restart() end,
      onExit = function() self:exitSession() end
    }
    GTLicenseHUD.draw(
      self.sessionTime,
      self.testConfig,
      self:getNumericState(),
      self.failReason,
      speedKmh,
      self.achievedMedal,
      callbacks
    )
  end
end

-- ==============================================================================
-- CSP Global Script Hooks Integration
-- ==============================================================================
EngineRuntime.bindCSPHooks(LicenseEngine, GTLicenseHUD, GTRenderGates, GTAudioManager)

return LicenseEngine
