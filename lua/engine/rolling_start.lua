-- ==============================================================================
-- Gran Turismo License Engine for Assetto Corsa (CSP)
-- File: lua/engine/rolling_start.lua
-- Description: Native AI autopilot rolling start maintenance, spline offset
--              control, and fallback linear velocity stabilization.
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

local Utils = safeRequire("utils")
local RollingStart = {}

local toVec3 = Utils and Utils.toVec3 or function(v)
  if v == nil then return vec3(0, 0, 0) end
  if type(v) == 'cdata' or (type(v) == 'userdata') then return v end
  if type(v) == 'table' then
    if v.x ~= nil and v.y ~= nil and v.z ~= nil then
      return vec3(tonumber(v.x) or 0, tonumber(v.y) or 0, tonumber(v.z) or 0)
    elseif v[1] ~= nil and v[2] ~= nil and v[3] ~= nil then
      return vec3(tonumber(v[1]) or 0, tonumber(v[2]) or 0, tonumber(v[3]) or 0)
    end
  end
  return vec3(0, 0, 0)
end

local safeNormalize = Utils and Utils.safeNormalize or function(dir)
  local v = toVec3(dir)
  local len = math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
  if len > 0.0001 then return vec3(v.x / len, v.y / len, v.z / len) end
  return vec3(0, 0, 1)
end

---Estimates a realistic starting gear for rolling start velocity.
---@param speedKmh number
---@return integer gearIndex (1-based gear, 1 to 6)
function RollingStart.estimateStartingGear(speedKmh)
  if speedKmh <= 0 then
    return 1
  elseif speedKmh <= 45 then
    return 1
  elseif speedKmh <= 80 then
    return 2
  elseif speedKmh <= 125 then
    return 3
  elseif speedKmh <= 175 then
    return 4
  elseif speedKmh <= 230 then
    return 5
  else
    return 6
  end
end

---Engages rolling start countdown physics along the straight sector line via native AI autopilot.
---Enables autopilot, caps AI speed to target rolling speed, and locks to the ideal racing line.
---@param carIndex integer? @0-based car index (default: 0)
---@param targetSpeedKmh number @Target rolling speed in km/h
---@param targetGear integer? @Target gear to engage and maintain
---@param targetRPM number? @Target engine RPM to maintain
---@param fallbackFwd table|vec3|number[]? @Forward vector
function RollingStart.startAIRolling(carIndex, targetSpeedKmh, targetGear, targetRPM, fallbackFwd)
  carIndex = carIndex or 0
  targetSpeedKmh = tonumber(targetSpeedKmh) or 70.0
  targetGear = (targetGear and targetGear > 0) and targetGear or RollingStart.estimateStartingGear(targetSpeedKmh)
  targetRPM = (targetRPM and targetRPM > 0) and targetRPM or 3500

  -- Ensure no forced pedal locks hold the car or starve AI throttle
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

  -- Engage native AI autopilot for car 0
  if physics and physics.setCarAutopilot then
    physics.setCarAutopilot(true, false)
  end

  -- Configure AI parameters to strictly follow the racing line at target rolling speed
  if physics and physics.setAITopSpeed then
    physics.setAITopSpeed(carIndex, targetSpeedKmh)
  end
  if physics and physics.setAILevel then
    physics.setAILevel(carIndex, 1.0)
  end
  if physics and physics.setAIAggression then
    physics.setAIAggression(carIndex, 0.0)
  end
  if physics and physics.setAICaution then
    physics.setAICaution(carIndex, 0.1)
  end
  if physics and physics.setAISplineAbsoluteOffset then
    physics.setAISplineAbsoluteOffset(carIndex, 0.0, false)
  elseif physics and physics.setAISplineOffset then
    physics.setAISplineOffset(carIndex, 0.0, false)
  end

  -- Firmly engage target gear and RPM
  if physics and physics.engageGear then
    physics.engageGear(carIndex, targetGear)
  end
  if physics and physics.setEngineRPM then
    physics.setEngineRPM(carIndex, targetRPM)
  end

  if ac and ac.log then
    ac.log(string.format("[PhysicsHooks] startAIRolling car=%d: autopilot=true, speed=%.1f km/h, gear=%d, rpm=%d",
      carIndex, targetSpeedKmh, targetGear, targetRPM))
  end
