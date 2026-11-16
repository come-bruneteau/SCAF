"""Package SCAF's existing compiled OpenXR layer for GitHub Releases.

Run from anywhere: python plugins/vr_hud/openxr/tools/make_release.py
No administrator privileges or third-party dependencies are required.
"""
from __future__ import annotations
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # openxr/
BUILD = ROOT / "vendor" / "OpenXR-Layer-Template" / "bin" / "x64" / "Release"
OUTPUT = ROOT / "dist" / "releases"
PACK = "SCAF-OpenXR-Windows-x64"


def main() -> None:
    manifest = BUILD / "openxr-api-layer.json"
    if not manifest.is_file():
        raise SystemExit(f"[ERREUR] Manifeste manquant : {manifest}. Compiler Release|x64 d'abord.")
    config = json.loads(manifest.read_text(encoding="utf-8-sig"))
    raw_dll = config.get("api_layer", {}).get("library_path")
    if not isinstance(raw_dll, str) or not raw_dll:
        raise SystemExit("[ERREUR] Champ api_layer.library_path absent.")
    rel = Path(raw_dll.replace("\\", "/"))
    if rel.is_absolute() or ".." in rel.parts or len(rel.parts) != 1 or rel.suffix.lower() != ".dll":
        raise SystemExit(f"[ERREUR] DLL non relative ou invalide : {raw_dll!r}")
    dll = BUILD / rel
    if not dll.is_file():
        raise SystemExit(f"[ERREUR] DLL compilée introuvable : {dll}")
    if dll.stat().st_size < 10000:
        raise SystemExit("[ERREUR] DLL anormalement petite, vérifier la compilation.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    staging = OUTPUT / PACK
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()
    shutil.copy2(manifest, staging / "openxr-api-layer.json")
    shutil.copy2(dll, staging / rel.name)
    for name in ("Install-User.cmd", "Uninstall-User.cmd", "README_DEPLOIEMENT.txt"):
        shutil.copy2(Path(__file__).with_name(name), staging / name)
    archive = OUTPUT / f"{PACK}.zip"
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(staging.iterdir()):
            z.write(f, arcname=f"{PACK}/{f.name}")
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    (OUTPUT / f"{archive.name}.sha256").write_text(f"{sha}  {archive.name}\n", encoding="ascii")
    print(f"[SCAF] Archive : {archive}")
    print(f"[SCAF] SHA256  : {sha}")
    print("[SCAF] A publier dans GitHub Releases, avec le .sha256.")

if __name__ == "__main__":
    main()
