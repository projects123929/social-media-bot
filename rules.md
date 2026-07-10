# AI Video Ad Production Pipeline (9:16, 30-35 Sec) — Generic Template

> Reference approach: build one fixed "story world" (characters + location),
> break it into a 9-panel storyboard, then animate every 3 panels as one
> video-generation clip using "start frame + end frame + motion prompt".
> This file is a reusable template — fill in the placeholders for each new
> video; do not hardcode a specific brand/character here.

---

## Fixed Constraints (apply to every video, no exceptions)

- **Duration:** 30-35 seconds total
- **Aspect ratio:** 9:16
- **Max scenes:** 5 (this pipeline typically produces 3 video-generation
  clips of ~10s each, built from 3-panel groups — stay at or under 5)
- **Captions:** burned into the video, not reliant on platform auto-captions
- **Content restrictions:**
  - No political content
  - No religious content
  - No copyrighted music (use licensed/royalty-free audio only)

---

## 0. How the Pipeline Works (Workflow Overview)

1. **Character & Product Lock** — Generate a "Character Reference Sheet" and
   a "Product Reference Sheet" (image model — Nano Banana, GPT-Image,
   Ideogram, etc.) first. This keeps the same seed/character consistent
   across every later shot.
2. **9-Panel Storyboard** — Generate all 9 panels from a single grid-layout
   image prompt, so lighting, character faces, and set stay consistent
   (using the locked reference sheets as input).
3. **Chunking Strategy** — Split the 9 panels into 3 groups of 3:
   - Panels 1-3 → Video Prompt 1 (0-10s)
   - Panels 4-6 → Video Prompt 2 (10-20s)
   - Panels 7-9 → Video Prompt 3 (20-30s)
4. **Image-to-Video** — Feed each group's first and last panel into the
   video model (Kling, Veo, Runway, Seedance, etc.) as "start frame" and
   "end frame", with a motion prompt describing what happens in between.
5. **Continuity Rule** — The end frame of one video prompt becomes the
   start frame of the next (same character position, lighting, camera
   framing) so there's no jump-cut or visual drift between clips.
6. **Audio Layer** — Generate dialogue separately via TTS (ElevenLabs or
   similar), then lip-sync it (Kling lip-sync, HeyGen, Runway Act-One), or
   use a video model with native dialogue/lip-sync support directly in the
   generation prompt.
7. **Post-Production** — Color grade, add a brand/end-card, add music/SFX,
   and export the final 30-35s vertical video.

---

## 1. Script Template

**Title:** `{AD_TITLE}`

**Concept:** `{ONE_TO_TWO_SENTENCE_STORY_CONCEPT}`

**Characters:** `{CHARACTER_LIST}`

**Emotion arc:** `{EMOTION_BEAT_1}` → `{EMOTION_BEAT_2}` → `{EMOTION_BEAT_3}` → `{EMOTION_BEAT_4}` (e.g. Curiosity → Tension → Resolution → Payoff)

**Tagline / end card:** `{CLOSING_TAGLINE}`

---

## 2. Master Product/Subject Board Prompt (template)

```xml
<prompt>
  <task>Generate a high-resolution reference sheet for {SUBJECT_NAME}</task>
  <subject>
    <name>{SUBJECT_NAME}</name>
    <description>{VISUAL_DESCRIPTION — packaging, shape, colors, materials, distinguishing marks}</description>
  </subject>
  <shots_required>
    <shot>Front-facing full view, studio lighting, neutral background</shot>
    <shot>3/4 angle shot with soft shadow</shot>
    <shot>Close-up detail shot showing texture/material</shot>
    <shot>{CONTEXT_SPECIFIC_SHOT — e.g. in use, opened, in a natural setting}</shot>
    <shot>{MOOD_SHOT — e.g. warm/appetizing/dramatic framing appropriate to the story}</shot>
  </shots_required>
  <style>
    <lighting>{LIGHTING_STYLE}</lighting>
    <background>{BACKGROUND_STYLE}</background>
    <resolution>4K, commercial-quality</resolution>
    <mood>{MOOD_DESCRIPTORS}</mood>
  </style>
  <negative_prompt>no blur, no distorted text/logo, no incorrect colors, no watermark, no morphing</negative_prompt>
</prompt>
```

