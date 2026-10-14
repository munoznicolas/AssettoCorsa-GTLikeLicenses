-- ==============================================================================
-- Gran Turismo License Engine for Assetto Corsa (CSP)
-- File: lua/engine/ghost_manager.lua
-- Description: Manages Gold medal ghost car trajectory evaluation,
--              lead offset pacing, delta computation, and driver mode toggling.
-- ==============================================================================

local GhostManager = {}
GhostManager.__index = GhostManager

-- Ghost Modes
GhostManager.MODE = {
  OFF   = 0, -- Ghost hidden
  EXACT = 1, -- Running at exact Gold medal pace (0.0s delta)
  PACER = 2  -- Running ahead as a pacer (+0.5s lead)
}

local MODE_NAMES = {
  [GhostManager.MODE.OFF]   = "DISABLED",
  [GhostManager.MODE.EXACT] = "EXACT GOLD (0.0s)",
  [GhostManager.MODE.PACER] = "PACER (+0.5s LEAD)"
}

---Constructs a new Ghost Manager instance.
---@param testConfig table @Test JSON definition
---@param ghostTrajectory table|nil @Precomputed ghost trajectory array
---@return table @GhostManager instance
function GhostManager.new(testConfig, ghostTrajectory)
  local self = setmetatable({}, GhostManager)

  self.testConfig = testConfig or {}
  self.trajectory = ghostTrajectory or {}
  self.mode = GhostManager.MODE.OFF -- Default to OFF (disabled)
  self.leadOffset = 0.5 -- 0.5s lead in PACER mode

  self.goldTime = 20.0
  if self.testConfig.targets and self.testConfig.targets.gold_seconds then
    self.goldTime = tonumber(self.testConfig.targets.gold_seconds) or 20.0
  end

  self.activePos = nil
  self.activeHeading = { 0, 0, 1 }
  self.activeSpeed = 0.0
  self.isBraking = false
  self.playerDelta = 0.0

  -- On-Screen Display notification for hotkey toggles
  self.osdMessage = nil
  self.osdTimer = 0.0

  -- Key debounce flag for 'G' key
  self.keyDebounce = false

  self:reset()
  return self
end

---Resets the ghost state to initial conditions (called during session reset).
function GhostManager:reset()
  self.activePos = nil
  self.activeHeading = { 0, 0, 1 }
  self.activeSpeed = 0.0
  self.isBraking = false
  self.playerDelta = 0.0

  -- Initialize ghost at spawn if available
  if self.testConfig.spawn and self.testConfig.spawn.position then
    local p = self.testConfig.spawn.position
    self.activePos = { p[1], p[2], p[3] }
    if self.testConfig.spawn.forward_vector then
      local f = self.testConfig.spawn.forward_vector
      self.activeHeading = { f[1], f[2], f[3] }
    end
    self.activeSpeed = tonumber(self.testConfig.spawn.initial_speed_kmh) or 0.0
  end
end

---Toggles ghost mode in order: PACER -> EXACT -> OFF -> PACER.
function GhostManager:toggleMode()
  if self.mode == GhostManager.MODE.PACER then
    self.mode = GhostManager.MODE.EXACT
  elseif self.mode == GhostManager.MODE.EXACT then
    self.mode = GhostManager.MODE.OFF
  else
    self.mode = GhostManager.MODE.PACER
  end

  self.osdMessage = "[G] GHOST MODE: " .. (MODE_NAMES[self.mode] or "UNKNOWN")
  self.osdTimer = 2.5
end

---Sets explicit ghost mode.
---@param mode number
function GhostManager:setMode(mode)
  self.mode = mode or GhostManager.MODE.OFF
end

