import re

with open('frontend/src/components/agent/character/StaticPoses.tsx', 'r', encoding='utf-8') as f:
    static_code = f.read()

with open('frontend/src/components/agent/character/AnimatedPoses.tsx', 'r', encoding='utf-8') as f:
    anim_code = f.read()

# Let's inspect pose by pose in StaticPoses
pose_blocks = re.findall(r'case \'(pose-[^\']+)\':\s*return \(\s*<>\s*(.*?)\s*</>\s*\);', static_code, re.DOTALL)
print(f"Found {len(pose_blocks)} static poses")

for pose_name, block in pose_blocks:
    xs = [float(x) for x in re.findall(r'(?:cx|x)="([0-9.]+)"', block)]
    ys = [float(y) for y in re.findall(r'(?:cy|y)="([0-9.]+)"', block)]
    if xs and ys:
        print(f"{pose_name}: X=[{min(xs):.1f}, {max(xs):.1f}], Y=[{min(ys):.1f}, {max(ys):.1f}]")

# Same for animations
anim_blocks = re.findall(r'case \'(anim-[^\']+)\':\s*return \(\s*<>\s*(.*?)\s*</>\s*\);', anim_code, re.DOTALL)
print(f"\nFound {len(anim_blocks)} animated poses")

for anim_name, block in anim_blocks:
    xs = [float(x) for x in re.findall(r'(?:cx|x)="([0-9.]+)"', block)]
    ys = [float(y) for y in re.findall(r'(?:cy|y)="([0-9.]+)"', block)]
    if xs and ys:
        print(f"{anim_name}: X=[{min(xs):.1f}, {max(xs):.1f}], Y=[{min(ys):.1f}, {max(ys):.1f}]")
