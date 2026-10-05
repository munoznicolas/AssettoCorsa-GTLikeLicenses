-- ==============================================================================
-- Gran Turismo License Engine for Assetto Corsa (CSP)
-- File: lua/engine/gt_physics_hooks.lua
-- Description: Physics manipulation hooks for car teleportation, rolling launch
--              velocity vectors, and control locking during countdown sequences.
-- ==============================================================================

local GTPhysicsHooks = {}

---Converts an array {x, y, z}, table {x=..., y=..., z=...}, or vec3 to a valid vec3.
---@param v table|vec3|number[]
---@return vec3
function GTPhysicsHooks.toVec3(v)
  if v == nil then
    return vec3(0, 0, 0)
  end

  -- Already a vec3 or cdata object with x, y, z
  if type(v) == 'cdata' or (type(v) == 'userdata') then
    return v
  end

  if type(v) == 'table' then
    if v.x ~= nil and v.y ~= nil and v.z ~= nil then
      return vec3(tonumber(v.x) or 0, tonumber(v.y) or 0, tonumber(v.z) or 0)
    elseif v[1] ~= nil and v[2] ~= nil and v[3] ~= nil then
      return vec3(tonumber(v[1]) or 0, tonumber(v[2]) or 0, tonumber(v[3]) or 0)
    end
  end

  return vec3(0, 0, 0)
end

---Normalizes a direction vector safely.
---@param dir vec3
---@return vec3
local function safeNormalize(dir)
  local len = math.sqrt(dir.x * dir.x + dir.y * dir.y + dir.z * dir.z)
  if len > 0.0001 then
    return vec3(dir.x / len, dir.y / len, dir.z / len)
  end
  return vec3(0, 0, 1) -- default forward facing vector
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

  -- Apply slight vertical offset to avoid ground mesh penetration
  local targetPos = vec3(rawPos.x, rawPos.y + verticalOffset, rawPos.z)

  -- Teleport car using CSP physics API
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
    if physics and physics.setCarVelocity then
      physics.setCarVelocity(carIndex, vec3(0, 0, 0))
    end
    if physics and physics.engageGear then
      physics.engageGear(carIndex, 1)
    end
    return true
  end

  local fwd = safeNormalize(GTPhysicsHooks.toVec3(forwardVector))
  local speedMs = speedKmh / 3.6
  local vel = vec3(fwd.x * speedMs, fwd.y * speedMs, fwd.z * speedMs)

  -- Apply linear velocity vector to the car
  if physics and physics.setCarVelocity then
    physics.setCarVelocity(carIndex, vel)
  end

  -- Engage an appropriate gear for the rolling launch speed
  local gear = GTPhysicsHooks.estimateStartingGear(speedKmh)
  if physics and physics.engageGear then
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

return GTPhysicsHooks
