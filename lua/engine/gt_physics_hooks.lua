-- ==============================================================================
-- Gran Turismo License Engine for Assetto Corsa (CSP)
-- File: lua/engine/gt_physics_hooks.lua
-- Description: Physics manipulation hooks for car teleportation, rolling launch
--              velocity vectors, and control locking during countdown sequences.
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

local GTUtils = safeRequire("gt_utils")
local GTPhysicsHooks = {}

GTPhysicsHooks.toVec3 = GTUtils and GTUtils.toVec3 or function(v)
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

local safeNormalize = GTUtils and GTUtils.safeNormalize or function(dir)
  local v = GTPhysicsHooks.toVec3(dir)
  local len = math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
  if len > 0.0001 then return vec3(v.x / len, v.y / len, v.z / len) end
  return vec3(0, 0, 1)
end

---Estimates a realistic starting gear for rolling start velocity.
---@param speedKmh number
---@return integer gearIndex (1-based gear, 1 to 6)
function GTPhysicsHooks.estimateStartingGear(speedKmh)
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

---Teleports the car to the specified world coordinates and heading vector.
---Raises the car slightly (+0.05m) to avoid bottoming out or clipping into road colliders.
---@param carIndex integer @0-based car index (0 for player car)
---@param position table|vec3|number[] @World position [X, Y, Z]
---@param forwardVector table|vec3|number[] @Heading direction [dX, dY, dZ]
---@param verticalOffset number? @Optional elevation offset in meters (default: 0.05m)
---@return boolean success
function GTPhysicsHooks.teleportCar(carIndex, position, forwardVector, verticalOffset)
  carIndex = carIndex or 0
  verticalOffset = verticalOffset or 0.05

  local rawPos = GTPhysicsHooks.toVec3(position)
  local fwd = safeNormalize(GTPhysicsHooks.toVec3(forwardVector))
  local targetPos = vec3(rawPos.x, rawPos.y + verticalOffset, rawPos.z)

  -- Teleport car using CSP physics APIs
  if ac and ac.setCarPhysicPosition then
    ac.setCarPhysicPosition(carIndex, targetPos)
  end
  if ac and ac.setCarPhysicHeading then
    ac.setCarPhysicHeading(carIndex, fwd, vec3(0, 1, 0))
  end
  if physics and physics.setCarPosition then
    physics.setCarPosition(carIndex, targetPos, fwd)
  end

  -- Reset car physical condition (repairs damage, resets tire wear and temperatures)
  if physics and physics.resetCarState then
    physics.resetCarState(carIndex, 1.0)
  end

  return true
end

---Imparts a forward linear velocity vector for rolling start scenarios.
---@param carIndex integer @0-based car index
---@param forwardVector table|vec3|number[] @Normalized forward direction
---@param speedKmh number @Initial speed in kilometers per hour
---@return boolean success
function GTPhysicsHooks.applyRollingVelocity(carIndex, forwardVector, speedKmh)
  carIndex = carIndex or 0
  speedKmh = tonumber(speedKmh) or 0

  if speedKmh <= 0 then
    -- Standing start: ensure velocity is zeroed out
    if ac and ac.setCarPhysicLinearVelocity then
      ac.setCarPhysicLinearVelocity(carIndex, vec3(0, 0, 0))
    elseif physics and physics.setCarVelocity then
      physics.setCarVelocity(carIndex, vec3(0, 0, 0))
    end
    return true
  end

  local fwd = safeNormalize(GTPhysicsHooks.toVec3(forwardVector))
  local speedMs = speedKmh / 3.6
  local vel = vec3(fwd.x * speedMs, fwd.y * speedMs, fwd.z * speedMs)

  -- Apply linear velocity vector to the car
  if ac and ac.setCarPhysicLinearVelocity then
    ac.setCarPhysicLinearVelocity(carIndex, vel)
  elseif physics and physics.setCarVelocity then
    physics.setCarVelocity(carIndex, vel)
  end

  -- Stabilize pitch/roll rotation at spawn
  if ac and ac.setCarPhysicAngularVelocity then
    ac.setCarPhysicAngularVelocity(carIndex, vec3(0, 0, 0))
  end

  -- Engage an appropriate gear and engine RPM for rolling launch speed
  local gear = GTPhysicsHooks.estimateStartingGear(speedKmh)
  if ac and ac.accessCarPhysics then
    local phys = ac.accessCarPhysics(carIndex)
    if phys then
      pcall(function() phys:setGear(gear) end)
      pcall(function() phys:setEngineRPM(3500) end)
    end
  elseif physics and physics.engageGear then
    physics.engageGear(carIndex, gear)
  end

  return true
end

---Locks player steering, throttle, and brakes during the countdown phase.
---@param durationSeconds number @Time in seconds to hold the lock
---@param isStandingStart boolean @Whether this test is a standing launch (if true, forces brakes)
function GTPhysicsHooks.lockControls(durationSeconds, isStandingStart)
  durationSeconds = durationSeconds or 3.0

  if physics and physics.lockUserControlsFor then
    physics.lockUserControlsFor(durationSeconds)
  end

  if isStandingStart then
    -- On standing starts, engage brakes and handbrake so the vehicle does not roll on slopes
    if physics and physics.forceUserBrakesFor then
      physics.forceUserBrakesFor(durationSeconds, 1.0)
    end
    if physics and physics.forceUserHandbrakeFor then
      physics.forceUserHandbrakeFor(durationSeconds, 1.0)
    end
    if physics and physics.lockUserGearboxFor then
      physics.lockUserGearboxFor(durationSeconds, false)
    end
  end
end

