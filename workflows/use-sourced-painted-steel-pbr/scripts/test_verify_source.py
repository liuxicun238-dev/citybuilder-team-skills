#!/usr/bin/env python3
"""Small synthetic fixtures test verification behavior, not material appearance."""

import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from verify_source import crop_metrics, fingerprints, local_file, png_header, verify


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


class SourceVerificationTests(unittest.TestCase):
    def setUp(self):
        # Stay inside this skill's directory and remove fixtures when each test ends.
        self.tmp = tempfile.TemporaryDirectory(prefix=".verify-test-", dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.image = self.root / "map.png"
        ihdr = struct.pack(">IIBBBBB", 2, 2, 16, 0, 0, 0, 0)
        self.image.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                              + chunk(b"IDAT", zlib.compress(b"\x00" * 10)) + chunk(b"IEND", b""))
        self.gltf = self.root / "material.gltf"
        self.gltf.write_text(json.dumps({"materials": [{"name": "test", "pbrMetallicRoughness": {"metallicFactor": 0}}]}))
        self.manifest = {"schema_version": 1, "asset": "fixture", "source_size_px": [2, 2],
                         "source_tile_m": [2.5, 2.5], "crop_pixels_xyxy": [0, 0, 1, 2],
                         "mapped_panel_m": [1.5, 2.75], "maps": [
                             {"filename": "map.png", **fingerprints(self.image), **png_header(self.image)}],
                         "gltf": {"material_name": "test", "metallic_factor": 0, **fingerprints(self.gltf)}}

    def test_valid_source_and_gltf(self):
        result = verify(self.manifest, self.root, self.gltf)
        self.assertTrue(result["source_files_verified"])
        self.assertTrue(result["gltf"]["verified"])
        self.assertEqual(result["crop"]["fit_factors_xy"], [1.2, 1.1])
        self.assertEqual(result["crop"]["crop_uv_umin_vmin_umax_vmax"], [0, 0, 0.5, 1])

    def test_optional_gltf_is_not_claimed_verified(self):
        self.assertFalse(verify(self.manifest, self.root)["gltf"]["verified"])

    def test_tampered_bytes_fail(self):
        with self.image.open("ab") as stream:
            stream.write(b"changed")
        with self.assertRaisesRegex(ValueError, "Mismatch"):
            verify(self.manifest, self.root)

    def test_hash_mismatch_fails(self):
        self.manifest["maps"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "sha256"):
            verify(self.manifest, self.root)

    def test_bad_crop_and_nan_fail(self):
        bad = copy.deepcopy(self.manifest)
        bad["crop_pixels_xyxy"] = [0, 0, 3, 2]
        with self.assertRaisesRegex(ValueError, "outside"):
            crop_metrics(bad)
        bad = copy.deepcopy(self.manifest)
        bad["source_tile_m"][0] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite"):
            crop_metrics(bad)

    def test_top_left_to_bottom_left_uv(self):
        self.manifest["crop_pixels_xyxy"] = [0, 0, 2, 1]
        self.assertEqual(crop_metrics(self.manifest)["crop_uv_umin_vmin_umax_vmax"], [0, 0.5, 1, 1])

    def test_unsafe_source_paths_fail(self):
        for filename in ("../outside.png", "/outside.png", "..\\outside.png"):
            with self.assertRaises(ValueError):
                local_file(self.root, filename)

    def test_missing_file_and_bad_header_fail(self):
        with self.assertRaisesRegex(ValueError, "Missing"):
            local_file(self.root, "absent.png")
        self.image.write_bytes(b"Not a PNG")
        with self.assertRaisesRegex(ValueError, "Invalid PNG"):
            png_header(self.image)

    def test_wrong_factor_fails(self):
        self.manifest["gltf"]["metallic_factor"] = 1
        with self.assertRaisesRegex(ValueError, "metallic factor"):
            verify(self.manifest, self.root, self.gltf)


if __name__ == "__main__":
    unittest.main()
