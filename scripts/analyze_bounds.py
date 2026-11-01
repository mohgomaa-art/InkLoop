import re

with open('frontend/src/components/agent/character/StaticPoses.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

numbers_x = [float(x) for x in re.findall(r'(?:cx|x)="([0-9.]+)"', text)]
numbers_y = [float(y) for y in re.findall(r'(?:cy|y)="([0-9.]+)"', text)]

print('X range in StaticPoses:', min(numbers_x), 'to', max(numbers_x))
print('Y range in StaticPoses:', min(numbers_y), 'to', max(numbers_y))

with open('frontend/src/components/agent/character/AnimatedPoses.tsx', 'r', encoding='utf-8') as f:
    anim_text = f.read()

anim_x = [float(x) for x in re.findall(r'(?:cx|x)="([0-9.]+)"', anim_text)]
anim_y = [float(y) for y in re.findall(r'(?:cy|y)="([0-9.]+)"', anim_text)]

print('X range in AnimatedPoses:', min(anim_x), 'to', max(anim_x))
print('Y range in AnimatedPoses:', min(anim_y), 'to', max(anim_y))
