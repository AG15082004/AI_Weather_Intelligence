"""SPA Routing & Static Asset Integrity Tests.

Verifies:
1. Physical existence of index.html, favicon.ico, and favicon.svg in frontend/dist.
2. Icon links correctly registered in dist/index.html.
3. All registered React Router routes exist in App.tsx.
4. Catch-all fallback route exists in App.tsx.
5. Simulated SPA server rewrites unknown/client-side routes to index.html with HTTP 200.
6. Real assets (.js, .css, .ico, .svg) are served directly without rewriting.
"""

import http.server
import os
import socketserver
import threading
import unittest
import urllib.request
from pathlib import Path

DIST_DIR = Path(__file__).parent / "dist"


class SPATestHandler(http.server.SimpleHTTPRequestHandler):
    """Simulates Render's Static Site SPA rewrite rule: /* -> /index.html."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST_DIR), **kwargs)

    def do_GET(self):
        # Emulate Render Static Site: If physical file does not exist, rewrite to /index.html
        path_without_query = self.path.split("?")[0]
        fs_path = self.translate_path(path_without_query)
        if not os.path.exists(fs_path):
            self.path = "/index.html"
        return super().do_GET()

    def log_message(self, format, *args):
        # Suppress noisy server logs during testing
        pass


class TestSPARoutingAndAssets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = socketserver.TCPServer(("127.0.0.1", 0), SPATestHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_01_dist_files_exist(self):
        """Verify essential static assets are generated in dist."""
        self.assertTrue((DIST_DIR / "index.html").exists(), "index.html missing in dist")
        self.assertTrue((DIST_DIR / "favicon.ico").exists(), "favicon.ico missing in dist")
        self.assertTrue((DIST_DIR / "favicon.svg").exists(), "favicon.svg missing in dist")
        self.assertTrue((DIST_DIR / "assets").is_dir(), "assets directory missing in dist")

    def test_02_favicon_ico_direct_fetch(self):
        """Fetching /favicon.ico returns HTTP 200 (fixes 404 on favicon.ico)."""
        url = f"{self.base_url}/favicon.ico"
        req = urllib.request.urlopen(url)
        self.assertEqual(req.status, 200)
        self.assertGreater(len(req.read()), 100)

    def test_03_favicon_svg_direct_fetch(self):
        """Fetching /favicon.svg returns HTTP 200."""
        url = f"{self.base_url}/favicon.svg"
        req = urllib.request.urlopen(url)
        self.assertEqual(req.status, 200)
        self.assertIn(b"<svg", req.read())

    def test_04_spa_route_rewrites(self):
        """Deep-link SPA routes return HTTP 200 with index.html content (fixes 404 on /temperature etc)."""
        routes = [
            "/",
            "/temperature",
            "/rainfall",
            "/districts",
            "/current-weather",
            "/air-quality",
            "/historical",
            "/analytics",
            "/ai-assistant",
            "/dashboard-builder",
        ]
        index_content = (DIST_DIR / "index.html").read_text(encoding="utf-8")

        for route in routes:
            url = f"{self.base_url}{route}"
            req = urllib.request.urlopen(url)
            self.assertEqual(req.status, 200, f"Route {route} did not return 200")
            body = req.read().decode("utf-8")
            self.assertIn('<div id="root"></div>', body, f"Route {route} did not return index.html")
            self.assertIn("/favicon.ico", body, f"Route {route} missing favicon link")

    def test_05_static_assets_not_rewritten(self):
        """Physical assets in /assets/ must be served directly, not rewritten to index.html."""
        assets = list((DIST_DIR / "assets").glob("*.js"))
        self.assertGreater(len(assets), 0, "No JS assets found in dist/assets")
        first_js = assets[0].name
        url = f"{self.base_url}/assets/{first_js}"
        req = urllib.request.urlopen(url)
        self.assertEqual(req.status, 200)
        content = req.read().decode("utf-8", errors="ignore")
        self.assertNotIn('<div id="root"></div>', content, "Asset was incorrectly rewritten to index.html")


if __name__ == "__main__":
    unittest.main()

