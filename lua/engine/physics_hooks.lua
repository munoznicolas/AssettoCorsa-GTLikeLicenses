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
local PhysicsHooks = {}

PhysicsHooks.toVec3 = Utils and Utils.toVec3 or function(v)
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
  local v = PhysicsHooks.toVec3(dir)
  local len = math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
  if len > 0.0001 then return vec3(v.x / len, v.y / len, v.z / len) end
  return vec3(0, 0, 1)
end

local lastGearEngageTime = {}

---Estimates a realistic starting gear for rolling start velocity.
---@param speedKmh number
---@return integer gearIndex (1-based gear, 1 to 6)
function PhysicsHooks.estimateStartingGear(speedKmh)
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

---Converts world forward vector to Assetto Corsa's internal orientation coordinate convention.
---In AC C++ physics, the orientation vector convention is negated relative to car.look (-fwd).
---@param forwardVector table|vec3|number[]
---@return vec3
function PhysicsHooks.toACLookVector(forwardVector)
  local fwd = safeNormalize(PhysicsHooks.toVec3(forwardVector))
  return vec3(-fwd.x, -fwd.y, -fwd.z)
end

---Teleports the car to the specified world coordinates and heading vector.
---Raises the car slightly (+0.05m) to avoid bottoming out or clipping into road colliders.
---@param carIndex integer @0-based car index (0 for player car)
---@param position table|vec3|number[] @World position [X, Y, Z]
---@param forwardVector table|vec3|number[] @Heading direction [dX, dY, dZ]
---@param verticalOffset number? @Optional elevation offset in meters (default: 0.05m)
---@return boolean success
function PhysicsHooks.teleportCar(carIndex, position, forwardVector, verticalOffset)
  carIndex = carIndex or 0
  verticalOffset = verticalOffset or 0.5

  local rawPos = PhysicsHooks.toVec3(position)

  -- Safety guard: if rawPos is dummy default (0, 0.5, 0), do not drop car into void
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

  -- Teleport car using CSP physics APIs
  -- Assetto Corsa orientation convention is encapsulated by toACLookVector
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
---@param carIndex integer @0-based car index
---@param forwardVector table|vec3|number[] @Normalized forward direction
---@param speedKmh number @Initial speed in kilometers per hour
---@param targetGear integer? @Optional gear index to engage
---@param targetRPM number? @Optional target engine RPM
---@return boolean success
function PhysicsHooks.applyRollingVelocity(carIndex, forwardVector, speedKmh, targetGear, targetRPM)
  carIndex = carIndex or 0
  speedKmh = tonumber(speedKmh) or 0

  if speedKmh <= 0 then
    -- Standing start: ensure velocity is zeroed out and 1st gear engaged
    if ac and ac.setCarPhysicLinearVelocity then
      ac.setCarPhysicLinearVelocity(carIndex, vec3(0, 0, 0))
    elseif physics and physics.setCarVelocity then
      physics.setCarVelocity(carIndex, vec3(0, 0, 0))
    end
    local gear = (targetGear and targetGear > 0) and targetGear or 1
    local rpm = (targetRPM and targetRPM > 0) and targetRPM or 1000
    if physics and physics.engageGear then
      physics.engageGear(carIndex, gear)
    end
    if physics and physics.setEngineRPM then
      physics.setEngineRPM(carIndex, rpm)
    end
    if ac and ac.overrideCarControls then
      local ctrl = ac.overrideCarControls(carIndex)
      if ctrl then
      end
    end
    return true
  end

  local fwd = safeNormalize(PhysicsHooks.toVec3(forwardVector))
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
  local gear = (targetGear and targetGear > 0) and targetGear or PhysicsHooks.estimateStartingGear(speedKmh)
  local rpm = (targetRPM and targetRPM > 0) and targetRPM or 3500

  if physics and physics.engageGear then
    physics.engageGear(carIndex, gear)
  end
  if physics and physics.setEngineRPM then
    physics.setEngineRPM(carIndex, rpm)
  end
  if ac and ac.overrideCarControls then
    local ctrl = ac.overrideCarControls(carIndex)
    if ctrl then
    end
  end

  -- Initialize wheel angular velocity matching launch road speed and clear brakes
  local car = ac.getCar and ac.getCar(carIndex)
  local tyreRadius = (car and car.wheels and car.wheels[0] and car.wheels[0].tyreRadius and car.wheels[0].tyreRadius > 0.1) and car.wheels[0].tyreRadius or 0.30
  local targetOmega = speedMs / tyreRadius
  if physics and physics.setWheelAngularVelocity then
    local allWheels = (ac and ac.Wheel and ac.Wheel.All) or 60
    physics.setWheelAngularVelocity(carIndex, allWheels, targetOmega)
  end
  if physics and physics.forceUserBrakesFor then
    physics.forceUserBrakesFor(0)
  end
  if physics and physics.forceUserHandbrakeFor then
    physics.forceUserHandbrakeFor(0)
  end

  if ac and ac.log then
    ac.log(string.format("[PhysicsHooks] applyRollingVelocity car=%d: targetSpeed=%.1f km/h, vel=(%.2f, %.2f, %.2f), gear=%d, rpm=%d",
      carIndex, speedKmh, vel.x, vel.y, vel.z, gear, rpm))
  end

  return true
