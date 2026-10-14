-- ==============================================================================
-- Gran Turismo License Engine for Assetto Corsa (CSP)
-- File: lua/engine/adjudicator.lua
-- Description: Real-time adjudication engine for driving test evaluations:
--              1. Off-track limits (> max_wheels_off) with debounced contact points
--              2. Wall/barrier impact force threshold (collision depth)
--              3. Vehicle spin-out detection (> max_yaw_angle_deg)
--              4. Stop box spatial containment and verified complete standstill
--              5. Target time limit expiration (> bronze_seconds)
--              6. 2D line segment gate crossing detection (start/finish)
-- ==============================================================================

local Adjudicator = {}
Adjudicator.__index = Adjudicator

---Creates a new Adjudicator instance bound to a specific test configuration.
---@param testConfig table @Test configuration complying with test_definition.schema.json
---@return table Adjudicator instance
function Adjudicator.new(testConfig)
  local self = setmetatable({}, Adjudicator)
  self:init(testConfig)
  return self
end

---Initializes or reinitializes the adjudicator state.
---@param testConfig table
function Adjudicator:init(testConfig)
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
  self.hasPassedStartGate = true
  self.hasCrossedFinishGate = false
  self.hasLaunched = false
  self.stoppedInBox = false
  self.isDisqualified = false
  self.failReason = nil
  self.isPassed = false
  self.previousCarPos = nil
  self.consecutiveOffTrackFrames = 0
  self.standstillTimer = 0

  if ac and ac.log then
    ac.log(string.format("[GTLicense] Adjudicator:init | test_id=%s | startGate=%s | finishGate=%s | fg_p1=%s | fg_p2=%s",
      tostring(self.testConfig.test_id),
      tostring(self.startGate ~= nil),
      tostring(self.finishGate ~= nil),
      tostring(self.finishGate and self.finishGate.p1 ~= nil),
      tostring(self.finishGate and self.finishGate.p2 ~= nil)))
  end

  return self
end

---Extends gate endpoints laterally across the track so wide lines and kerbs are reliably detected.
local function getExtendedGate(gate, buffer)
  if not gate or not gate.p1 or not gate.p2 then return nil, nil end
  buffer = buffer or 12.0
  local p1 = gate.p1
  local p2 = gate.p2
  local x1, z1 = p1.x or p1[1], p1.z or p1[3]
  local x2, z2 = p2.x or p2[1], p2.z or p2[3]
  local dx, dz = x2 - x1, z2 - z1
  local len = math.sqrt(dx * dx + dz * dz)
  if len > 0.001 then
    local nx, nz = dx / len, dz / len
    return { x = x1 - nx * buffer, z = z1 - nz * buffer }, { x = x2 + nx * buffer, z = z2 + nz * buffer }
  end
  return p1, p2
end

---2D Line-Segment Intersection test on the X-Z ground plane.
---Checks whether car trajectory from p1 to p2 crosses gate segment p3 to p4.
---@param p1 table|vec3 @Previous car position
---@param p2 table|vec3 @Current car position
---@param p3 table|vec3|number[] @Gate point 1
---@param p4 table|vec3|number[] @Gate point 2
---@return boolean intersects
function Adjudicator.segmentsIntersect2D(p1, p2, p3, p4)
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
function Adjudicator.isInsideStopBox(pos, stopBox)
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

  -- 2D rotation around Y axis
  local rotDeg = stopBox.rotation_deg or 0
  local rad = math.rad(-rotDeg)
  local cosR = math.cos(rad)
  local sinR = math.sin(rad)

  local localX = dx * cosR - dz * sinR
  local localZ = dx * sinR + dz * cosR

  local halfX = sx * 0.5
  local halfZ = sz * 0.5

  local inside = (math.abs(localX) <= halfX) and (math.abs(localZ) <= halfZ)
  return inside, localX, localZ
end

---Adjudicates track limits: debounces contact patch track valid status for 2 frames.
---@param car table|ac.CarState
---@return boolean failed, string? reason
function Adjudicator:checkOffTrack(car)
  if not car then return false end

  local wheelsOff = 0
  local hasWheelData = false

  if car.wheels then
    for i = 0, 3 do
      local w = car.wheels[i]
      if w and w.surfaceValidTrack ~= nil then
        hasWheelData = true
        if w.surfaceValidTrack == false then
          wheelsOff = wheelsOff + 1
        end
      end
    end
  end

  if not hasWheelData then
    wheelsOff = tonumber(car.wheelsOutside) or 0
  end

  if wheelsOff > self.maxWheelsOff then
    self.consecutiveOffTrackFrames = self.consecutiveOffTrackFrames + 1
    if self.consecutiveOffTrackFrames >= 2 then
      return true, string.format("Track Limits Exceeded (%d wheels off track)", wheelsOff)
    end
  else
    self.consecutiveOffTrackFrames = 0
  end

  return false
end

---Adjudicates wall and barrier collision events against force thresholds.
---@param car table|ac.CarState
---@return boolean failed, string? reason
function Adjudicator:checkWallCollision(car)
  if not car then return false end

  local depth = 0
  local ok, val = pcall(function() return car.collisionDepth end)
  if ok and val then
    depth = tonumber(val) or 0
  end

  if depth > 0.05 then
    return true, "Barrier Contact (Penetration Impact)"
  end

  return false
end

