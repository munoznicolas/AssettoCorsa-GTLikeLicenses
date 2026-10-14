-- ==============================================================================
-- Gran Turismo License Engine - Results & Medal Evaluator
-- File: lua/engine/results.lua
-- Description: Adjudicates medal achievements (GOLD, SILVER, BRONZE, NONE)
--              and compiles comprehensive session performance results.
-- ==============================================================================

local Results = {}

---Evaluates medal rank based on achieved session time against target thresholds.
---@param timeSeconds number
---@param targets table? @{ gold_seconds = x, silver_seconds = y, bronze_seconds = z }
---@return string medal ("GOLD" | "SILVER" | "BRONZE" | "NONE")
function Results.evaluateMedal(timeSeconds, targets)
  targets = targets or {}
  local gold = tonumber(targets.gold_seconds) or 999
  local silver = tonumber(targets.silver_seconds) or 999
  local bronze = tonumber(targets.bronze_seconds) or 999

  if timeSeconds <= gold then
    return "GOLD"
  elseif timeSeconds <= silver then
    return "SILVER"
  elseif timeSeconds <= bronze then
    return "BRONZE"
  else
    return "NONE"
  end
end

---Builds the results report table.
---@param testConfig table
---@param sessionTime number
---@param achievedMedal string?
---@param failReason string?
---@return table results
function Results.compileResults(testConfig, sessionTime, achievedMedal, failReason)
  local targets = (testConfig and testConfig.targets) or {}
  local gold = tonumber(targets.gold_seconds) or 0
  local silver = tonumber(targets.silver_seconds) or 0
  local bronze = tonumber(targets.bronze_seconds) or 0

  return {
    test_id = testConfig and testConfig.test_id,
    title = testConfig and testConfig.title,
    time = sessionTime,
    medal = achievedMedal or "NONE",
    target_gold = gold,
    target_silver = silver,
    target_bronze = bronze,
    delta_gold = sessionTime - gold,
    delta_silver = sessionTime - silver,
    delta_bronze = sessionTime - bronze,
    passed = (achievedMedal ~= nil and achievedMedal ~= "NONE"),
    fail_reason = failReason
  }
end

-- Backward compatibility alias
Results.GTResults = Results

return Results

