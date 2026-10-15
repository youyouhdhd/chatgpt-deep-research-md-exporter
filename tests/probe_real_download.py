"""Real-browser probe: why is chrome.downloads.download's filename ignored,
and which alternative naming mechanism actually works?

Variants:
  A) offscreen blob + downloads.download(filename)   (current extension pipeline)
  E) http URL  + downloads.download(filename)        (scheme dependency check)
  F) popup-local <a download> anchor click            (classic naming pattern)
  G) offscreen <a download> anchor click             (candidate production fix)

Downloads go natively to a folder we own via a browser-level CDP session.
Run:  python tests/probe_real_download.py [chromium|chrome]
"""

import json
import re
import shutil
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PROBE_FILENAME = "中文报告probe_2026-10-15_10-00.md"
UUID_MD = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.md$")

PROBE_BACKGROUND = """
let probeNameCache = '';
chrome.runtime.onInstalled.addListener(() => {});
chrome.runtime.onStartup.addListener(() => {});
chrome.runtime.onMessage.addListener((message) => {
  if (message?.type === 'PROBE_SET_NAME') {
    probeNameCache = String(message.filename || '');
  }
  return false;
});
// probe-only: rename downloads via onDeterminingFilename (sync suggest)
chrome.downloads.onDeterminingFilename.addListener((item, suggest) => {
  const name = probeNameCache;
  if (name && !item.filename.includes(name)) {
    suggest({ filename: name, conflictAction: 'overwrite' });
  } else {
    suggest();
  }
});
"""

HELPER_PAGE = """<!doctype html>
<html><body>
<script src="helper.js"></script>
</body></html>
"""

HELPER_SCRIPT = """(async () => {
  const log = async (text) => { try { await chrome.storage.session.set({ helperLog: text }); } catch {} };
  await log('loaded');
  try {
    const stored = await chrome.storage.session.get({ probeMarkdown: '', probeFilename: 'probe.md' });
    await log('storage: ' + JSON.stringify(Object.keys(stored)));
    const blob = new Blob([String(stored.probeMarkdown)], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = String(stored.probeFilename);
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    await log('clicked');
    setTimeout(() => URL.revokeObjectURL(url), 120000);
  } catch (error) {
    await log('error: ' + String(error));
  }
})();
"""


