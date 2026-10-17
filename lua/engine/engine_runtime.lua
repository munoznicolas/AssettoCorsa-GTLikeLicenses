-- ==============================================================================
-- Gran Turismo License Engine for Assetto Corsa (CSP)
-- File: lua/engine/engine_runtime.lua
-- Description: Runtime helpers, countdown/handover state steppers, IPC shared
--              state synchronization, event registration, and public getters
--              for LicenseEngine.
-- ==============================================================================

local function safeRequire(name)
  local ok, mod = pcall(require, name)
  if ok then return mod end
  ok, mod = pcall(require, "engine/" .. name)
  if ok then return mod end
  ok, mod = pcall(require, "lua/engine/" .. name)
  if ok then return mod end
  return nil
end

local PhysicsHooks = safeRequire("physics_hooks")

local EngineRuntime = {}

---Dispatches an event to all registered listeners on the engine instance.
---@param engine table
---@param eventName string
---@param ... any
function EngineRuntime.dispatchEvent(engine, eventName, ...)
  local list = engine.listeners and engine.listeners[eventName]
  if list then
    for i = 1, #list do
      pcall(list[i], ...)
    end
  end
end

---Reads [GTLICENSE] and [RACE] flags from race.ini into the engine instance.
---@param engine table
function EngineRuntime.loadRaceIniFlags(engine)
  engine.isTelemetryRecorder = (engine.testConfig and (
    engine.testConfig.test_id == "AI_TELEMETRY_RECORDER"
    or engine.testConfig.is_telemetry_recording == true
    or engine.testConfig.isTelemetryRecording == true
  )) or false

  engine.isAITestMode = false
  engine.aiLevel = 1.0
  if engine.isTelemetryRecorder then
    engine.isAITestMode = true
    engine.aiLevel = 1.0
  end

  if ac and ac.INIConfig and ac.INIConfig.raceConfig then
    local ok, race = pcall(ac.INIConfig.raceConfig)
    if ok and race then
      local val = race:get("GTLICENSE", "AI_TEST_MODE", "")
      if val == "1" or val == "true" or val == "TRUE" then
        engine.isAITestMode = true
      end
      local tId = race:get("GTLICENSE", "TEST_ID", "")
      if tId == "AI_TELEMETRY_RECORDER" then
        engine.isTelemetryRecorder = true
        engine.isAITestMode = true
      end
      local rstVal = race:get("GTLICENSE", "RESTART_AT_TIME", "")
      if rstVal and tonumber(rstVal) and tonumber(rstVal) > 0 then
        engine.restartAtTime = tonumber(rstVal)
      end
      local lvl = race:get("RACE", "AI_LEVEL", "")
      if lvl and tonumber(lvl) then
        engine.aiLevel = tonumber(lvl) / 100.0
      end
    end
  end
end

---Releases user control locks and engages AI autopilot for telemetry hotlap recording.
---@param engine table
function EngineRuntime.engageTelemetryRecorderAutopilot(engine)
  if engine.aiCoordinator then
    engine.aiCoordinator:initAutopilot(0, engine.aiLevel or 1.0, engine.isTelemetryRecorder)
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
end

