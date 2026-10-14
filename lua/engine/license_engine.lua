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

local Utils          = safeRequire("utils")
local PhysicsHooks   = safeRequire("physics_hooks")
local Adjudicator    = safeRequire("adjudicator")
local SessionReset   = safeRequire("session_reset")
local ConfigLoader   = safeRequire("config_loader")
local Results        = safeRequire("results")

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

local GTLicenseHUD   = tryRequireUI("gt_license_hud")
local GTRenderGates  = tryRequireUI("gt_render_gates")
local GTAudioManager = tryRequireUI("gt_audio_manager")

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
local DEFAULT_TEST_CONFIG = ConfigLoader.DEFAULT_TEST_CONFIG

---Creates and initializes the master license engine coordinator.
---@param testDefinition table|string? @Test config table or path to test JSON
---@return table LicenseEngine instance
function LicenseEngine.new(testDefinition)
  local self = setmetatable({}, { __index = LicenseEngine })

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
  self.sessionReset = SessionReset.new({
    autoResetDelay = 1.8
  })
  self.sessionReset:onReset(function(reason)
    self:onSessionResetTriggered(reason)
  end)

  -- Load test definition
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

  -- State machine variables
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

  -- Initialize Adjudicator
  self.adjudicator = Adjudicator.new(self.testConfig)

  -- Telemetry recording check
  self.isTelemetryRecorder = (self.testConfig and (self.testConfig.test_id == "AI_TELEMETRY_RECORDER" or self.testConfig.is_telemetry_recording == true or self.testConfig.isTelemetryRecording == true)) or false

  -- Autonomous AI Demo / Test Mode check from race.ini
  self.isAITestMode = false
  self.aiLevel = 1.0
  if self.isTelemetryRecorder then
    self.isAITestMode = true
    self.aiLevel = 1.0
  end
  if ac and ac.INIConfig and ac.INIConfig.raceConfig then
    local ok, race = pcall(ac.INIConfig.raceConfig)
    if ok and race then
      local val = race:get("GTLICENSE", "AI_TEST_MODE", "")
      if val == "1" or val == "true" or val == "TRUE" then
        self.isAITestMode = true
      end
      local tId = race:get("GTLICENSE", "TEST_ID", "")
      if tId == "AI_TELEMETRY_RECORDER" then
        self.isTelemetryRecorder = true
        self.isAITestMode = true
      end
      local rstVal = race:get("GTLICENSE", "RESTART_AT_TIME", "")
      if rstVal and tonumber(rstVal) and tonumber(rstVal) > 0 then
        self.restartAtTime = tonumber(rstVal)
      end
      local lvl = race:get("RACE", "AI_LEVEL", "")
      if lvl and tonumber(lvl) then
        self.aiLevel = tonumber(lvl) / 100.0
      end
    end
  end

  self.restartCount = 0
  self.telemetrySamples = {}

  -- Listen for Assetto Corsa native session restart (e.g. from ESC menu)
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

  -- Initialize AI & Rolling Start Coordinator
  if AICoordinator then
    self.aiCoordinator = AICoordinator.new(self.testConfig)
  end

  -- Initialize Telemetry & Diagnostics Logger
  if TelemetryLogger then
    self.telemetryLogger = TelemetryLogger.new()
  end

  -- Initialize Inter-Process Shared State
  if LicenseShared and LicenseShared.connect then
    self.sharedState = LicenseShared.connect()
  end

  -- Begin countdown immediately upon creation
  self:startCountdown()

  return self
end

---Registers an event callback for state changes.
---@param fn fun(newState: string, oldState: string)
function LicenseEngine:onStateChanged(fn)
  table.insert(self.listeners.stateChanged, fn)
end

---Registers an event callback for countdown ticks (3, 2, 1).
---@param fn fun(tick: integer)
function LicenseEngine:onCountdownTick(fn)
  table.insert(self.listeners.countdownTick, fn)
end

---Registers an event callback for the "GO!" signal.
---@param fn fun()
function LicenseEngine:onGo(fn)
  table.insert(self.listeners.go, fn)
end

---Registers an event callback for test completion (pass).
---@param fn fun(results: table)
function LicenseEngine:onTestPassed(fn)
  table.insert(self.listeners.testPassed, fn)
end

---Registers an event callback for test failure (disqualification).
---@param fn fun(reason: string)
function LicenseEngine:onTestFailed(fn)
  table.insert(self.listeners.testFailed, fn)
end