end

---Locks player steering, throttle, and brakes during the countdown phase.
---@param durationSeconds number @Time in seconds to hold the lock
---@param isStandingStart boolean @Whether this test is a standing launch (if true, forces brakes)
---@param targetGear integer? @Target gear to lock
---@param targetRPM number? @Target engine RPM
function PhysicsHooks.lockControls(durationSeconds, isStandingStart, targetGear, targetRPM)
  durationSeconds = durationSeconds or 3.0

  if isStandingStart then
    local gear = (targetGear and targetGear > 0) and targetGear or 1
    local rpm = (targetRPM and targetRPM > 0) and targetRPM or 1000
    if physics and physics.engageGear then
      physics.engageGear(0, gear)
    end
    if physics and physics.setEngineRPM then
      physics.setEngineRPM(0, rpm)
    end
    if ac and ac.overrideCarControls then
      local ctrl = ac.overrideCarControls(0)
      if ctrl then
      end
    end
    if physics and physics.lockUserControlsFor then
      physics.lockUserControlsFor(durationSeconds)
    end
    -- On standing starts, engage brakes and handbrake so the vehicle does not roll on slopes
    if physics and physics.forceUserBrakesFor then
      physics.forceUserBrakesFor(durationSeconds, 1.0)
    end
    if physics and physics.forceUserHandbrakeFor then
      physics.forceUserHandbrakeFor(durationSeconds, 1.0)
    end
    -- Note: We deliberately bypass physics.lockUserGearboxFor because AC's starting line logic
    -- resets the transmission into neutral, which breaks seamless in-gear launch.
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

---Engages rolling start countdown physics along the straight sector line via native AI autopilot.
---Enables autopilot, caps AI speed to target rolling speed, and locks to the ideal racing line.
---@param carIndex integer? @0-based car index (default: 0)
---@param targetSpeedKmh number @Target rolling speed in km/h
---@param targetGear integer? @Target gear to engage and maintain
---@param targetRPM number? @Target engine RPM to maintain
---@param fallbackFwd table|vec3|number[]? @Forward vector
function PhysicsHooks.startAIRolling(carIndex, targetSpeedKmh, targetGear, targetRPM, fallbackFwd)
  carIndex = carIndex or 0
  targetSpeedKmh = tonumber(targetSpeedKmh) or 70.0
  targetGear = (targetGear and targetGear > 0) and targetGear or PhysicsHooks.estimateStartingGear(targetSpeedKmh)
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