---Handles first live simulation frame initialization of vehicle spawn or telemetry recorder.
---@param engine table
---@param car table
---@param failedState string
---@return boolean handled
function EngineRuntime.initializeFirstLiveFrame(engine, car, failedState)
  engine.spawnInitialized = true
  if engine.isTelemetryRecorder then
    EngineRuntime.engageTelemetryRecorderAutopilot(engine)
    if ac and ac.log then
      ac.log(string.format("[GTLicense] First live frame telemetry recorder init (native hotlap start): spd=%.2f km/h, gear=%d, AI level=%.2f",
        car.speedKmh, car.gear, engine.aiLevel or 1.0))
    end
    return true
  end

  local spawnOk, spawnErr = PhysicsHooks.setupSpawn(engine.testConfig, 0)
  if not spawnOk then
    if ac and ac.log then
      ac.log(string.format("[GTLicense] CRITICAL: Live frame setupSpawn failed: %s! Aborting countdown to prevent pit collision.", tostring(spawnErr)))
    end
    engine.state = failedState
    engine.failReason = "Invalid Spawn Configuration: " .. tostring(spawnErr)
    return true
  end

  local isStanding = (engine.testConfig.start_mode == "STANDING")
  PhysicsHooks.lockControls(3.0, isStanding, engine.targetStartingGear, engine.targetStartingRPM)

  if ac and ac.log then
    ac.log(string.format("[GTLicense] First live frame spawn applied: pos=(%.2f, %.2f, %.2f), look=(%.2f, %.2f, %.2f), speed=%.2f km/h",
      car.position.x, car.position.y, car.position.z,
      car.look.x, car.look.y, car.look.z, car.speedKmh))
  end
  return true
end

---Updates the COUNTDOWN state (3-2-1 ticks, rolling AI maintenance, and GO! handover).
---@param engine table
---@param dt number
---@param car table?
---@param runningState string
function EngineRuntime.updateCountdown(engine, dt, car, runningState)
  engine.countdownTimer = engine.countdownTimer - dt
  local currentStep = math.ceil(engine.countdownTimer)

  if engine.testConfig and engine.testConfig.spawn then
    local initialSpeed = tonumber(engine.testConfig.spawn.initial_speed_kmh) or 0
    local isStanding = (engine.testConfig.start_mode == "STANDING") or (initialSpeed <= 0)
    local targetGear = engine.targetStartingGear
      or (tonumber(engine.testConfig.spawn.gear) and tonumber(engine.testConfig.spawn.gear) > 0 and tonumber(engine.testConfig.spawn.gear))
      or (isStanding and 1 or PhysicsHooks.estimateStartingGear(initialSpeed))
    local targetRPM = engine.targetStartingRPM
      or (tonumber(engine.testConfig.spawn.rpm) and tonumber(engine.testConfig.spawn.rpm) > 0 and tonumber(engine.testConfig.spawn.rpm))
      or (isStanding and 1000 or 3500)

    if initialSpeed > 0 then
      PhysicsHooks.maintainAIRolling(0, initialSpeed, engine.testConfig.spawn.forward_vector, dt, targetGear, targetRPM)
    else
      if not car or car.gear ~= 1 then
        if physics and physics.engageGear then
          physics.engageGear(0, 1)
        end
      end
    end
  end

  if currentStep >= 1 and currentStep < engine.countdownLastStep then
    engine.countdownLastStep = currentStep
    EngineRuntime.dispatchEvent(engine, "countdownTick", currentStep)
    if engine.telemetryLogger then
      engine.telemetryLogger:logCountdownTick(car, currentStep)
    end
  end

  if engine.countdownTimer <= 0 then
    local initSpeed = tonumber(engine.testConfig.spawn and engine.testConfig.spawn.initial_speed_kmh) or 0
    local isStanding = (engine.testConfig.start_mode == "STANDING") or (initSpeed <= 0)
    local targetGear = engine.targetStartingGear
      or (engine.testConfig.spawn and engine.testConfig.spawn.gear and tonumber(engine.testConfig.spawn.gear) > 0 and tonumber(engine.testConfig.spawn.gear))
      or (isStanding and 1 or PhysicsHooks.estimateStartingGear(initSpeed))

    if engine.isAITestMode then
      if engine.aiCoordinator then
        engine.aiCoordinator:initAutopilot(0, engine.aiLevel or 0.95, false)
      end
      PhysicsHooks.unlockControls(0, targetGear)
      engine.isAIRollingActive = false
      if ac and ac.log then
        ac.log(string.format("[GTLicense] AI Test Mode ACTIVE: Autopilot maintained at %.0f%% AI level", (engine.aiLevel or 0.95) * 100))
      end
    else
      if engine.isAIRollingActive or initSpeed > 0 then
        PhysicsHooks.stopAIRolling(0, targetGear)
        engine.isAIRollingActive = false
      else
        PhysicsHooks.unlockControls(0, targetGear)
      end
    end

    if engine.aiCoordinator then
      engine.aiCoordinator:triggerGreenFlag()
    end
    if engine.adjudicator and (engine.testConfig.start_mode == "ROLLING") then
      engine.adjudicator.hasPassedStartGate = true
    end
    EngineRuntime.dispatchEvent(engine, "go")
    engine:setState(runningState)
    if engine.telemetryLogger then
      engine.telemetryLogger:logCountdownGo(car, targetGear)
    end
  end