---Registers an event callback for results screen presentation.
---@param fn fun(results: table)
function LicenseEngine:onResultsShown(fn)
  table.insert(self.listeners.resultsShown, fn)
end

---Registers an event callback for session resets.
---@param fn fun(reason: string)
function LicenseEngine:onReset(fn)
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

    -- Engage native Assetto Corsa AI autopilot at 100% proficiency for hotlap recording
    if self.aiCoordinator then
      self.aiCoordinator:initAutopilot(0, self.aiLevel or 1.0, self.isTelemetryRecorder)
    end
    if physics and physics.lockUserControlsFor then
      physics.lockUserControlsFor(0)
    end
    if physics and physics.setCarNoInput then
      physics.setCarNoInput(false)
    end
    if physics and physics.forceUserThrottleFor then
      physics.forceUserThrottleFor(0, 0)
    end
    if physics and physics.forceUserBrakesFor then
      physics.forceUserBrakesFor(0, 0)
    end
    if physics and physics.forceUserHandbrakeFor then
      physics.forceUserHandbrakeFor(0, 0)
    end

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

  -- Reinitialize Adjudicator with current test config
  self.adjudicator:init(self.testConfig)
  self.adjudicator.isAITestMode = self.isAITestMode

  -- Teleport car to spawn coordinates and impart rolling launch velocity if configured
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

  -- Lock controls during countdown
  PhysicsHooks.lockControls(3.0, isStanding, targetGear, targetRPM)

  if ac and ac.log then
    ac.log(string.format("[GTLicense] Countdown started | start_mode=%s | isStanding=%s | initial_speed=%.1f km/h | gear=%d | rpm=%d",
      tostring(self.testConfig.start_mode), tostring(isStanding),
      initialSpeed, targetGear, targetRPM))
  end
end

---Evaluates medal rank based on achieved session time.
---@param timeSeconds number
---@return string medal ("GOLD" | "SILVER" | "BRONZE" | "NONE")
function LicenseEngine:evaluateMedal(timeSeconds)
  if self.isAITestMode then
    return "GOLD"
  end
  return Results.evaluateMedal(timeSeconds, self.testConfig and self.testConfig.targets)
end

---Builds the results report table.
---@return table results
function LicenseEngine:compileResults()
  return Results.compileResults(self.testConfig, self.sessionTime, self.achievedMedal, self.failReason)
end

---Called when SessionReset fires a reset.
---@param reason string
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

---Triggers manual session restart immediately.
function LicenseEngine:restart()
  self.sessionReset:executeReset("MANUAL_CALL")
end