def prepare_extension_copy(dest: Path) -> None:
    for name in [
        "manifest.json", "popup.html", "popup.css", "popup.js",
        "content.js", "page-bridge.js",
    ]:
        shutil.copy2(ROOT / name, dest / name)

    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    manifest["web_accessible_resources"] = [{
        "resources": ["popup.html", "offscreen.html"],
        "matches": ["<all_urls>"],
    }]
    manifest["background"] = {"service_worker": "background.js"}
    (dest / "background.js").write_text(PROBE_BACKGROUND, encoding="utf-8")
    manifest["permissions"] = sorted(set(manifest.get("permissions", []) + ["storage"]))
    (dest / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (dest / "helper.html").write_text(HELPER_PAGE, encoding="utf-8")
    (dest / "helper.js").write_text(HELPER_SCRIPT, encoding="utf-8")


def wait_for_new_file(directory: Path, before: set, timeout_s: float = 15.0):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        current = {p.name for p in directory.iterdir()}
        new = current - before
        if new:
            time.sleep(0.5)
            for name in sorted(new):
                path = directory / name
                if path.exists():
                    return path
        time.sleep(0.3)
    raise AssertionError(f"no new file within {timeout_s}s in {directory}: "
                         f"{sorted(p.name for p in directory.iterdir())}")


class MarkdownHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        payload = "# http served markdown\n".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


def main() -> None:
    channel = sys.argv[1] if len(sys.argv) > 1 else "chromium"
    server = HTTPServer(("127.0.0.1", 0), MarkdownHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    http_url = f"http://127.0.0.1:{server.server_port}/served-report.md"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        ext_dir = tmp_path / "ext"
        ext_dir.mkdir()
        prepare_extension_copy(ext_dir)
        downloads = tmp_path / "downloads"
        downloads.mkdir()
        profile = tmp_path / "profile"

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                str(profile),
                channel=channel,
                headless=False,
                args=[
                    f"--disable-extensions-except={ext_dir}",
                    f"--load-extension={ext_dir}",
                ],
            )
            try:
                boot = context.new_page()
                boot.goto("chrome://extensions")
                deadline = time.time() + 20
                worker = None
                while time.time() < deadline:
                    for sw in context.service_workers:
                        if sw.url.startswith("chrome-extension://"):
                            worker = sw
                            break
                    if worker:
                        break
                    time.sleep(0.3)
                boot.close()
                assert worker, "extension service worker never started"
                ext_id = re.match(r"chrome-extension://([a-p]{32})/", worker.url).group(1)
                print(f"[{channel}] extension id:", ext_id)

                page = context.new_page()
                page.goto(f"chrome-extension://{ext_id}/popup.html", wait_until="domcontentloaded")
                page.wait_for_function("typeof triggerNamedDownload === 'function'")

                version_page = context.new_page()
                version_page.goto("chrome://version")
                cmdline = version_page.evaluate("document.title")  # placeholder
                cmdline = version_page.evaluate(
                    "() => document.querySelector('#command_line') ? "
                    "document.querySelector('#command_line').textContent : document.body.innerText.slice(0, 2000)")
                version_page.close()
                print("command line flags with 'download':",
                      [seg for seg in str(cmdline).split() if "ownload" in seg] or "(none)")

                cdp = context.browser.new_browser_cdp_session()
                cdp.send("Browser.setDownloadBehavior", {
                    "behavior": "allow",
                    "downloadPath": str(downloads),
                    "eventsEnabled": False,
                })

                def trigger(js: str, arg, label: str):
                    before = {q.name for q in downloads.iterdir()}
                    try:
                        page.evaluate(js, arg)
                        got = wait_for_new_file(downloads, before)
                    except AssertionError as error:
                        print(f"{label} -> FAILED: {error}")
                        return None
                    print(f"{label} -> {got.name}")
                    return got

                # 每个变体独立跑（--only X）：Chrome 对无手势自动下载有节流，
                # 同一页面连续多次下载会让后续变体静默失败、互相污染结论。
                only = None
                for idx, arg in enumerate(sys.argv):
                    if arg == "--only":
                        only = sys.argv[idx + 1].upper()

                def run_variant(key: str, fn) -> None:
                    if only and only != key:
                        return
                    fn()

                def variant_e():
                    trigger(
                        """async (payload) => {
                            await chrome.downloads.download({
                                url: payload.url,
                                filename: payload.filename,
                                saveAs: false,
                                conflictAction: 'overwrite',
                            });
                        }""",
                        {"url": http_url, "filename": PROBE_FILENAME},
                        "E) http URL + downloads(filename)      ",
                    )

                def variant_f():
                    trigger(
                        """async (filename) => {
                            const blob = new Blob(['# popup anchor'], { type: 'text/markdown;charset=utf-8' });
                            const url = URL.createObjectURL(blob);
                            const anchor = document.createElement('a');
                            anchor.href = url;
                            anchor.download = filename;
                            document.body.appendChild(anchor);
                            anchor.click();
                            anchor.remove();
                        }""",
                        PROBE_FILENAME,
                        "F) popup anchor download attribute     ",
                    )

                def variant_j():
                    trigger(
                        """async (payload) => {
                            await chrome.storage.session.set({
                                probeMarkdown: '# helper tab probe',
                                probeFilename: payload.filename,
                                helperLog: 'reset',
                            });
                            await chrome.tabs.create({ url: 'helper.html', active: true });
                        }""",
                        {"filename": PROBE_FILENAME},
                        "J) helper tab (active) anchor download  ",
                    )

                def variant_k():
                    trigger(
                        """async (payload) => {
                            const base64 = btoa(String.fromCharCode(
                              ...new TextEncoder().encode('# data url anchor probe 中文')
                            ));
                            const anchor = document.createElement('a');
                            anchor.href = 'data:text/markdown;charset=utf-8;base64,' + base64;
                            anchor.download = payload.filename;
                            document.body.appendChild(anchor);
                            anchor.click();
                            anchor.remove();
                        }""",
                        {"filename": PROBE_FILENAME},
                        "K) popup anchor + data URL               ",
                    )

                def variant_p():
                    # 生产代码路径：直接调用 popup.js 里的真实函数
                    trigger(
                        """async () => {
                            const filename = buildDownloadFilename(
                                { title: '6a77363c-0f05-4a0d-b321-04b3231b080b' },
                                { title: 'gpt-生产验证报告' },
                            );
                            window.__probeFilename = filename;
                            triggerNamedDownload(
                                buildDownloadDataUrl('# 生产验证\\n\\ncontent'),
                                filename,
                            );
                        }""",
                        None,
                        "P) PRODUCTION buildDownloadFilename + anchor",
                    )
                    time.sleep(0.2)
                    prod_name = page.evaluate("window.__probeFilename")
                    print("P) production filename:", prod_name)

                run_variant("E", variant_e)
                run_variant("F", variant_f)
                run_variant("J", variant_j)
                run_variant("K", variant_k)
                run_variant("P", variant_p)

                print()
                print(f"expected: {PROBE_FILENAME!r}")
            finally:
                context.close()
                server.shutdown()


if __name__ == "__main__":
    main()
