# ============ ADMIN ELEVATION ============
# Re-launch this script with UAC "runas" so the whole app
# (Flask, remote code, subprocess.Popen of exe files) runs elevated.

def _is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _elevate():
    """Relaunch the current script with administrator privileges."""
    script = os.path.abspath(sys.argv[0])
    # Re-quote every original argument so paths with spaces survive.
    params = " ".join(f'"{a}"' for a in sys.argv[1:])

    try:
        # ShellExecuteW returns an HINSTANCE; > 32 means success.
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,          # hwnd
            "runas",       # lpVerb  -> triggers the UAC prompt
            sys.executable,# lpFile  -> python.exe
            f'"{script}" {params}'.strip(),
            None,          # lpDirectory
            1              # nShowCmd -> SW_SHOWNORMAL
        )
    except Exception as e:
        print(f"[elevation] ShellExecuteW failed: {e}")
        return False

    if ret <= 32:
        # Common codes: 5 = access denied (user cancelled UAC)
        print(f"[elevation] UAC refused or failed (code {ret}). "
              f"Continuing without admin rights.")
        return False
    return True


if not _is_admin():
    print("[elevation] Not running as admin - requesting elevation...")
    if _elevate():
        # The elevated instance is now running in a new process.
        # Exit this unelevated one so we don't run everything twice.
        sys.exit(0)
    else:
        print("[elevation] Proceeding without administrator privileges.")
else:
    print("[elevation] Running with administrator privileges.")