---Disengages AI autopilot and seamlessly returns full control to the player at GO!
---@param carIndex integer? @0-based car index (default: 0)
---@param targetGear integer? @Optional gear to engage upon control release
function PhysicsHooks.stopAIRolling(carIndex, targetGear)
  carIndex = carIndex or 0

  -- Deactivate AI autopilot
  if physics and physics.setCarAutopilot then
    physics.setCarAutopilot(false)
  end

  -- Remove AI top speed ceiling so player can accelerate without restriction
  if physics and physics.setAITopSpeed then
    physics.setAITopSpeed(carIndex, 999999.0)
  end

  -- Unlock steering override so player has immediate steering control
  local nan = (math and math.nan) or (0 / 0)
  if physics and physics.overrideSteering then
    physics.overrideSteering(carIndex, nan)
  end

  -- Unlock controls, gearbox lock, and engage target gear
  PhysicsHooks.unlockControls(carIndex, targetGear)

  if ac and ac.log then
    ac.log(string.format("[PhysicsHooks] stopAIRolling car=%d: autopilot=false, handover complete, gear=%d", carIndex, targetGear or 0))
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
function PhysicsHooks.maintainAIRolling(carIndex, targetSpeedKmh, fallbackFwd, dt, targetGear, targetRPM)
  carIndex = carIndex or 0
  targetSpeedKmh = tonumber(targetSpeedKmh) or 70.0
  targetGear = (targetGear and targetGear > 0) and targetGear or PhysicsHooks.estimateStartingGear(targetSpeedKmh)
  targetRPM = (targetRPM and targetRPM > 0) and targetRPM or 3500

  local hasSpline = (ac and ac.hasTrackSpline) and ac.hasTrackSpline() or true
  if hasSpline then
    -- Native AI Autopilot rolling maintenance:
    -- Preserve AI top speed ceiling, full AI level, and zero spline offset
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

    -- If car speed dropped significantly below target rolling speed (e.g. spawn settling or session restart),
    -- re-assert forward velocity so the vehicle doesn't bog down or crawl in 1st gear
    local car = ac.getCar and ac.getCar(carIndex)
    if targetSpeedKmh > 0 and car and car.speedKmh < (targetSpeedKmh * 0.75) then
      local rawFwd = PhysicsHooks.toVec3(fallbackFwd)
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
    -- Fallback when track has no AI spline:
    -- Maintain horizontal forward velocity while preserving vertical velocity (vy)
    -- so natural gravity and suspension compression remain fully active
    local car = ac.getCar and ac.getCar(carIndex)
    local rawFwd = PhysicsHooks.toVec3(fallbackFwd)
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

  -- Ensure target gear remains firmly engaged during countdown
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
        ctrl.clutch = 0.0 -- Force clutch release
      end
    end
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

  -- 1. Prevent engine stall by engaging neutral, disabling stall, and pressing clutch before teleporting
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

  -- Reposition car to target sector coordinates
  lastGearEngageTime[carIndex] = 0
  local ok = PhysicsHooks.teleportCar(carIndex, spawn.position, spawn.forward_vector)
  if not ok then
    return false, "Failed to teleport car to spawn coordinates"
  end

  if physics and physics.setEngineRPM then
    physics.setEngineRPM(carIndex, targetRPM)
  end

  -- 3. Impart initial rolling launch velocity if defined
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

  -- 4. Firmly assert target gear and lock gearbox immediately upon spawn
  if physics and physics.engageGear then
    physics.engageGear(carIndex, targetGear)
  end
  if ac and ac.overrideCarControls then
    local ctrl = ac.overrideCarControls(carIndex)
    if ctrl then
      ctrl.clutch = 1.0 -- Release clutch override
    end
  end

  if ac and ac.log then
    ac.log(string.format("[PhysicsHooks] setupSpawn car=%d: start_mode=%s, initial_speed=%.1f km/h, gear=%d, rpm=%d, pos=(%.2f, %.2f, %.2f)",
      carIndex, tostring(testConfig.start_mode), initialSpeed, targetGear, targetRPM, spawn.position[1], spawn.position[2], spawn.position[3]))
  end

  return true
end

---Continuously re-applies linear velocity on frame updates during COUNTDOWN state.
---Prevents native AC engine from clearing velocity vectors before GO!
---@param carIndex integer @0-based car index
---@param forwardVector table|vec3|number[] @Forward facing direction
---@param speedKmh number @Target rolling speed in km/h
---@return boolean success
function PhysicsHooks.maintainRollingVelocity(carIndex, forwardVector, speedKmh)
  carIndex = carIndex or 0
  speedKmh = tonumber(speedKmh) or 0
  if speedKmh <= 0 then return false end

  local fwd = safeNormalize(PhysicsHooks.toVec3(forwardVector))
  local speedMs = speedKmh / 3.6
  local vel = vec3(fwd.x * speedMs, fwd.y * speedMs, fwd.z * speedMs)

  if physics and physics.setCarVelocity then
    physics.setCarVelocity(carIndex, vel)
  end

  local gear = PhysicsHooks.estimateStartingGear(speedKmh)
  if physics and physics.engageGear then
    physics.engageGear(carIndex, gear)
  end
  -- Clear brakes and spin wheels at road speed
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
---@param carIndex integer @0-based car index
---@param speedKmh number @Speed limit in km/h (use 1e9 or 999999 for unlimited)
function PhysicsHooks.setAITopSpeed(carIndex, speedKmh)
  carIndex = carIndex or 0
  speedKmh = tonumber(speedKmh) or 999999.0
  if physics and physics.setAITopSpeed then
    physics.setAITopSpeed(carIndex, speedKmh)
  end
end

---Limits the maximum throttle output of an AI car.
---@param carIndex integer @0-based car index
---@param throttleLimit number @Throttle cap between 0.0 and 1.0
function PhysicsHooks.setAIThrottleLimit(carIndex, throttleLimit)
  carIndex = carIndex or 0
  throttleLimit = math.max(0.0, math.min(1.0, tonumber(throttleLimit) or 1.0))
  if physics and physics.setAIThrottleLimit then
    physics.setAIThrottleLimit(carIndex, throttleLimit)
  end
end

---Adjusts the caution level of an AI driver.
---@param carIndex integer @0-based car index
---@param level number @Caution level (0.0 = aggressive, 1.0 = normal, 3.0+ = extra cautious)
function PhysicsHooks.setAICaution(carIndex, level)
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
function PhysicsHooks.setAISplineAbsoluteOffset(carIndex, offsetMeters, isRelative)
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
function PhysicsHooks.setAIStopCounter(carIndex, seconds)
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
function PhysicsHooks.smoothSplineOffsetDecay(currentOffset, targetOffset, dt, maxRate)
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

return PhysicsHooks