---Ends the current session and exits back to Content Manager or AC menu.
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
  -- Check for UI App requested restart
  if self.sharedState and self.sharedState.requestRestart then
    self.sharedState.requestRestart = false
    self:restart()
    return
  end

  -- Check for automated programmed test restart (used for automated telemetry validation)
  if self.restartAtTime and self.state == LicenseEngine.STATE.RUNNING and (self.restartCount or 0) == 0 and self.sessionTime >= self.restartAtTime then
    if ac and ac.log then
      ac.log(string.format("[GTLicense] Automated programmed restart triggered at sessionTime=%.2fs", self.sessionTime))
    end
    self:restart()
    return
  end

  -- Check for UI App requested exit
  if self.sharedState and self.sharedState.requestExit then
    self.sharedState.requestExit = false
    self:exitSession()
    return
  end

  -- Check ESC key for exit during terminal/results states
  if self.state == LicenseEngine.STATE.RESULTS or self.state == LicenseEngine.STATE.PASSED or self.state == LicenseEngine.STATE.FAILED then
    local escPressed = false
    if ui and ui.keyboardButtonPressed and ui.KeyIndex and ui.KeyIndex.Escape then
      escPressed = ui.keyboardButtonPressed(ui.KeyIndex.Escape)
    elseif ac and ac.isKeyPressed and ac.KeyIndex and ac.KeyIndex.Escape then
      escPressed = ac.isKeyPressed(ac.KeyIndex.Escape)
    end
    if escPressed then
      self:exitSession()
      return
    end
  end

  -- 1. Check restart inputs and auto-reset countdown
  self.sessionReset:update(dt)

  local car = ac and ac.getCar and ac.getCar(0)

  -- Ensure car is properly spawned and oriented on the first live simulation frame
  if not self.spawnInitialized and car then
    self.spawnInitialized = true
    if self.isTelemetryRecorder then
      -- In telemetry recording mode, preserve Assetto Corsa's native hotlap spawn!
      -- Do NOT force artificial gear, RPM, or velocity overrides.
      if self.aiCoordinator then
        self.aiCoordinator:initAutopilot(0, self.aiLevel or 1.0, self.isTelemetryRecorder)
      end
      if physics and physics.lockUserControlsFor then
        physics.lockUserControlsFor(0)
      end
      if physics and physics.setCarNoInput then
        physics.setCarNoInput(false)
      end
      if physics and physics.forceUserThrottleFor then
        physics.forceUserThrottleFor(0, 0)
      end
      if physics and physics.forceUserBrakesFor then
        physics.forceUserBrakesFor(0, 0)
      end
      if physics and physics.forceUserHandbrakeFor then
        physics.forceUserHandbrakeFor(0, 0)
      end

      if ac and ac.log then
        ac.log(string.format("[GTLicense] First live frame telemetry recorder init (native hotlap start): spd=%.2f km/h, gear=%d, AI level=%.2f",
          car.speedKmh, car.gear, self.aiLevel or 1.0))
      end
      return
    end

    local spawnOk, spawnErr = PhysicsHooks.setupSpawn(self.testConfig, 0)
    if not spawnOk then
      if ac and ac.log then
        ac.log(string.format("[GTLicense] CRITICAL: Live frame setupSpawn failed: %s! Aborting countdown to prevent pit collision.", tostring(spawnErr)))
      end
      self.state = LicenseEngine.STATE.FAILED
      self.failReason = "Invalid Spawn Configuration: " .. tostring(spawnErr)
      return
    end

    local isStanding = (self.testConfig.start_mode == "STANDING")
    PhysicsHooks.lockControls(3.0, isStanding, self.targetStartingGear, self.targetStartingRPM)

    if ac and ac.log then
      ac.log(string.format("[GTLicense] First live frame spawn applied: pos=(%.2f, %.2f, %.2f), look=(%.2f, %.2f, %.2f), speed=%.2f km/h",
        car.position.x, car.position.y, car.position.z,
        car.look.x, car.look.y, car.look.z, car.speedKmh))
    end
    -- Allow one physics integration step for car kinematics & gear engagement to settle
    return
  end

  -- 2. State machine evaluation
  if self.state == LicenseEngine.STATE.COUNTDOWN then
    self.countdownTimer = self.countdownTimer - dt
    local currentStep = math.ceil(self.countdownTimer)

    -- AI / rolling / standing physics maintenance during countdown:
    if self.testConfig and self.testConfig.spawn then
      local initialSpeed = tonumber(self.testConfig.spawn.initial_speed_kmh) or 0
      local isStanding = (self.testConfig.start_mode == "STANDING") or (initialSpeed <= 0)
      local targetGear = self.targetStartingGear
        or (tonumber(self.testConfig.spawn.gear) and tonumber(self.testConfig.spawn.gear) > 0 and tonumber(self.testConfig.spawn.gear))
        or (isStanding and 1 or PhysicsHooks.estimateStartingGear(initialSpeed))
      local targetRPM = self.targetStartingRPM
        or (tonumber(self.testConfig.spawn.rpm) and tonumber(self.testConfig.spawn.rpm) > 0 and tonumber(self.testConfig.spawn.rpm))
        or (isStanding and 1000 or 3500)

      if initialSpeed > 0 then
        PhysicsHooks.maintainAIRolling(0, initialSpeed, self.testConfig.spawn.forward_vector, dt, targetGear, targetRPM)
      else
        -- Standing start: maintain 1st gear engaged and brakes held during countdown
        if not car or car.gear ~= 1 then
          if physics and physics.engageGear then
            physics.engageGear(0, 1)
          end
        end
      end
    end

    if currentStep >= 1 and currentStep < self.countdownLastStep then
      self.countdownLastStep = currentStep
      dispatchEvent(self, "countdownTick", currentStep)
      if self.telemetryLogger then
        self.telemetryLogger:logCountdownTick(car, currentStep)
      end
    end

    if self.countdownTimer <= 0 then
      -- Release AI autopilot and hand control to player on GO! (or maintain autopilot if isAITestMode)
      local initSpeed = tonumber(self.testConfig.spawn and self.testConfig.spawn.initial_speed_kmh) or 0
      local isStanding = (self.testConfig.start_mode == "STANDING") or (initSpeed <= 0)
      local targetGear = self.targetStartingGear
        or (self.testConfig.spawn and self.testConfig.spawn.gear and tonumber(self.testConfig.spawn.gear) > 0 and tonumber(self.testConfig.spawn.gear))
        or (isStanding and 1 or PhysicsHooks.estimateStartingGear(initSpeed))

      if self.isAITestMode then
        -- Autonomous AI test mode: keep AI autopilot engaged at target AI level (e.g. 95%)
        if self.aiCoordinator then
          self.aiCoordinator:initAutopilot(0, self.aiLevel or 0.95, false)
        end
        PhysicsHooks.unlockControls(0, targetGear)
        self.isAIRollingActive = false
        if ac and ac.log then
          ac.log(string.format("[GTLicense] AI Test Mode ACTIVE: Autopilot maintained at %.0f%% AI level", (self.aiLevel or 0.95) * 100))
        end
      else
        if self.isAIRollingActive or initSpeed > 0 then
          PhysicsHooks.stopAIRolling(0, targetGear)
          self.isAIRollingActive = false
        else
          PhysicsHooks.unlockControls(0, targetGear)
        end
      end

      if self.aiCoordinator then
        self.aiCoordinator:triggerGreenFlag()
      end
      if self.adjudicator and (self.testConfig.start_mode == "ROLLING") then
        self.adjudicator.hasPassedStartGate = true
      end
      dispatchEvent(self, "go")
      self:setState(LicenseEngine.STATE.RUNNING)
      if self.telemetryLogger then
        self.telemetryLogger:logCountdownGo(car, targetGear)
      end
    end

  elseif self.state == LicenseEngine.STATE.RUNNING then
    self.sessionTime = self.sessionTime + dt

    -- Continuously maintain AI autopilot parameters at maximum performance in AI test mode
    if self.isAITestMode and self.aiCoordinator then
      self.aiCoordinator:maintainAutopilot(0, math.max(1.0, self.aiLevel or 1.0), self.isTelemetryRecorder)
    end

    if self.telemetryLogger then
      self.telemetryLogger:logLiveTrack(car, self.sessionTime)
    end

    -- Ensure gear remains firmly engaged right after handover on rolling and standing starts
    if self.sessionTime < 0.5 and self.testConfig and self.testConfig.spawn then
      local initSpeed = tonumber(self.testConfig.spawn.initial_speed_kmh) or 0
      local isStanding = (self.testConfig.start_mode == "STANDING") or (initSpeed <= 0)
      local targetGear = self.targetStartingGear
        or (tonumber(self.testConfig.spawn.gear) and tonumber(self.testConfig.spawn.gear) > 0 and tonumber(self.testConfig.spawn.gear))
        or (isStanding and 1 or PhysicsHooks.estimateStartingGear(initSpeed))
      local targetRPM = self.targetStartingRPM
        or (tonumber(self.testConfig.spawn.rpm) and tonumber(self.testConfig.spawn.rpm) > 0 and tonumber(self.testConfig.spawn.rpm))
        or (isStanding and 1000 or 3500)
      if car and car.gear < targetGear and physics and physics.engageGear then
        physics.engageGear(0, targetGear)
      end
      if car and car.rpm < 2000 and physics and physics.setEngineRPM and not isStanding then
        physics.setEngineRPM(0, targetRPM)
      end
    elseif self.sessionTime >= 0.5 and not self.gearOverrideReleased then
      self.gearOverrideReleased = true
      PhysicsHooks.releaseGearOverride(0)
      if ac and ac.log then
        ac.log("[GTLicense] Handover gear guard expired (t>=0.5s) | Released sticky gearbox control override")
      end
    end

    -- Autonomous AI transmission shifting & anti-neutral guard in AI test mode
    if self.isAITestMode and self.sessionTime >= 0.5 and car and self.aiCoordinator then
      self.aiCoordinator:updateAIShifting(car)
    end

    -- Telemetry logging of wheel speeds and suspension right after GO
    if self.sessionTime <= 1.2 and self.telemetryLogger then
      self.telemetryLogger:logHandoverKinematics(car, self.sessionTime)
    end

    -- Adjudicate failure conditions and finish gate/stop box completion
    if not self.isTelemetryRecorder then
      local adjResult = self.adjudicator:adjudicate(dt, self.sessionTime, car)

      if adjResult.status == "FAILED" then
        self.failReason = adjResult.reason or "Disqualified"
        self:setState(LicenseEngine.STATE.FAILED)
        dispatchEvent(self, "testFailed", self.failReason)
        -- Do NOT auto restart on timer; wait for user input (hotkey, gamepad, or UI retry)
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
    -- Continuously maintain 50% braking across completed and failed states (PASSED, RESULTS, FAILED)
    local enableAI = (self.state == LicenseEngine.STATE.PASSED or self.state == LicenseEngine.STATE.RESULTS)
    PhysicsHooks.applyFailureBraking(0, 0.5, enableAI)

    if self.state == LicenseEngine.STATE.PASSED then
      -- Brief celebration delay before showing results dialog
      self.resultsTimer = self.resultsTimer - dt
      if self.resultsTimer <= 0 then
        self:setState(LicenseEngine.STATE.RESULTS)
        dispatchEvent(self, "resultsShown", self.results)
      end
    end
  end

  -- 3. Update AI Coordinator
  if self.aiCoordinator then
    self.aiCoordinator:update(dt, self.sessionTime)
  end

  -- 4. Update audio cues if audio manager is loaded
  if GTAudioManager and GTAudioManager.update then
    GTAudioManager.update(dt, self:getNumericState(), self.countdownTimer, self.achievedMedal)
  end

  -- 5. Sync state to Inter-Process Shared State for AC Lua App
  if self.sharedState then
    self.sharedState.isActive = true
    self.sharedState.sessionTime = self.sessionTime
    self.sharedState.currentState = self:getNumericState()
    self.sharedState.countdownTimer = self.countdownTimer
    self.sharedState.isGo = (self.state == LicenseEngine.STATE.RUNNING and self.sessionTime < 0.85)
    self.sharedState.failReason = self.failReason or ""
    if self.testConfig then
      self.sharedState.testId = self.testConfig.test_id or ""
      self.sharedState.testTitle = self.testConfig.title or ""
      self.sharedState.lessonObjective = self.testConfig.lesson_objective or ""
      if self.testConfig.targets then
        self.sharedState.goldTime = self.testConfig.targets.gold_seconds or 0
        self.sharedState.silverTime = self.testConfig.targets.silver_seconds or 0
        self.sharedState.bronzeTime = self.testConfig.targets.bronze_seconds or 0
      end
    end
    if car then
      self.sharedState.speedKmh = car.speedKmh or 0
      self.sharedState.gear = car.gear or 0
      self.sharedState.rpm = car.rpm or 0
    end
    self.sharedState.medalAchieved = self.achievedMedal or ""
  end

  -- 6. Continuous in-game telemetry recording (samples across countdown, running, and restarts)
  if self.telemetryLogger then
    self.telemetryLogger:recordSample(
      car,
      self.sessionTime,
      dt,
      self.state,
      self.countdownTimer,
      self.testConfig,
      self.targetStartingGear,
      self.restartCount
    )
  end