---

## 3. Master Character Board Prompt (template)

```xml
<prompt>
  <task>Generate a character consistency reference sheet with all characters together, multiple angles and expressions</task>
  <characters>
    <character id="1">
      <name>{CHARACTER_1_NAME}</name>
      <age>{CHARACTER_1_AGE}</age>
      <appearance>{CHARACTER_1_APPEARANCE}</appearance>
      <personality_expression>{CHARACTER_1_EXPRESSION}</personality_expression>
    </character>
    <!-- repeat <character> block per additional character -->
  </characters>
  <shots_required>
    <shot>Front view, all characters together, neutral expression</shot>
    <shot>Close-up per character, key expression for the story</shot>
    <shot>Medium shot showing the primary relationship/interaction</shot>
  </shots_required>
  <style>
    <setting>{LOCATION_DESCRIPTION}</setting>
    <art_style>{ART_STYLE — e.g. photorealistic cinematic, flat cartoon, 3D animated}</art_style>
    <resolution>4K, consistent character identity across every panel (same face structure, same clothing)</resolution>
  </style>
  <negative_prompt>no face distortion, no changing clothes between shots, no extra fingers, no inconsistent age/height, no blur, no morphing</negative_prompt>
</prompt>
```

---

## 4. Master 9-Panel Storyboard Prompt (template)

```xml
<prompt>
  <task>Generate a 9-panel sequential storyboard grid image (3x3 layout, labeled Panel 1 to Panel 9) for a 9:16 vertical video, using the locked character sheet and product/subject sheet as reference for full consistency</task>
  <global_style>
    <format>Vertical 9:16, each panel labeled with panel number and shot type at top</format>
    <consistency>Same characters, same location, same lighting mood, same subject design across all panels</consistency>
    <mood>{OVERALL_MOOD}</mood>
  </global_style>

  <panel number="1" shot="WIDE SHOT">{SETUP_BEAT — establish characters/location}</panel>
  <panel number="2" shot="MEDIUM SHOT">{SETUP_BEAT — introduce subject/product}</panel>
  <panel number="3" shot="CLOSE-UP">{SETUP_BEAT — reaction/hook}</panel>

  <panel number="4" shot="MEDIUM CLOSE-UP">{TURN_BEAT — complication or discovery}</panel>
  <panel number="5" shot="MEDIUM SHOT">{TURN_BEAT — action taken}</panel>
  <panel number="6" shot="CLOSE-UP">{TURN_BEAT — emotional reaction}</panel>

  <panel number="7" shot="MEDIUM SHOT">{PAYOFF_BEAT — resolution moment}</panel>
  <panel number="8" shot="WIDE SHOT - EMOTIONAL CLIMAX">{PAYOFF_BEAT — emotional high point}</panel>
  <panel number="9" shot="FINAL BRAND PANEL">Hero shot of {SUBJECT_NAME} with tagline text below: "{CLOSING_TAGLINE}"</panel>

  <negative_prompt>no distortion of faces between panels, no change of clothing between panels, no change of location layout, no blurry text, no extra limbs, no watermark, no character identity drift</negative_prompt>
</prompt>
```

---

## 5. Video Prompts (3 clips × ~10s each = 30-35s total, template)

### Video Prompt 1 — Panels 1 to 3 (0-10s)

```xml
<video_prompt id="1" duration="10s" aspect_ratio="9:16">
  <reference>Use Panel 1, Panel 2, Panel 3 as start/mid/end reference frames</reference>
  <scene_description>{DESCRIBE THE ACTION ACROSS PANELS 1-3}</scene_description>
  <camera_motion>{CAMERA MOVEMENT PER SHOT}</camera_motion>
  <dialogue language="{LANGUAGE}">
    <line character="{CHARACTER}" timing="0-3s">{LINE}</line>
    <line character="{CHARACTER}" timing="4-7s">{LINE}</line>
    <line character="{CHARACTER}" timing="8-10s">{LINE}</line>
  </dialogue>
  <lip_sync>Enable native lip-sync matching dialogue exactly to mouth movement, natural pacing, no mismatch</lip_sync>
  <continuity>Maintain identical character faces, clothing, and lighting as locked in the reference sheets</continuity>
  <transitions>{TRANSITION STYLE BETWEEN SHOTS}</transitions>
  <audio>{BACKGROUND SCORE / AMBIENT SOUND / FOLEY}</audio>
  <negative_prompt>no morphing of faces, no flickering, no extra limbs, no warped hands, no text glitches, no background object popping, no character identity change between shots</negative_prompt>
</video_prompt>
```

