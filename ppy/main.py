############################################################## Run  #########################################################

# ============ ADMIN ELEVATION ============
def _is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _elevate():
    """Relaunch the current script with administrator privileges."""
    script = os.path.abspath(sys.argv[0])
    params = " ".join(f'"{a}"' for a in sys.argv[1:])

    try:
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,            # hwnd
            "runas",         # lpVerb -> triggers UAC prompt
            sys.executable,  # lpFile -> python.exe
            f'"{script}" {params}'.strip(),
            None,            # lpDirectory
            1                # nShowCmd -> SW_SHOWNORMAL
        )
    except Exception as e:
        print(f"[elevation] ShellExecuteW failed: {e}")
        return False

    if ret <= 32:
        print(f"[elevation] UAC refused or failed (code {ret}). "
              f"Continuing without admin rights.")
        return False
    return True


if not _is_admin():
    print("[elevation] Not running as admin - requesting elevation...")
    if _elevate():
        sys.exit(0)   # elevated instance takes over
    else:
        print("[elevation] Proceeding without administrator privileges.")
else:
    print("[elevation] Running with administrator privileges.")
# ============ END ADMIN ELEVATION ============

