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
local GTConfigLoader = safeRequire("gt_config_loader")
local GTResults      = safeRequire("gt_results")

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
local GTAudioManager = tryRequireUI("gt_audio_manager")

local GTLicenseShared = nil
pcall(function() GTLicenseShared = require("engine/gt_shared_state") end)
if not GTLicenseShared then
  pcall(function() GTLicenseShared = require("gt_shared_state") end)
end

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

-- Default fallback test configuration & loader delegation
GTLicenseEngine.DEFAULT_TEST_CONFIG = GTConfigLoader.DEFAULT_TEST_CONFIG
GTLicenseEngine.loadTestConfig = GTConfigLoader.loadTestConfig
local DEFAULT_TEST_CONFIG = GTConfigLoader.DEFAULT_TEST_CONFIG

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

  -- Initialize Inter-Process Shared State
  if GTLicenseShared and GTLicenseShared.connect then
    self.sharedState = GTLicenseShared.connect()
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

    if newState == GTLicenseEngine.STATE.FAILED then
      GTPhysicsHooks.applyFailureBraking(0, 0.5)
      if ac and ac.log then
        ac.log(string.format("[GTLicense] Failure triggered: reason='%s' | Deploying 50%% emergency braking", tostring(self.failReason)))
      end
    elseif oldState == GTLicenseEngine.STATE.FAILED then
      GTPhysicsHooks.releaseFailureBraking(0)
      if ac and ac.log then
        ac.log("[GTLicense] Leaving FAILED state | Releasing failure braking")
      end
    end

    dispatchEvent(self, "stateChanged", newState, oldState)
  end
end

---Starts or restarts the 3-2-1 countdown sequence.
function GTLicenseEngine:startCountdown()
  GTPhysicsHooks.releaseFailureBraking(0)
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
  local initialSpeed = tonumber(self.testConfig.spawn and self.testConfig.spawn.initial_speed_kmh or 0) or 0
  self.isAIRollingActive = (not isStanding) and (initialSpeed > 0)

  local targetGear = tonumber(self.testConfig.spawn and self.testConfig.spawn.gear)
  if not targetGear or targetGear <= 0 then
    targetGear = isStanding and 1 or GTPhysicsHooks.estimateStartingGear(initialSpeed)
  end
  local targetRPM = tonumber(self.testConfig.spawn and self.testConfig.spawn.rpm)
  if not targetRPM or targetRPM <= 0 then
    targetRPM = isStanding and 1000 or 3500
  end
  self.targetStartingGear = targetGear
  self.targetStartingRPM = targetRPM

  GTPhysicsHooks.setupSpawn(self.testConfig, 0)

  -- Lock controls during countdown
  GTPhysicsHooks.lockControls(3.0, isStanding, targetGear, targetRPM)

  if ac and ac.log then
    ac.log(string.format("[GTLicense] Countdown started | start_mode=%s | isStanding=%s | initial_speed=%.1f km/h | gear=%d | rpm=%d",
      tostring(self.testConfig.start_mode), tostring(isStanding),
      initialSpeed, targetGear, targetRPM))
  end
end

---Evaluates medal rank based on achieved session time.
---@param timeSeconds number
---@return string medal ("GOLD" | "SILVER" | "BRONZE" | "NONE")
function GTLicenseEngine:evaluateMedal(timeSeconds)
  return GTResults.evaluateMedal(timeSeconds, self.testConfig and self.testConfig.targets)
end

---Builds the results report table.
---@return table results
function GTLicenseEngine:compileResults()
  return GTResults.compileResults(self.testConfig, self.sessionTime, self.achievedMedal, self.failReason)
end

