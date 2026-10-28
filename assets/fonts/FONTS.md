# InkLoop Typography & Font Selection (OFL)

In compliance with hackathon regulations:
- Text in InkLoop is **always** rendered by deterministic code (HTML/SVG in Chromium), **never** by AI image generators.
- All bundled fonts are licensed under the **SIL Open Font License (OFL-1.1)**.
- Fonts are embedded locally to guarantee offline rendering reproducibility and prevent CDN dependency.

---

## Shortlisted Fonts

### Arabic (RTL) Typography
1. **Cairo**
   - **Designer:** Mohamed Gaber, Accents by Eduardo Tunni
   - **License:** SIL Open Font License, Version 1.1 (OFL-1.1)
   - **Role:** Primary comic dialogue and sound-effect font for Arabic. Wide glyph coverage, high legibility at dialogue scale, clean geometric sans-serif that fits comic speech bubbles.
2. **Tajawal**
   - **Designer:** Boutros Fonts
   - **License:** SIL Open Font License, Version 1.1 (OFL-1.1)
   - **Role:** Alternate clean dialogue font for dialogue-heavy panels.
3. **Amiri**
   - **Designer:** Khaled Hosny
   - **License:** SIL Open Font License, Version 1.1 (OFL-1.1)
   - **Role:** Narrative captions, historical/fantasy beats, and title cards.

### Latin (LTR) Typography
1. **Bangers**
   - **Designer:** Vernon Adams
   - **License:** SIL Open Font License, Version 1.1 (OFL-1.1)
   - **Role:** High-impact comic titles, shouts, and sound effects (SFX).
2. **Comic Neue**
   - **Designer:** Craig Hang
   - **License:** SIL Open Font License, Version 1.1 (OFL-1.1)
   - **Role:** Primary clean, modern comic book dialogue font.
3. **Kalam**
   - **Designer:** Indian Type Foundry
   - **License:** SIL Open Font License, Version 1.1 (OFL-1.1)
   - **Role:** Casual handwriting, thought bubbles, and notebook notes.

---

## Text-Integrity Assertion Rule
Before exporting any page to PDF, the engine performs a deterministic assertion:
$$\text{RenderedText}(P) \equiv \text{SourceScript}(P)$$
No LLM is permitted to rewrite, truncate, or invent dialogue during the layout phase.