---Interpolates trajectory sample points at time t.
---@param t number @Target time in seconds
---@return table @{ pos, heading, speed_kmh, is_braking }
function GhostManager:sampleTrajectory(t)
  local samples = self.trajectory
  local n = #samples

  if n == 0 then
    -- Fallback: interpolate linearly between spawn and finish gate
    local pStart = (self.testConfig.spawn and self.testConfig.spawn.position) or { 0, 0, 0 }
    local finishGate = self.testConfig.timing and self.testConfig.timing.finish_gate
    local pFinish = pStart
    if finishGate and finishGate.p1 and finishGate.p2 then
      pFinish = {
        0.5 * (finishGate.p1[1] + finishGate.p2[1]),
        0.5 * (finishGate.p1[2] + finishGate.p2[2]),
        0.5 * (finishGate.p1[3] + finishGate.p2[3])
      }
    end

    local alpha = math.max(0.0, math.min(1.0, t / self.goldTime))
    return {
      pos = {
        pStart[1] + alpha * (pFinish[1] - pStart[1]),
        pStart[2] + alpha * (pFinish[2] - pStart[2]),
        pStart[3] + alpha * (pFinish[3] - pStart[3])
      },
      heading = self.testConfig.spawn and self.testConfig.spawn.forward_vector or { 0, 0, 1 },
      speed_kmh = 100.0 * (1.0 - alpha * 0.5),
      is_braking = alpha > 0.8
    }
  end

  if t <= samples[1].t then
    local s = samples[1]
    return { pos = s.pos, heading = s.heading, speed_kmh = s.speed_kmh, is_braking = s.is_braking }
  end

  if t >= samples[n].t then
    local s = samples[n]
    return { pos = s.pos, heading = s.heading, speed_kmh = s.speed_kmh, is_braking = s.is_braking }
  end

  -- Binary search or linear segment search
  local low = 1
  local high = n
  while low <= high do
    local mid = math.floor((low + high) / 2)
    if samples[mid].t <= t then
      if mid == n or samples[mid + 1].t > t then
        low = mid
        break
      else
        low = mid + 1
      end
    else
      high = mid - 1
    end
  end

  local s0 = samples[low]
  local s1 = samples[math.min(n, low + 1)]
  local dt = math.max(1e-4, s1.t - s0.t)
  local frac = math.max(0.0, math.min(1.0, (t - s0.t) / dt))

  local pos = {
    s0.pos[1] + frac * (s1.pos[1] - s0.pos[1]),
    s0.pos[2] + frac * (s1.pos[2] - s0.pos[2]),
    s0.pos[3] + frac * (s1.pos[3] - s0.pos[3])
  }

  local heading = {
    s0.heading[1] + frac * (s1.heading[1] - s0.heading[1]),
    s0.heading[2] + frac * (s1.heading[2] - s0.heading[2]),
    s0.heading[3] + frac * (s1.heading[3] - s0.heading[3])
  }

  local speed = s0.speed_kmh + frac * (s1.speed_kmh - s0.speed_kmh)
  local isBraking = s0.is_braking or s1.is_braking

  return { pos = pos, heading = heading, speed_kmh = speed, is_braking = isBraking }
end

---Updates ghost simulation state per frame.
---@param dt number @Frame delta time
---@param sessionTime number @Current running session time in seconds
---@param playerPos table|nil @Player 3D world position {x, y, z}
function GhostManager:update(dt, sessionTime, playerPos)
  -- 1. Update OSD timer
  if self.osdTimer > 0 then
    self.osdTimer = self.osdTimer - dt
    if self.osdTimer <= 0 then
      self.osdMessage = nil
    end
  end

  -- 2. Detect 'G' hotkey for Ghost Mode toggle
  local gPressed = false
  if ui and ui.keyboardButtonDown and ui.KeyIndex and ui.KeyIndex.G then
    gPressed = ui.keyboardButtonDown(ui.KeyIndex.G)
  elseif ac and ac.isKeyDown and ac.KeyIndex and ac.KeyIndex.G then
    gPressed = ac.isKeyDown(ac.KeyIndex.G)
  end

  if gPressed then
    if not self.keyDebounce then
      self:toggleMode()
      self.keyDebounce = true
    end
  else
    self.keyDebounce = false
  end

  -- If ghost is turned off, skip trajectory sampling
  if self.mode == GhostManager.MODE.OFF then
    return
  end

  -- 3. Calculate effective ghost sample time
  local offset = (self.mode == GhostManager.MODE.PACER) and self.leadOffset or 0.0
  local sampleT = math.max(0.0, sessionTime + offset)

  local sample = self:sampleTrajectory(sampleT)
  self.activePos = sample.pos
  self.activeHeading = sample.heading
  self.activeSpeed = sample.speed_kmh
  self.isBraking = sample.is_braking

  -- 4. Calculate live player vs ghost distance/time delta
  if playerPos and self.activePos then
    local dx = playerPos[1] - self.activePos[1]
    local dz = playerPos[3] - self.activePos[3]
    local distToGhost = math.sqrt(dx * dx + dz * dz)
    local vMs = math.max(5.0, (self.activeSpeed / 3.6))
    -- Negative delta means player is trailing behind ghost; positive means ahead
    self.playerDelta = distToGhost / vMs
    -- Check dot product with heading to see if player is ahead or behind
    local dot = dx * self.activeHeading[1] + dz * self.activeHeading[3]
    if dot < 0 then
      self.playerDelta = -self.playerDelta
    end
  end
end

---Returns the active ghost render state.
---@return table @{ active, mode, pos, heading, speed_kmh, is_braking, delta, osd_message }
function GhostManager:getState()
  return {
    active = (self.mode ~= GhostManager.MODE.OFF and self.activePos ~= nil),
    mode = self.mode,
    mode_name = MODE_NAMES[self.mode] or "DISABLED",
    pos = self.activePos,
    heading = self.activeHeading,
    speed_kmh = self.activeSpeed,
    is_braking = self.isBraking,
    delta = self.playerDelta,
    osd_message = self.osdMessage
  }
end

GhostManager.GTGhostManager = GhostManager

return GhostManager
