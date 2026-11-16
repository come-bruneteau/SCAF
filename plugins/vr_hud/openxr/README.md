# SCAF VR-003 — Transparent head-locked OpenXR prototype

**Status: experimental source prototype. No Windows DLL has been built or tested yet.**

This adds a translucent cyan reticle and four **static seven-segment numbers** inside the existing DCS OpenXR session. It uses an OpenXR **API layer** based on the MIT-licensed `mbucchia/OpenXR-Layer-Template` example, not a separate VR application. It attaches an alpha-blended quad to `XR_REFERENCE_SPACE_TYPE_VIEW` so the graphic follows the user's head.

### What this demonstrates
- `XR_REFERENCE_SPACE_TYPE_VIEW` for head lock.
- `XR_COMPOSITION_LAYER_BLEND_TEXTURE_SOURCE_ALPHA_BIT` and a clear alpha=0 background.
- `XrCompositionLayerQuad` appended inside `xrEndFrame()`.
- Existing DCS rendering is otherwise passed through.
- A minimal seven-segment speed/altitude/fuel/G visual arrangement using **static** values only. The mock values are *not* SCAF telemetry; do not use them to interpret flight.

### Requirements
- Windows 10/11 x64, Git, Python 3, Visual Studio 2022 with **Desktop development with C++**, and NuGet tooling.
- A working DCS World session already running in **OpenXR** (Quest Link OpenXR runtime or another active OpenXR runtime).
- Compatible graphics route. The upstream example targets D3D11 drawing and uses a composition framework for graphics interop. Other graphics combinations are **not validated here**.
- Hardware headset recommended for test, but **this source package has not been compiled or tested in DCS**.

### 1. Prepare source

From the SCAF root, run:

```powershell
.\plugins\vr_hud\openxr\prepare_windows.bat
```

The script clones the exact example branch in the local `vendor/` folder and patches its `openxr-api-layer/layer.cpp`. It does **not** install or enable any OpenXR API layer. It also does **not** change DCS files, Quest Link, or SCAF networking.

For manual setup:

```powershell
cd plugins/vr_hud/openxr
mkdir vendor -ErrorAction SilentlyContinue
git clone --branch examples/overlay-basic-d3d11 --recurse-submodules https://github.com/mbucchia/OpenXR-Layer-Template.git vendor/OpenXR-Layer-Template
py -3 apply_to_template.py vendor/OpenXR-Layer-Template
```

If the upstream branch changes enough for the patch to become incompatible, the script fails instead of applying a partial patch. The example tree observed while preparing this prototype was `2827205005310dfb799226f5d197afe253a5d4ab`; for fully reproducible builds, check out that commit and then update submodules before patching.

### 2. Build

Open `vendor/OpenXR-Layer-Template/XR_APILAYER_NOVENDOR_template.sln` in Visual Studio. Select **Release** and **x64**; restore any NuGet packages and build the solution. Expected output is in `vendor/OpenXR-Layer-Template/bin/x64/Release/`.

The upstream example includes registration and unregistration scripts. **Do not blindly enable the layer globally**: an implicit OpenXR layer can load in *all* OpenXR applications and a development bug may crash them. Back up its registration settings, prefer controlled tests, and shut down DCS before enabling/disabling any layer. Follow the upstream example's `scripts/Install-Layer.ps1` and `scripts/Uninstall-Layer.ps1` instructions when ready to test, and inspect the generated `openxr-api-layer.json` and DLL paths before running either script.

The API layer may coexist with OpenKneeboard, but layer ordering can matter. For the first test, disable other nonessential OpenXR API layers; restore your normal setup afterward. If DCS fails to start, disable/unregister the experimental layer before trying again.

### 3. Test plan (VR-003)

1. Confirm DCS in VR still starts without our API layer.
2. Build the x64 DLL and verify the generated manifest points to the correct DLL.
3. Register the layer following the upstream instructions **only for testing**.
4. Restart DCS in VR. Confirm the cockpit is visible behind the cyan symbology, with no opaque panel.
5. Turn your head left/right: the overlay should remain centered in the field of view.
6. Check both eyes, comfort and readability. Do not use the prototype for precision alignment.
7. Unregister the layer after testing, especially if other OpenXR software behaves unexpectedly.

**Important:** the HUD currently displays static sample numbers (527 / 2435 / 3753 / 084). It does *not* yet consume `ws://127.0.0.1:50501`. Connecting real telemetry is the next step after the injection and transparency tests pass.

### Folder contents

- `src/scaf_hud.h`: simple C++ Direct3D 11.1 transparent HUD drawing routines.
- `apply_to_template.py`: patches an upstream layer example in-place and is idempotent.
- `prepare_windows.bat`: prepares the upstream source tree on Windows.
- `tests/test_apply_to_template.py`: Python patcher tests (do not validate OpenXR runtime behavior).

### Test without Visual Studio

```powershell
py -3 -m unittest discover -s plugins/vr_hud/openxr/tests -v
```

### Licensing
The upstream OpenXR API layer template is MIT-licensed; its original copyright and license remain in the cloned source. This SCAF patch package is distributed under the repository's license. The upstream dependency must retain its original license notices.

### External source documentation
- https://github.com/mbucchia/OpenXR-Layer-Template/tree/examples/overlay-basic-d3d11
- https://github.com/mbucchia/OpenXR-Layer-Template/wiki/Tutorial-2:-Your-first-in-VR-overlay
- https://registry.khronos.org/OpenXR/specs/1.0-khr/html/xrspec.html