---Called when GTSessionReset fires a reset.
---@param reason string
function GTLicenseEngine:onSessionResetTriggered(reason)
  GTPhysicsHooks.releaseFailureBraking(0)
  if self.isAIRollingActive then
    GTPhysicsHooks.stopAIRolling(0, 0)
    self.isAIRollingActive = false
  end
  if self.ghostManager then
    self.ghostManager:reset()
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
  -- Check for UI App requested restart
  if self.sharedState and self.sharedState.requestRestart then
    self.sharedState.requestRestart = false
    self:restart()
    return
  end

  -- 1. Check restart inputs and auto-reset countdown
  self.sessionReset:update(dt)

  local car = ac and ac.getCar and ac.getCar(0)

  -- Ensure car is properly spawned and oriented on the first live simulation frame
  if not self.spawnInitialized and car then
    self.spawnInitialized = true
    GTPhysicsHooks.setupSpawn(self.testConfig, 0)
    local isStanding = (self.testConfig.start_mode == "STANDING")
    GTPhysicsHooks.lockControls(3.0, isStanding, self.targetStartingGear, self.targetStartingRPM)

    if ac and ac.log then
      ac.log(string.format("[GTLicense] First live frame spawn applied: pos=(%.2f, %.2f, %.2f), look=(%.2f, %.2f, %.2f), speed=%.2f km/h",
        car.position.x, car.position.y, car.position.z,
        car.look.x, car.look.y, car.look.z, car.speedKmh))
    end
    -- Allow one physics integration step for car kinematics & gear engagement to settle
    return
  end

  -- 2. State machine evaluation
  if self.state == GTLicenseEngine.STATE.COUNTDOWN then
    self.countdownTimer = self.countdownTimer - dt
    local currentStep = math.ceil(self.countdownTimer)

    -- AI / rolling / standing physics maintenance during countdown:
    if self.testConfig and self.testConfig.spawn then
      local initialSpeed = tonumber(self.testConfig.spawn.initial_speed_kmh) or 0
      local isStanding = (self.testConfig.start_mode == "STANDING") or (initialSpeed <= 0)
      local targetGear = self.targetStartingGear
        or (tonumber(self.testConfig.spawn.gear) and tonumber(self.testConfig.spawn.gear) > 0 and tonumber(self.testConfig.spawn.gear))
        or (isStanding and 1 or GTPhysicsHooks.estimateStartingGear(initialSpeed))
      local targetRPM = self.targetStartingRPM
        or (tonumber(self.testConfig.spawn.rpm) and tonumber(self.testConfig.spawn.rpm) > 0 and tonumber(self.testConfig.spawn.rpm))
        or (isStanding and 1000 or 3500)

      if initialSpeed > 0 then
        GTPhysicsHooks.maintainAIRolling(0, initialSpeed, self.testConfig.spawn.forward_vector, dt, targetGear, targetRPM)
      else
        -- Standing start: maintain 1st gear engaged and brakes held during countdown
        if not car or car.gear ~= 1 then
          if physics and physics.engageGear then
            physics.engageGear(0, 1)
          end
        end
        if ac and ac.overrideCarControls then
          local ctrl = ac.overrideCarControls(0)
          if ctrl then
            ctrl.requestedGearIndex = 1
          end
        end
      end
    end

    if currentStep >= 1 and currentStep < self.countdownLastStep then
      self.countdownLastStep = currentStep
      dispatchEvent(self, "countdownTick", currentStep)
      if ac and ac.log then
        local spd = car and car.speedKmh or 0
        local gear = car and car.gear or 0
        local lx = car and car.look and car.look.x or 0
        local lz = car and car.look and car.look.z or 0
        local hb = car and car.handbrake or 0
        local brk = car and car.brake or 0
        local gas = car and car.gas or 0
        local vy = car and car.velocity and car.velocity.y or 0
        local wFL = (car and car.wheels and car.wheels[0] and car.wheels[0].angularSpeed) or 0
        local wFR = (car and car.wheels and car.wheels[1] and car.wheels[1].angularSpeed) or 0
        local wRL = (car and car.wheels and car.wheels[2] and car.wheels[2].angularSpeed) or 0
        local wRR = (car and car.wheels and car.wheels[3] and car.wheels[3].angularSpeed) or 0
        local sFL = (car and car.wheels and car.wheels[0] and car.wheels[0].suspensionTravel) or 0
        local sRL = (car and car.wheels and car.wheels[2] and car.wheels[2].suspensionTravel) or 0
        local ldFL = (car and car.wheels and car.wheels[0] and car.wheels[0].load) or 0
        local ldRL = (car and car.wheels and car.wheels[2] and car.wheels[2].load) or 0
        local slpRL = (car and car.wheels and car.wheels[2] and car.wheels[2].slipRatio) or 0
        local cphys = ac.getCarPhysics and ac.getCarPhysics(0)
        local dtVel = cphys and cphys.drivetrainVelocity or 0
        local clState = cphys and cphys.clutchState or 0
        local px = car and car.position and car.position.x or 0
        local py = car and car.position and car.position.y or 0
        local pz = car and car.position and car.position.z or 0
        local st = car and car.steer or 0
        ac.log(string.format("[GTLicense] Countdown Tick %d | Spd=%.1f | Gear=%d | pos=(%.1f, %.1f, %.1f) | vy=%.2f | Gas=%.2f | Susp=(FL:%.3f, RL:%.3f) | Load=(FL:%.0f, RL:%.0f) | SlipRL=%.2f | Omegas=(FL:%.1f, FR:%.1f, RL:%.1f, RR:%.1f) | DT=%.1f | Cl=%.2f",
          currentStep, spd, gear, px, py, pz, vy, gas, sFL, sRL, ldFL, ldRL, slpRL, wFL, wFR, wRL, wRR, dtVel, clState))
      end
    end

    if self.countdownTimer <= 0 then
      -- Release AI autopilot and hand control to player on GO!
      local initSpeed = tonumber(self.testConfig.spawn and self.testConfig.spawn.initial_speed_kmh) or 0
      local isStanding = (self.testConfig.start_mode == "STANDING") or (initSpeed <= 0)
      local targetGear = self.targetStartingGear
        or (self.testConfig.spawn and self.testConfig.spawn.gear and tonumber(self.testConfig.spawn.gear) > 0 and tonumber(self.testConfig.spawn.gear))
        or (isStanding and 1 or GTPhysicsHooks.estimateStartingGear(initSpeed))
      if self.isAIRollingActive or initSpeed > 0 then
        GTPhysicsHooks.stopAIRolling(0, targetGear)
        self.isAIRollingActive = false
      else
        GTPhysicsHooks.unlockControls(0, targetGear)
      end

      if self.aiCoordinator then
        self.aiCoordinator:triggerGreenFlag()
      end
      if self.adjudicator and (self.testConfig.start_mode == "ROLLING") then
        self.adjudicator.hasPassedStartGate = true
      end
      dispatchEvent(self, "go")
      self:setState(GTLicenseEngine.STATE.RUNNING)
      if ac and ac.log then
        local spd = car and car.speedKmh or 0
        local lx = car and car.look and car.look.x or 0
        local lz = car and car.look and car.look.z or 0
        local px = car and car.position and car.position.x or 0
        local py = car and car.position and car.position.y or 0
        local pz = car and car.position and car.position.z or 0
        local st = car and car.steer or 0
        local wFL = (car and car.wheels and car.wheels[0] and car.wheels[0].angularSpeed) or 0
        local wFR = (car and car.wheels and car.wheels[1] and car.wheels[1].angularSpeed) or 0
        local wRL = (car and car.wheels and car.wheels[2] and car.wheels[2].angularSpeed) or 0
        local wRR = (car and car.wheels and car.wheels[3] and car.wheels[3].angularSpeed) or 0
        local cphys = ac.getCarPhysics and ac.getCarPhysics(0)
        local dtVel = cphys and cphys.drivetrainVelocity or 0
        local clState = cphys and cphys.clutchState or 0
        local rBrk = cphys and cphys.wheels and cphys.wheels[2] and cphys.wheels[2].brakeTorque or 0
        local rHb = cphys and cphys.wheels and cphys.wheels[2] and cphys.wheels[2].handbrakeTorque or 0
        local rShaft = cphys and cphys.wheels and cphys.wheels[2] and cphys.wheels[2].shaftVelocity or 0
        ac.log(string.format("[GTLicense] Countdown GO! | Spd=%.1f | Gear=%d | pos=(%.1f, %.1f, %.1f) | look=(%.2f, %.2f) | Steer=%.1f deg | Omegas=(FL:%.1f, FR:%.1f, RL:%.1f, RR:%.1f)",
          spd, targetGear, px, py, pz, lx, lz, st, wFL, wFR, wRL, wRR))
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

    -- Ensure gear remains firmly engaged right after handover on rolling and standing starts
    if self.sessionTime < 0.5 and self.testConfig and self.testConfig.spawn then
      local initSpeed = tonumber(self.testConfig.spawn.initial_speed_kmh) or 0
      local isStanding = (self.testConfig.start_mode == "STANDING") or (initSpeed <= 0)
      local targetGear = self.targetStartingGear
        or (tonumber(self.testConfig.spawn.gear) and tonumber(self.testConfig.spawn.gear) > 0 and tonumber(self.testConfig.spawn.gear))
        or (isStanding and 1 or GTPhysicsHooks.estimateStartingGear(initSpeed))
      local targetRPM = self.targetStartingRPM
        or (tonumber(self.testConfig.spawn.rpm) and tonumber(self.testConfig.spawn.rpm) > 0 and tonumber(self.testConfig.spawn.rpm))
        or (isStanding and 1000 or 3500)
      if car and car.gear < targetGear and physics and physics.engageGear then
        physics.engageGear(0, targetGear)
      end
      if car and car.rpm < 2000 and physics and physics.setEngineRPM and not isStanding then
        physics.setEngineRPM(0, targetRPM)
      end
    end

    -- Telemetry logging of wheel speeds and suspension right after GO
    if self.sessionTime <= 1.2 and ac and ac.log then
      if not self.lastPostGoLog or (self.sessionTime - self.lastPostGoLog >= 0.2) then
        self.lastPostGoLog = self.sessionTime
        local wFL = (car and car.wheels and car.wheels[0] and car.wheels[0].angularSpeed) or 0
        local wFR = (car and car.wheels and car.wheels[1] and car.wheels[1].angularSpeed) or 0
        local wRL = (car and car.wheels and car.wheels[2] and car.wheels[2].angularSpeed) or 0
        local wRR = (car and car.wheels and car.wheels[3] and car.wheels[3].angularSpeed) or 0
        local sFL = (car and car.wheels and car.wheels[0] and car.wheels[0].suspensionTravel) or 0
        local sRL = (car and car.wheels and car.wheels[2] and car.wheels[2].suspensionTravel) or 0
        local ldFL = (car and car.wheels and car.wheels[0] and car.wheels[0].load) or 0
        local ldRL = (car and car.wheels and car.wheels[2] and car.wheels[2].load) or 0
        local vy = car and car.velocity and car.velocity.y or 0
        ac.log(string.format("[GTLicense] Post-GO t=%.2fs | Spd=%.1f | Gear=%d | vy=%.2f | Susp=(FL:%.3f, RL:%.3f) | Load=(FL:%.0f, RL:%.0f) | Omegas=(FL:%.1f, FR:%.1f, RL:%.1f, RR:%.1f)",
          self.sessionTime, car and car.speedKmh or 0, car and car.gear or 0, vy, sFL, sRL, ldFL, ldRL, wFL, wFR, wRL, wRR))
      end
    end

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
    -- Fail banner active, waiting for manual restart ('R', space, gamepad) or retry
    -- Continuously maintain 50% failure braking to bring vehicle to a controlled stop
    GTPhysicsHooks.applyFailureBraking(0, 0.5)

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

  -- 5. Sync state to Inter-Process Shared State for AC Lua App
  if self.sharedState then
    self.sharedState.isActive = true
    self.sharedState.sessionTime = self.sessionTime
    self.sharedState.currentState = self:getNumericState()
    self.sharedState.countdownTimer = self.countdownTimer
    self.sharedState.isGo = (self.state == GTLicenseEngine.STATE.RUNNING and self.sessionTime < 0.85)
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
    if self.ghostManager then
      local gState = self.ghostManager:getState()
      if gState then
        self.sharedState.ghostDelta = gState.delta or 0
        self.sharedState.ghostActive = gState.active or false
        self.sharedState.ghostMode = gState.mode or 1
        self.sharedState.ghostOSD = gState.osd_message or ""
      end
    end
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

  -- Ghost wireframe rendering completely removed
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

