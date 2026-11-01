import re

with open('frontend/src/components/agent/character/StaticPoses.tsx', 'r', encoding='utf-8') as f:
    static_code = f.read()

with open('frontend/src/components/agent/character/AnimatedPoses.tsx', 'r', encoding='utf-8') as f:
    anim_code = f.read()

# Let's find every pose condition in StaticPoses
pose_cases = re.findall(r"poseId === '([^']+)'", static_code)
print("Static pose cases:", pose_cases)

anim_cases = re.findall(r"animId === '([^']+)'", anim_code)
print("Anim cases:", anim_cases)

# Check all path coordinates
for name in pose_cases:
    # find block
    start_idx = static_code.find(f"poseId === '{name}'")
    next_idx = len(static_code)
    for other in pose_cases:
        if other != name:
            idx = static_code.find(f"poseId === '{other}'", start_idx + 10)
            if idx != -1 and idx < next_idx:
                next_idx = idx
    block = static_code[start_idx:next_idx]
    
    # parse numbers from path data d="..."
    d_strings = re.findall(r'd="([^"]+)"', block)
    coords = []
    for d in d_strings:
        # find float pairs or coordinates
        nums = re.findall(r'[-+]?[0-9]*\.?[0-9]+', d)
        coords.extend([float(n) for n in nums])
    
    # cx, cy, x, y
    for attr in ['cx', 'cy', 'x', 'y']:
        vals = re.findall(rf'{attr}="([0-9.]+)"', block)
        coords.extend([float(v) for v in vals])
        
    print(f"{name}: min={min(coords) if coords else 0}, max={max(coords) if coords else 0}")