### Video Prompt 2 — Panels 4 to 6 (10-20s)

```xml
<video_prompt id="2" duration="10s" aspect_ratio="9:16">
  <reference>Use Panel 4, Panel 5, Panel 6 as start/mid/end reference frames. Start frame must visually match the end frame of Video Prompt 1.</reference>
  <scene_description>{DESCRIBE THE ACTION ACROSS PANELS 4-6}</scene_description>
  <camera_motion>{CAMERA MOVEMENT PER SHOT}</camera_motion>
  <dialogue language="{LANGUAGE}">
    <line character="{CHARACTER}" timing="10-13s">{LINE}</line>
    <line character="{CHARACTER}" timing="14-17s">{LINE}</line>
    <line character="{CHARACTER}" timing="18-20s">{LINE}</line>
  </dialogue>
  <lip_sync>Enable native lip-sync matching dialogue exactly to mouth movement, natural pacing, no mismatch</lip_sync>
  <continuity>Same characters, same clothing, same location as previous video; lighting must match exactly</continuity>
  <transitions>{TRANSITION STYLE BETWEEN SHOTS}</transitions>
  <audio>{BACKGROUND SCORE / SFX}</audio>
  <negative_prompt>no morphing during action, no distortion of subject design, no flickering faces, no lighting mismatch from previous clip, no identity drift</negative_prompt>
</video_prompt>
```

### Video Prompt 3 — Panels 7 to 9 (20-30s, + end card to 35s)

```xml
<video_prompt id="3" duration="10s" aspect_ratio="9:16">
  <reference>Use Panel 7, Panel 8, Panel 9 as start/mid/end reference frames. Start frame must visually match the end frame of Video Prompt 2.</reference>
  <scene_description>{DESCRIBE THE ACTION ACROSS PANELS 7-9, ENDING ON THE HERO/BRAND SHOT}</scene_description>
  <camera_motion>{CAMERA MOVEMENT PER SHOT}</camera_motion>
  <dialogue language="{LANGUAGE}">
    <line character="{CHARACTER}" timing="20-23s">{LINE}</line>
    <line character="{CHARACTER}" timing="24-27s">{LINE}</line>
  </dialogue>
  <brand_end_card timing="27-35s">
    <text>{CLOSING_TAGLINE}</text>
    <visual>{SUBJECT_NAME} centered, soft glow, clean background, logo/branding crisp and legible</visual>
  </brand_end_card>
  <lip_sync>Enable native lip-sync for dialogue shots; no lip-sync needed for the end card</lip_sync>
  <continuity>Same characters, same setting, same lighting continued from previous clip</continuity>
  <transitions>{TRANSITION STYLE, ENDING IN A DISSOLVE INTO THE END CARD}</transitions>
  <audio>Music swells into a resolving note; optional sonic logo on the end card</audio>
  <negative_prompt>no distortion during motion, no face morphing, no logo/text glitches on end card, no watermark, no artifacts during dissolve, no color mismatch with previous clips</negative_prompt>
</video_prompt>
```

---

## 6. Quick Execution Checklist

- [ ] Fill in Section 1 (Script) with the specific idea/character/tagline for this video
- [ ] Generate the product/subject board (Section 2) → select the best reference shots
- [ ] Generate the character board (Section 3) → lock face/clothing, note the seed/reference ID
- [ ] Generate the 9-panel storyboard (Section 4) using the same seed/reference for consistency
- [ ] Crop panels into 3 groups (1-3, 4-6, 7-9) as start/end frames
- [ ] Run Video Prompt 1, 2, 3 through the video model in image-to-video mode (start frame + end frame + prompt)
- [ ] Check continuity after each clip (face, clothing, lighting match)
- [ ] Generate dialogue audio (TTS + lip-sync tool if native lip-sync isn't available)
- [ ] Assemble the 3 clips, add background score and SFX, burn in captions
- [ ] Final color grade + brand end card + export at 9:16, 30-35s
