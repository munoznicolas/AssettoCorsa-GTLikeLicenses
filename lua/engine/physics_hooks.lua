-- ==============================================================================
-- Gran Turismo License Engine for Assetto Corsa (CSP)
-- File: lua/engine/physics_hooks.lua
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

local Utils = safeRequire("utils")
local RollingStart = safeRequire("rolling_start")
local PhysicsHooks = {}

PhysicsHooks.toVec3 = (Utils and Utils.toVec3) or function(v)
  if type(v) == 'table' then
    return vec3(tonumber(v.x or v[1]) or 0, tonumber(v.y or v[2]) or 0, tonumber(v.z or v[3]) or 0)
  end
  return v or vec3(0, 0, 0)
end

local safeNormalize = (Utils and Utils.safeNormalize) or function(dir)
  local v = PhysicsHooks.toVec3(dir)
  local len = math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
  return len > 0.0001 and vec3(v.x / len, v.y / len, v.z / len) or vec3(0, 0, 1)
end

local lastGearEngageTime = {}
PhysicsHooks.estimateStartingGear = RollingStart.estimateStartingGear

---Converts world forward vector to Assetto Corsa's internal orientation coordinate convention.
---@param forwardVector table|vec3|number[]
---@return vec3
function PhysicsHooks.toACLookVector(forwardVector)
  local fwd = safeNormalize(PhysicsHooks.toVec3(forwardVector))
  return vec3(-fwd.x, -fwd.y, -fwd.z)
end

---Teleports the car to the specified world coordinates and heading vector.
function PhysicsHooks.teleportCar(carIndex, position, forwardVector, verticalOffset)
  carIndex = carIndex or 0
  verticalOffset = verticalOffset or 0.5
  local rawPos = PhysicsHooks.toVec3(position)

  if math.abs(rawPos.x) < 0.01 and math.abs(rawPos.z) < 0.01 and rawPos.y < 1.0 then
    if ac and ac.log then
      ac.log("[PhysicsHooks] Guard: detected dummy (0, 0.5, 0) spawn. Preserving native spawn point.")
    end
    return true
  end

  local fwd = safeNormalize(PhysicsHooks.toVec3(forwardVector))
  local targetPos = vec3(rawPos.x, rawPos.y + verticalOffset, rawPos.z)

  local carBefore = ac and ac.getCar and ac.getCar(carIndex)
  if carBefore and ac and ac.log then
    ac.log(string.format("[PhysicsHooks] Teleport BEFORE: pos=(%.2f, %.2f, %.2f), look=(%.2f, %.2f, %.2f)",
      carBefore.position.x, carBefore.position.y, carBefore.position.z,
      carBefore.look.x, carBefore.look.y, carBefore.look.z))
  end

  if physics and physics.setCarPosition then
    physics.setCarPosition(carIndex, targetPos, PhysicsHooks.toACLookVector(forwardVector))
  end

  local carAfter = ac and ac.getCar and ac.getCar(carIndex)
  if carAfter and ac and ac.log then
    ac.log(string.format("[PhysicsHooks] Teleport AFTER: pos=(%.2f, %.2f, %.2f), look=(%.2f, %.2f, %.2f), targetFwd=(%.2f, %.2f, %.2f)",
      carAfter.position.x, carAfter.position.y, carAfter.position.z,
      carAfter.look.x, carAfter.look.y, carAfter.look.z,
      fwd.x, fwd.y, fwd.z))
  end

  return true
end

