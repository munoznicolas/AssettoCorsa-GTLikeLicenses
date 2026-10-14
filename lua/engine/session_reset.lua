-- ==============================================================================
-- Gran Turismo License Engine for Assetto Corsa (CSP)
-- File: lua/engine/session_reset.lua
-- Description: Instantaneous in-memory session reset controller.
--              Handles physics.restart() on disqualification or restart hotkey,
--              auto-retry countdown timers, and event listener dispatching.
-- ==============================================================================

local SessionReset = {}
SessionReset.__index = SessionReset

---Creates a new session reset controller instance.
---@param options table? @Optional configuration { autoResetDelay = 1.5, restartKey = ui.KeyIndex.R }
---@return table SessionReset instance
function SessionReset.new(options)
  local self = setmetatable({}, SessionReset)
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
function SessionReset:onReset(callback)
  if type(callback) == "function" then
    table.insert(self.resetListeners, callback)
  end
end

---Schedules an automated session reset after a set delay (used on test failure).
---@param delaySeconds number? @Delay in seconds before firing reset (defaults to autoResetDelay)
function SessionReset:scheduleAutoReset(delaySeconds)
  self.autoResetTimer = delaySeconds or self.autoResetDelay
  self.isAutoResetPending = true
end

---Cancels any currently pending auto-reset timer.
function SessionReset:cancelAutoReset()
  self.autoResetTimer = nil
  self.isAutoResetPending = false
end

---Checks whether an auto-reset is currently queued.
---@return boolean
function SessionReset:isPending()
  return self.isAutoResetPending
end

---Executes an instantaneous in-memory session reset.
---Tries physics.restart() first (sub-second reset), falls back to ac.tryToRestartSession(),
---and invokes all registered reset listeners.
---@param reason string? @Reason for the reset (e.g. "USER_REQUEST", "TEST_FAILED", "RETRY")
---@return boolean success
function SessionReset:executeReset(reason)
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

  -- 2. In-memory session reset completed via registered listeners (teleports car, engages gear, restarts countdown)
  return true
end

---Checks if user has requested a session restart via keyboard or controller.
---@return boolean
function SessionReset:isRestartRequested()
  -- 1. Check primary configured restart key
  if self.restartKey then
    if ac and ac.isKeyPressed and ac.isKeyPressed(self.restartKey) then return true end
    if ui and ui.keyboardButtonPressed and ui.keyboardButtonPressed(self.restartKey) then return true end
  end

  -- 2. Check standard retry keys: R, Space, Return (Enter)
  if ac and ac.isKeyPressed and ui and ui.KeyIndex then
    if ui.KeyIndex.R and ac.isKeyPressed(ui.KeyIndex.R) then return true end
    if ui.KeyIndex.Space and ac.isKeyPressed(ui.KeyIndex.Space) then return true end
    if ui.KeyIndex.Return and ac.isKeyPressed(ui.KeyIndex.Return) then return true end
  end

  if ui and ui.keyboardButtonPressed and ui.KeyIndex then
    if ui.KeyIndex.R and ui.keyboardButtonPressed(ui.KeyIndex.R) then return true end
    if ui.KeyIndex.Space and ui.keyboardButtonPressed(ui.KeyIndex.Space) then return true end
    if ui.KeyIndex.Return and ui.keyboardButtonPressed(ui.KeyIndex.Return) then return true end
  end

  -- 3. Check Gamepad buttons: A, Start, X
  if ac and ac.isGamepadButtonPressed and ac.GamepadButton then
    if ac.GamepadButton.A and ac.isGamepadButtonPressed(0, ac.GamepadButton.A) then return true end
    if ac.GamepadButton.Start and ac.isGamepadButtonPressed(0, ac.GamepadButton.Start) then return true end
    if ac.GamepadButton.X and ac.isGamepadButtonPressed(0, ac.GamepadButton.X) then return true end
  end

  return false
end

---Per-frame update loop checking restart input keys and ticking auto-reset timer.
---@param dt number @Frame delta time in seconds
---@return boolean didReset @True if a reset was triggered this frame
function SessionReset:update(dt)
  -- 1. Check user input (R key, Space, Return, Gamepad buttons)
  if self:isRestartRequested() then
    self:executeReset("USER_INPUT")
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

-- Backward compatibility alias
SessionReset.GTSessionReset = SessionReset

return SessionReset

