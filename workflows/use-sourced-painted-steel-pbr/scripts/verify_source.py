#!/usr/bin/env python3
"""Read-only source fingerprint/header and crop verifier; Python standard library."""

import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import struct
import sys


DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "references/blue-metal-plate.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local_file(root, filename):
    """Reject absolute/traversing paths and symlinks escaping the source root."""
    path = PurePosixPath(filename)
    require(not path.is_absolute() and ".." not in path.parts and "\\" not in filename,
            "Source filename must be a safe relative path")
    root = Path(root).resolve()
    candidate = (root / filename).resolve()
    require(candidate != root and root in candidate.parents,
            "Source filename escapes the supplied directory")
    require(candidate.is_file(), "Missing source file: " + filename)
    return candidate


def fingerprints(path):
    sha = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            sha.update(block)
            md5.update(block)
    return {"bytes": size, "sha256": sha.hexdigest(), "md5": md5.hexdigest()}


def png_header(path):
    with path.open("rb") as stream:
        header = stream.read(33)
    require(len(header) == 33 and header[:8] == b"\x89PNG\r\n\x1a\n"
            and header[8:16] == b"\x00\x00\x00\rIHDR", "Invalid PNG header: " + path.name)
    width, height, depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", header[16:29])
    return {"size_px": [width, height], "png_bit_depth": depth, "png_color_type": color_type}


def crop_metrics(manifest):
    width, height = manifest["source_size_px"]
    left, top, right, bottom = manifest["crop_pixels_xyxy"]
    sw, sh = manifest["source_tile_m"]
    tw, th = manifest["mapped_panel_m"]
    require(all(isinstance(x, int) and not isinstance(x, bool)
                for x in [width, height, left, top, right, bottom]), "Crop and image sizes must be integers")
    require(width > 0 and height > 0 and 0 <= left < right <= width
            and 0 <= top < bottom <= height, "Crop is empty or outside the source image")
    require(all(isinstance(x, (int, float)) and not isinstance(x, bool)
                and math.isfinite(x) and x > 0 for x in [sw, sh, tw, th]),
            "Physical dimensions must be finite and positive")
    cw, ch = (right - left) / width * sw, (bottom - top) / height * sh
    factors = [tw / cw, th / ch]
    return {"crop_size_px": [right - left, bottom - top],
            "crop_uv_umin_vmin_umax_vmax": [left / width, 1 - bottom / height,
                                            right / width, 1 - top / height],
            "crop_physical_m": [cw, ch], "fit_factors_xy": factors,
            "fit_change_percent_xy": [(x - 1) * 100 for x in factors]}


def verify(manifest, source_dir, gltf_path=None):
    require(manifest["schema_version"] == 1, "Unsupported manifest schema")
    report = {"asset": manifest["asset"], "crop": crop_metrics(manifest), "maps": {}}
    require(bool(manifest["maps"]), "No source maps declared")
    seen = set()
    for entry in manifest["maps"]:
        name = entry["filename"]
        require(name not in seen, "Duplicate source filename: " + name)
        seen.add(name)
        path = local_file(source_dir, name)
        actual = {**fingerprints(path), **png_header(path)}
        require(entry["size_px"] == manifest["source_size_px"], "Maps have inconsistent source dimensions")
        for key, value in actual.items():
            require(value == entry[key], "Mismatch for " + name + ": " + key)
        report["maps"][name] = {"verified": True, **actual}
    report["gltf"] = {"verified": False, "reason": "Not supplied"}
    if gltf_path is not None:
        spec = manifest["gltf"]
        path = Path(gltf_path)
        actual = fingerprints(path)
        for key, value in actual.items():
            require(value == spec[key], "Mismatch for official glTF: " + key)
        data = json.loads(path.read_text(encoding="utf-8"))
        materials = [m for m in data.get("materials", []) if m.get("name") == spec["material_name"]]
        require(len(materials) == 1, "Expected exactly one named glTF material")
        factor = materials[0].get("pbrMetallicRoughness", {}).get("metallicFactor", 1)
        require(factor == spec["metallic_factor"], "Unexpected glTF metallic factor")
        report["gltf"] = {"verified": True, "metallic_factor": factor, **actual}
    report["source_files_verified"] = True
    report["all_requested_checks_passed"] = True
    report["not_checked"] = ["Pixel/channel ranges", "Live license status", "Mesh UVs and tangents",
                             "Shader wiring", "Image-path portability", "Rendered visual quality"]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--gltf", type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        print(json.dumps(verify(manifest, args.source_dir, args.gltf), indent=2))
    except (OSError, ValueError, KeyError, TypeError, struct.error) as error:
        print(json.dumps({"all_requested_checks_passed": False, "error": str(error)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