---Imparts a forward linear velocity vector for rolling start scenarios.
function PhysicsHooks.applyRollingVelocity(carIndex, forwardVector, speedKmh, targetGear, targetRPM)
  carIndex = carIndex or 0
  speedKmh = tonumber(speedKmh) or 0

  if speedKmh <= 0 then
    if ac and ac.setCarPhysicLinearVelocity then
      ac.setCarPhysicLinearVelocity(carIndex, vec3(0, 0, 0))
    elseif physics and physics.setCarVelocity then
      physics.setCarVelocity(carIndex, vec3(0, 0, 0))
    end
    local gear = (targetGear and targetGear > 0) and targetGear or 1
    local rpm = (targetRPM and targetRPM > 0) and targetRPM or 1000
    if physics and physics.engageGear then physics.engageGear(carIndex, gear) end
    if physics and physics.setEngineRPM then physics.setEngineRPM(carIndex, rpm) end
    if ac and ac.overrideCarControls then ac.overrideCarControls(carIndex) end
    return true
  end

  local fwd = safeNormalize(PhysicsHooks.toVec3(forwardVector))
  local speedMs = speedKmh / 3.6
  local vel = vec3(fwd.x * speedMs, fwd.y * speedMs, fwd.z * speedMs)

  if ac and ac.setCarPhysicLinearVelocity then
    ac.setCarPhysicLinearVelocity(carIndex, vel)
  elseif physics and physics.setCarVelocity then
    physics.setCarVelocity(carIndex, vel)
  end

  if ac and ac.setCarPhysicAngularVelocity then
    ac.setCarPhysicAngularVelocity(carIndex, vec3(0, 0, 0))
  end

  local gear = (targetGear and targetGear > 0) and targetGear or PhysicsHooks.estimateStartingGear(speedKmh)
  local rpm = (targetRPM and targetRPM > 0) and targetRPM or 3500

  if physics and physics.engageGear then physics.engageGear(carIndex, gear) end
  if physics and physics.setEngineRPM then physics.setEngineRPM(carIndex, rpm) end
  if ac and ac.overrideCarControls then ac.overrideCarControls(carIndex) end

  local car = ac.getCar and ac.getCar(carIndex)
  local tyreRadius = (car and car.wheels and car.wheels[0] and car.wheels[0].tyreRadius and car.wheels[0].tyreRadius > 0.1) and car.wheels[0].tyreRadius or 0.30
  local targetOmega = speedMs / tyreRadius
  if physics and physics.setWheelAngularVelocity then
    local allWheels = (ac and ac.Wheel and ac.Wheel.All) or 60
    physics.setWheelAngularVelocity(carIndex, allWheels, targetOmega)
  end
  if physics and physics.forceUserBrakesFor then physics.forceUserBrakesFor(0) end
  if physics and physics.forceUserHandbrakeFor then physics.forceUserHandbrakeFor(0) end

  if ac and ac.log then
    ac.log(string.format("[PhysicsHooks] applyRollingVelocity car=%d: targetSpeed=%.1f km/h, vel=(%.2f, %.2f, %.2f), gear=%d, rpm=%d",
      carIndex, speedKmh, vel.x, vel.y, vel.z, gear, rpm))
  end

  return true
end

---Locks player steering, throttle, and brakes during the countdown phase.
function PhysicsHooks.lockControls(durationSeconds, isStandingStart, targetGear, targetRPM)
  durationSeconds = durationSeconds or 3.0

  if isStandingStart then
    local gear = (targetGear and targetGear > 0) and targetGear or 1
    local rpm = (targetRPM and targetRPM > 0) and targetRPM or 1000
    if physics and physics.engageGear then physics.engageGear(0, gear) end
    if physics and physics.setEngineRPM then physics.setEngineRPM(0, rpm) end
    if ac and ac.overrideCarControls then ac.overrideCarControls(0) end
    if physics and physics.lockUserControlsFor then physics.lockUserControlsFor(durationSeconds) end
    if physics and physics.forceUserBrakesFor then physics.forceUserBrakesFor(durationSeconds, 1.0) end
    if physics and physics.forceUserHandbrakeFor then physics.forceUserHandbrakeFor(durationSeconds, 1.0) end
  else
    -- Rolling start: Native AI autopilot handles vehicle driving.
    -- Ensure user locks and pedal forces are released so native AI can throttle and steer smoothly.
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
    if targetGear and targetGear > 0 then
      if physics and physics.engageGear then
        physics.engageGear(0, targetGear)
      end
      if physics and physics.setEngineRPM then
        physics.setEngineRPM(0, targetRPM or 3500)
      end
    end
  end
end

---Releases steering lock and restores normal driver or AI steering input.
---Under CSP, passing NaN to physics.overrideSteering clears the override.
---@param carIndex integer? @0-based car index
function PhysicsHooks.releaseSteeringOverride(carIndex)
  carIndex = carIndex or 0
  local nan = (math and math.nan) or (0 / 0)
  if physics and physics.overrideSteering then
    physics.overrideSteering(carIndex, nan)
  end
end

