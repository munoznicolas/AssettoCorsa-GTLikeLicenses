import sys, re

filepath = 'lua/engine/gt_physics_hooks.lua'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

helper = """
local isAITestModeCached = nil
local function getIsAITestMode()
  if isAITestModeCached ~= nil then return isAITestModeCached end
  isAITestModeCached = false
  if ac and ac.INIConfig and ac.INIConfig.raceConfig then
    local ok, race = pcall(ac.INIConfig.raceConfig)
    if ok and race then
      local val = race:get("GTLICENSE", "AI_TEST_MODE", "")
      if val == "1" or val == "true" or val == "TRUE" then
        isAITestModeCached = true
      end
    end
  end
  return isAITestModeCached
end

local function safeEngageGear(physics, carIndex, gear)
  if getIsAITestMode() then return end
  if physics and physics.engageGear then
    physics.engageGear(carIndex, gear)
  end
end
"""

if 'safeEngageGear' not in content:
    content = content.replace('local GTPhysicsHooks = {}', 'local GTPhysicsHooks = {}\n' + helper)

pattern = r'if physics and physics\.engageGear then\s+physics\.engageGear\(([^,]+),\s*([^)]+)\)\s+end'
new_content, count = re.subn(pattern, r'safeEngageGear(physics, \g<1>, \g<2>)', content)

print(f'Replaced {count} instances of engageGear')
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)

