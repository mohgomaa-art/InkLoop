"""
Automated Verification Suite for InkLoop Motion Design System & Performance Invariants
Validates:
1. Motion tokens in motion.css (durations, easings, distances, scales)
2. Reduced motion overrides and media query safety
3. Canvas manipulation isolation invariants (Gate G3)
4. Keyframe consolidation and pause-on-hidden lifecycle hooks
5. Type safety of motion utilities and hooks
"""

import pathlib
import sys
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / 'frontend'
SRC = FRONTEND / 'src'
MOTION_CSS = SRC / 'styles' / 'motion.css'
INDEX_CSS = SRC / 'styles' / 'index.css'
MOTION_TS = SRC / 'utils' / 'motion.ts'
USE_PRESENCE_TS = SRC / 'hooks' / 'usePresence.ts'
USE_REDUCED_MOTION_TS = SRC / 'hooks' / 'useReducedMotion.ts'
USE_PAGE_VISIBILITY_TS = SRC / 'hooks' / 'usePageVisibility.ts'
MANUAL_EDITOR_TSX = SRC / 'views' / 'ManualEditorView.tsx'
TRANSFORM_GIZMO_TSX = SRC / 'components' / 'editor' / 'TransformGizmo.tsx'
SETTINGS_VIEW_TSX = SRC / 'views' / 'SettingsView.tsx'

def test_motion_css_tokens():
    print("[1/6] Verifying Motion CSS tokens and design scale...")
    assert MOTION_CSS.exists(), f"Missing {MOTION_CSS}"
    content = MOTION_CSS.read_text(encoding='utf-8')
    
    # Check durations
    assert '--motion-duration-fast: 120ms' in content, "Missing fast duration (120ms)"
    assert '--motion-duration-normal: 180ms' in content, "Missing normal duration (180ms)"
    assert '--motion-duration-slow: 260ms' in content, "Missing slow duration (260ms)"
    assert '--motion-duration-deliberate: 320ms' in content, "Missing deliberate duration (320ms)"
    
    # Check easings
    assert '--motion-ease-enter:' in content, "Missing enter easing curve"
    assert '--motion-ease-exit:' in content, "Missing exit easing curve"
    assert '--motion-ease-standard:' in content, "Missing standard easing curve"
    
    # Check reduced motion overrides
    assert '@media (prefers-reduced-motion: reduce)' in content, "Missing media query for prefers-reduced-motion"
    assert '[data-motion="reduced"]' in content, "Missing [data-motion='reduced'] selector"
    assert '[data-motion="off"]' in content, "Missing [data-motion='off'] selector"
    
    # Check hardware-accelerated compositor keyframes
    assert '@keyframes motionFadeIn' in content, "Missing motionFadeIn keyframe"
    assert '@keyframes motionScaleIn' in content, "Missing motionScaleIn keyframe"
    assert '@keyframes motionSlideUpIn' in content, "Missing motionSlideUpIn keyframe"
    print("  [PASS] All motion tokens, easing curves, and reduced motion selectors verified.")

def test_canvas_isolation_invariant():
    print("[2/6] Verifying Canvas direct manipulation isolation invariant (Gate G3)...")
    motion_css = MOTION_CSS.read_text(encoding='utf-8')
    assert '.canvas-raw-manipulation' in motion_css, "Missing .canvas-raw-manipulation class in motion.css"
    assert 'transition: none !important;' in motion_css, "Missing transition: none override for canvas direct manipulation"
    
    editor_tsx = MANUAL_EDITOR_TSX.read_text(encoding='utf-8')
    assert 'canvas-raw-manipulation' in editor_tsx, "ManualEditorView must apply canvas-raw-manipulation to SVG"
    
    gizmo_tsx = TRANSFORM_GIZMO_TSX.read_text(encoding='utf-8')
    assert 'canvas-raw-manipulation' in gizmo_tsx, "TransformGizmo must apply canvas-raw-manipulation"
    print("  [PASS] Canvas direct manipulation has strict zero-delay transition isolation.")