end

---Maintains the 0.5s post-GO gear/RPM guard and AI shifting during RUNNING state.
---@param engine table
---@param car table?
function EngineRuntime.updateRunningHandover(engine, car)
  if engine.sessionTime < 0.5 and engine.testConfig and engine.testConfig.spawn then
    local initSpeed = tonumber(engine.testConfig.spawn.initial_speed_kmh) or 0
    local isStanding = (engine.testConfig.start_mode == "STANDING") or (initSpeed <= 0)
    local targetGear = engine.targetStartingGear
      or (tonumber(engine.testConfig.spawn.gear) and tonumber(engine.testConfig.spawn.gear) > 0 and tonumber(engine.testConfig.spawn.gear))
      or (isStanding and 1 or PhysicsHooks.estimateStartingGear(initSpeed))
    local targetRPM = engine.targetStartingRPM
      or (tonumber(engine.testConfig.spawn.rpm) and tonumber(engine.testConfig.spawn.rpm) > 0 and tonumber(engine.testConfig.spawn.rpm))
      or (isStanding and 1000 or 3500)
    if car and car.gear < targetGear and physics and physics.engageGear then
      physics.engageGear(0, targetGear)
    end
    if car and car.rpm < 2000 and physics and physics.setEngineRPM and not isStanding then
      physics.setEngineRPM(0, targetRPM)
    end
  elseif engine.sessionTime >= 0.5 and not engine.gearOverrideReleased then
    engine.gearOverrideReleased = true
    PhysicsHooks.releaseGearOverride(0)
    if ac and ac.log then
      ac.log("[GTLicense] Handover gear guard expired (t>=0.5s) | Released sticky gearbox control override")
    end
  end

  if engine.isAITestMode and engine.sessionTime >= 0.5 and car and engine.aiCoordinator then
    engine.aiCoordinator:updateAIShifting(car)
  end

  if engine.sessionTime <= 1.2 and engine.telemetryLogger then
    engine.telemetryLogger:logHandoverKinematics(car, engine.sessionTime)
  end
end

---Synchronizes engine state to Inter-Process Shared State for the AC Lua App.
---@param engine table
---@param car table?
---@param runningState string
function EngineRuntime.syncSharedState(engine, car, runningState)
  if not engine.sharedState then return end
  engine.sharedState.isActive = true
  engine.sharedState.sessionTime = engine.sessionTime
  engine.sharedState.currentState = engine:getNumericState()
  engine.sharedState.countdownTimer = engine.countdownTimer
  engine.sharedState.isGo = (engine.state == runningState and engine.sessionTime < 0.85)
  engine.sharedState.failReason = engine.failReason or ""
  if engine.testConfig then
    engine.sharedState.testId = engine.testConfig.test_id or ""
    engine.sharedState.testTitle = engine.testConfig.title or ""
    engine.sharedState.lessonObjective = engine.testConfig.lesson_objective or ""
    if engine.testConfig.targets then
      engine.sharedState.goldTime = engine.testConfig.targets.gold_seconds or 0
      engine.sharedState.silverTime = engine.testConfig.targets.silver_seconds or 0
      engine.sharedState.bronzeTime = engine.testConfig.targets.bronze_seconds or 0
    end
  end
  if car then
    engine.sharedState.speedKmh = car.speedKmh or 0
    engine.sharedState.gear = car.gear or 0
    engine.sharedState.rpm = car.rpm or 0
  end
  engine.sharedState.medalAchieved = engine.achievedMedal or ""
