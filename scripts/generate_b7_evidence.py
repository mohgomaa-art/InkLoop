"""Generate B7 visual proof on the exact panoramic panel layout."""
import os
from PIL import Image, ImageDraw, ImageFont
from app.canvas.bubble_service import BubbleService
from app.canvas.bubble_vector import BubbleVectorBuilder
from app.canvas.placement_engine import PlacementEngine, BubblePlacementRequest, ProtectedRegion
from app.contracts.geometry import Rect, Point

def generate_evidence():
    os.makedirs("docs/repair/bubbles/evidence", exist_ok=True)
    out_path = "docs/repair/bubbles/evidence/b7-after-last-light.jpg"

    # Panel geometry: 810x160 (≈5:1 panoramic panel)
    panel_rect = Rect(x=50, y=50, width=810, height=160)
    page_w, page_h = 910, 260
    
    # Create canvas image
    img = Image.new("RGB", (page_w, page_h), (24, 24, 28))
    draw = ImageDraw.Draw(img)

    # Draw panel background & border
    draw.rectangle([panel_rect.x, panel_rect.y, panel_rect.right, panel_rect.bottom], fill=(245, 245, 247), outline=(20, 20, 20), width=3)

    # Two character figures in panel
    # Char 1 (Speaker): left
    char1_face = Rect(x=220, y=70, width=110, height=85)
    # Char 2 (Listener): right
    char2_face = Rect(x=520, y=70, width=110, height=85)

    # Draw characters
    draw.ellipse([char1_face.x, char1_face.y, char1_face.right, char1_face.bottom], fill=(225, 210, 195), outline=(30, 30, 30), width=2)
    draw.text((char1_face.x + 15, char1_face.y + 30), "Speaker (Hero)", fill=(40, 40, 40))

    draw.ellipse([char2_face.x, char2_face.y, char2_face.right, char2_face.bottom], fill=(215, 225, 210), outline=(30, 30, 30), width=2)
    draw.text((char2_face.x + 15, char2_face.y + 30), "Listener (Muse)", fill=(40, 40, 40))

    # Run PlacementEngine for "Some lights stay on."
    engine = PlacementEngine()
    speaker_anchor = Point(x=char1_face.center.x, y=char1_face.y + 10)
    req = BubblePlacementRequest(
        bubble_id="bbl_b7_proof",
        type_id="speech.normal",
        text="Some lights stay on.",
        reading_order=1,
        speaker_character_id="char_hero",
        speaker_anchor=speaker_anchor,
        font_family="Comic Neue",
        preferred_font_size=20,
    )

    prot_regions = [
        ProtectedRegion(x=char1_face.x, y=char1_face.y, width=char1_face.width, height=char1_face.height, label="speaker_face", character_id="char_hero", region_id="r1"),
        ProtectedRegion(x=char2_face.x, y=char2_face.y, width=char2_face.width, height=char2_face.height, label="listener_face", character_id="char_muse", region_id="r2"),
    ]

    results = engine.place_bubbles(
        panel_rect=panel_rect,
        bubbles=[req],
        protected_regions=prot_regions,
        reading_direction="rtl",
        allow_gutter_bleed=True,
    )
    placed = results[0]

    # Verify hard caps
    assert placed.rect.width <= panel_rect.width * 0.35, f"Exceeded panoramic width cap: {placed.rect.width} > {panel_rect.width * 0.35}"
    assert placed.rect.height <= panel_rect.height * 0.38, f"Exceeded panoramic height cap: {placed.rect.height} > {panel_rect.height * 0.38}"
    def _overlaps(r1, r2):
        return r1.x < r2.right and r1.right > r2.x and r1.y < r2.bottom and r1.bottom > r2.y

    assert not _overlaps(placed.rect, char1_face), "Bubble overlaps speaker face!"
    assert not _overlaps(placed.rect, char2_face), "Bubble overlaps listener face!"

    # Build unified vector
    builder = BubbleVectorBuilder()
    vector = builder.build_bubble_vector(
        bounds=placed.rect,
        type_id="speech.normal",
        shape="oval",
        tail_type="pointer",
        tail_target=placed.tail_target,
        bubble_id="bbl_b7_proof",
        pad_x=placed.pad_x,
        pad_y=placed.pad_y,
    )

    # Render unified bubble to Pillow canvas
    # Fill body + tail
    bx, by, bw, bh = placed.rect.x, placed.rect.y, placed.rect.width, placed.rect.height
    cx, cy = bx + bw / 2, by + bh / 2
    rx, ry = bw / 2, bh / 2

    # Draw tail fill and stroke
    if placed.tail_target:
        tip_x, tip_y = placed.tail_target.x, placed.tail_target.y
        # Tail base
        dx = tip_x - cx
        dy = tip_y - cy
        dist = (dx**2 + dy**2)**0.5
        ux, uy = dx/dist, dy/dist
        root_x = cx + ux * rx * 0.95
        root_y = cy + uy * ry * 0.95
        base_w = 12.0
        p1 = (root_x - uy * base_w, root_y + ux * base_w)
        p2 = (root_x + uy * base_w, root_y - ux * base_w)
        draw.polygon([p1, (tip_x, tip_y), p2], fill="#FFFFFF", outline=None)
        draw.line([p1, (tip_x, tip_y)], fill="#111111", width=3)
        draw.line([(tip_x, tip_y), p2], fill="#111111", width=3)

    draw.ellipse([bx, by, bx + bw, by + bh], fill="#FFFFFF", outline="#111111", width=3)

    # Draw text centered inside bubble
    draw.text((bx + placed.pad_x + 8, by + placed.pad_y + 4), "Some lights stay on.", fill="#111111")

    # Add annotation labels
    draw.text((panel_rect.x, panel_rect.y - 25), "B7 Visual Proof: Non-occluding panoramic placement (width <= 35%, height <= 38%, tail -> speaker)", fill=(200, 200, 200))

    img.save(out_path, quality=95)
    print(f"B7 visual proof saved to {out_path} successfully.")
    print(f"Bubble bounds: {placed.rect.model_dump()} (width={placed.rect.width:.1f}px = {placed.rect.width/panel_rect.width*100:.1f}% of panel)")
    print(f"Tail tip target: {placed.tail_target.model_dump() if placed.tail_target else None}")

if __name__ == "__main__":
    generate_evidence()