end

-- ==============================================================================
-- Public Getters for HUD, 3D Rendering & Audio Subsystems
-- ==============================================================================

function LicenseEngine:getState()
  return self.state
end

function LicenseEngine:getSessionTime()
  return self.sessionTime
end

function LicenseEngine:getCountdownTimer()
  return math.max(0, self.countdownTimer)
end

function LicenseEngine:getCountdownStep()
  if self.countdownTimer > 0 then
    return math.ceil(self.countdownTimer)
  else
    return 0 -- GO
  end
end

function LicenseEngine:getFailReason()
  return self.failReason
end

function LicenseEngine:getMedal()
  return self.achievedMedal
end

function LicenseEngine:getResults()
  return self.results
end

function LicenseEngine:getActiveTest()
  return self.testConfig
end

function LicenseEngine:getNumericState()
  if self.state == LicenseEngine.STATE.COUNTDOWN then
    return 1
  elseif self.state == LicenseEngine.STATE.RUNNING then
    return 2
  elseif self.state == LicenseEngine.STATE.PASSED or self.state == LicenseEngine.STATE.RESULTS then
    return 3
  elseif self.state == LicenseEngine.STATE.FAILED then
    return 4
  else
    return 0
  end
end

function LicenseEngine:draw3D(dt)
  if GTRenderGates and GTRenderGates.draw3D then
    local car = ac and ac.getCar and ac.getCar(0)
    local carPos = car and car.position
    local speedKmh = car and car.speedKmh
    GTRenderGates.draw3D(dt, carPos, self:getNumericState(), speedKmh)
  end

  -- Ghost wireframe rendering completely removed
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

function LicenseEngine:getGhostState()
  return nil
end

-- ==============================================================================
-- CSP Global Script Hooks Integration
-- ==============================================================================
-- If executed as the top-level CSP scenario script, wire directly into script.*
if script ~= nil then
  local activeEngine = LicenseEngine.new(nil)
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
      activeEngine = LicenseEngine.new(nil)
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

return LicenseEngine

