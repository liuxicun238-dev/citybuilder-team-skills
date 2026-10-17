---
name: use-sourced-painted-steel-pbr
description: Build and review believable painted-steel panel materials from licensed, verified PBR sources, preserving physical scale and channel alignment. Use for steel doors, cabinets and similar coated panels, especially when procedural weathering looks artificial.
---

# Use sourced painted-steel PBR

The useful starting point is an appropriate real material source, its matching data maps, and its appearance on the actual mesh. A description of weathering or a complicated shader does not reproduce the source's visual quality.

## Establish the source and baseline

1. Match the reference's coating, broad fading, wear size, and surface history before choosing a source. Inspect the full source and a proposed crop; a thumbnail can conceal seams, lighting baked into color, or a distinctive repeating mark.
2. Obtain the original maps through the provider's official asset page/API. Record creator, license URL, download URLs, resolution, physical coverage, channel conventions, and hashes. Keep source files immutable. Stop if licensing or the necessary maps cannot be verified; do not present guessed maps as sourced PBR.
3. Start with the source's BaseColor, Roughness and tangent Normal unchanged. Use the material's authored metalness, not a value inferred from the word “steel.” Intact paint is dielectric even over a metal substrate. Separate exposed metal or oxide needs source evidence or an explicitly reviewed edit.
4. Freeze geometry, UVs, source images and the currently accepted panel look before modifying another component. Work on a candidate copy. Approval of the panel appearance does not approve duplicated leaf wear, unrelated frame/hardware treatments, or final engine behavior.

For the approved Blue Metal Plate example, read [the worked example](references/blue-metal-plate.md). Its small [source manifest](references/blue-metal-plate.json) records official acquisition URLs and exact source fingerprints. Textures are deliberately not bundled.

## Keep the mapping physically coherent

- Prefer a UV window into the untouched full-resolution images for the initial proof. Apply exactly the same crop and transform to every channel. For any exported physical crop, preserve bit depth and record that its file bytes have changed.
- Measure the mesh in meters and derive the crop's real coverage from the source tile. Report both horizontal and vertical fit factors; avoid stretching a small scratch sample over a whole door. A tolerable fit is a visual judgment for this asset, not a universal percentage.
- Give large neighboring panels distinct, plausible source regions when the source allows it. Compare the whole assembly for recognizable repetition. A second crop, rotation or mirror must respect runoff/grain direction and tangent normals; none is automatically an improvement.
- BaseColor is color-managed as sRGB. Roughness, metallic, packed ARM/ORM, height and normal are linear data/Non-Color. Decode packed channels by the provider's specification. Do not multiply AO into BaseColor or treat roughness as gloss without an explicit conversion.
- For Blender, use an ordinary image-based Principled material and tangent-space Normal Map node. Start authored normals at strength 1. Keep extra noise, displacement, retint and synthetic weathering off until the source baseline is reviewed.

### Mirrored and rotated normals

The normal's tangent frame must match the UVs used to sample it. If mesh UVs are mirrored, regenerate/export tangents with the correct handedness and ensure the importer preserves that sign; do not blindly invert a channel as well. If only shader coordinates or image pixels are flipped/rotated while the mesh tangent basis stays unchanged, transform the decoded normal's X/Y components consistently, or bake into the final UV layout. A shader-only U flip needs an X sign flip; a V flip needs a Y sign flip, under the unchanged-basis assumption. OpenGL/DirectX Y conversion is a separate operation. Check all such cases on the actual mesh under a grazing light, including the reverse face and UV seams.

## Use actual renders as the visual gate

Render the saved candidate on its actual geometry, using a neutral environment, fixed exposure/view transform, and comparable camera/light settings across candidates. Provide a whole-assembly front view, an oblique/grazing-light view, and local views of the panel and its frame/hardware transition.

Check:

- The reference's broad color breakup and wear scale survive at the intended viewing distance
- Normal detail reads as coating/metal relief rather than melted ridges, inflated bumps or shading seams
- Paint has a coherent roughness response without plastic glare or arbitrary metallic brightness
- Both leaves avoid conspicuous identical marks and impossible directional wear
- Frame, braces, handles and hinges belong to the same assembly while retaining their own coating and wear behavior

A texture contact sheet is source evidence, not a render of the model. A passed hash/UV check is technical evidence, not visual acceptance. Label pending views, untested target engines, unsupported approximations and unapproved components clearly. If the source still looks wrong, revisit source choice, scale, channels and lighting before stacking masks on top.

## Deliver a reproducible material

Keep the source manifest, mapping/scale settings, node/channel settings and real evidence images alongside the scene. Use relative texture paths or supported image packing. Reopen a relocated copy and check that every image resolves without an original-cache fallback; then inspect the exported material in the actual target renderer when available. Record normal convention and any conversions.

The included [verifier](scripts/verify_source.py) uses only Python's standard library. It reads local files, checks the manifest's hashes/PNG headers and crop math, and optionally checks the official glTF's material factor. It does not download, edit textures, assemble a Blender scene, render, or prove visual quality.

Run from this skill directory, supplying a directory containing the manifest's source filenames:

```sh
python scripts/verify_source.py --source-dir SOURCE_DIRECTORY --gltf OFFICIAL_GLTF_FILE
python scripts/test_verify_source.py
```

Omitting `--gltf` leaves that evidence explicitly unverified. For a different material, supply `--manifest` with a separately verified manifest; do not reuse this example's hashes or metalness assumptions.
