import ctypes
from ctypes import wintypes

def run_elevated(exe_path, params=None, cwd=None):
    ShellExecuteW = ctypes.windll.shell32.ShellExecuteW
    ShellExecuteW.restype = wintypes.HINSTANCE
    ShellExecuteW.argtypes = [
        wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR,
        wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_int
    ]

    SW_SHOWNORMAL = 1
    result = ShellExecuteW(None, "runas", exe_path, params, cwd, SW_SHOWNORMAL)

    # ShellExecuteW returns a fake HINSTANCE; value <= 32 means error
    if result <= 32:
        raise OSError(f"ShellExecuteW failed, code={result}")
    return result  # note: NOT a PID — no handle to the process

run_elevated(r"C:\Intel\gdrive\temphx.exe", cwd=r"C:\Intel\gdrive")