---Immediately unlocks all user inputs and releases forced brakes.
---@param carIndex integer? @0-based car index (default: 0)
---@param targetGear integer? @Optional gear to engage upon control release (e.g. 2 for rolling start)
function PhysicsHooks.unlockControls(carIndex, targetGear)
  carIndex = carIndex or 0
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
  PhysicsHooks.releaseSteeringOverride(carIndex)
  if physics and physics.setAIThrottleLimit then
    physics.setAIThrottleLimit(carIndex, 1.0)
  end
  -- Note: We deliberately bypass physics.lockUserGearboxFor(0, false) as it triggers AC starting line reset
  if targetGear and targetGear > 0 then
    if physics and physics.engageGear then
      physics.engageGear(carIndex, targetGear)
    end
    if physics and physics.setEngineRPM then
      physics.setEngineRPM(carIndex, 3500)
    end
    if ac and ac.overrideCarControls then
      local ctrl = ac.overrideCarControls(carIndex)
      if ctrl then
        ctrl.steer = math.huge
        ctrl.gas = math.huge
        ctrl.brake = math.huge
      end
    end
  end
  if physics and physics.setEngineStallEnabled then
    physics.setEngineStallEnabled(carIndex, true)
  end
end

---Releases sticky gearbox override flags in overrideCarControls, allowing player and AI to freely shift gears.
---@param carIndex integer? @0-based car index (default: 0)
function PhysicsHooks.releaseGearOverride(carIndex)
  carIndex = carIndex or 0
  if ac and ac.overrideCarControls then
    local ctrl = ac.overrideCarControls(carIndex)
    if ctrl then
      ctrl.gearUp = false
      ctrl.gearDown = false
      ctrl.clutch = 0.0
    end
  end
end

