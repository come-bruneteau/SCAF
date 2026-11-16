"""Offline tests for reproducible OpenXR preparation, without Visual Studio."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'tools' / 'prepare_build.py'
spec = importlib.util.spec_from_file_location('prepare_build', MODULE)
prep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prep)


class BuildTests(unittest.TestCase):
    def template(self):
        return '''#include "layer.h"
context1->OMSetRenderTargets(1, rtv.GetAddressOf(), nullptr);
const float background[4] = {0.0f, 0.0f, 0.0f, 0.2f};
context1->ClearRenderTargetView(rtv.Get(), background);
ID3D11RenderTargetView* nullRTV = nullptr;
overlay.pose = Pose::Translation({0.0f, 0.0f, -1.0f});
overlay.size.width = 0.8f;
overlay.size.height = 0.6f;
'''

    def test_patch_and_idempotency(self):
        result = prep.patch_layer(self.template())
        self.assertIn('scaf::DrawHud(', result)
        self.assertIn('"scaf_hud.h"', result)
        self.assertIn('Pose::Translation({0.0f, 0.0f, -1.25f})', result)
        self.assertIn('overlay.size.width = 0.52f;', result)
        self.assertIn('overlay.size.height = 0.39f;', result)
        self.assertEqual(prep.patch_layer(result), result)

    def test_incompatible_template_fails_safely(self):
        with self.assertRaises(prep.BuildPreparationError):
            prep.patch_layer('#include "layer.h"')

    def test_copy_header(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            folder = p / 'openxr-api-layer'
            folder.mkdir()
            (folder / 'layer.cpp').write_text(self.template(), encoding='utf-8')
            src = p / 'source.h'
            src.write_text('// SCAF HEADLOCKED HUD', encoding='utf-8')
            prep.apply_template(p, src)
            self.assertEqual((folder / 'scaf_hud.h').read_text(), src.read_text())
            prep.apply_template(p, src)
            self.assertEqual((folder / 'layer.cpp').read_text(), prep.patch_layer(self.template()))


if __name__ == '__main__':
    unittest.main()
