# CHANGELOG — v01-hands (2026-10-16)

Source: lessons from the citizen-skill-v01-run test build (`/workspace/citizen-skill-v01-run/`). The hands and hand motion were rejected and then reworked. Backup of the unmodified package: `/workspace/character-modeling-skill-v01.orig/`.

## Added
- `references/hands.md` — new reference:
  1. **Hand gate items.** Five separate fingers, knuckles, nails, palm pad volume, thenar eminence, thumb-web, thumb opposition angle and wrist-to-cuff transition. Sizes must be checked against a real reference with source and license recorded. ANSUR II 1.70–1.76 m male figures are included.
  2. **Finger bone spec.** 3 joints per finger, thumb included, for 30 finger bones in total. All LODs use the same rig. LOD1/LOD2 may merge finger weights into the palm/hand bone. At most 4 weights per vertex, normalized.
  3. **Walk hand pose.** Relaxed and half-closed, with fingers slightly and individually bent. Wrist rotation follows the arm swing with a 2–4 frame follow-through lag. Zero hand-to-trousers/thigh intersections on every frame, plus a reported minimum clearance in mm.
  4. **Required images.** Palm and back close-ups in open and half-closed poses, a side-by-side with a real hand, and a walk hand close-up gif.
- `CHANGELOG-v01-hands.md` (this file).

## Changed
- `SKILL.md`:
  - The reference index now links `references/hands.md`.
  - New section "门槛补充（v01-hands）" summarising the hand gate, the finger bones, the walk hand pose and the required images.
  - It also lists the known gaps and the head-first lesson.
- `references/validation.md`: new section "补充门槛" covering:
  - the hand gate, finger bones, walk hand pose and required images;
  - known gaps: clothing folds and zipper, foot sliding, backpack secondary motion, flat-colour materials;
  - the head lesson.
- `references/workflow.md`: new section 9 covering:
  - **Gate ordering:** the head must pass before body, clothing or rig work.
  - **Head lesson:**
    - Parameter push plus smoothing on the recipe head plateaued after 3 rounds.
    - Voxel remeshing broke the existing skinning.
    - Fix: get matching orthographic front and side references early and do sculpt-level work.
  - A pointer to hands.md, and a list of open items to report before delivery.
- `MANIFEST.json`:
  - Hashes regenerated for the changed files.
  - `references/hands.md` and `CHANGELOG-v01-hands.md` added.
  - Checked with `scripts/verify_package.py`.

## Not changed
- Pipeline scripts, payload references and EXTERNAL-AGENT-PROMPT.txt are byte-identical to the backup.
