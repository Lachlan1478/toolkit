from __future__ import annotations
import os, re, time, json, threading
from pathlib import Path
from typing import Optional, Tuple

from loguru import logger
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# Config via env (with sensible defaults/overrides)
BASE44_URL = os.getenv("BASE44_URL", "https://app.base44.com").rstrip("/")
BASE44_EMAIL = os.getenv("BASE44_EMAIL", "")
BASE44_PASSWORD = os.getenv("BASE44_PASSWORD", "")
BASE44_TOTP_SECRET = os.getenv("BASE44_TOTP_SECRET", "")  # optional, if MFA


# Selectors (override via env if the UI changes)
SEL_LOGIN_EMAIL = os.getenv("BASE44_SEL_LOGIN_EMAIL", 'input[name="email"]')
SEL_LOGIN_PASSWORD = os.getenv("BASE44_SEL_LOGIN_PASSWORD", 'input[name="password"]')
SEL_LOGIN_SUBMIT = os.getenv("BASE44_SEL_LOGIN_SUBMIT", 'button:has-text("Sign in")')
SEL_TOTP_INPUT = os.getenv("BASE44_SEL_TOTP_INPUT", 'input[autocomplete="one-time-code"]')
SEL_TOTP_SUBMIT = os.getenv("BASE44_SEL_TOTP_SUBMIT", 'button:has-text("Verify")')

# Builder page widgets
SEL_SPEC_TEXTAREA = os.getenv("BASE44_SEL_SPEC_TEXTAREA", 'textarea, [contenteditable="true"]')
SEL_GENERATE_BUTTON = os.getenv("BASE44_SEL_GENERATE_BUTTON", 'button:has-text("Generate"), button:has-text("Build")')
SEL_PREVIEW_LINK = os.getenv("BASE44_SEL_PREVIEW_LINK", 'a:has-text("Preview"), a[href*="/preview/"]')

# Big builder input (by placeholder text is most stable)
SEL_SPEC_INPUT_PLACEHOLDER = os.getenv(
    "BASE44_SEL_SPEC_INPUT_PH",
    r"Describe the app you want to create"  # partial, case-insensitive
)

# Submit button candidates (fallback to “button in same card”)
SEL_SUBMIT_BUTTONS = os.getenv(
    "BASE44_SEL_SUBMIT_BUTTONS",
    'button:has-text("Generate"), button:has-text("Build"), button:has-text("Create"), button[aria-label*="Generate" i], button[aria-label*="Submit" i]'
)

# Keep this:
SEL_PREVIEW_LINK = os.getenv("BASE44_SEL_PREVIEW_LINK", 'a:has-text("Preview"), a[href*="/preview/"]')

# Where to persist session
USER_DATA_DIR = os.getenv("PW_USER_DATA_DIR", "/usr/src/app/.pw-user-data")
STORAGE_STATE = os.path.join(USER_DATA_DIR, "storage_state.json")

DASH_URL_SNIPPETS = ["/dashboard", "/home", "/projects", "/apps"]

ARTIFACT_DIR = Path.cwd() / "artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)

_lock = threading.Lock()  # simple cross-thread guard

