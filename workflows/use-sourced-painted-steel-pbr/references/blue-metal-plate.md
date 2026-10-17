# Worked example: original Blue Metal Plate panel

## What produced the accepted improvement

The panel proof used [Poly Haven's Blue Metal Plate](https://polyhaven.com/a/blue_metal_plate), credited to Rob Tuytel, with [Poly Haven's CC0 license](https://polyhaven.com/license) recorded in its source provenance. Credit is retained for traceability; CC0 does not make attribution mandatory. The improvement came from retaining the source's irregular, broad paint fading and its aligned roughness/normal detail at a plausible physical size.

The reviewed panel used untouched 4096 × 4096 PNG BaseColor, Roughness and OpenGL Normal images. There was no retint, synthetic rust/scratch overlay, extra noise normal, or displacement. The actual source's ARM blue channel was read back at full precision as min=max=0; the official glTF also sets metallicFactor=0. The panel remained dielectric. This is specific to that coated material, not a rule that every steel surface has zero metalness.

The panel's macro appearance was accepted. Reusing the same crop on both leaves was a disclosed proof limitation, not approval of repeated wear. Clean frame/hardware treatments and handle materials were still separate work. Do not promote the whole original assembly to an approved final asset.

## Acquisition and checksums

[blue-metal-plate.json](blue-metal-plate.json) contains official URLs, byte counts, MD5 values recorded from the official file listing, and SHA-256 fingerprints of the cached originals. Four PNGs total 217,422,933 bytes, approximately 207 MiB; acquire them separately rather than committing them with this skill.

1. Open the official asset and license pages; confirm the intended resolution and reuse terms at acquisition.
2. Retrieve the official [file manifest](https://api.polyhaven.com/files/blue_metal_plate) and the exact 4K PNG variants listed in the local manifest. Save them using its local filenames: Diffuse.png, Rough.png, nor_gl.png and arm.png. Renaming without recompression preserves bytes.
3. For independent material semantics, also retrieve the manifest's official glTF URL. Its image references use JPEG variants; that does not make their hashes interchangeable with the PNGs in this proof.
4. Run the included verifier against the downloaded files. A mismatch means the exact recorded source was not reproduced. Investigate a source revision or wrong variant; do not silently rewrite expected hashes to make the check pass.
5. Preserve the provider's current metadata and license evidence alongside the material package. The local manifest records past evidence; a checksum is not a legal determination.

The verifier does not decode pixel values or reperform the ARM full-precision readback. For any new/revised source, inspect packed channels at native precision in an appropriate image tool or renderer. Do not use an 8-bit preview to assert exact 16-bit channel ranges.

## Exact crop and scale

The baseline uses the original files with a UV crop, so the source image bytes remain unchanged:

- Source coverage: 2.5 × 2.5 m, 4096 × 4096 px
- Pixel crop: [1280, 0, 3120, 4096], top-left origin, right/bottom exclusive
- Pixel extent: 1840 × 4096 px
- UV window: U 0.3125 to 0.76171875; V 0 to 1
- Source crop coverage: 1.123046875 × 2.5 m
- Mapped panel: 1.192 × 2.584 m
- Fit factors: 1.06139826087 horizontally, 1.0336 vertically
- Stretch relative to the source: approximately 6.14% and 3.36%

For a top-left pixel rectangle [left, top, right, bottom] in W × H pixels, convert to a bottom-left UV convention as U=[left/W, right/W], V=[1-bottom/H, 1-top/H]. Physical crop width is (right-left)/W × source_width_m, and height is (bottom-top)/H × source_height_m. Divide target dimensions by those values to get fit factors. Use one shared transformation for all source channels.

The original proof used identical crop coordinates for both leaves. A production variation should be a new reviewed candidate, with normal handedness and source directionality checked after any transform. Merely mirroring a recognizable stain can still produce obvious repetition.

## What earlier attempts taught

Handmade overlays in this particular comparison read as blurry curtains, organized chalk-like clusters, or flame-like rust. Increasing metal brightness did not solve those pattern and coating errors. The useful correction was returning to a verified source at the right scale before adjusting anything. These failures do not imply that procedural methods can never work; they identify why those specific candidates were unconvincing.

## Historical evidence and its limits

[accepted-panel-proof-snapshot.json](accepted-panel-proof-snapshot.json) freezes the config, source-map header observations and relevant exact assembly excerpts, plus SHA-256 hashes of the original full artifacts. It is an evidence record, not a portable assembly tool. Its assembly excerpts depend on that project's geometry and include the historical repeated panel crop. Unrelated frame/hardware assembly code is deliberately omitted. Do not run it as this skill's generic recipe.

In the original door project, evidence paths relative to the double_steel_door directory were:

- materials/real_source_candidate/source_proof_config.json
- materials/real_source_candidate/SOURCE_INSPECTION.json
- materials/real_source_candidate/scripts/assemble_source_proof.py
- materials/real_source_candidate/source/SOURCE_LICENSE.md
- materials/real_source_candidate/source/official_blue_metal_plate_4k.gltf
- materials/real_source_candidate/evidence/Door_PBR_Front.png
- materials/real_source_candidate/evidence/Door_PBR_Latch.png
- materials/real_source_candidate/evidence/Source_and_Actual_Local.png

These larger project artifacts are not bundled with the skill. A copied older LICENSE_PROVENANCE.md described a different workshop experiment with retint and oxide layering; those transformations do not describe this accepted panel baseline. Prefer the frozen proof config/assembly and its source license record when reconstructing what was actually done.
