-- ==============================================================================
-- Gran Turismo License Engine for Assetto Corsa (CSP)
-- File: lua/engine/ai_coordinator.lua
-- Description: AI Traffic, Pace Car, and 2-Phase Rolling Start Coordinator.
--              Handles spline progress distance math, proportional gap scaling,
--              organic micro-weaving, and smooth green-flag transitions.
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

local AICoordinator = {}
AICoordinator.__index = AICoordinator

-- Operational Phases for Rolling Starts
AICoordinator.PHASE = {
  WARMUP_SINGLE_FILE = "WARMUP_SINGLE_FILE",
  GRID_DOUBLE_FILE   = "GRID_DOUBLE_FILE",
  GREEN_FLAG         = "GREEN_FLAG"
}

---Calculates the physical distance in meters along the track spline between two vehicles.
---@param carAheadIdx integer @0-based car index of lead vehicle
---@param carBehindIdx integer @0-based car index of trailing vehicle
---@return number distanceMeters
function AICoordinator.getSplineDistanceMeters(carAheadIdx, carBehindIdx)
  if not ac or not ac.getCar or not ac.getSim then
    return 0.0
  end

  local carAhead = ac.getCar(carAheadIdx)
  local carBehind = ac.getCar(carBehindIdx)

  if not carAhead or not carBehind then
    return 0.0
  end

  local trackLength = ac.getSim().trackLengthM or 1000.0
  local splineDelta = carAhead.splinePosition - carBehind.splinePosition

  -- Handle lap wrap-around if lead car has crossed start/finish line
  if splineDelta < -0.5 then
    splineDelta = splineDelta + 1.0
  elseif splineDelta > 0.5 then
    splineDelta = splineDelta - 1.0
  end

  return splineDelta * trackLength
end

---Computes a proportional speed scaling multiplier based on distance gap error.
---@param distMeters number @Current physical distance in meters
---@param targetGap number @Target desired gap in meters (default: 8.0m)
---@param minGap number @Minimum safety threshold distance (default: 1.5m)
---@param maxMult number? @Maximum catch-up speed multiplier (default: 1.5)
---@return number multiplier
function AICoordinator.getLinearSpeedMultiplier(distMeters, targetGap, minGap, maxMult)
  targetGap = targetGap or 8.0
  minGap = minGap or 1.5
  maxMult = maxMult or 1.5

  if distMeters <= minGap then
    return 0.0
  end

  if distMeters <= targetGap then
    local ratio = (distMeters - minGap) / (targetGap - minGap)
    return math.max(0.50, ratio)
  end

  local maxGap = targetGap + 12.0
  if distMeters >= maxGap then
    return maxMult
  end

  return 1.0 + ((distMeters - targetGap) / (maxGap - targetGap)) * (maxMult - 1.0)
end

---Generates an organic sine/cosine micro-weaving offset for realistic AI lane behavior.
---@param driverIdx integer @0-based driver index
---@param sessionTime number @Current session time in seconds
---@return number lateralOffsetMeters
function AICoordinator.getOrganicLaneOffset(driverIdx, sessionTime)
  driverIdx = driverIdx or 0
  sessionTime = sessionTime or 0

  local wave1 = math.sin(sessionTime * 0.25 + driverIdx * 1.7) * 0.40
  local wave2 = math.cos(sessionTime * 0.40 - driverIdx * 2.3) * 0.10

  return wave1 + wave2
end

---Creates a new AICoordinator instance from a test configuration table.
---@param testConfig table @Table complying with test_definition.schema.json
---@return table instance
function AICoordinator.new(testConfig)
  local self = setmetatable({}, AICoordinator)

  self.testConfig = testConfig or {}
  self.phase = AICoordinator.PHASE.WARMUP_SINGLE_FILE
  self.isGreenFlag = false

  -- Rolling Start Parameters
  local rs = testConfig.rolling_start or {}
  self.phase1SpeedKmh = rs.phase1_speed_kmh or 100.0
  self.phase2SpeedKmh = rs.phase2_speed_kmh or 70.0
  self.formationPointPct = rs.formation_point_pct or 0.67
  self.laneDistanceM = rs.lane_distance_m or 3.0
  self.p1LaneSide = rs.p1_lane_side or "LEFT"

  -- Pace Car Parameters
  local pc = testConfig.pace_car or {}
  self.isPaceCarActive = (testConfig.start_mode == "PACE_CAR") or (pc.enabled == true)
  self.paceCarIndex = pc.car_index or 1
  self.paceSpeedKmh = pc.target_speed_kmh or 80.0
  self.paceTargetGapM = pc.target_gap_m or 10.0
  self.paceMaxAllowedGapM = pc.max_allowed_gap_m or 30.0

  -- Dynamic Tracking Tables
  self.currentSplineOffsets = {}
  self.hasEnteredPhase2 = {}

  return self
end

---Updates AI traffic, pace car regulation, or rolling start state machine.
---@param dt number @Frame delta time in seconds
---@param sessionTime number @Accumulated session time in seconds
function AICoordinator:update(dt, sessionTime)
  if not ac or not ac.getSim then return end

  local sim = ac.getSim()
  local carsCount = sim.carsCount or 1

  -- 1. Handle Pace Car Test Mode (IB-5)
  if self.isPaceCarActive then
    self:updatePaceCar(dt, sessionTime)
  end

  -- 2. Handle Rolling Start Procedure
  if self.testConfig.start_mode == "ROLLING" and not self.isGreenFlag then
    self:updateRollingStart(dt, sessionTime, carsCount)
  elseif self.isGreenFlag then
    self:updateGreenFlagTransition(dt, carsCount)
  end
