-- ==============================================================================
-- Gran Turismo License Engine for Assetto Corsa (CSP)
-- File: lua/engine/gt_adjudicator.lua
-- Description: Real-time adjudication engine for failure conditions:
--              1. Off-track limits (> max_wheels_off)
--              2. Wall/barrier impact force threshold (physics.getCarCollisions)
--              3. Vehicle spin-out detection (> max_yaw_angle_deg)
--              4. Stop box spatial containment and complete rest (0 km/h) check
--              5. Target time limit expiration (> bronze_seconds)
--              6. 2D line segment gate crossing detection (start/finish)
-- ==============================================================================

local GTAdjudicator = {}
GTAdjudicator.__index = GTAdjudicator

---Creates a new Adjudicator instance bound to a specific test configuration.
---@param testConfig table @Test configuration complying with test_definition.schema.json
---@return table GTAdjudicator instance
function GTAdjudicator.new(testConfig)
  local self = setmetatable({}, GTAdjudicator)
  self:init(testConfig)
  return self
end

---Initializes or reinitializes the adjudicator state.
---@param testConfig table
function GTAdjudicator:init(testConfig)
  self.testConfig = testConfig or {}
  local failRules = self.testConfig.fail_rules or {}
  local targets = self.testConfig.targets or {}
  local timing = self.testConfig.timing or {}

  -- Failure rule thresholds
  self.maxWheelsOff = tonumber(failRules.max_wheels_off) or 2
  self.wallCollisionThresholdN = tonumber(failRules.wall_collision_threshold_n) or 1500
  self.maxYawAngleDeg = tonumber(failRules.max_yaw_angle_deg) or 90
  self.stopBoxOvershootFail = failRules.stop_box_overshoot_fail == true
  self.bronzeSeconds = tonumber(targets.bronze_seconds) or 999.0

  -- Timing geometry
  self.startGate = timing.start_gate
  self.finishGate = timing.finish_gate
  self.stopBox = timing.stop_box

  -- Runtime state
  self.hasPassedStartGate = false
  self.hasCrossedFinishGate = false
  self.stoppedInBox = false
  self.isDisqualified = false
  self.failReason = nil
  self.isPassed = false
  self.previousCarPos = nil
  self.consecutiveOffTrackFrames = 0
  self.standstillTimer = 0

  return self
end

---2D Line-Segment Intersection test on the X-Z ground plane.
---Checks whether car trajectory from p1 to p2 crosses gate segment p3 to p4.
---@param p1 table|vec3 @Previous car position
---@param p2 table|vec3 @Current car position
---@param p3 table|vec3|number[] @Gate point 1
---@param p4 table|vec3|number[] @Gate point 2
---@return boolean intersects
function GTAdjudicator.segmentsIntersect2D(p1, p2, p3, p4)
  local x1, z1 = p1.x or p1[1], p1.z or p1[3]
  local x2, z2 = p2.x or p2[1], p2.z or p2[3]
  local x3, z3 = p3.x or p3[1], p3.z or p3[3]
  local x4, z4 = p4.x or p4[1], p4.z or p4[3]

  local function ccw(ax, az, bx, bz, cx, cz)
    return ((cz - az) * (bx - ax)) > ((bz - az) * (cx - ax))
  end

  local a = ccw(x1, z1, x3, z3, x4, z4)
  local b = ccw(x2, z2, x3, z3, x4, z4)
  local c = ccw(x1, z1, x2, z2, x3, z3)
  local d = ccw(x1, z1, x2, z2, x4, z4)

  return (a ~= b) and (c ~= d)
end