end

---Maintains rolling motion under AI control along the racing line during COUNTDOWN state.
---Continuously re-asserts AI target speed and zero spline offset so the car adheres to the ideal line.
---Falls back to velocity maintenance if no track spline is present, preserving natural vertical gravity.
---@param carIndex integer? @0-based car index (default: 0)
---@param targetSpeedKmh number @Target rolling speed in km/h
---@param fallbackFwd table|vec3|number[]? @Forward vector
---@param dt number? @Frame delta time
---@param targetGear integer? @Target gear to continuously maintain
---@param targetRPM number? @Target engine RPM to maintain
function RollingStart.maintainAIRolling(carIndex, targetSpeedKmh, fallbackFwd, dt, targetGear, targetRPM)
  carIndex = carIndex or 0
  targetSpeedKmh = tonumber(targetSpeedKmh) or 70.0
  targetGear = (targetGear and targetGear > 0) and targetGear or RollingStart.estimateStartingGear(targetSpeedKmh)
  targetRPM = (targetRPM and targetRPM > 0) and targetRPM or 3500

  local hasSpline = (ac and ac.hasTrackSpline) and ac.hasTrackSpline() or true
  if hasSpline then
    if physics and physics.setCarAutopilot then
      physics.setCarAutopilot(true, false)
    end
    if physics and physics.setAITopSpeed then
      physics.setAITopSpeed(carIndex, targetSpeedKmh)
    end
    if physics and physics.setAISplineAbsoluteOffset then
      physics.setAISplineAbsoluteOffset(carIndex, 0.0, false)
    elseif physics and physics.setAISplineOffset then
      physics.setAISplineOffset(carIndex, 0.0, false)
    end

    local car = ac.getCar and ac.getCar(carIndex)
    if targetSpeedKmh > 0 and car and car.speedKmh < (targetSpeedKmh * 0.75) then
      local rawFwd = toVec3(fallbackFwd)
      local fwd = (rawFwd.x ~= 0 or rawFwd.y ~= 0 or rawFwd.z ~= 0)
        and safeNormalize(rawFwd)
        or (car and car.look and safeNormalize(car.look) or vec3(0, 0, 1))
      local speedMs = targetSpeedKmh / 3.6
      local curVy = (car.velocity and car.velocity.y) or (fwd.y * speedMs)
      local vel = vec3(fwd.x * speedMs, curVy, fwd.z * speedMs)
      if physics and physics.setCarVelocity then
        physics.setCarVelocity(carIndex, vel)
      end
    end
  else
    local car = ac.getCar and ac.getCar(carIndex)
    local rawFwd = toVec3(fallbackFwd)
    local fwd = (rawFwd.x ~= 0 or rawFwd.y ~= 0 or rawFwd.z ~= 0)
      and safeNormalize(rawFwd)
      or (car and car.look and safeNormalize(car.look) or vec3(0, 0, 1))
    local speedMs = targetSpeedKmh / 3.6
    local curVy = (car and car.velocity and car.velocity.y) or (fwd.y * speedMs)
    local vel = vec3(fwd.x * speedMs, curVy, fwd.z * speedMs)
    if physics and physics.setCarVelocity then
      physics.setCarVelocity(carIndex, vel)
    end
  end

  local car = ac.getCar and ac.getCar(carIndex)
  if targetGear and targetGear > 0 then
    if not car or car.gear ~= targetGear then
      if physics and physics.engageGear then
        physics.engageGear(carIndex, targetGear)
      end
    end
    if ac and ac.overrideCarControls then
      local ctrl = ac.overrideCarControls(carIndex)
      if ctrl then
        ctrl.clutch = 0.0
      end
    end
  end
end

