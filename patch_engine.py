import sys, re

filepath = 'lua/engine/gt_license_engine.lua'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r'''          -- Standing start: maintain 1st gear engaged and brakes held during countdown
          if not car or car\.gear ~= 1 then
            if physics and physics\.engageGear then
              physics\.engageGear\(0, 1\)
            end
          end'''

replacement = '''          -- Standing start: maintain 1st gear engaged and brakes held during countdown
          if not self.isAITestMode and (not car or car.gear ~= 1) then
            if physics and physics.engageGear then
              physics.engageGear(0, 1)
            end
          end'''

new_content = content.replace(pattern, replacement)
if new_content == content:
    print('Failed to replace in engine')
else:
    print('Replaced in engine')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

