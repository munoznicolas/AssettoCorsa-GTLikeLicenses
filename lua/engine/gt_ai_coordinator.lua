-- ==============================================================================
-- Gran Turismo License Engine for Assetto Corsa (CSP)
-- File: lua/engine/gt_ai_coordinator.lua
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

local GTPhysicsHooks = safeRequire("gt_physics_hooks")

local GTAICoordinator = {}
GTAICoordinator.__index = GTAICoordinator

-- Operational Phases for Rolling Starts
GTAICoordinator.PHASE = {
  WARMUP_SINGLE_FILE = "WARMUP_SINGLE_FILE",
  GRID_DOUBLE_FILE   = "GRID_DOUBLE_FILE",
  GREEN_FLAG         = "GREEN_FLAG"
}

---Calculates the physical distance in meters along the track spline between two vehicles.
---@param carAheadIdx integer @0-based car index of lead vehicle
---@param carBehindIdx integer @0-based car index of trailing vehicle
---@return number distanceMeters
function GTAICoordinator.getSplineDistanceMeters(carAheadIdx, carBehindIdx)
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
function GTAICoordinator.getLinearSpeedMultiplier(distMeters, targetGap, minGap, maxMult)
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
function GTAICoordinator.getOrganicLaneOffset(driverIdx, sessionTime)
  driverIdx = driverIdx or 0
  sessionTime = sessionTime or 0

  local wave1 = math.sin(sessionTime * 0.25 + driverIdx * 1.7) * 0.40
  local wave2 = math.cos(sessionTime * 0.40 - driverIdx * 2.3) * 0.10

  return wave1 + wave2
end

---Creates a new GTAICoordinator instance from a test configuration table.
---@param testConfig table @Table complying with test_definition.schema.json
---@return table instance
function GTAICoordinator.new(testConfig)
  local self = setmetatable({}, GTAICoordinator)

  self.testConfig = testConfig or {}
  self.phase = GTAICoordinator.PHASE.WARMUP_SINGLE_FILE
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
function GTAICoordinator:update(dt, sessionTime)
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
function GTAICoordinator:updatePaceCar(dt, sessionTime)
  if not ac or not ac.getCar then return end

  local paceCar = ac.getCar(self.paceCarIndex)
  if not paceCar then return end

  -- Apply top speed ceiling on Pace Car
  if GTPhysicsHooks then
    GTPhysicsHooks.setAITopSpeed(self.paceCarIndex, self.paceSpeedKmh)
    GTPhysicsHooks.setAIThrottleLimit(self.paceCarIndex, 1.0)
    GTPhysicsHooks.setAICaution(self.paceCarIndex, 2.0)
  end
end

---Manages 2-Phase Rolling Start grid logic and speed scaling.
---@param dt number @Frame delta time
---@param sessionTime number @Session time in seconds
---@param carsCount integer @Total number of cars in session
function GTAICoordinator:updateRollingStart(dt, sessionTime, carsCount)
  if not ac or not ac.getCar then return end

  local leadCar = ac.getCar(0)
  if not leadCar then return end

  -- Check if leader has reached formation point threshold (e.g. 67% spline position)
  if leadCar.splinePosition >= self.formationPointPct and self.phase == GTAICoordinator.PHASE.WARMUP_SINGLE_FILE then
    self.phase = GTAICoordinator.PHASE.GRID_DOUBLE_FILE
  end

  for i = 1, carsCount - 1 do
    local car = ac.getCar(i)
    if car and car.isAIControlled then
      local targetSpeed = self.phase1SpeedKmh
      local targetOffset = 0.0
      local caution = 1.0

      if self.phase == GTAICoordinator.PHASE.GRID_DOUBLE_FILE then
        targetSpeed = self.phase2SpeedKmh
        caution = 0.7

        -- Stagger Left / Right lanes based on grid position (odd vs even)
        local isOdd = (car.racePosition % 2 == 1)
        local baseOffset = isOdd and -self.laneDistanceM or self.laneDistanceM
        if self.p1LaneSide == "RIGHT" then
          baseOffset = -baseOffset
        end

        targetOffset = baseOffset + GTAICoordinator.getOrganicLaneOffset(i, sessionTime)

        -- Proportional gap scaling relative to car ahead in column
        local aheadIdx = (car.racePosition > 2) and (car.racePosition - 2) or 0
        local gap = GTAICoordinator.getSplineDistanceMeters(aheadIdx, i)
        if gap > 0 then
          local mult = GTAICoordinator.getLinearSpeedMultiplier(gap, 8.0, 1.5, 1.4)
          targetSpeed = targetSpeed * mult
        end
      else
        -- Phase 1 (Single File): Maintain single line with catch-up scaling
        local leadIdx = car.racePosition - 1
        local gap = GTAICoordinator.getSplineDistanceMeters(leadIdx, i)
        if gap > 40.0 then
          targetSpeed = self.phase1SpeedKmh * 1.25
        elseif gap < 20.0 then
          targetSpeed = math.max(30.0, self.phase1SpeedKmh - 15.0)
        end
      end

      -- Smoothly interpolate lateral spline offset
      local currentOffset = self.currentSplineOffsets[i] or 0.0
      local newOffset = currentOffset
      if GTPhysicsHooks then
        newOffset = GTPhysicsHooks.smoothSplineOffsetDecay(currentOffset, targetOffset, dt, 1.5)
        GTPhysicsHooks.setAITopSpeed(i, targetSpeed)
        GTPhysicsHooks.setAICaution(i, caution)
        GTPhysicsHooks.setAISplineAbsoluteOffset(i, newOffset, false)
      end
      self.currentSplineOffsets[i] = newOffset
    end
  end
end

---Handles Green Flag release and smooth spline offset decay.
---@param dt number @Frame delta time
---@param carsCount integer @Total cars count
function GTAICoordinator:updateGreenFlagTransition(dt, carsCount)
  for i = 1, carsCount - 1 do
    local currentOffset = self.currentSplineOffsets[i] or 0.0
    if math.abs(currentOffset) > 0.001 then
      local newOffset = currentOffset
      if GTPhysicsHooks then
        newOffset = GTPhysicsHooks.smoothSplineOffsetDecay(currentOffset, 0.0, dt, 0.5)
        GTPhysicsHooks.setAISplineAbsoluteOffset(i, newOffset, false)
        GTPhysicsHooks.setAITopSpeed(i, 999999.0)
        GTPhysicsHooks.setAICaution(i, 1.0)
      end
      self.currentSplineOffsets[i] = newOffset
    end
  end
end

---Triggers Green Flag release event.
function GTAICoordinator:triggerGreenFlag()
  self.isGreenFlag = true
  self.phase = GTAICoordinator.PHASE.GREEN_FLAG
end

return GTAICoordinator