---Deploys car brakes at specified intensity upon test failure/disqualification or completion.
---Also zeroes user throttle so the vehicle slows down in a smooth, controlled manner.
---@param carIndex integer? @0-based car index (default: 0)
---@param intensity number? @Braking intensity between 0.0 and 1.0 (default: 0.5 for 50%)
---@param enableAI boolean? @Whether to enable AI autopilot for steering
function PhysicsHooks.applyFailureBraking(carIndex, intensity, enableAI)
  carIndex = carIndex or 0
  intensity = tonumber(intensity) or 0.5
  if physics and physics.setCarAutopilot then
    physics.setCarAutopilot(enableAI == true, false)
  end
  if physics and physics.forceUserThrottleFor then
    physics.forceUserThrottleFor(1.0, 0.0)
  end
  if physics and physics.forceUserBrakesFor then
    physics.forceUserBrakesFor(1.0, intensity)
  end
  if enableAI and physics and physics.setAIThrottleLimit then
    physics.setAIThrottleLimit(carIndex, 0.0)
  end
  if ac and ac.overrideCarControls then
    local ctrl = ac.overrideCarControls(carIndex)
    if ctrl then
      ctrl.gas = 0.0
      ctrl.brake = intensity
      -- Note: Do NOT override steer (leave as math.huge or don't touch) so AI can steer
    end
  end
end

-- Aliases for completion and general controlled post-test braking
PhysicsHooks.applyControlledBraking = PhysicsHooks.applyFailureBraking

---Releases failure or completion braking and restores user throttle and brake control.
---@param carIndex integer? @0-based car index (default: 0)
function PhysicsHooks.releaseFailureBraking(carIndex)
  carIndex = carIndex or 0
  if physics and physics.forceUserThrottleFor then
    physics.forceUserThrottleFor(0, 0)
  end
  if physics and physics.forceUserBrakesFor then
    physics.forceUserBrakesFor(0, 0)
  end
  if physics and physics.setAIThrottleLimit then
    physics.setAIThrottleLimit(carIndex, 1.0)
  end
  if ac and ac.overrideCarControls then
    local ctrl = ac.overrideCarControls(carIndex)
    if ctrl then
      ctrl.gas = math.huge
      ctrl.brake = math.huge
    end
  end
end

-- Aliases for completion and general controlled post-test braking
PhysicsHooks.releaseControlledBraking = PhysicsHooks.releaseFailureBraking

PhysicsHooks.startAIRolling = RollingStart.startAIRolling
PhysicsHooks.maintainAIRolling = RollingStart.maintainAIRolling
PhysicsHooks.maintainRollingVelocity = RollingStart.maintainRollingVelocity
PhysicsHooks.setAITopSpeed = RollingStart.setAITopSpeed
PhysicsHooks.setAIThrottleLimit = RollingStart.setAIThrottleLimit
PhysicsHooks.setAICaution = RollingStart.setAICaution
PhysicsHooks.setAISplineAbsoluteOffset = RollingStart.setAISplineAbsoluteOffset
PhysicsHooks.setAIStopCounter = RollingStart.setAIStopCounter
PhysicsHooks.smoothSplineOffsetDecay = RollingStart.smoothSplineOffsetDecay

---Disengages AI autopilot and seamlessly returns full control to the player at GO!
---@param carIndex integer? @0-based car index (default: 0)
---@param targetGear integer? @Optional gear to engage upon control release
function PhysicsHooks.stopAIRolling(carIndex, targetGear)
  carIndex = carIndex or 0

  if physics and physics.setCarAutopilot then
    physics.setCarAutopilot(false)
  end
  if physics and physics.setAITopSpeed then
    physics.setAITopSpeed(carIndex, 999999.0)
  end

  local nan = (math and math.nan) or (0 / 0)
  if physics and physics.overrideSteering then
    physics.overrideSteering(carIndex, nan)
  end

  PhysicsHooks.unlockControls(carIndex, targetGear)

  if ac and ac.log then
    ac.log(string.format("[PhysicsHooks] stopAIRolling car=%d: autopilot=false, handover complete, gear=%d", carIndex, targetGear or 0))
  end
end

---Orchestrates full spawn placement and physics initialization from a test definition config.
---@param testConfig table @Table complying with test_definition.schema.json
---@param carIndex integer? @0-based car index (default: 0)
---@return boolean success, string? errorMessage
function PhysicsHooks.setupSpawn(testConfig, carIndex)
  if not testConfig then
    return false, "Invalid test configuration: nil"
  end

  if testConfig.test_id == "AI_TELEMETRY_RECORDER" or testConfig.is_telemetry_recording then
    if ac and ac.log then
      ac.log("[PhysicsHooks] Telemetry recording mode: preserving native track spawn point")
    end
    return true
  end

  if not testConfig.spawn or not testConfig.spawn.position then
    return false, "Invalid test configuration: missing spawn definition"
  end

  carIndex = carIndex or 0
  local spawn = testConfig.spawn
  local initialSpeed = tonumber(spawn.initial_speed_kmh) or 0
  local isStanding = (testConfig.start_mode == "STANDING") or (initialSpeed <= 0)

  local targetGear = tonumber(spawn.gear)
  if not targetGear or targetGear <= 0 then
    targetGear = isStanding and 1 or PhysicsHooks.estimateStartingGear(initialSpeed)
  end
  local targetRPM = tonumber(spawn.rpm)
  if not targetRPM or targetRPM <= 0 then
    targetRPM = isStanding and 1000 or 3500
  end

  if physics and physics.setEngineStallEnabled then
    physics.setEngineStallEnabled(carIndex, false)
  end
  if physics and physics.resetCarState then
    physics.resetCarState(carIndex)
  end
  if physics and physics.engageGear then
    physics.engageGear(carIndex, 0)
  end
  if ac and ac.overrideCarControls then
    local ctrl = ac.overrideCarControls(carIndex)
    if ctrl then
      ctrl.clutch = 1.0
    end
  end

  lastGearEngageTime[carIndex] = 0
  local ok = PhysicsHooks.teleportCar(carIndex, spawn.position, spawn.forward_vector)
  if not ok then
    return false, "Failed to teleport car to spawn coordinates"
  end

  if physics and physics.setEngineRPM then
    physics.setEngineRPM(carIndex, targetRPM)
  end

  if initialSpeed > 0 then
    if physics and physics.forceUserHandbrakeFor then
      physics.forceUserHandbrakeFor(0, 0)
    end
    if physics and physics.forceUserBrakesFor then
      physics.forceUserBrakesFor(0, 0)
    end
    PhysicsHooks.applyRollingVelocity(carIndex, spawn.forward_vector, initialSpeed, targetGear, targetRPM)
    PhysicsHooks.startAIRolling(carIndex, initialSpeed, targetGear, targetRPM, spawn.forward_vector)
  else
    if physics and physics.setCarAutopilot then
      physics.setCarAutopilot(false)
    end
    PhysicsHooks.applyRollingVelocity(carIndex, spawn.forward_vector, 0, targetGear, targetRPM)
  end

  if physics and physics.engageGear then
    physics.engageGear(carIndex, targetGear)
  end
  if ac and ac.overrideCarControls then
    local ctrl = ac.overrideCarControls(carIndex)
    if ctrl then
      ctrl.clutch = 1.0
    end
  end

  if ac and ac.log then
    ac.log(string.format("[PhysicsHooks] setupSpawn car=%d: start_mode=%s, initial_speed=%.1f km/h, gear=%d, rpm=%d, pos=(%.2f, %.2f, %.2f)",
      carIndex, tostring(testConfig.start_mode), initialSpeed, targetGear, targetRPM, spawn.position[1], spawn.position[2], spawn.position[3]))
  end

  return true
end

return PhysicsHooks