---Adjudicates vehicle spin out (> max_yaw_angle_deg).
---@param car table|ac.CarState
---@return boolean failed, string? reason
function Adjudicator:checkVehicleSpin(car)
  if not car then return false end

  local speedKmh = car.speedKmh or 0
  if speedKmh < 15 then
    return false
  end

  -- Angle between vehicle forward look vector and linear velocity
  if car.velocity and car.look then
    local vx, vz = car.velocity.x, car.velocity.z
    local velLen = math.sqrt(vx * vx + vz * vz)

    if velLen > 2.0 then
      local nvx, nvz = vx / velLen, vz / velLen
      local lx, lz = car.look.x, car.look.z
      local lookLen = math.sqrt(lx * lx + lz * lz)

      if lookLen > 0.1 then
        local nlx, nlz = lx / lookLen, lz / lookLen
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
function Adjudicator:checkStopBoxStatus(car, dt)
  if not self.stopBox or not car then
    return false, false, nil
  end

  local pos = car.position
  local speedKmh = car.speedKmh or 0
  local isInside, _, localZ = Adjudicator.isInsideStopBox(pos, self.stopBox)
  local halfZ = (self.stopBox.size[3] or 20) * 0.5

  -- Track vehicle launch from initial standing start
  if speedKmh >= 5.0 then
    self.hasLaunched = true
  end

  -- Check complete standstill (speed < 0.5 km/h for 0.3s)
  if self.hasLaunched and speedKmh < 0.5 then
    self.standstillTimer = self.standstillTimer + dt
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

  -- Check stop box overshoot (car traveled beyond boundary while moving)
  if self.stopBoxOvershootFail and (localZ > (halfZ + 1.0)) and (speedKmh > 5.0) then
    return false, true, "Overshot Stop Box"
  end

  return false, false, nil
end

---Adjudicates start/finish gate crossing logic.
---@param currPos table
---@param sessionTime number
---@return boolean crossedFinish
function Adjudicator:checkGateCrossings(currPos, sessionTime)
  -- 1. Start Gate
  if not self.hasPassedStartGate and self.previousCarPos and self.startGate then
    if Adjudicator.segmentsIntersect2D(self.previousCarPos, currPos, self.startGate.p1, self.startGate.p2) then
      self.hasPassedStartGate = true
    end
  end

  -- 2. Finish Gate
  if self.finishGate and not self.hasCrossedFinishGate then
    local p1 = self.finishGate.p1
    local p2 = self.finishGate.p2
    local midX = ((p1.x or p1[1]) + (p2.x or p2[1])) * 0.5
    local midZ = ((p1.z or p1[3]) + (p2.z or p2[3])) * 0.5
    local distToFinish = math.sqrt((currPos.x - midX)^2 + (currPos.z - midZ)^2)

    local ep1, ep2 = getExtendedGate(self.finishGate, 15.0)
    local crossedSegment = false
    if self.previousCarPos and ep1 and ep2 then
      crossedSegment = Adjudicator.segmentsIntersect2D(self.previousCarPos, currPos, ep1, ep2)
    end

    if crossedSegment or (distToFinish <= 12.0) then
      self.hasCrossedFinishGate = true
      if ac and ac.log then
        ac.log(string.format("[GTLicense] Finish Gate CROSSED at t=%.2fs! pos=(%.2f, %.2f, %.2f), distToMid=%.1fm",
          sessionTime, currPos.x, currPos.y, currPos.z, distToFinish))
      end
    end
  end

  return self.hasCrossedFinishGate
end

---Main per-frame adjudication tick implementing composable rule evaluation.
---@param dt number @Delta time in seconds
---@param sessionTime number @Active running time in seconds
---@param car table|ac.CarState @Car state from ac.getCar(0)
---@return table result @{ status="RUNNING"|"PASSED"|"FAILED", reason=string }
function Adjudicator:_adjudicateInternal(dt, sessionTime, car)
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

  -- 1. Check bronze target time limit
  local limitSeconds = (self.isAITestMode and (self.bronzeSeconds + 30.0)) or self.bronzeSeconds
  if sessionTime > limitSeconds then
    self.isDisqualified = true
    self.failReason = "Time Limit Exceeded"
    return { status = "FAILED", reason = self.failReason }
  end

  -- 2. Check track limits
  local offTrack, offTrackReason = self:checkOffTrack(car)
  if offTrack then
    self.isDisqualified = true
    self.failReason = offTrackReason
    return { status = "FAILED", reason = self.failReason }
  end

  -- 3. Check barrier collisions
  local hitWall, wallReason = self:checkWallCollision(car)
  if hitWall then
    self.isDisqualified = true
    self.failReason = wallReason
    return { status = "FAILED", reason = self.failReason }
  end

  -- 4. Check vehicle spinout
  local spun, spinReason = self:checkVehicleSpin(car)
  if spun then
    self.isDisqualified = true
    self.failReason = spinReason
    return { status = "FAILED", reason = self.failReason }
  end

  -- 5. Evaluate gate crossings
  self:checkGateCrossings(currPos, sessionTime)

  -- 7. Evaluate completion criteria (Stop Box vs Finish Gate)
  if self.stopBox then
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
    if self.hasCrossedFinishGate then
      self.isPassed = true
      return { status = "PASSED", reason = nil }
    end
  end

  -- Store position for next frame's segment crossing calculations
  self.previousCarPos = { x = currPos.x, y = currPos.y, z = currPos.z }
  return { status = "RUNNING" }
end

---Public adjudicate entry point wrapped with error protection.
---@param dt number
---@param sessionTime number
---@param car table|ac.CarState
---@return table result
function Adjudicator:adjudicate(dt, sessionTime, car)
  local ok, res = pcall(self._adjudicateInternal, self, dt, sessionTime, car)
  if not ok then
    if ac and ac.log then
      ac.log("[GTLicense] ADJUDICATOR CRASH: " .. tostring(res))
    end
    return { status = "RUNNING" }
  end
  return res
end

return Adjudicator