end

---Attaches event listener methods and public getters to the LicenseEngine table.
---@param LicenseEngine table
function EngineRuntime.attachMethods(LicenseEngine)
  function LicenseEngine:onStateChanged(fn)
    table.insert(self.listeners.stateChanged, fn)
  end

  function LicenseEngine:onCountdownTick(fn)
    table.insert(self.listeners.countdownTick, fn)
  end

  function LicenseEngine:onGo(fn)
    table.insert(self.listeners.go, fn)
  end

  function LicenseEngine:onTestPassed(fn)
    table.insert(self.listeners.testPassed, fn)
  end

  function LicenseEngine:onTestFailed(fn)
    table.insert(self.listeners.testFailed, fn)
  end

  function LicenseEngine:onResultsShown(fn)
    table.insert(self.listeners.resultsShown, fn)
  end

  function LicenseEngine:onReset(fn)
    table.insert(self.listeners.reset, fn)
  end

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
      return 0
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

  function LicenseEngine:getGhostState()
    return nil
  end
end

---Handles external UI restart/exit requests, automated test restarts, and terminal ESC key exits.
---@param engine table
---@param STATE table
---@return boolean interrupted
function EngineRuntime.checkSessionInterrupts(engine, STATE)
  if engine.sharedState and engine.sharedState.requestRestart then
    engine.sharedState.requestRestart = false
    engine:restart()
    return true
  end

  if engine.restartAtTime and engine.state == STATE.RUNNING and (engine.restartCount or 0) == 0 and engine.sessionTime >= engine.restartAtTime then
    if ac and ac.log then
      ac.log(string.format("[GTLicense] Automated programmed restart triggered at sessionTime=%.2fs", engine.sessionTime))
    end
    engine:restart()
    return true
  end

  if engine.sharedState and engine.sharedState.requestExit then
    engine.sharedState.requestExit = false
    engine:exitSession()
    return true
  end

  if engine.state == STATE.RESULTS or engine.state == STATE.PASSED or engine.state == STATE.FAILED then
    local escPressed = false
    if ui and ui.keyboardButtonPressed and ui.KeyIndex and ui.KeyIndex.Escape then
      escPressed = ui.keyboardButtonPressed(ui.KeyIndex.Escape)
    elseif ac and ac.isKeyPressed and ac.KeyIndex and ac.KeyIndex.Escape then
      escPressed = ac.isKeyPressed(ac.KeyIndex.Escape)
    end
    if escPressed then
      engine:exitSession()
      return true
    end
  end

  return false
end

---Binds LicenseEngine to global CSP `script.*` lifecycle hooks when running inside AC.
---@param LicenseEngine table
---@param hud table?
---@param gates table?
---@param audio table?
function EngineRuntime.bindCSPHooks(LicenseEngine, hud, gates, audio)
  if script == nil then return end

  local function initAll()
    local eng = LicenseEngine.new(nil)
    if hud and hud.init then hud.init(eng:getActiveTest()) end
    if gates and gates.init then gates.init(eng:getActiveTest()) end
    if audio and audio.init then audio.init() end
    return eng
  end

  local activeEngine = initAll()

  function script.init()
    if not activeEngine then activeEngine = initAll() end
  end

  function script.update(dt)
    if activeEngine then activeEngine:update(dt) end
  end

  function script.draw3D(dt)
    if activeEngine then activeEngine:draw3D(dt) end
  end

  function script.drawUI()
    if activeEngine then activeEngine:drawUI() end
  end
end

return EngineRuntime
