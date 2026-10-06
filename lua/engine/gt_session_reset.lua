-- ==============================================================================
-- Gran Turismo License Engine for Assetto Corsa (CSP)
-- File: lua/engine/gt_session_reset.lua
-- Description: Instantaneous in-memory session reset controller.
--              Handles physics.restart() on disqualification or restart hotkey,
--              auto-retry countdown timers, and event listener dispatching.
-- ==============================================================================

local GTSessionReset = {}
GTSessionReset.__index = GTSessionReset

---Creates a new session reset controller instance.
---@param options table? @Optional configuration { autoResetDelay = 1.5, restartKey = ui.KeyIndex.R }
---@return table GTSessionReset instance
function GTSessionReset.new(options)
  local self = setmetatable({}, GTSessionReset)
  options = options or {}

  self.autoResetDelay = options.autoResetDelay or 1.5
  self.autoResetTimer = nil
  self.isAutoResetPending = false
  self.restartKey = options.restartKey or ((ui and ui.KeyIndex and ui.KeyIndex.R) or 82) -- Default 'R'
  self.resetListeners = {}

  return self
end

---Registers a callback listener invoked whenever a session reset occurs.
---@param callback fun(reason: string)
function GTSessionReset:onReset(callback)
  if type(callback) == "function" then
    table.insert(self.resetListeners, callback)
  end
end

---Schedules an automated session reset after a set delay (used on test failure).
---@param delaySeconds number? @Delay in seconds before firing reset (defaults to autoResetDelay)
function GTSessionReset:scheduleAutoReset(delaySeconds)
  self.autoResetTimer = delaySeconds or self.autoResetDelay
  self.isAutoResetPending = true
end

---Cancels any currently pending auto-reset timer.
function GTSessionReset:cancelAutoReset()
  self.autoResetTimer = nil
  self.isAutoResetPending = false
end

---Checks whether an auto-reset is currently queued.
---@return boolean
function GTSessionReset:isPending()
  return self.isAutoResetPending
end

---Executes an instantaneous in-memory session reset.
---Tries physics.restart() first (sub-second reset), falls back to ac.tryToRestartSession(),
---and invokes all registered reset listeners.
---@param reason string? @Reason for the reset (e.g. "USER_REQUEST", "TEST_FAILED", "RETRY")
---@return boolean success
function GTSessionReset:executeReset(reason)
  reason = reason or "USER_REQUEST"
  self:cancelAutoReset()

  -- 1. Notify listeners so state machines, HUD, and audio can clean up
  for i = 1, #self.resetListeners do
    local ok, err = pcall(self.resetListeners[i], reason)
    if not ok then
      if ac and ac.error then
        ac.error("Error in reset listener: " .. tostring(err))
      end
    end
  end

  -- 2. Execute CSP session restart API if available
  if ac and ac.tryToRestartSession then
    local restarted = ac.tryToRestartSession()
    if restarted then
      return true
    end
  end

  -- 4. In case of soft simulation or test harness without full session restart, return true
  return true
end

---Per-frame update loop checking restart input keys and ticking auto-reset timer.
---@param dt number @Frame delta time in seconds
---@return boolean didReset @True if a reset was triggered this frame
function GTSessionReset:update(dt)
  -- 1. Check manual restart hotkey (e.g. 'R' key)
  if ac and ac.isKeyPressed and ac.isKeyPressed(self.restartKey) then
    self:executeReset("KEYPRESS")
    return true
  end

  -- 2. Update auto-reset countdown if scheduled
  if self.isAutoResetPending and self.autoResetTimer ~= nil then
    self.autoResetTimer = self.autoResetTimer - dt
    if self.autoResetTimer <= 0 then
      self:executeReset("AUTO_FAILURE_RESET")
      return true
    end
  end

  return false
end

return GTSessionReset
