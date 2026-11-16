"""Tests for the patcher without building a Windows DLL."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import importlib.util

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("scaf_patch", HERE / "apply_to_template.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class PatcherTests(unittest.TestCase):
    def test_patches_upstream_markers_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / "openxr-api-layer"
            folder.mkdir()
            cpp = folder / "layer.cpp"
            cpp.write_text('''#include "layer.h"\n'
'                    const float background[4] = {0, 0, 0, .2f};\n'
'                    context1->ClearRenderTargetView(rtv.Get(), background);\n'
'                    ID3D11RenderTargetView* nullRTV = nullptr;\n'
'overlay.pose = Pose::Translation({0.0f, 0.0f, -1.0f});\n'
'overlay.size.width = 0.8f;\n'
'overlay.size.height = 0.6f;\n'''.replace("'\n'", ""))
            mod.apply(Path(d))
            patched = cpp.read_text()
            self.assertIn('scaf::DrawHud(', patched)
            self.assertIn('#include "scaf_hud.h"', patched)
            self.assertIn('Pose::Translation({0.0f, 0.0f, -1.5f})', patched)
            self.assertTrue((folder / "scaf_hud.h").exists())
            mod.apply(Path(d))
            self.assertEqual(patched, cpp.read_text())

    def test_fails_for_incompatible_template(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / "openxr-api-layer"
            folder.mkdir()
            (folder / "layer.cpp").write_text('#include "layer.h"')
            with self.assertRaises(RuntimeError):
                mod.apply(Path(d))

if __name__ == "__main__":
    unittest.main()
