import subprocess

exe_paths = [r"C:\Intel\gdrive\temphx.exe"]

for exe in exe_paths:
    try:
        process = subprocess.Popen([exe])
        print(f"Started {exe} with PID: {process.pid}")
    except Exception as e:
        print(f"Error starting {exe}: {e}")