---Tests whether a 3D position is spatially contained inside an Oriented Bounding Box (OBB).
---@param pos table|vec3 @Vehicle world position
---@param stopBox table @{ center=[x,y,z], size=[sx,sy,sz], rotation_deg=deg }
---@return boolean isInside, number localX, number localZ
function GTAdjudicator.isInsideStopBox(pos, stopBox)
  if not stopBox or not stopBox.center or not stopBox.size then
    return false, 0, 0
  end

  local px = pos.x or pos[1]
  local py = pos.y or pos[2]
  local pz = pos.z or pos[3]

  local cx = stopBox.center[1]
  local cy = stopBox.center[2]
  local cz = stopBox.center[3]

  local sx = stopBox.size[1]
  local sy = stopBox.size[2]
  local sz = stopBox.size[3]

  -- Height containment check (generous vertical window of +- 4m)
  if math.abs(py - cy) > (sy * 0.5 + 4.0) then
    return false, 0, 0
  end

  -- Translation relative to box center
  local dx = px - cx
  local dz = pz - cz

  -- Rotation into local stop box space
  local rotRad = -math.rad(stopBox.rotation_deg or 0)
  local cosR = math.cos(rotRad)
  local sinR = math.sin(rotRad)

  local localX = dx * cosR - dz * sinR
  local localZ = dx * sinR + dz * cosR

  local halfX = sx * 0.5
  local halfZ = sz * 0.5

  local isInside = (math.abs(localX) <= halfX) and (math.abs(localZ) <= halfZ)
  return isInside, localX, localZ
end

---Adjudicates off-track limit violations (> max_wheels_off).
---@param car table|ac.CarState
---@return boolean failed, string? reason
function GTAdjudicator:checkOffTrack(car)
  if not car then return false end

  -- In CSP Lua, car.wheelsOutsideTrack or car.wheelsOutside indicates wheel count
  local wheelsOut = car.wheelsOutsideTrack or car.wheelsOutside or 0

  if wheelsOut > self.maxWheelsOff then
    return true, string.format("Off Track: Exceeded Track Limits (%d wheels off)", wheelsOut)
  end

  return false
end

---Adjudicates wall and barrier collision events against force thresholds.
---Uses physics.getCarCollisions() with fallback to car state telemetry.
---@param car table|ac.CarState
---@return boolean failed, string? reason
function GTAdjudicator:checkWallCollision(car)
  -- 1. Check physics collision array if available in CSP
  if physics and physics.getCarCollisions then
    local collisions = physics.getCarCollisions()
    if collisions and #collisions > 0 then
      for i = 1, #collisions do
        local col = collisions[i]
        local impactForce = col.force or col.impact or 0
        if impactForce > self.wallCollisionThresholdN then
          return true, string.format("Barrier Contact (Impact: %.0f N)", impactForce)
        end
      end
    end
  end

  -- 2. Fallback check: car.collisionDepth and car.collidedWith
  if car then
    local depth = car.collisionDepth or 0
    if depth > 0.08 then
      return true, "Barrier Contact (Severe Impact)"
    end
  end

  return false
end

---Adjudicates vehicle spin out (> max_yaw_angle_deg).
---@param car table|ac.CarState
---@return boolean failed, string? reason
function GTAdjudicator:checkVehicleSpin(car)
  if not car then return false end

  local speedKmh = car.speedKmh or 0
  -- Only evaluate spin when moving with sufficient kinetic momentum (> 15 km/h)
  if speedKmh < 15 then
    return false
  end

  -- Angle between car look vector and velocity direction
  if car.velocity and car.look then
    local vx, vz = car.velocity.x, car.velocity.z
    local velLen = math.sqrt(vx * vx + vz * vz)

    if velLen > 2.0 then
      local nvx, nvz = vx / velLen, vz / velLen
      local lx, lz = car.look.x, car.look.z
      local lookLen = math.sqrt(lx * lx + lz * lz)

      if lookLen > 0.1 then
        nlx, nlz = lx / lookLen, lz / lookLen
        local dot = nlx * nvx + nlz * nvz
        dot = math.max(-1.0, math.min(1.0, dot))
        local yawAngleDeg = math.deg(math.acos(dot))

        if yawAngleDeg > self.maxYawAngleDeg then
          return true, string.format("Vehicle Spin Out (Angle: %.0f deg)", yawAngleDeg)
        end
      end
    end
  end

  -- Angle relative to track spline tangent if available
  if ac and ac.trackProgressTangent and car.splinePosition then
    local tangent = ac.trackProgressTangent(car.splinePosition)
    if tangent and car.look then
      local dot = car.look.x * tangent.x + car.look.z * tangent.z
      dot = math.max(-1.0, math.min(1.0, dot))
      local splineAngleDeg = math.deg(math.acos(dot))

      if splineAngleDeg > self.maxYawAngleDeg then
        return true, string.format("Vehicle Spin Out (Spline Heading: %.0f deg)", splineAngleDeg)
      end
    end
  end

  return false
end