class Base44Bot:
    def __init__(self, headless: bool = False):
        # runtime evaluation so env set before import isn't required
        self.headless = headless
        # slow_mo is also read at runtime
        self._slow_mo_ms = int(os.getenv("BASE44_SLOW_MO_MS", "0"))
        self._p = None
        self._browser = None          # type: ignore
        self._context = None          # type: ignore
        self._page = None
        print(f"headless: {self.headless}")

    def __enter__(self):
        self._p = sync_playwright().start()

        storage_path = os.getenv("BASE44_STORAGE_STATE", "storage_state.json")
        user_data_dir = os.getenv("BASE44_USER_DATA_DIR", "")     # if set -> persistent
        channel       = os.getenv("BASE44_BROWSER_CHANNEL", None) # "chrome" | "msedge" | None
        profile_dir   = os.getenv("BASE44_PROFILE_DIR", "Default")

        if user_data_dir:
            # PERSISTENT CONTEXT PATH: returns a BrowserContext directly.
            self._context = self._p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel=channel,
                headless=self.headless,
                args=[f"--profile-directory={profile_dir}"] if profile_dir else None,
            )
            self._page = self._context.new_page()
        else:
            # NORMAL PATH: launch Browser, then make a new_context (optionally from storage_state)
            self._browser = self._p.chromium.launch(headless=self.headless)
            if Path(storage_path).exists():
                self._context = self._browser.new_context(storage_state=storage_path)
            else:
                self._context = self._browser.new_context()
            self._page = self._context.new_page()

        return self

    def __exit__(self, exc_type, exc, tb):
        # Only save storage_state when *not* using a live persistent profile
        storage_path = os.getenv("BASE44_STORAGE_STATE", "storage_state.json")
        if not os.getenv("BASE44_USER_DATA_DIR") and self._context:
            try:
                self._context.storage_state(path=storage_path)
            except Exception:
                pass
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
        finally:
            if self._p:
                self._p.stop()
        return False

    # ---------- Auth ----------
    def ensure_logged_in(self):
        """Assume session-based auth. If the builder box is visible, we're logged in."""
        page = self._page
        page.set_default_timeout(30000)
        page.goto(BASE44_URL + "/", wait_until="domcontentloaded")

        # 1) Prefer the big builder input by placeholder text
        try:
            box = page.get_by_placeholder(re.compile(r"Describe the app you want to create", re.I))
            box.wait_for(state="visible", timeout=5000)
            # persist session for next runs
            try: self._context.storage_state(path="storage_state.json")
            except Exception: pass
            return
        except Exception:
            pass

        # 2) Fallback: any textarea/contenteditable visible
        try:
            page.locator(SEL_SPEC_TEXTAREA).first.wait_for(state="visible", timeout=5000)
            try: self._context.storage_state(path="storage_state.json")
            except Exception: pass
            return
        except Exception:
            ss = ARTIFACT_DIR / "login_missing_builder.png"
            try: page.screenshot(path=str(ss), full_page=True)
            except Exception: pass
            raise RuntimeError(
                f"Builder not visible (likely not logged in). Screenshot: {ss}. "
                "Log in once and re-seed storage_state.json or run with a persistent profile."
            )

    def _is_logged_in(self) -> bool:
        # Minimal heuristic: some known element exists when logged in
        # If the builder has a spec textarea, that’s a good indicator
        try:
            self._page.wait_for_selector(SEL_SPEC_TEXTAREA, timeout=4000)
            return True
        except PWTimeout:
            return False

    def _totp_code(self) -> str:
        import pyotp  # installed in Dockerfile
        return pyotp.TOTP(BASE44_TOTP_SECRET).now()

    # ---------- Build ----------
    def build_from_spec(self, spec_text: str) -> Tuple[str, str]:
        """
        Paste spec_text on the builder page, submit, and return (app_id, preview_url).
        """
        self.ensure_logged_in()

        print("Building from Spec")

        page = self._page
        page.goto(f"{BASE44_URL}/", wait_until="domcontentloaded")

        # Find the big text area by placeholder; fall back to textarea/contenteditable
        input_loc = None
        try:
            input_loc = page.get_by_placeholder(re.compile(SEL_SPEC_INPUT_PLACEHOLDER, re.I))
            input_loc.wait_for(state="visible", timeout=15000)
        except Exception:
            # Fallback to your generic selector
            input_loc = page.locator('textarea, [contenteditable="true"]').first
            input_loc.wait_for(state="visible", timeout=15000)

        # Clear then type (works for both textarea and contenteditable in most UIs)
        try:
            tag = page.evaluate("(el) => el.tagName && el.tagName.toLowerCase()", input_loc.element_handle())
        except Exception:
            tag = None

        if tag in ("textarea", "input"):
            input_loc.fill("")  # clear
            input_loc.fill(spec_text)
        else:
            # contenteditable path
            page.evaluate(
                "(el, txt) => { el.focus(); el.innerText=''; el.dispatchEvent(new Event('input',{bubbles:true})); }",
                input_loc.element_handle()
            )
            input_loc.type(spec_text, delay=1)

        # --- submit (icon-first & minimal) ---
        submitted = False

        # 1) Click the icon-only button inside the same container as the input
        try:
            container = input_loc.locator(
                "xpath=ancestor::*[(self::div or self::section)][.//textarea or .//*[@contenteditable='true']][1]"
            )
            # any clickable with an SVG icon (covers the orange arrow)
            icon_btns = container.locator("button:has(svg), [role='button']:has(svg), a:has(svg)")
            if icon_btns.count() > 0:
                b = icon_btns.first
                b.scroll_into_view_if_needed()
                b.wait_for(state="visible", timeout=3000)
                b.click(timeout=5000)
                submitted = True
        except Exception:
            pass

        # 2) Keyboard fallback: Ctrl/Cmd + Enter
        if not submitted:
            try:
                mod = "Control" if os.name == "nt" else "Meta"
                input_loc.press(f"{mod}+Enter")
                submitted = True
            except Exception:
                pass

        # 3) Last resort: try any global icon button (sometimes the arrow is outside the card)
        if not submitted:
            try:
                gbtn = self._page.locator("button:has(svg), [role='button']:has(svg), a:has(svg)").first
                gbtn.scroll_into_view_if_needed()
                gbtn.click(timeout=5000)
                submitted = True
            except Exception:
                pass

        # 4) Plain Enter as final fallback
        if not submitted:
            try:
                input_loc.press("Enter")
                submitted = True
            except Exception:
                pass

        if not submitted:
            ss = ARTIFACT_DIR / "submit_failed.png"
            try: self._page.screenshot(path=str(ss), full_page=True)
            except Exception: pass
            raise RuntimeError(f"Could not submit spec. Screenshot: {ss}")

        # Wait for preview to appear or a new tab to open with /preview/
        preview_url = self._wait_for_preview_url()

        app_id = self._extract_app_id(preview_url) or ("unknown_" + str(int(time.time())))
        return app_id, preview_url

    def _wait_for_preview_url(self, timeout_ms: int = 180000) -> str:
        deadline = time.time() + (timeout_ms / 1000.0)

        while time.time() < deadline:
            # 1) DOM link
            try:
                link = self._page.locator(SEL_PREVIEW_LINK).first
                if link.is_visible():
                    href = link.get_attribute("href")
                    if href and "preview" in href:
                        return href if href.startswith("http") else (BASE44_URL + href)
            except PWTimeout:
                pass
            except Exception:
                pass

            # 2) Any page with /preview/
            for p in self._context.pages:
                url = p.url or ""
                if "/preview/" in url:
                    return url

            time.sleep(1.0)

        raise TimeoutError("Timed out waiting for preview URL")

    def _extract_app_id(self, preview_url: str) -> Optional[str]:
        # Heuristic: /preview/<app_id> or query param ?app_id=...
        m = re.search(r"/preview/([a-zA-Z0-9_-]+)", preview_url)
        if m:
            return m.group(1)
        m = re.search(r"[?&]app_id=([a-zA-Z0-9_-]+)", preview_url)
        if m:
            return m.group(1)
        return None
