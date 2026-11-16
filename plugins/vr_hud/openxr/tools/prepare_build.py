"""Prepare a reproducible SCAF OpenXR Visual Studio build from the upstream template.

Uses a pinned upstream commit and copies SCAF's source-controlled HUD header.
No administrator privileges or registry modifications are performed.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'vendor' / 'OpenXR-Layer-Template'
UPSTREAM = 'https://github.com/mbucchia/OpenXR-Layer-Template.git'
UPSTREAM_COMMIT = '2827205005310dfb799226f5d197afe253a5d4ab'


class BuildPreparationError(RuntimeError):
    pass


def require_one(content: str, old: str, description: str) -> None:
    if content.count(old) != 1:
        raise BuildPreparationError(
            f'{description}: expected exactly one upstream anchor; found {content.count(old)}. '
            'The upstream template may have changed.'
        )


def patch_layer(content: str) -> str:
    """Patch only validated blocks in the pinned upstream layer.cpp; idempotent."""
    include = '#include "scaf_hud.h"'
    if include in content:
        if content.count(include) != 1 or 'scaf::DrawHud(' not in content:
            raise BuildPreparationError('Partially patched layer.cpp; restore the pinned template.')
        return content

    anchor = '#include "layer.h"'
    require_one(content, anchor, 'header include')

    start = 'const float background[4] = {0.0f, 0.0f, 0.0f, 0.2f};'
    end = 'ID3D11RenderTargetView* nullRTV = nullptr;'
    require_one(content, start, 'drawing start')
    require_one(content, end, 'drawing end')
    before, tail = content.split(start, 1)
    _discard, after = tail.split(end, 1)
    if 'context1->OMSetRenderTargets(1, rtv.GetAddressOf(), nullptr);' not in before:
        raise BuildPreparationError('Unexpected drawing context in upstream source')
    content = (before + 'scaf::DrawHud(context1.Get(), rtv.Get(), '
               'swapchainInfo.width, swapchainInfo.height);\n\n                    '
               + end + after)

    pose = 'overlay.pose = Pose::Translation({0.0f, 0.0f, -1.0f});'
    width = 'overlay.size.width = 0.8f;'
    height = 'overlay.size.height = 0.6f;'
    for old, desc in ((pose, 'quad pose'), (width, 'quad width'), (height, 'quad height')):
        require_one(content, old, desc)
    content = content.replace(pose, 'overlay.pose = Pose::Translation({0.0f, 0.0f, -1.25f});')
    content = content.replace(width, 'overlay.size.width = 0.52f;')
    content = content.replace(height, 'overlay.size.height = 0.39f;')
    content = content.replace(anchor, anchor + '\n#include "scaf_hud.h"', 1)
    return content


def apply_template(template: Path, source_header: Path) -> None:
    cpp = template / 'openxr-api-layer' / 'layer.cpp'
    header = template / 'openxr-api-layer' / 'scaf_hud.h'
    if not cpp.is_file():
        raise BuildPreparationError(f'Missing OpenXR template: {cpp}')
    if not source_header.is_file():
        raise BuildPreparationError(f'Missing SCAF source header: {source_header}')
    original = cpp.read_text(encoding='utf-8-sig')
    patched = patch_layer(original)
    if patched != original:
        cpp.write_text(patched, encoding='utf-8', newline='')
    # Always refresh the header; future HUD changes need no historical upgrade scripts.
    shutil.copy2(source_header, header)


def git(*args: str, cwd: Path | None = None) -> str:
    completed = subprocess.run(['git', *args], cwd=cwd, text=True, capture_output=True, check=False)
    if completed.returncode:
        raise BuildPreparationError(f'git {" ".join(args)} failed:\n{completed.stderr or completed.stdout}')
    return completed.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description='Prepare the pinned OpenXR template for SCAF')
    parser.add_argument('--reset-vendor', action='store_true',
                        help='Discard local modifications inside ignored vendor/ and recreate from upstream')
    args = parser.parse_args()

    if args.reset_vendor and VENDOR.exists():
        # Only delete the known, ignored vendor checkout.
        if not (VENDOR / '.git').exists():
            raise SystemExit('Refusing to remove vendor path: not a Git checkout')
        shutil.rmtree(VENDOR)
    if not VENDOR.exists():
        VENDOR.parent.mkdir(parents=True, exist_ok=True)
        git('clone', '--branch', 'examples/overlay-basic-d3d11', '--recurse-submodules', UPSTREAM, str(VENDOR))
    if not (VENDOR / '.git').exists():
        raise SystemExit(f'Existing vendor path is not a Git checkout: {VENDOR}')

    # For a fresh checkout, pin the upstream revision and submodules.
    current = git('rev-parse', 'HEAD', cwd=VENDOR)
    if current != UPSTREAM_COMMIT:
        # Avoid overwriting the user's modified template by accident.
        if git('status', '--porcelain', cwd=VENDOR):
            raise SystemExit('Vendor has local edits; use --reset-vendor only if you want to discard them.')
        git('checkout', '--detach', UPSTREAM_COMMIT, cwd=VENDOR)
    git('submodule', 'update', '--init', '--recursive', cwd=VENDOR)
    apply_template(VENDOR, ROOT / 'src' / 'scaf_hud.h')
    solution = VENDOR / 'XR_APILAYER_NOVENDOR_template.sln'
    print('[SCAF] OpenXR template prepared:', VENDOR)
    print('[SCAF] Pinned upstream commit:', UPSTREAM_COMMIT)
    print('[SCAF] Open in Visual Studio:', solution)
    print('[SCAF] Build Release | x64. No OpenXR layer was registered.')


if __name__ == '__main__':
    try:
        main()
    except (BuildPreparationError, OSError) as exc:
        raise SystemExit(f'[SCAF] Build preparation failed: {exc}') from exc