end

---Regulates Pace Car behavior (e.g. IB-5 Pace Car Challenge).
---@param dt number @Frame delta time
---@param sessionTime number @Session time in seconds
function AICoordinator:updatePaceCar(dt, sessionTime)
  if not ac or not ac.getCar then return end

  local paceCar = ac.getCar(self.paceCarIndex)
  if not paceCar then return end

  -- Apply top speed ceiling on Pace Car
  if PhysicsHooks then
    PhysicsHooks.setAITopSpeed(self.paceCarIndex, self.paceSpeedKmh)
    PhysicsHooks.setAIThrottleLimit(self.paceCarIndex, 1.0)
    PhysicsHooks.setAICaution(self.paceCarIndex, 2.0)
  end
end

---Manages 2-Phase Rolling Start grid logic and speed scaling.
---@param dt number @Frame delta time
---@param sessionTime number @Session time in seconds
---@param carsCount integer @Total number of cars in session
function AICoordinator:updateRollingStart(dt, sessionTime, carsCount)
  if not ac or not ac.getCar then return end

  local leadCar = ac.getCar(0)
  if not leadCar then return end

  -- Check if leader has reached formation point threshold (e.g. 67% spline position)
  if leadCar.splinePosition >= self.formationPointPct and self.phase == AICoordinator.PHASE.WARMUP_SINGLE_FILE then
    self.phase = AICoordinator.PHASE.GRID_DOUBLE_FILE
  end

  for i = 1, carsCount - 1 do
    local car = ac.getCar(i)
    if car and car.isAIControlled then
      local targetSpeed = self.phase1SpeedKmh
      local targetOffset = 0.0
      local caution = 1.0

      if self.phase == AICoordinator.PHASE.GRID_DOUBLE_FILE then
        targetSpeed = self.phase2SpeedKmh
        caution = 0.7

        -- Stagger Left / Right lanes based on grid position (odd vs even)
        local isOdd = (car.racePosition % 2 == 1)
        local baseOffset = isOdd and -self.laneDistanceM or self.laneDistanceM
        if self.p1LaneSide == "RIGHT" then
          baseOffset = -baseOffset
        end

        targetOffset = baseOffset + AICoordinator.getOrganicLaneOffset(i, sessionTime)

        -- Proportional gap scaling relative to car ahead in column
        local aheadIdx = (car.racePosition > 2) and (car.racePosition - 2) or 0
        local gap = AICoordinator.getSplineDistanceMeters(aheadIdx, i)
        if gap > 0 then
          local mult = AICoordinator.getLinearSpeedMultiplier(gap, 8.0, 1.5, 1.4)
          targetSpeed = targetSpeed * mult
        end
      else
        -- Phase 1 (Single File): Maintain single line with catch-up scaling
        local leadIdx = car.racePosition - 1
        local gap = AICoordinator.getSplineDistanceMeters(leadIdx, i)
        if gap > 40.0 then
          targetSpeed = self.phase1SpeedKmh * 1.25
        elseif gap < 20.0 then
          targetSpeed = math.max(30.0, self.phase1SpeedKmh - 15.0)
        end
      end

      -- Smoothly interpolate lateral spline offset
      local currentOffset = self.currentSplineOffsets[i] or 0.0
      local newOffset = currentOffset
      if PhysicsHooks then
        newOffset = PhysicsHooks.smoothSplineOffsetDecay(currentOffset, targetOffset, dt, 1.5)
        PhysicsHooks.setAITopSpeed(i, targetSpeed)
        PhysicsHooks.setAICaution(i, caution)
        PhysicsHooks.setAISplineAbsoluteOffset(i, newOffset, false)
      end
      self.currentSplineOffsets[i] = newOffset
    end
  end
end

---Handles Green Flag release and smooth spline offset decay.
---@param dt number @Frame delta time
---@param carsCount integer @Total cars count
function AICoordinator:updateGreenFlagTransition(dt, carsCount)
  for i = 1, carsCount - 1 do
    local currentOffset = self.currentSplineOffsets[i] or 0.0
    if math.abs(currentOffset) > 0.001 then
      local newOffset = currentOffset
      if PhysicsHooks then
        newOffset = PhysicsHooks.smoothSplineOffsetDecay(currentOffset, 0.0, dt, 0.5)
        PhysicsHooks.setAISplineAbsoluteOffset(i, newOffset, false)
        PhysicsHooks.setAITopSpeed(i, 999999.0)
        PhysicsHooks.setAICaution(i, 1.0)
      end
      self.currentSplineOffsets[i] = newOffset
    end
  end
end

---Triggers Green Flag release event.
function AICoordinator:triggerGreenFlag()
  self.isGreenFlag = true
  self.phase = AICoordinator.PHASE.GREEN_FLAG
end

---Initializes native AI autopilot parameters on a vehicle.
---@param carIndex integer? @0-based car index
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
---@param carIndex integer? @0-based car index
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

AICoordinator.GTAICoordinator = AICoordinator

return AICoordinator
