-- ==============================================================================
-- Gran Turismo License Engine for Assetto Corsa (CSP)
-- File: lua/engine/ai_coordinator.lua
-- Description: AI Autopilot & Calibration Coordinator for Solo License Tests.
--              Coordinates native Assetto Corsa AI autopilot lifecycle, telemetry
--              evaluation runs, and transmission anti-neutral recovery on vehicle 0.
-- ==============================================================================

local AICoordinator = {}
AICoordinator.__index = AICoordinator

---Creates a new AICoordinator instance for the single-vehicle license session.
---@param testConfig table @Table complying with test_definition.schema.json
---@return table instance
function AICoordinator.new(testConfig)
  local self = setmetatable({}, AICoordinator)

  self.testConfig = testConfig or {}
  self.isGreenFlag = false

  return self
end

---Updates AI coordinator state machine.
---In GT License tests, only vehicle 0 (player car) exists.
---@param dt number @Frame delta time in seconds
---@param sessionTime number @Accumulated session time in seconds
function AICoordinator:update(dt, sessionTime)
  -- Vehicle 0 countdown physics and rolling starts are maintained directly via PhysicsHooks
end

---Triggers Green Flag release event at session GO.
function AICoordinator:triggerGreenFlag()
  self.isGreenFlag = true
end

---Initializes native AI autopilot parameters on a vehicle (car 0).
---@param carIndex integer? @0-based car index (default: 0)
---@param aiLevel number? @AI proficiency (0.0 to 1.0)
---@param isTelemetryRecorder boolean? @Whether in telemetry recorder mode
function AICoordinator:initAutopilot(carIndex, aiLevel, isTelemetryRecorder)
  carIndex = carIndex or 0
  aiLevel = aiLevel or 1.0
  if physics and physics.setCarAutopilot then
    physics.setCarAutopilot(true, false)
  end
  self:maintainAutopilot(carIndex, aiLevel, isTelemetryRecorder)
end

---Continuously asserts AI autopilot parameters for performance and spline adherence.
---@param carIndex integer? @0-based car index (default: 0)
---@param aiLevel number? @AI proficiency (0.0 to 1.0)
---@param isTelemetryRecorder boolean? @Whether in telemetry recorder mode
function AICoordinator:maintainAutopilot(carIndex, aiLevel, isTelemetryRecorder)
  carIndex = carIndex or 0
  aiLevel = aiLevel or 1.0
  if physics and physics.setAILevel then
    physics.setAILevel(carIndex, aiLevel)
  end
  if physics and physics.setAIAggression then
    physics.setAIAggression(carIndex, isTelemetryRecorder and 0.0 or 1.0)
  end
  if physics and physics.setAICaution then
    physics.setAICaution(carIndex, 0.0)
  end
  if physics and physics.setAITopSpeed then
    physics.setAITopSpeed(carIndex, 999999.0)
  end
  if physics and physics.setAISplineAbsoluteOffset then
    physics.setAISplineAbsoluteOffset(carIndex, 0.0, false)
  end
  if physics and physics.setAIThrottleLimit then
    physics.setAIThrottleLimit(carIndex, 1.0)
  end
end

---Ensures the vehicle is not stalled in neutral if user controls previously interfered.
---All regular gear shifting (upshifts, downshifts, powerband management) is completely handled
---by Assetto Corsa's native AI transmission logic.
---@param car table? @Assetto Corsa car state (ac.getCar)
function AICoordinator:updateAIShifting(car)
  if not car then return end

  -- Anti-neutral recovery: If vehicle slips to neutral (gear <= 0) while rolling, engage 1st gear
  if car.gear <= 0 and car.speedKmh > 5 then
    if physics and physics.engageGear then
      physics.engageGear(0, 1)
    end
    if ac and ac.overrideCarControls then
      local ctrl = ac.overrideCarControls(0)
      if ctrl then ctrl.requestedGearIndex = 1 end
    end
  end
end

return AICoordinator
