-- ==============================================================================
-- Gran Turismo License Engine - Telemetry & Diagnostics Logger
-- File: lua/engine/telemetry_logger.lua
-- Description: Decoupled telemetry and diagnostic logger for session lifecycle,
--              handover suspension kinematics, and periodic vehicle tracking.
-- ==============================================================================

local TelemetryLogger = {}
TelemetryLogger.__index = TelemetryLogger

---Creates a new telemetry logger instance.
---@return table
function TelemetryLogger.new()
  local self = setmetatable({}, TelemetryLogger)
  self.lastPeriodicLog = 0
  self.lastPostGoLog = 0
  return self
end

---Logs periodic simulation position, speed, and spline progress (throttled).
---@param car table? @Assetto Corsa car state (ac.getCar)
---@param sessionTime number @Active session time in seconds
---@param interval number? @Throttle interval in seconds (default: 2.0s)
function TelemetryLogger:logLiveTrack(car, sessionTime, interval)
  if not car or not (ac and ac.log) then return end
  interval = interval or 2.0

  if sessionTime - self.lastPeriodicLog >= interval then
    self.lastPeriodicLog = sessionTime
    local pos = car.position or { x = 0, y = 0, z = 0 }
    local spd = car.speedKmh or 0
    local spline = car.splinePosition or 0
    local gear = car.gear or 0
    ac.log(string.format(
      "[GTLicense] LIVE TRACK: t=%.1fs | pos=(%.1f, %.1f, %.1f) | spd=%.1f | spline=%.4f | gear=%d",
      sessionTime, pos.x, pos.y, pos.z, spd, spline, gear
    ))
  end
end

---Logs high-frequency wheel angular speeds, suspension travel, and vertical velocity right after GO.
---@param car table? @Assetto Corsa car state (ac.getCar)
---@param sessionTime number @Active session time in seconds
---@param durationWindow number? @Window during which handover is logged (default: 1.2s)
function TelemetryLogger:logHandoverKinematics(car, sessionTime, durationWindow)
  if not car or not (ac and ac.log) then return end
  durationWindow = durationWindow or 1.2

  if sessionTime <= durationWindow then
    if sessionTime - self.lastPostGoLog >= 0.2 then
      self.lastPostGoLog = sessionTime
      local wFL = (car.wheels and car.wheels[0] and car.wheels[0].angularSpeed) or 0
      local wFR = (car.wheels and car.wheels[1] and car.wheels[1].angularSpeed) or 0
      local wRL = (car.wheels and car.wheels[2] and car.wheels[2].angularSpeed) or 0
      local wRR = (car.wheels and car.wheels[3] and car.wheels[3].angularSpeed) or 0
      local sFL = (car.wheels and car.wheels[0] and car.wheels[0].suspensionTravel) or 0
      local sRL = (car.wheels and car.wheels[2] and car.wheels[2].suspensionTravel) or 0
      local ldFL = (car.wheels and car.wheels[0] and car.wheels[0].load) or 0
      local ldRL = (car.wheels and car.wheels[2] and car.wheels[2].load) or 0
      local vy = (car.velocity and car.velocity.y) or 0
      local spd = car.speedKmh or 0
      local gear = car.gear or 0

      ac.log(string.format(
        "[GTLicense] Post-GO t=%.2fs | Spd=%.1f | Gear=%d | vy=%.2f | Susp=(FL:%.3f, RL:%.3f) | Load=(FL:%.0f, RL:%.0f) | Omegas=(FL:%.1f, FR:%.1f, RL:%.1f, RR:%.1f)",
        sessionTime, spd, gear, vy, sFL, sRL, ldFL, ldRL, wFL, wFR, wRL, wRR
      ))
    end
  end
end

---Logs snapshot at countdown GO trigger.
---@param car table? @Assetto Corsa car state (ac.getCar)
---@param targetGear integer @Engaged gear at GO
function TelemetryLogger:logCountdownGo(car, targetGear)
  if not (ac and ac.log) then return end
  local spd = car and car.speedKmh or 0
  local px = car and car.position and car.position.x or 0
  local py = car and car.position and car.position.y or 0
  local pz = car and car.position and car.position.z or 0
  local lx = car and car.look and car.look.x or 0
  local lz = car and car.look and car.look.z or 0
  local st = car and car.steer or 0
  local wFL = (car and car.wheels and car.wheels[0] and car.wheels[0].angularSpeed) or 0
  local wFR = (car and car.wheels and car.wheels[1] and car.wheels[1].angularSpeed) or 0
  local wRL = (car and car.wheels and car.wheels[2] and car.wheels[2].angularSpeed) or 0
  local wRR = (car and car.wheels and car.wheels[3] and car.wheels[3].angularSpeed) or 0

  ac.log(string.format(
    "[GTLicense] Countdown GO! | Spd=%.1f | Gear=%d | pos=(%.1f, %.1f, %.1f) | look=(%.2f, %.2f) | Steer=%.1f deg | Omegas=(FL:%.1f, FR:%.1f, RL:%.1f, RR:%.1f)",
    spd, targetGear, px, py, pz, lx, lz, st, wFL, wFR, wRL, wRR
  ))