---Adjudicates stop box containment and complete stop for acceleration & braking tests.
---@param car table|ac.CarState
---@param dt number
---@return boolean isComplete, boolean isFailed, string? statusReason
function GTAdjudicator:checkStopBoxStatus(car, dt)
  if not self.stopBox or not car then
    return false, false, nil
  end

  local pos = car.position
  local speedKmh = car.speedKmh or 0
  local isInside, localX, localZ = GTAdjudicator.isInsideStopBox(pos, self.stopBox)
  local halfZ = (self.stopBox.size[3] or 20) * 0.5

  -- Check if car came to a complete stop (speed < 0.5 km/h)
  if speedKmh < 0.5 then
    self.standstillTimer = self.standstillTimer + dt
    -- Require 0.3s of verified standstill to prevent transient speed dips
    if self.standstillTimer >= 0.3 then
      if isInside then
        return true, false, "Stopped inside target box"
      else
        return false, true, "Stopped Outside Target Box"
      end
    end
  else
    self.standstillTimer = 0
  end

  -- Check for stop box overshoot (car traveled beyond the far boundary while moving)
  if self.stopBoxOvershootFail and (localZ > (halfZ + 1.0)) and (speedKmh > 5.0) then
    return false, true, "Overshot Stop Box"
  end

  return false, false, nil
end

---Main per-frame adjudication tick.
---@param dt number @Delta time in seconds
---@param sessionTime number @Active running time in seconds
---@param car table|ac.CarState @Car state from ac.getCar(0)
---@return table result @{ status="RUNNING"|"PASSED"|"FAILED", reason=string, gateCrossed=boolean }
function GTAdjudicator:adjudicate(dt, sessionTime, car)
  -- If already in a terminal state, return cached status
  if self.isDisqualified then
    return { status = "FAILED", reason = self.failReason }
  end
  if self.isPassed then
    return { status = "PASSED", reason = nil }
  end

  if not car then
    return { status = "RUNNING" }
  end

  local currPos = car.position

  -- 1. Check start gate crossing
  if not self.hasPassedStartGate and self.previousCarPos and self.startGate then
    if GTAdjudicator.segmentsIntersect2D(self.previousCarPos, currPos, self.startGate.p1, self.startGate.p2) then
      self.hasPassedStartGate = true
    end
  end

  -- 2. Check bronze time limit expiration
  if sessionTime > self.bronzeSeconds then
    self.isDisqualified = true
    self.failReason = "Time Limit Exceeded"
    return { status = "FAILED", reason = self.failReason }
  end

  -- 3. Adjudicate off-track violation
  local offTrack, offTrackReason = self:checkOffTrack(car)
  if offTrack then
    self.isDisqualified = true
    self.failReason = offTrackReason
    return { status = "FAILED", reason = self.failReason }
  end

  -- 4. Adjudicate wall/barrier impact
  local hitWall, wallReason = self:checkWallCollision(car)
  if hitWall then
    self.isDisqualified = true
    self.failReason = wallReason
    return { status = "FAILED", reason = self.failReason }
  end

  -- 5. Adjudicate spin out
  local spun, spinReason = self:checkVehicleSpin(car)
  if spun then
    self.isDisqualified = true
    self.failReason = spinReason
    return { status = "FAILED", reason = self.failReason }
  end

  -- 6. Adjudicate finish line / Stop box logic
  if self.hasPassedStartGate and self.finishGate and not self.hasCrossedFinishGate and self.previousCarPos then
    if GTAdjudicator.segmentsIntersect2D(self.previousCarPos, currPos, self.finishGate.p1, self.finishGate.p2) then
      self.hasCrossedFinishGate = true
    end
  end

  if self.stopBox then
    -- Acceleration & Braking test: requires stopping inside the stop box
    local complete, failed, reason = self:checkStopBoxStatus(car, dt)
    if failed then
      self.isDisqualified = true
      self.failReason = reason
      return { status = "FAILED", reason = self.failReason }
    elseif complete then
      self.isPassed = true
      return { status = "PASSED", reason = nil }
    end
  else
    -- Standard sector or lap test: crossing the finish gate triggers pass
    if self.hasCrossedFinishGate then
      self.isPassed = true
      return { status = "PASSED", reason = nil }
    end
  end

  -- Store position for next frame's segment crossing calculations
  self.previousCarPos = vec3(currPos.x, currPos.y, currPos.z)

  return { status = "RUNNING" }
end

return GTAdjudicator