---Continuously re-applies linear velocity on frame updates during COUNTDOWN state.
---@param carIndex integer @0-based car index
---@param forwardVector table|vec3|number[] @Forward facing direction
---@param speedKmh number @Target rolling speed in km/h
---@return boolean success
function RollingStart.maintainRollingVelocity(carIndex, forwardVector, speedKmh)
  carIndex = carIndex or 0
  speedKmh = tonumber(speedKmh) or 0
  if speedKmh <= 0 then return false end

  local fwd = safeNormalize(toVec3(forwardVector))
  local speedMs = speedKmh / 3.6
  local vel = vec3(fwd.x * speedMs, fwd.y * speedMs, fwd.z * speedMs)

  if physics and physics.setCarVelocity then
    physics.setCarVelocity(carIndex, vel)
  end

  local gear = RollingStart.estimateStartingGear(speedKmh)
  if physics and physics.engageGear then
    physics.engageGear(carIndex, gear)
  end
  if physics and physics.forceUserBrakesFor then
    physics.forceUserBrakesFor(0, 0)
  end
  if physics and physics.forceUserHandbrakeFor then
    physics.forceUserHandbrakeFor(0, 0)
  end
  local car = ac.getCar and ac.getCar(carIndex)
  local tyreRadius = (car and car.wheels and car.wheels[0] and car.wheels[0].tyreRadius and car.wheels[0].tyreRadius > 0.1) and car.wheels[0].tyreRadius or 0.30
  local targetOmega = speedMs / tyreRadius
  if physics and physics.setWheelAngularVelocity then
    local allWheels = (ac and ac.Wheel and ac.Wheel.All) or 60
    physics.setWheelAngularVelocity(carIndex, allWheels, targetOmega)
  end

  return true
end

---Sets an absolute top speed ceiling (in km/h) on an AI controlled vehicle.
function RollingStart.setAITopSpeed(carIndex, speedKmh)
  carIndex = carIndex or 0
  speedKmh = tonumber(speedKmh) or 999999.0
  if physics and physics.setAITopSpeed then
    physics.setAITopSpeed(carIndex, speedKmh)
  end
end

---Limits the maximum throttle output of an AI car.
function RollingStart.setAIThrottleLimit(carIndex, throttleLimit)
  carIndex = carIndex or 0
  throttleLimit = math.max(0.0, math.min(1.0, tonumber(throttleLimit) or 1.0))
  if physics and physics.setAIThrottleLimit then
    physics.setAIThrottleLimit(carIndex, throttleLimit)
  end
end

---Adjusts the caution level of an AI driver.
function RollingStart.setAICaution(carIndex, level)
  carIndex = carIndex or 0
  level = tonumber(level) or 1.0
  if physics and physics.setAICaution then
    physics.setAICaution(carIndex, level)
  end
end

---Sets the lateral offset of an AI car relative to the track ideal spline.
function RollingStart.setAISplineAbsoluteOffset(carIndex, offsetMeters, isRelative)
  carIndex = carIndex or 0
  offsetMeters = tonumber(offsetMeters) or 0.0
  isRelative = isRelative or false
  if physics and physics.setAISplineAbsoluteOffset then
    physics.setAISplineAbsoluteOffset(carIndex, offsetMeters, isRelative)
  elseif physics and physics.setAISplineOffset then
    physics.setAISplineOffset(carIndex, offsetMeters, isRelative)
  end
end

---Commands an AI car to remain stationary for a set duration.
function RollingStart.setAIStopCounter(carIndex, seconds)
  carIndex = carIndex or 0
  seconds = math.max(0.0, tonumber(seconds) or 0.0)
  if physics and physics.setAIStopCounter then
    physics.setAIStopCounter(carIndex, seconds)
  end
end

---Linearly decays a lateral spline offset toward a target value at a safe rate.
function RollingStart.smoothSplineOffsetDecay(currentOffset, targetOffset, dt, maxRate)
  currentOffset = tonumber(currentOffset) or 0.0
  targetOffset = tonumber(targetOffset) or 0.0
  dt = tonumber(dt) or 0.016
  maxRate = maxRate or 0.5

  local diff = targetOffset - currentOffset
  local maxMove = maxRate * dt

  if math.abs(diff) <= maxMove then
    return targetOffset
  else
    return currentOffset + (diff > 0 and maxMove or -maxMove)
  end
end

return RollingStart