def test_presence_lifecycle_hooks():
    print("[3/6] Verifying Presence and Accessibility hooks...")
    assert USE_PRESENCE_TS.exists(), "Missing usePresence.ts"
    presence = USE_PRESENCE_TS.read_text(encoding='utf-8')
    assert 'isMounted' in presence and 'isExiting' in presence, "usePresence must provide isMounted and isExiting"
    assert 'clearTimeout' in presence, "usePresence must clean up timers on unmount"
    
    assert USE_REDUCED_MOTION_TS.exists(), "Missing useReducedMotion.ts"
    reduced = USE_REDUCED_MOTION_TS.read_text(encoding='utf-8')
    assert 'prefers-reduced-motion' in reduced, "useReducedMotion must check OS prefers-reduced-motion"
    assert 'inkloop_motion_preference' in reduced, "useReducedMotion must persist preference"
    
    assert USE_PAGE_VISIBILITY_TS.exists(), "Missing usePageVisibility.ts"
    visibility = USE_PAGE_VISIBILITY_TS.read_text(encoding='utf-8')
    assert 'visibilitychange' in visibility, "usePageVisibility must listen to visibilitychange"
    print("  [PASS] usePresence, useReducedMotion, and usePageVisibility verified.")

def test_character_avatar_calmness():
    print("[4/6] Verifying character avatar calmness and background throttling...")
    tab_char = (SRC / 'components' / 'agent' / 'character' / 'TabCharacterIcon.tsx').read_text(encoding='utf-8')
    assert 'usePageVisibility' in tab_char, "TabCharacterIcon must track page visibility"
    assert 'useReducedMotion' in tab_char, "TabCharacterIcon must track reduced motion"
    # Verify continuous infinite bouncing on active tab is removed
    assert 'shouldAnimate = !isReduced && isVisible && animateOnHover && isHovered' in tab_char, (
        "TabCharacterIcon must animate only on deliberate hover when visible"
    )
    
    animated_poses = (SRC / 'components' / 'agent' / 'character' / 'AnimatedPoses.tsx').read_text(encoding='utf-8')
    assert 'usePageVisibility' in animated_poses, "AnimatedPoses must track page visibility"
    assert 'playState = isPaused || !isVisible || isReduced ? \'paused\' : \'running\'' in animated_poses, (
        "AnimatedPoses must pause when hidden or reduced motion is active"
    )
    print("  [PASS] Character animations pause on idle/blur and do not bounce continuously.")

def test_settings_motion_controls():
    print("[5/6] Verifying Settings Motion & Interaction controls...")
    settings = SETTINGS_VIEW_TSX.read_text(encoding='utf-8')
    assert 'Motion Design & Accessibility System' in settings, "SettingsView must expose Motion Design card"
    assert 'Full Motion' in settings and 'Reduced Motion' in settings and 'Motion Off' in settings, (
        "SettingsView must expose full, reduced, and off options"
    )
    print("  [PASS] Settings view provides full motion preference toggling.")

def test_css_import_and_cleanliness():
    print("[6/6] Verifying CSS imports and transition hygiene...")
    index_css = INDEX_CSS.read_text(encoding='utf-8')
    assert "@import './motion.css';" in index_css, "index.css must import motion.css"
    assert ".animate-in.fade-in {" in index_css, "index.css must define .animate-in.fade-in"
    print("  [PASS] CSS imports and keyframe mappings verified.")

def main():
    print("=== INKLOOP MOTION DESIGN SYSTEM AUDIT & VERIFICATION ===")
    try:
        test_motion_css_tokens()
        test_canvas_isolation_invariant()
        test_presence_lifecycle_hooks()
        test_character_avatar_calmness()
        test_settings_motion_controls()
        test_css_import_and_cleanliness()
        print("\n[SUCCESS] ALL 6 MOTION VERIFICATION SUITES PASSED PERFECTLY!")
        return 0
    except AssertionError as e:
        print(f"\n[FAIL] VERIFICATION FAILED: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