---Immediately unlocks all user inputs and releases forced brakes.
function GTPhysicsHooks.unlockControls()
  if physics and physics.lockUserControlsFor then
    physics.lockUserControlsFor(0)
  end
  if physics and physics.forceUserBrakesFor then
    physics.forceUserBrakesFor(0, 0)
  end
  if physics and physics.forceUserHandbrakeFor then
    physics.forceUserHandbrakeFor(0, 0)
  end
  if physics and physics.lockUserGearboxFor then
    physics.lockUserGearboxFor(0, false)
  end
end

---Orchestrates full spawn placement and physics initialization from a test definition config.
---@param testConfig table @Table complying with test_definition.schema.json
---@param carIndex integer? @0-based car index (default: 0)
---@return boolean success, string? errorMessage
function GTPhysicsHooks.setupSpawn(testConfig, carIndex)
  if not testConfig or not testConfig.spawn then
    return false, "Invalid test configuration: missing spawn definition"
  end

  carIndex = carIndex or 0
  local spawn = testConfig.spawn
  local initialSpeed = tonumber(spawn.initial_speed_kmh) or 0
  local isStanding = (testConfig.start_mode == "STANDING") or (initialSpeed == 0)

  -- 1. Reposition car to target sector coordinates
  local ok = GTPhysicsHooks.teleportCar(carIndex, spawn.position, spawn.forward_vector)
  if not ok then
    return false, "Failed to teleport car to spawn coordinates"
  end

  -- 2. Impart initial rolling launch velocity if defined
  if initialSpeed > 0 then
    GTPhysicsHooks.applyRollingVelocity(carIndex, spawn.forward_vector, initialSpeed)
  else
    GTPhysicsHooks.applyRollingVelocity(carIndex, spawn.forward_vector, 0)
  end

  return true
end

---Continuously re-applies linear velocity on frame updates during COUNTDOWN state.
---Prevents native AC engine from clearing velocity vectors before GO!
---@param carIndex integer @0-based car index
---@param forwardVector table|vec3|number[] @Forward facing direction
---@param speedKmh number @Target rolling speed in km/h
---@return boolean success
function GTPhysicsHooks.maintainRollingVelocity(carIndex, forwardVector, speedKmh)
  carIndex = carIndex or 0
  speedKmh = tonumber(speedKmh) or 0
  if speedKmh <= 0 then return false end

  local fwd = safeNormalize(GTPhysicsHooks.toVec3(forwardVector))
  local speedMs = speedKmh / 3.6
  local vel = vec3(fwd.x * speedMs, fwd.y * speedMs, fwd.z * speedMs)

  if ac and ac.setCarPhysicLinearVelocity then
    ac.setCarPhysicLinearVelocity(carIndex, vel)
  elseif physics and physics.setCarVelocity then
    physics.setCarVelocity(carIndex, vel)
  end

  return true
end

---Sets an absolute top speed ceiling (in km/h) on an AI controlled vehicle.
---@param carIndex integer @0-based car index
---@param speedKmh number @Speed limit in km/h (use 1e9 or 999999 for unlimited)
function GTPhysicsHooks.setAITopSpeed(carIndex, speedKmh)
  carIndex = carIndex or 0
  speedKmh = tonumber(speedKmh) or 999999.0
  if physics and physics.setAITopSpeed then
    physics.setAITopSpeed(carIndex, speedKmh)
  end
end

---Limits the maximum throttle output of an AI car.
---@param carIndex integer @0-based car index
---@param throttleLimit number @Throttle cap between 0.0 and 1.0
function GTPhysicsHooks.setAIThrottleLimit(carIndex, throttleLimit)
  carIndex = carIndex or 0
  throttleLimit = math.max(0.0, math.min(1.0, tonumber(throttleLimit) or 1.0))
  if physics and physics.setAIThrottleLimit then
    physics.setAIThrottleLimit(carIndex, throttleLimit)
  end
end

---Adjusts the caution level of an AI driver.
---@param carIndex integer @0-based car index
---@param level number @Caution level (0.0 = aggressive, 1.0 = normal, 3.0+ = extra cautious)
function GTPhysicsHooks.setAICaution(carIndex, level)
  carIndex = carIndex or 0
  level = tonumber(level) or 1.0
  if physics and physics.setAICaution then
    physics.setAICaution(carIndex, level)
  end
end

---Sets the lateral offset of an AI car relative to the track ideal spline.
---@param carIndex integer @0-based car index
---@param offsetMeters number @Offset distance in meters (negative = left, positive = right)
---@param isRelative boolean? @Whether offset is relative to car position (default: false)
function GTPhysicsHooks.setAISplineAbsoluteOffset(carIndex, offsetMeters, isRelative)
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
---@param carIndex integer @0-based car index
---@param seconds number @Hold duration in seconds
function GTPhysicsHooks.setAIStopCounter(carIndex, seconds)
  carIndex = carIndex or 0
  seconds = math.max(0.0, tonumber(seconds) or 0.0)
  if physics and physics.setAIStopCounter then
    physics.setAIStopCounter(carIndex, seconds)
  end
end

---Linearly decays a lateral spline offset toward a target value at a safe rate.
---@param currentOffset number @Current lateral offset in meters
---@param targetOffset number @Target lateral offset in meters (e.g. 0.0 for racing line)
---@param dt number @Frame delta time in seconds
---@param maxRate number? @Max rate of offset decay in m/s (default: 0.5 m/s)
---@return number newOffset
function GTPhysicsHooks.smoothSplineOffsetDecay(currentOffset, targetOffset, dt, maxRate)
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

return GTPhysicsHooks

