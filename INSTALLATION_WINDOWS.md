# SCAF — Fast installation on a Windows simulator PC

1. Install **Python 3** from https://www.python.org/downloads/windows/ if it is not already installed.
2. Copy or clone the SCAF repository, with `install.bat` and `install.ps1` in its root directory.
3. **Double-click `install.bat`** (internet access required for the initial Python package installation).
4. Wait for `SCAF Python setup completed successfully`.
5. Start the core from the repository root:

   ```powershell
   .\.venv\Scripts\python.exe -m core.networking.receiver
   ```

6. Start the live HUD in a second terminal:

   ```powershell
   .\.venv\Scripts\python.exe -m plugins.vr_hud.python.src.main --live
   ```

## Notes

- `install.ps1` searches the repo recursively for `requirements.txt` and installs all of them in the `.venv` environment; it ignores `.venv`, `.git`, `node_modules` and similar generated directories.
- Installing into `.venv` avoids changing packages installed globally on the simulator PC.
- The script does **not** install DCS, OpenKneeboard, Meta Quest Link or OpenXR. Those must be installed/configured separately.
- The Lua exporter must be integrated into the **correct DCS Saved Games/Scripts/Export.lua** location. If a file already exists, merge its content carefully instead of overwriting it.
- `requirements.txt` may include optional or development dependencies. If any single package fails (e.g. a compiler is needed), the installer stops with an error and tells you which file it was processing.
- To repeat the installation later, simply run `install.bat` again.
- For automated CI or unattended use: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -SkipUpgrade`.
- Add `.venv/` to `.gitignore` and **do not commit the environment**.