end

---Logs snapshot on each countdown tick (3, 2, 1).
---@param car table? @Assetto Corsa car state (ac.getCar)
---@param currentStep integer @Tick number (3, 2, 1)
function TelemetryLogger:logCountdownTick(car, currentStep)
  if not (ac and ac.log) then return end
  local spd = car and car.speedKmh or 0
  local gear = car and car.gear or 0
  local vy = car and car.velocity and car.velocity.y or 0
  local gas = car and car.gas or 0
  local wFL = (car and car.wheels and car.wheels[0] and car.wheels[0].angularSpeed) or 0
  local wFR = (car and car.wheels and car.wheels[1] and car.wheels[1].angularSpeed) or 0
  local wRL = (car and car.wheels and car.wheels[2] and car.wheels[2].angularSpeed) or 0
  local wRR = (car and car.wheels and car.wheels[3] and car.wheels[3].angularSpeed) or 0
  local sFL = (car and car.wheels and car.wheels[0] and car.wheels[0].suspensionTravel) or 0
  local sRL = (car and car.wheels and car.wheels[2] and car.wheels[2].suspensionTravel) or 0
  local ldFL = (car and car.wheels and car.wheels[0] and car.wheels[0].load) or 0
  local ldRL = (car and car.wheels and car.wheels[2] and car.wheels[2].load) or 0
  local slpRL = (car and car.wheels and car.wheels[2] and car.wheels[2].slipRatio) or 0
  local cphys = ac.getCarPhysics and ac.getCarPhysics(0)
  local dtVel = cphys and cphys.drivetrainVelocity or 0
  local clState = cphys and cphys.clutchState or 0
  local px = car and car.position and car.position.x or 0
  local py = car and car.position and car.position.y or 0
  local pz = car and car.position and car.position.z or 0

  ac.log(string.format(
    "[GTLicense] Countdown Tick %d | Spd=%.1f | Gear=%d | pos=(%.1f, %.1f, %.1f) | vy=%.2f | Gas=%.2f | Susp=(FL:%.3f, RL:%.3f) | Load=(FL:%.0f, RL:%.0f) | SlipRL=%.2f | Omegas=(FL:%.1f, FR:%.1f, RL:%.1f, RR:%.1f) | DT=%.1f | Cl=%.2f",
    currentStep, spd, gear, px, py, pz, vy, gas, sFL, sRL, ldFL, ldRL, slpRL, wFL, wFR, wRL, wRR, dtVel, clState
  ))
end

---Samples vehicle kinematics and outputs to data/telemetry_eval.json for automated testing loops.
---@param car table? @Assetto Corsa car state (ac.getCar)
---@param sessionTime number
---@param dt number
---@param state string
---@param countdownTimer number
---@param testConfig table
---@param targetGear integer
---@param restartCount integer
function TelemetryLogger:recordSample(car, sessionTime, dt, state, countdownTimer, testConfig, targetGear, restartCount)
  if not car then return end
  if not self.samples then
    self.samples = {}
    self.sampleTimer = 0
  end
  self.sampleTimer = (self.sampleTimer or 0) + dt
  if self.sampleTimer >= 0.15 then
    self.sampleTimer = 0
    table.insert(self.samples, {
      t = sessionTime,
      countdown = (state == "COUNTDOWN") and countdownTimer or 0,
      state = state,
      speedKmh = car.speedKmh,
      posX = car.position.x,
      posY = car.position.y,
      posZ = car.position.z,
      lookX = car.look.x,
      lookY = car.look.y,
      lookZ = car.look.z,
      gear = car.gear,
      rpm = car.rpm,
      restartCount = restartCount or 0
    })

    if io and io.save and JSON and JSON.stringify then
      local dump = {
        test_id = testConfig and testConfig.test_id or "UNKNOWN",
        start_mode = testConfig and testConfig.start_mode or "STANDING",
        initial_speed_kmh = (testConfig and testConfig.spawn and testConfig.spawn.initial_speed_kmh) or 0,
        target_gear = targetGear or 1,
        restart_count = restartCount or 0,
        samples = self.samples
      }
      local scriptFolder = ac and ac.getFolder and (ac.getFolder(ac.FolderID.ScriptOrigin) or ac.getFolder(1024))
      if scriptFolder then
        io.save(scriptFolder .. "/data/telemetry_eval.json", JSON.stringify(dump))
      end
    end
  end
end

---Resets timer state on session restart.
function TelemetryLogger:reset()
  self.lastPeriodicLog = 0
  self.lastPostGoLog = 0
  self.sampleTimer = 0
end

return TelemetryLogger

