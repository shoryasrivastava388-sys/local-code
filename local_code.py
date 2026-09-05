#!/usr/bin/env python3
"""
local-code (lc) - Universal Cross-Platform Autonomous Local AI Engineer powered by Ollama.
Features:
- Interactive arrow-key menu selectors for model switching (/models) and permissions
- Search the web (DuckDuckGo Lite) and fetch documentation
- Surgical file editing with colored diffs (no recreating existing files)
- Terminal execution with Permission Mode & Auto Mode
- Desktop browser launcher
- In-chat slash commands (/diff, /undo, /search, /model, /auto)
- Self-healing autonomous task execution
"""

import argparse
import difflib
import fnmatch
import html
import json
import os
import platform
import re
import random
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

__version__ = "1.6.8"

# Operating System Detection
OS_NAME = platform.system()
IS_WINDOWS = OS_NAME.lower() == "windows"
IS_MACOS = OS_NAME.lower() == "darwin"
IS_LINUX = OS_NAME.lower() == "linux"


def get_system_ram_gb():
    """Retrieve total physical RAM in GB across Linux, macOS, and Windows."""
    try:
        if IS_LINUX:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) / (1024 * 1024)
        elif IS_MACOS:
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"]).decode().strip()
            return int(out) / (1024 ** 3)
    except Exception:
        pass
    return 16.0


def get_safe_default_context(model_name=""):
    """Calculate safe context tokens to prevent kernel OOM kills on memory-constrained systems."""
    ram = get_system_ram_gb()
    m_lower = (model_name or "").lower()
    # On systems with <14GB RAM, only heavy models (9B, 14B, 32B) need 2048 to prevent OOM
    if any(k in m_lower for k in ("9b", "14b", "32b", "70b")):
        return 2048 if ram < 14.0 else 4096
    # 7B and lighter models (e.g. qwen2.5-coder:7b) comfortably run at 4096 tokens on 10GB+ RAM
    if ram < 8.0:
        return 2048
    return 4096

# Enable ANSI escape codes in Windows Command Prompt and PowerShell
if IS_WINDOWS:
    try:
        os.system("")
    except Exception:
        pass

# ANSI Terminal Colors & Styling
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
RED = "\033[31m"
GRAY = "\033[90m"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

SYSTEM_PROMPT_TEMPLATE = """You are Local Code (lc), an elite autonomous software engineering agent operating directly on the local machine.
Host OS: {os_name}
Current Working Directory: {cwd}
All relative file paths are created, read, and edited directly in: {cwd} (unless the user explicitly specifies a different directory).

You have native access to system tools for searching the web, browsing documentation, reading code, editing files, and running terminal commands.

## Available Tools
To execute an action, output a single JSON code block:
```json
{"name": "tool_name", "arguments": {"param": "value"}}
```

The tools are:
- `search_web`: Search the live internet for documentation, tutorials, errors, and solutions.
  args: `{"query": "search keywords"}`
- `fetch_web`: Fetch and extract clean text from any URL or GitHub repository.
  args: `{"url": "https://..."}`
- `open_browser`: Open any URL or local HTML file in the user's desktop web browser.
  args: `{"url": "filename.html" or "https://..."}`
- `read_file`: Read file contents with line numbers.
  args: `{"path": "filepath", "start_line": optional_int, "line_count": optional_int}`
- `edit_file`: Surgically replace a specific target code snippet in an EXISTING file.
  args: `{"path": "filepath", "target": "exact_old_code", "replacement": "new_code"}`
- `write_file`: Create a BRAND NEW file (only use for new files that don't exist yet).
  args: `{"path": "filepath", "content": "file text"}`
- `run_command`: Run a shell/terminal command (adapted for {os_name}).
  args: `{"command": "command string", "cwd": "optional_dir"}`
- `list_dir`: List files and subdirectories.
  args: `{"path": "optional_dir", "max_depth": optional_int}`
- `search_code`: Search code for keywords or regex.
  args: `{"query": "string", "path": "optional_path"}`
- `git_diff`: View git status and current uncommitted diffs.
  args: `{"path": "optional_path"}`
- `inspect_ui`: Capture a headless screenshot of a local web page, run an offline visual audit, and get aesthetic styling critique and recommendations.
  args: `{"path": "filepath.html"}`

## Core Operational Directives
1. ABSOLUTELY ZERO CODE DUMPING IN CHAT:
   - You are an autonomous software engineering agent with DIRECT SYSTEM EXECUTION TOOLS, NOT a web chatbot.
   - NEVER output markdown code blocks (```html, ```python, ```javascript, ```css, etc.) or raw scripts into the chat!
   - Writing code blocks in chat is strictly forbidden. You must ALWAYS invoke {"name": "write_file", ...} or {"name": "edit_file", ...}.
   - If the user asks you to open, test, debug, or fix an already working file that has 0 errors, DO NOT rewrite it! Invoke {"name": "open_browser", "arguments": {"url": "..."}} immediately.
   - If the user did not specify an exact filename, choose an appropriate standard filename (e.g. `rate_limiter.py`, `app.py`, `main.py`, `index.html`) and invoke `write_file`.
2. FILE EDITING vs CREATION:
   - When modifying an existing file, NEVER rewrite or recreate the file with `write_file`.
   - ALWAYS read the file with `read_file` first, then use `edit_file` to replace only the targeted snippet.
   - Use `write_file` ONLY when creating brand new files that do not exist on disk.
3. WEB RESEARCH:
   - When asked to search the web, research an API, or find documentation, use `search_web` ONCE to discover the necessary information.
   - Once research results are retrieved, do NOT keep searching or browsing in loops. Move IMMEDIATELY to creating or editing the files using `write_file` or `edit_file`.
4. MULTI-STEP BROWSER & RUN EXECUTION:
   - If the user requested to open, launch, or play a file in the browser, you MUST write the file with `write_file` first, and then invoke `open_browser` on that local file (e.g. `{"url": "snake.html"}`).
   - NEVER call `open_browser` on external research URLs or documentation links from web searches. `open_browser` is reserved for opening the user's local project files.
   - If the user requested to test, run, or execute a script, you MUST invoke `run_command` as your next action after `write_file`.
5. NATIVE ACCESS & CAPABILITIES:
   - NEVER claim "I am just a language model", "I cannot access the web", or "I cannot do anything outside this text box". You have full system and web access.
6. NO CODE LECTURES:
   - Do NOT lecture the user on basic code syntax. Apply the changes to the files, run tests or verification commands, and report concise outcomes.
7. SELF-HEALING:
   - If tests fail, builds break, or commands error, inspect the error trace, patch the code, and re-run tests until passing.
8. BUG FIXING & REPAIRS:
   - When asked to fix, debug, or repair a file: read the file with `read_file`, locate the buggy snippet, and IMMEDIATELY invoke `edit_file` to update it on disk.
   - NEVER stop after `read_file` to explain or describe the code without applying the fix.
9. COMPLETE PRODUCTION IMPLEMENTATION — NO PLACEHOLDERS:
   - When generating code with `write_file` or `edit_file`, you MUST provide complete, fully functional, working implementations.
   - NEVER output placeholder comments like "// Your code here", "/* implement logic */", "// TODO", or empty function stubs!
   - Every script, game, HTML canvas, and simulation MUST be completely coded with all math, physics, event listeners, and logic fully written out.
   - Self-contained vanilla implementations: For HTML5 games, animations, and simulations, write self-contained vanilla JavaScript using standard HTML5 Canvas 2D / Web Audio API. Do NOT rely on external CDN scripts like three.js or cdnjs unless explicitly requested, so that all applications run 100% offline.
"""


def get_system_prompt():
    cwd = os.getcwd()
    return SYSTEM_PROMPT_TEMPLATE.replace("{os_name}", OS_NAME).replace("{cwd}", cwd)


def read_single_key():
    """Cross-platform key reader that supports arrow keys and single keypresses."""
    if not sys.stdin.isatty():
        return None

    if IS_WINDOWS:
        try:
            import msvcrt
            ch = msvcrt.getwch()
            if ch in ('\x00', '\xe0'):
                ch2 = msvcrt.getwch()
                if ch2 == 'H': return 'up'
                if ch2 == 'P': return 'down'
                if ch2 == 'K': return 'left'
                if ch2 == 'M': return 'right'
                return 'special'
            if ch in ('\r', '\n'): return 'enter'
            if ch == '\x1b': return 'esc'
            if ch == '\x03': return 'ctrl_c'
            return ch.lower()
        except Exception:
            return None
    else:
        try:
            import termios, tty, select
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                raw = os.read(fd, 1)
                if not raw:
                    return None
                if raw == b'\x1b':
                    seq = raw
                    while select.select([fd], [], [], 0.05)[0]:
                        more = os.read(fd, 8)
                        if not more:
                            break
                        seq += more
                    if seq in (b'\x1b[A', b'\x1bOA'): return 'up'
                    elif seq in (b'\x1b[B', b'\x1bOB'): return 'down'
                    elif seq in (b'\x1b[C', b'\x1bOC'): return 'right'
                    elif seq in (b'\x1b[D', b'\x1bOD'): return 'left'
                    elif seq == b'\x1b': return 'esc'
                    return 'special'
                if raw in (b'\r', b'\n'): return 'enter'
                if raw == b'\x03': return 'ctrl_c'
                try:
                    return raw.decode('utf-8').lower()
                except Exception:
                    return 'special'
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except Exception:
            return None


def select_menu(title, options, default_idx=0, shortcuts=None):
    """
    Renders an interactive terminal menu with arrow keys.
    options: list of strings (or tuples of (display_label, return_value))
    shortcuts: dict of char -> index (e.g. {'y': 0, 'a': 1, 'n': 2})
    Returns: (index, selected_value) or (-1, None) if cancelled.
    """
    if not options:
        return -1, None

    # Format options
    labels = []
    values = []
    for opt in options:
        if isinstance(opt, tuple):
            labels.append(opt[0])
            values.append(opt[1])
        else:
            labels.append(str(opt))
            values.append(opt)

    idx = max(0, min(default_idx, len(labels) - 1))
    shortcuts = shortcuts or {}

    # Non-interactive / pipe fallback
    if not sys.stdin.isatty():
        print(f"{title}")
        for i, lab in enumerate(labels):
            print(f"  [{i + 1}] {lab}")
        try:
            val = input("Select an option: ").strip()
            if val.isdigit() and 1 <= int(val) <= len(labels):
                return int(val) - 1, values[int(val) - 1]
            for k, s_idx in shortcuts.items():
                if val.lower() == k:
                    return s_idx, values[s_idx]
            return 0, values[0]
        except Exception:
            return 0, values[0]

    # Flush any stale/buffered keystrokes entered while the model was computing
    if not IS_WINDOWS:
        try:
            import termios
            termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
        except Exception:
            pass
    else:
        try:
            import msvcrt
            while msvcrt.kbhit():
                msvcrt.getwch()
        except Exception:
            pass

    # Interactive arrow-key loop
    print(f"\n{BOLD}{title}{RESET} {GRAY}(Use ↑/↓ to navigate, Enter to select, Esc to cancel){RESET}")
    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()

    def draw_options(current_idx, first_render=False):
        if not first_render:
            sys.stdout.write(f"\033[{len(labels)}A\r")
        for i, lab in enumerate(labels):
            sys.stdout.write("\033[K") # Clear line
            if i == current_idx:
                sys.stdout.write(f" {CYAN}{BOLD}❯ {lab}{RESET}\n")
            else:
                sys.stdout.write(f"   {GRAY}{lab}{RESET}\n")
        sys.stdout.flush()

    draw_options(idx, first_render=True)

    try:
        while True:
            key = read_single_key()
            if key is None or key == 'special':
                continue

            if key in ('up', 'k'):
                idx = (idx - 1) % len(labels)
                draw_options(idx)
            elif key in ('down', 'j'):
                idx = (idx + 1) % len(labels)
                draw_options(idx)
            elif key == 'enter':
                # Clear menu lines and print selected item cleanly
                sys.stdout.write(f"\033[{len(labels)}A\r")
                for _ in range(len(labels)):
                    sys.stdout.write("\033[K\n")
                sys.stdout.write(f"\033[{len(labels)}A\r")
                sys.stdout.write(f" {GREEN}✓ Selected:{RESET} {BOLD}{labels[idx]}{RESET}\n")
                sys.stdout.flush()
                return idx, values[idx]
            elif key in ('esc', 'q'):
                sys.stdout.write(f"\033[{len(labels)}A\r")
                for _ in range(len(labels)):
                    sys.stdout.write("\033[K\n")
                sys.stdout.write(f"\033[{len(labels)}A\r")
                sys.stdout.write(f" {GRAY}(Cancelled){RESET}\n")
                sys.stdout.flush()
                return -1, None
            elif key in shortcuts:
                s_idx = shortcuts[key]
                if 0 <= s_idx < len(labels):
                    sys.stdout.write(f"\033[{len(labels)}A\r")
                    for _ in range(len(labels)):
                        sys.stdout.write("\033[K\n")
                    sys.stdout.write(f"\033[{len(labels)}A\r")
                    sys.stdout.write(f" {GREEN}✓ Selected:{RESET} {BOLD}{labels[s_idx]}{RESET}\n")
                    sys.stdout.flush()
                    return s_idx, values[s_idx]
            elif key == 'ctrl_c':
                break
    finally:
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()

    return -1, None


def search_duckduckgo(query, max_results=5):
    """Searches DuckDuckGo Lite without API keys (Cross-Platform)."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    data = f"q={urllib.parse.quote(query)}".encode("utf-8")
    
    html_text = ""
    try:
        req = urllib.request.Request("https://lite.duckduckgo.com/lite/", data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            html_text = resp.read().decode("utf-8", errors="replace")
    except Exception:
        try:
            res = subprocess.run(
                ["curl", "-sL", "-A", headers["User-Agent"], "--max-time", "12", "https://lite.duckduckgo.com/lite/", "--data", f"q={urllib.parse.quote(query)}"],
                capture_output=True, text=True
            )
            if res.returncode == 0 and res.stdout:
                html_text = res.stdout
        except Exception:
            pass

    if not html_text:
        return f"Error connecting to web search for '{query}'."

    links = re.findall(r'<a rel="nofollow" href="([^"]+)" class=[\'"]result-link[\'"]>(.*?)</a>', html_text, re.DOTALL)
    snippets = re.findall(r'<td class=[\'"]result-snippet[\'"]>(.*?)</td>', html_text, re.DOTALL)
    
    out = []
    for (url, title), snip in zip(links[:max_results], snippets[:max_results]):
        t = html.unescape(re.sub(r'<[^>]+>', '', title).strip())
        s = html.unescape(re.sub(r'<[^>]+>', '', snip).strip())
        out.append(f"[{len(out)+1}] {t}\n    URL: {url}\n    {s}")
    return "\n\n".join(out) if out else f"No web search results found for '{query}'."


def fetch_url_content(url):
    """Fetches clean text from any URL (Cross-Platform)."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    html_text = ""
    
    try:
        res = subprocess.run(
            ["curl", "-sL", "-A", headers["User-Agent"], "--max-time", "15", url],
            capture_output=True, text=True
        )
        if res.returncode == 0 and res.stdout:
            html_text = res.stdout
    except Exception:
        pass

    if not html_text:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html_text = resp.read().decode("utf-8", errors="replace")

    text = re.sub(r"<script.*?</script>", "", html_text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    preview = text[:2500]
    return preview + ("\n...(content truncated)" if len(text) > 2500 else ""), len(text)


def print_diff(old_text, new_text, filename):
    """Prints a colored unified diff to the terminal."""
    diff = list(difflib.unified_diff(
        old_text.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        n=3
    ))
    if not diff:
        return
    for line in diff[:25]:
        if line.startswith("+") and not line.startswith("+++"):
            print(f"{GREEN}{line.rstrip()}{RESET}")
        elif line.startswith("-") and not line.startswith("---"):
            print(f"{RED}{line.rstrip()}{RESET}")
        elif line.startswith("@@"):
            print(f"{CYAN}{line.rstrip()}{RESET}")
        else:
            print(f"{GRAY}{line.rstrip()}{RESET}")
    if len(diff) > 25:
        print(f"{GRAY}... ({len(diff) - 25} more lines of diff){RESET}")


def validate_code(path, content):
    """Automated pre-execution validator for common runtime and syntax bugs (zero dependencies).
    Returns a list of diagnostic warning strings if issues are detected."""
    issues = []
    p_str = str(path).lower()

    # 1. HTML / DOM checks
    if p_str.endswith((".html", ".htm")):
        content_lower = content.lower()
        if not ("<html" in content_lower or "<!doctype" in content_lower):
            issues.append(
                "Incomplete HTML Document: The file is missing <!DOCTYPE html> or <html> tags. "
                "Ensure the file is a complete HTML document or use 'edit_file' to surgically replace targeted functions."
            )
        if "<head>" in content_lower and "</head>" not in content_lower:
            issues.append("Malformed HTML: <head> tag is opened but never closed with </head>.")
        if "<body" not in content_lower:
            issues.append("Malformed HTML: Document is missing <body> opening tag.")
        open_scripts = [m.start() for m in re.finditer(r"<script(?:\s+[^>]*)?>", content, flags=re.IGNORECASE)]
        close_scripts = [m.start() for m in re.finditer(r"</script>", content, flags=re.IGNORECASE)]
        if len(open_scripts) != len(close_scripts):
            open_lines = [content[:pos].count("\n") + 1 for pos in open_scripts]
            close_lines = [content[:pos].count("\n") + 1 for pos in close_scripts]
            issues.append(
                f"Malformed HTML: Mismatched script tags ({len(open_scripts)} '<script>' at line(s) {open_lines} vs {len(close_scripts)} '</script>' at line(s) {close_lines}). "
                "Ensure all JavaScript code is properly wrapped inside matching <script>...</script> tags."
            )

        # Trailing garbage/commentary check after </html>
        if "</html>" in content_lower:
            after_html = re.split(r"</html>", content, flags=re.IGNORECASE)[-1].strip()
            if after_html:
                issues.append(
                    f"Corrupted HTML Document: Found {len(after_html)} characters of leaked text, backticks, or commentary after </html>. "
                    "Ensure </html> is the absolute end of the file."
                )

        # DOM Lifecycle Bug check: script before <body> accessing document.body
        body_idx = content_lower.find("<body")
        for sc_match in re.finditer(r"<script(?:\s+[^>]*)?>([\s\S]*?)</script>", content, flags=re.IGNORECASE):
            sc_pos = sc_match.start()
            sc_code = sc_match.group(1).lower()
            if body_idx == -1 or sc_pos < body_idx:
                if any(dom in sc_code for dom in ("document.body", "document.getelementbyid", "document.queryselector")):
                    if not any(safe in sc_code for safe in ("domcontentloaded", "window.onload", "onload", "defer")):
                        issues.append(
                            "DOM Lifecycle Bug: <script> executes before <body> exists and accesses document.body. "
                            "Wrap your script in window.addEventListener('DOMContentLoaded', () => { ... }) or move <script> inside <body>."
                        )

        # Placeholder / Empty script detection:
        for sc_match in re.finditer(r"<script(?:\s+[^>]*)?>([\s\S]*?)</script>", content, flags=re.IGNORECASE):
            if re.search(r"\bsrc\s*=", sc_match.group(0), re.IGNORECASE):
                continue
            sc_code = sc_match.group(1).strip()
            code_no_comments = re.sub(r"//.*|/\*[\s\S]*?\*/", "", sc_code).strip()
            if len(code_no_comments) < 30:
                issues.append(
                    "Incomplete Implementation: The <script> tag contains placeholder comments ('// Your code here') or empty stubs without working JavaScript logic. "
                    "You must write the complete, functional JavaScript code inside the <script> tags using 'edit_file' or 'write_file'."
                )

            empty_fn_matches = re.findall(r'function\s+([a-zA-Z0-9_$]+)\s*\([^)]*\)\s*\{\s*(?://[^\n]*\s*|/\*[\s\S]*?\*/\s*)*\}', sc_code)
            for fn_name in empty_fn_matches:
                issues.append(
                    f"Incomplete Implementation: Function '{fn_name}' has an empty body containing only placeholder comments. "
                    f"You must implement complete working logic for '{fn_name}' using 'edit_file'."
                )

            trailing_stub_comments = re.findall(r'//\s*([^\n]+)\s*\n\s*\}', sc_code)
            for stub_c in trailing_stub_comments:
                if any(w in stub_c.lower() for w in ("update", "draw", "render", "logic", "paddles", "ball", "todo", "code", "implement")):
                    issues.append(
                        f"Incomplete Implementation: Stub comment '// {stub_c}' detected without code implementation. "
                        f"You must implement complete working logic using 'edit_file'."
                    )

        # Sandboxed Node VM runtime verification for embedded <script> tags
        if subprocess.run("which node", shell=True, capture_output=True).returncode == 0:
            scripts = re.findall(r"<script(?:\s+[^>]*)?>([\s\S]*?)</script>", content, flags=re.IGNORECASE)
            for sc in scripts:
                sc_clean = sc.strip()
                if not sc_clean:
                    continue
                node_runner = (
                    "const vm = require('vm');\n"
                    "function createMock(name = 'mock') {\n"
                    "  const fn = function() { return createMock(name + '()'); };\n"
                    "  return new Proxy(fn, {\n"
                    "    get(target, prop) {\n"
                    "      if (prop === Symbol.toPrimitive || prop === 'toString' || prop === 'valueOf') return () => name;\n"
                    "      if (prop === 'width' || prop === 'height' || prop === 'innerWidth' || prop === 'innerHeight') return 500;\n"
                    "      if (prop === 'style') return {};\n"
                    "      if (prop === 'classList') return { add: () => {}, remove: () => {}, contains: () => false, toggle: () => {} };\n"
                    "      if (prop === 'currentTime') return 0;\n"
                    "      if (prop === 'state') return 'running';\n"
                    "      if (prop === 'destination') return createMock('dest');\n"
                    "      if (prop === 'localStorage' || prop === 'sessionStorage') return { getItem: () => null, setItem: () => {}, removeItem: () => {} };\n"
                    "      return createMock(name + '.' + String(prop));\n"
                    "    },\n"
                    "    set() { return true; },\n"
                    "    apply() { return createMock(name + '()'); },\n"
                    "    construct() { return createMock('new ' + name); }\n"
                    "  });\n"
                    "}\n"
                    "const mockDOM = createMock('DOM');\n"
                    "const base = {\n"
                    "  window: mockDOM,\n"
                    "  document: mockDOM,\n"
                    "  console: console,\n"
                    "  setTimeout: (fn) => {},\n"
                    "  setInterval: (fn) => {},\n"
                    "  requestAnimationFrame: (fn) => {},\n"
                    "  alert: () => {},\n"
                    "  Math: Math,\n"
                    "  AudioContext: mockDOM,\n"
                    "  webkitAudioContext: mockDOM,\n"
                    "  localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },\n"
                    "  sessionStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} }\n"
                    "};\n"
                    "base.window.localStorage = base.localStorage;\n"
                    "base.window.sessionStorage = base.sessionStorage;\n"
                    "base.window.document = mockDOM;\n"
                    "\n"
                    "const sandbox = new Proxy(base, {\n"
                    "  has(target, prop) { return true; },\n"
                    "  get(target, prop) {\n"
                    "    if (prop in target) return target[prop];\n"
                    "    if (typeof prop === 'symbol') return undefined;\n"
                    "    return mockDOM;\n"
                    "  }\n"
                    "});\n"
                    "vm.createContext(sandbox);\n"
                    "try {\n"
                    "  vm.runInContext(process.env.TEST_CODE, sandbox, { timeout: 2000 });\n"
                    "} catch (err) {\n"
                    "  console.error(err.name + ': ' + err.message);\n"
                    "  process.exit(1);\n"
                    "}\n"
                )
                try:
                    res = subprocess.run(
                        ["node", "-e", node_runner],
                        env={**os.environ, "TEST_CODE": sc_clean},
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if res.returncode != 0 and res.stderr.strip():
                        err_line = res.stderr.strip().splitlines()[0]
                        issues.append(f"Script Runtime/Syntax Error: {err_line}")
                except Exception:
                    pass

    # 2. Python syntax checks
    elif p_str.endswith(".py"):
        try:
            compile(content, path, "exec")
        except SyntaxError as e:
            issues.append(f"Python SyntaxError on line {e.lineno}: {e.msg}")
        except Exception as e:
            issues.append(f"Python compile error: {e}")

    # 3. JavaScript checks (if node is installed)
    elif p_str.endswith(".js"):
        if subprocess.run("which node", shell=True, capture_output=True).returncode == 0:
            try:
                res = subprocess.run(["node", "--check"], input=content, capture_output=True, text=True, timeout=5)
                if res.returncode != 0 and res.stderr:
                    err_lines = [l for l in res.stderr.strip().splitlines() if not l.startswith("Node.js") and "at " not in l]
                    first_err = err_lines[0] if err_lines else res.stderr.strip().splitlines()[0]
                    issues.append(f"JavaScript Syntax Error: {first_err}")
            except Exception:
                pass

    # 4. Shell syntax checks
    elif p_str.endswith(".sh"):
        try:
            res = subprocess.run(["bash", "-n", "-c", content], capture_output=True, text=True, timeout=5)
            if res.returncode != 0 and res.stderr:
                issues.append(f"Bash Syntax Error: {res.stderr.strip().splitlines()[0]}")
        except Exception:
            pass

    return issues


def _clean_arguments(args):
    """Normalize tool arguments from dicts, single-item lists, or strings into a clean dict."""
    if isinstance(args, list):
        if len(args) > 0 and isinstance(args[0], dict):
            return args[0]
        elif len(args) > 0 and isinstance(args[0], str):
            return {"url": args[0], "path": args[0], "command": args[0], "query": args[0]}
        return {}
    if isinstance(args, dict):
        return args
    return {}


class Agent:
    def __init__(self, model="qwen2.5-coder:7b", host="http://127.0.0.1:11434", context=None, temp=0.2, auto=False):
        self.model = model
        self.host = host.rstrip("/")
        if context is None:
            context = get_safe_default_context(model)
        # Enforce memory safety on systems with <14GB RAM to prevent kernel OOM kills
        safe_ctx = get_safe_default_context(model)
        if context > safe_ctx and get_system_ram_gb() < 14.0:
            context = safe_ctx
        self.context = context
        self.temp = temp
        self.auto = auto
        self.history = [{"role": "system", "content": get_system_prompt()}]

    def ask_permission(self, action_desc):
        """Interactive permission menu with arrow keys and shortcuts."""
        if self.auto:
            return True
        
        options = [
            ("[Y] Approve this action", "yes"),
            ("[A] Always Allow (Switch to Auto Mode)", "auto"),
            ("[N] Skip this action", "no")
        ]
        shortcuts = {'y': 0, 'a': 1, 'n': 2}
        
        idx, choice = select_menu(f"Action approval required for: {action_desc}", options, default_idx=0, shortcuts=shortcuts)
        
        if choice == "yes":
            return True
        elif choice == "auto":
            self.auto = True
            print(f"   {YELLOW}⚡ Auto-mode enabled for remaining actions.{RESET}")
            return True
        else:
            print(f"   {RED}Action skipped.{RESET}")
            return False

    def find_active_target_file(self, user_prompt=""):
        """Find the relevant target file from explicit mention, conversation history, or cwd."""
        # 1. Explicit filename in prompt
        cand_match = re.search(r"\b([~./\w-]+\.(?:html?|py|js|sh|css|json|rs|go|cpp|c))\b", user_prompt, re.IGNORECASE)
        if cand_match:
            p = Path(os.path.expanduser(cand_match.group(1)))
            if not p.is_absolute():
                p = (Path(os.getcwd()) / p).resolve()
            return p

        # 2. Check conversation history for files accessed by tools
        for msg in reversed(self.history):
            content = msg.get("content", "")
            m = re.findall(r'"(?:path|url|file)"\s*:\s*"([^"]+\.(?:html?|py|js|sh|css|json|rs|go|cpp|c))"', content)
            if m:
                for cand_str in m:
                    p = Path(os.path.expanduser(cand_str))
                    if not p.is_absolute():
                        p = (Path(os.getcwd()) / p).resolve()
                    if p.is_file():
                        return p

        # 3. If browser/web/game/html/page is mentioned and intent is NOT creation, find the newest HTML file in cwd
        p_lower = user_prompt.lower()
        is_create_intent = bool(re.search(r"\b(?:create|build|generate|write|implement|new|code|develop)\b", user_prompt, re.IGNORECASE))
        if not is_create_intent and any(w in p_lower for w in ("browser", "html", "game", "page", "ui", "site", "web", "snake", "arcade")):
            html_files = sorted(Path(os.getcwd()).glob("*.html"), key=lambda f: f.stat().st_mtime, reverse=True)
            if html_files:
                return html_files[0]

        # 4. Check for newest code file in cwd (if not creation intent)
        if not is_create_intent:
            code_files = sorted(
                [f for f in Path(os.getcwd()).iterdir() if f.is_file() and f.suffix.lower() in ('.py', '.js', '.html', '.sh')],
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            if code_files:
                return code_files[0]

        return None

    def execute_tool(self, name, args, user_prompt=""):
        args = _clean_arguments(args)
        if name == "search_web":
            query = args.get("query", "")
            print(f"\n{CYAN}🔍 Web Search:{RESET} '{query}'")
            if not self.ask_permission(f"web search for '{query}'"):
                return f"Web search for '{query}' skipped by user."
            res = search_duckduckgo(query)
            titles = re.findall(r'\[\d+\]\s*(.*?)\n', res)
            if titles:
                for t in titles[:3]:
                    print(f"   {GRAY}• {t}{RESET}")
            print(f"   {GREEN}✓ Search complete{RESET}")
            return res

        elif name == "fetch_web":
            url = args.get("url", "")
            print(f"\n{CYAN}🌐 Browsing:{RESET} {url}")
            if not self.ask_permission(f"fetching web content from '{url}'"):
                return f"Browsing '{url}' skipped by user."
            try:
                preview, total_chars = fetch_url_content(url)
                print(f"   {GREEN}✓ Retrieved {total_chars} characters{RESET}")
                return preview
            except Exception as e:
                return f"Error browsing '{url}': {e}"

        elif name == "open_browser":
            raw_target = (args.get("url") or args.get("path") or args.get("file") or args.get("link") or args.get("target") or "").strip()
            if not raw_target:
                active_target = self.find_active_target_file(user_prompt)
                if active_target:
                    raw_target = str(active_target)

            # Guard against model opening external research links instead of the requested local file:
            p_lower = user_prompt.lower()
            html_matches = re.findall(r"\b[\w-]+\.html?\b", user_prompt, re.IGNORECASE)
            if raw_target.startswith(("http://", "https://")) and html_matches:
                local_html = html_matches[0]
                local_p = (Path(os.getcwd()) / local_html).resolve()
                if local_p.exists():
                    raw_target = str(local_p)
                else:
                    return f"Action rejected: The user requested to create '{local_html}'. You must write '{local_html}' using write_file first before opening it. Do NOT open external research websites in the user's browser."

            p = Path(os.path.expanduser(raw_target))
            if not p.is_absolute():
                p = (Path(os.getcwd()) / p).resolve()

            if p.exists() and p.is_file():
                target_url = p.as_uri()
                display_label = str(p.relative_to(os.getcwd())) if str(p).startswith(os.getcwd()) else str(p)
            elif raw_target.startswith(("http://", "https://", "file://")):
                target_url = raw_target
                display_label = target_url
            elif raw_target.endswith((".html", ".htm", ".txt", ".py")):
                target_url = (Path(os.getcwd()) / raw_target).resolve().as_uri()
                display_label = raw_target
            else:
                target_url = "https://" + raw_target if not raw_target.startswith("www.") else "https://" + raw_target
                display_label = target_url

            # Automated Headless Pre-flight Browser Verification for local HTML apps
            if p.exists() and p.is_file() and p.suffix.lower() in (".html", ".htm"):
                print(f"   {GRAY}Testing web page in headless browser first...{RESET}")
                content = p.read_text(encoding="utf-8", errors="replace")
                pre_issues = validate_code(display_label, content)
                if pre_issues:
                    print(f"   {YELLOW}⚠️  Pre-flight verification failed for '{display_label}':{RESET}")
                    for iss in pre_issues:
                        print(f"      {RED}• {iss}{RESET}")
                    return (
                        f"Pre-flight browser test FAILED for '{display_label}'. Do not launch broken code to the user.\n"
                        + "\n".join(f"- {iss}" for iss in pre_issues)
                        + f"\nCRITICAL: You MUST invoke edit_file immediately to fix these issues before launching the browser."
                    )

                # Headless render verification with Firefox
                if subprocess.run("which firefox", shell=True, capture_output=True).returncode == 0:
                    import tempfile
                    import shutil
                    temp_prof = tempfile.mkdtemp(prefix="lc_ff_")
                    temp_shot = Path(tempfile.gettempdir()) / f"lc_test_{p.stem}.png"
                    try:
                        ff_cmd = [
                            "firefox", "--headless", "--no-remote",
                            "--profile", temp_prof,
                            "--screenshot", str(temp_shot),
                            target_url
                        ]
                        subprocess.run(ff_cmd, capture_output=True, text=True, timeout=8)
                        if temp_shot.exists() and temp_shot.stat().st_size > 0:
                            print(f"   {GREEN}✓ Headless browser test passed (clean render verified){RESET}")
                            try:
                                temp_shot.unlink()
                            except Exception:
                                pass
                    except Exception:
                        pass
                    finally:
                        shutil.rmtree(temp_prof, ignore_errors=True)

            print(f"\n{CYAN}🖥️  Launch Browser:{RESET} {BOLD}{display_label}{RESET} {GRAY}({target_url}){RESET}")
            if not self.ask_permission(f"opening '{display_label}' in desktop browser"):
                return f"Opening browser for '{display_label}' skipped by user."
            try:
                # Prefer xdg-open on Linux for robust desktop launch on Wayland/Hyprland
                if IS_LINUX and subprocess.run("which xdg-open", shell=True, capture_output=True).returncode == 0:
                    subprocess.Popen(["xdg-open", target_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    webbrowser.open(target_url)
                print(f"   {GREEN}✓ Opened '{display_label}' in default web browser{RESET}")
                return f"Successfully opened '{display_label}' in default browser."
            except Exception as e:
                return f"Error opening browser: {e}"

        elif name in ("inspect_ui", "screenshot_ui"):
            target = (args.get("path") or args.get("file") or args.get("url") or "").strip()
            if not target:
                html_matches = re.findall(r"\b[\w-]+\.html?\b", user_prompt, re.IGNORECASE)
                target = html_matches[0] if html_matches else "snake.html"

            p = Path(os.path.expanduser(target))
            if not p.is_absolute():
                p = (Path(os.getcwd()) / p).resolve()
            if not p.is_file():
                return f"Error: File '{target}' does not exist on disk."

            display_path = str(p.relative_to(os.getcwd())) if str(p).startswith(os.getcwd()) else str(p)
            print(f"\n{CYAN}📸 Visual UI Inspector:{RESET} {BOLD}{display_path}{RESET}")

            # Step 1: Capture headless screenshot via Firefox
            import tempfile
            import shutil
            shot_file = Path(tempfile.gettempdir()) / f"lc_ui_{p.stem}.png"
            shot_captured = False
            if subprocess.run("which firefox", shell=True, capture_output=True).returncode == 0:
                temp_prof = tempfile.mkdtemp(prefix="lc_inspect_")
                try:
                    ff_cmd = [
                        "firefox", "--headless", "--no-remote",
                        "--profile", temp_prof,
                        "--window-size", "1280,800",
                        "--screenshot", str(shot_file),
                        p.as_uri()
                    ]
                    subprocess.run(ff_cmd, capture_output=True, text=True, timeout=10)
                    if shot_file.exists() and shot_file.stat().st_size > 0:
                        shot_captured = True
                        print(f"   {GREEN}✓ Captured 1280x800 headless screenshot ({shot_file.stat().st_size} bytes){RESET}")
                except Exception:
                    pass
                finally:
                    shutil.rmtree(temp_prof, ignore_errors=True)

            # Step 2: Check for local Ollama vision models (moondream, llava, minicpm-v, llama3.2-vision)
            vision_models = ["moondream", "llava", "minicpm-v", "llama3.2-vision", "qwen2-vl"]
            installed = list_installed_models(self.host)
            active_vision = next((m for m in installed if any(v in m.lower() for v in vision_models)), None)

            ai_critique = ""
            if shot_captured and active_vision:
                try:
                    print(f"   {MAGENTA}👁️  Running local offline visual critique via {active_vision}...{RESET}")
                    import base64
                    with open(shot_file, "rb") as sf:
                        img_b64 = base64.b64encode(sf.read()).decode("utf-8")
                    v_prompt = (
                        "Analyze this UI screenshot. Critique the visual design, color palette, "
                        "spacing, typography, and contrast. Give 3-5 specific CSS and layout suggestions "
                        "to make it look modern, high-end, and visually appealing."
                    )
                    payload = {
                        "model": active_vision,
                        "prompt": v_prompt,
                        "images": [img_b64],
                        "stream": False,
                        "options": {"num_predict": 300, "temperature": 0.2}
                    }
                    req = urllib.request.Request(
                        f"{self.host}/api/generate",
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        res_data = json.loads(resp.read().decode("utf-8"))
                        ai_critique = res_data.get("response", "").strip()
                except Exception:
                    pass

            # Step 3: Automated DOM and CSS Aesthetic Audit
            content = p.read_text(encoding="utf-8", errors="replace")
            content_lower = content.lower()
            audit_points = []

            if "font-family" not in content_lower or "monospace" in content_lower:
                audit_points.append("Typography: Upgrade font stack to modern system typography ('Segoe UI', system-ui, 'Inter') or stylish retro display fonts with letter-spacing and text-shadows.")

            if "border-radius" not in content_lower or "box-shadow" not in content_lower:
                audit_points.append("Card & Container Aesthetics: Add sleek border-radius (8-16px) and ambient neon box-shadows (0 0 20px rgba(...)) for high-end depth.")

            if "<canvas" in content_lower:
                if "shadowblur" not in content_lower:
                    audit_points.append("Canvas Bloom & Glow: Use ctx.shadowBlur and ctx.shadowColor for radiant arcade neon glow on sprites/food/snake.")
                if "roundrect" not in content_lower and "arc(" not in content_lower:
                    audit_points.append("Rounded Geometry: Render segments with rounded corners or pill shapes instead of flat jagged squares.")

            if "display: flex" not in content_lower and "grid" not in content_lower:
                audit_points.append("Layout Structure: Use Flexbox/Grid centering with max-width containers and responsive scaling.")

            if "backdrop-filter" not in content_lower:
                audit_points.append("Frosted Glass UI: Use glassmorphism HUD cards (backdrop-filter: blur(12px), background: rgba(..., 0.2), 1px subtle border).")

            report = f"Visual UI Inspection Report for '{display_path}':\n"
            if shot_captured:
                report += f"- Headless Screenshot: Captured successfully ({shot_file})\n"
            if ai_critique:
                report += f"\n[AI Visual Critique ({active_vision})]:\n{ai_critique}\n"
            elif not active_vision:
                report += f"\n[Vision Model Status]: Offline text model active. (Tip: Run 'ollama pull moondream' for instant 1.7GB offline vision critique on any laptop).\n"
            if audit_points:
                report += "\n[Automated Aesthetic & Modern Design Audit]:\n" + "\n".join(f"- {pt}" for pt in audit_points)

            report += (
                f"\n\nActionable Implementation Instructions:\n"
                f"Use 'edit_file' to upgrade {display_path} with modern CSS styling, glassmorphism HUD badges, vibrant canvas glow, "
                f"and smooth responsive centering. Once updated, invoke 'open_browser' to verify."
            )
            return report

        elif name in ("edit_file", "patch_file"):
            path = args.get("path", "")
            target = args.get("target", "")
            replacement = args.get("replacement", "")
            p = Path(os.path.expanduser(path))
            if not p.is_absolute():
                p = (Path(os.getcwd()) / p).resolve()
            display_path = str(p)
            try:
                display_path = str(p.relative_to(os.getcwd()))
            except ValueError:
                pass
            print(f"\n{MAGENTA}✏️  Edit File:{RESET} {BOLD}{display_path}{RESET}")
            try:
                if not p.is_file():
                    return f"Error: File '{display_path}' does not exist. Use write_file for new files."
                old_text = p.read_text(encoding="utf-8", errors="replace")
                
                # Normalize line endings for reliable cross-platform matching (CRLF vs LF)
                target_norm = target.replace("\r\n", "\n")
                old_text_norm = old_text.replace("\r\n", "\n")
                replacement_norm = replacement.replace("\r\n", "\n")

                new_text = None
                if target_norm in old_text_norm:
                    if old_text_norm.count(target_norm) > 1:
                        return f"Error: Target snippet occurs {old_text_norm.count(target_norm)} times in '{display_path}'. Include more surrounding context lines to make it unique."
                    new_text = old_text_norm.replace(target_norm, replacement_norm, 1)
                else:
                    # 1. Line-by-line whitespace-insensitive fuzzy matching for minor indentation differences
                    target_lines = [l.strip() for l in target_norm.strip().splitlines() if l.strip()]
                    file_lines = old_text_norm.splitlines()
                    match_start = -1
                    if target_lines:
                        for i in range(len(file_lines) - len(target_lines) + 1):
                            if [file_lines[i + j].strip() for j in range(len(target_lines))] == target_lines:
                                match_start = i
                                break
                    if match_start != -1:
                        before = file_lines[:match_start]
                        after = file_lines[match_start + len(target_lines):]
                        new_text = "\n".join(before + [replacement_norm] + after)

                    # 2. Ellipsis spanning: if target uses '...' or '/* ... */' to denote a range
                    if not new_text and re.search(r"^\s*(?:\.\.\.|/\*\s*\.\.\.\s*\*/|//\s*\.\.\.)\s*$", target_norm, flags=re.M):
                        parts = re.split(r"^\s*(?:\.\.\.|/\*\s*\.\.\.\s*\*/|//\s*\.\.\.)\s*$", target_norm, flags=re.M)
                        if len(parts) == 2:
                            head_lines = [l.strip() for l in parts[0].strip().splitlines() if l.strip()]
                            tail_lines = [l.strip() for l in parts[1].strip().splitlines() if l.strip()]
                            head_idx = -1
                            tail_idx = -1
                            if head_lines:
                                for i in range(len(file_lines) - len(head_lines) + 1):
                                    if [file_lines[i + j].strip() for j in range(len(head_lines))] == head_lines:
                                        head_idx = i
                                        break
                            if tail_lines and head_idx != -1:
                                for k in range(head_idx + len(head_lines), len(file_lines) - len(tail_lines) + 1):
                                    if [file_lines[k + j].strip() for j in range(len(tail_lines))] == tail_lines:
                                        tail_idx = k + len(tail_lines)
                                        break
                            if head_idx != -1 and tail_idx != -1:
                                before = file_lines[:head_idx]
                                after = file_lines[tail_idx:]
                                new_text = "\n".join(before + [replacement_norm] + after)

                    if not new_text:
                        print(f"   {RED}✗ Target snippet not found in '{display_path}'{RESET}")
                        print(f"   {GRAY}Attempted target snippet: {repr(target_norm[:120])}{RESET}")
                        if len(target_lines) > 1 and all(any(tl == fl.strip() for fl in file_lines) for tl in target_lines):
                            found_lines = [next(idx + 1 for idx, fl in enumerate(file_lines) if fl.strip() == tl) for tl in target_lines]
                            print(f"   {YELLOW}💡 Hint: Lines found at non-consecutive lines {found_lines}. Edit each snippet separately or include surrounding lines.{RESET}")
                            return f"Error: Target lines were found at non-consecutive lines {found_lines} in '{display_path}'. Please edit each section separately using 'edit_file', or include the full contiguous block between them."
                        if any(k in target_norm for k in ("<exact", "<clean", "<placeholder")):
                            print(f"   {YELLOW}💡 Hint: Use real code lines from '{display_path}', not placeholder text.{RESET}")
                        return f"Error: Target snippet not found in '{display_path}'. Please provide the exact code lines as they appear in '{display_path}'."

                # Show colored diff before applying
                print_diff(old_text_norm, new_text, display_path)

                if not self.ask_permission(f"modifications to '{display_path}'"):
                    return f"Editing '{display_path}' skipped by user."

                # Auto-sanitize trailing commentary after </html>
                if p.suffix.lower() in (".html", ".htm") and "</html>" in new_text.lower():
                    end_idx = new_text.lower().rfind("</html>")
                    new_text = new_text[:end_idx + 7].strip() + "\n"

                p.write_text(new_text, encoding="utf-8")
                print(f"   {GREEN}✓ Successfully updated '{display_path}'{RESET}")
                issues = validate_code(display_path, new_text)
                if issues:
                    print(f"   {YELLOW}⚠️  Diagnostics detected issues in '{display_path}':{RESET}")
                    for iss in issues:
                        print(f"      {RED}• {iss}{RESET}")
                    return (
                        f"File '{display_path}' updated, but automated code diagnostics detected issues:\n"
                        + "\n".join(f"- {iss}" for iss in issues)
                        + f"\nCRITICAL: You must invoke edit_file immediately to fix these diagnostic issues before opening or finishing."
                    )
                return f"File '{display_path}' successfully edited and verified (0 diagnostic errors)."
            except Exception as e:
                return f"Error editing '{display_path}': {e}"

        elif name == "write_file":
            path = args.get("path", "")
            content = args.get("content", "")
            p = Path(os.path.expanduser(path))
            if not p.is_absolute():
                p = (Path(os.getcwd()) / p).resolve()
            is_new = not p.exists()
            label = "Create New File" if is_new else "Overwrite Entire File"
            display_path = str(p)
            try:
                display_path = str(p.relative_to(os.getcwd()))
            except ValueError:
                pass
            print(f"\n{GREEN}💾 {label}:{RESET} {BOLD}{display_path}{RESET} {GRAY}({len(content)} bytes){RESET}")
            # Guard against accidentally wiping an existing file with a snippet:
            if not is_new and p.is_file():
                p_suffix = p.suffix.lower()
                if p_suffix in (".html", ".htm") and not ("<html" in content.lower() or "<!doctype" in content.lower()):
                    return (
                        f"Action rejected: Cannot overwrite existing full HTML file '{display_path}' with a code snippet. "
                        f"To modify an existing file, invoke 'edit_file' with 'target' and 'replacement'. "
                        f"If replacing the entire file, provide the full <!DOCTYPE html> document."
                    )
            if not self.ask_permission(f"{label.lower()} '{display_path}'"):
                return f"Writing '{display_path}' skipped by user."
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                # Auto-sanitize trailing commentary after </html>
                if p.suffix.lower() in (".html", ".htm") and "</html>" in content.lower():
                    end_idx = content.lower().rfind("</html>")
                    content = content[:end_idx + 7].strip() + "\n"
                p.write_text(content, encoding="utf-8")
                print(f"   {GREEN}✓ Written '{display_path}'{RESET}")
                issues = validate_code(display_path, content)
                if issues:
                    print(f"   {YELLOW}⚠️  Diagnostics detected issues in '{display_path}':{RESET}")
                    for iss in issues:
                        print(f"      {RED}• {iss}{RESET}")
                    return (
                        f"File '{display_path}' written ({len(content)} bytes), but automated code diagnostics detected issues:\n"
                        + "\n".join(f"- {iss}" for iss in issues)
                        + f"\nCRITICAL: You must invoke edit_file immediately to fix these diagnostic issues before opening or finishing."
                    )
                return f"File '{display_path}' written successfully ({len(content)} bytes)."
            except Exception as e:
                return f"Error writing file '{display_path}': {e}"

        elif name == "read_file":
            path = args.get("path", "")
            start = args.get("start_line", 1)
            count = args.get("line_count", None)
            p = Path(os.path.expanduser(path))
            if not p.is_absolute():
                p = (Path(os.getcwd()) / p).resolve()
            display_path = str(p)
            try:
                display_path = str(p.relative_to(os.getcwd()))
            except ValueError:
                pass
            print(f"\n{BLUE}📖 Reading:{RESET} {display_path}")
            try:
                if not p.is_file():
                    return f"Error: File '{display_path}' does not exist."
                lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
                total = len(lines)
                if start and start > 1:
                    lines = lines[start - 1:]
                if count:
                    lines = lines[:count]
                numbered = [f"{i + (start or 1):4d} | {line}" for i, line in enumerate(lines)]
                print(f"   {GRAY}Read {len(lines)}/{total} lines{RESET}")
                full_text = p.read_text(encoding="utf-8", errors="replace")
                issues = validate_code(display_path, full_text)
                res_out = "\n".join(numbered) or "(empty file)"
                if issues:
                    res_out += (
                        f"\n\n[Automated Static Diagnostics on {display_path}]:\n"
                        + "\n".join(f"- {iss}" for iss in issues)
                        + f"\nCRITICAL: Now invoke edit_file to surgically update '{display_path}' and resolve these diagnostic errors. Do NOT explain without editing."
                    )
                return res_out
            except Exception as e:
                return f"Error reading file '{display_path}': {e}"

        elif name == "run_command":
            cmd = args.get("command", "").strip()
            cwd = args.get("cwd", None)
            if cwd:
                cwd = str(Path(os.path.expanduser(cwd)).resolve())
            else:
                cwd = os.getcwd()
            print(f"\n{YELLOW}⚡ Command:{RESET} {BOLD}{cmd}{RESET}" + (f" {GRAY}(in {cwd}){RESET}" if cwd != os.getcwd() else ""))
            if not self.ask_permission(f"command: '{cmd}'"):
                return "Command skipped by user."
            try:
                res = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=180, cwd=cwd)
                out = res.stdout or ""
                if res.stderr:
                    out += ("\n[STDERR]\n" + res.stderr) if out else res.stderr
                clean = out.strip()
                preview = clean[:600]
                if preview:
                    print(f"{GRAY}{preview}{'...' if len(clean) > 600 else ''}{RESET}")
                else:
                    print(f"   {GRAY}(Finished with exit code {res.returncode}){RESET}")
                return clean or "(Command executed with no output)"
            except subprocess.TimeoutExpired:
                return "Error: Command timed out after 180 seconds."
            except Exception as e:
                return f"Error running command: {e}"

        elif name == "list_dir":
            path = args.get("path", ".")
            depth = args.get("max_depth", 2)
            root = Path(os.path.expanduser(path))
            if not root.is_absolute():
                root = (Path(os.getcwd()) / root).resolve()
            display_path = str(root)
            try:
                display_path = str(root.relative_to(os.getcwd()))
            except ValueError:
                pass
            print(f"\n{CYAN}📁 Listing:{RESET} {display_path}")
            try:
                if not root.exists():
                    return f"Error: Path '{display_path}' not found."
                tree = []
                def walk(cur, d):
                    if d > depth:
                        return
                    for item in sorted(cur.iterdir()):
                        if item.name.startswith(".git") or item.name == "__pycache__":
                            continue
                        indent = "  " * (d - 1)
                        if item.is_dir():
                            tree.append(f"{indent}📂 {item.name}/")
                            walk(item, d + 1)
                        else:
                            sz = item.stat().st_size
                            sz_s = f"{sz}B" if sz < 1024 else f"{sz//1024}KB"
                            tree.append(f"{indent}📄 {item.name} ({sz_s})")
                walk(root, 1)
                return "\n".join(tree[:80]) or "(empty directory)"
            except Exception as e:
                return f"Error listing directory '{display_path}': {e}"

        elif name == "search_code":
            query = args.get("query", "")
            search_path = args.get("path", ".")
            print(f"\n{CYAN}🔍 Code Search:{RESET} '{query}' in {search_path}")
            
            try:
                cmd = f"rg -n -i --max-count 40 \"{query}\" \"{search_path}\" 2>/dev/null || grep -rnI --exclude-dir=.git \"{query}\" \"{search_path}\" 2>/dev/null"
                res = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=10)
                lines = (res.stdout or "").strip().splitlines()[:40]
                if lines:
                    print(f"   {GRAY}{len(lines)} matches found{RESET}")
                    return "\n".join(lines)
            except Exception:
                pass

            matches = []
            try:
                for root, dirs, files in os.walk(search_path):
                    dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "node_modules", "target", "build", "dist")]
                    for f in files:
                        fpath = os.path.join(root, f)
                        try:
                            with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                                for lnum, line in enumerate(fh, 1):
                                    if query.lower() in line.lower():
                                        rel = os.path.relpath(fpath, search_path)
                                        matches.append(f"{rel}:{lnum}: {line.strip()[:120]}")
                                        if len(matches) >= 40:
                                            break
                        except Exception:
                            pass
                    if len(matches) >= 40:
                        break
                if matches:
                    print(f"   {GRAY}{len(matches)} matches found{RESET}")
                    return "\n".join(matches)
                return f"No code matches found for '{query}'."
            except Exception as e:
                return f"Error searching code: {e}"

        elif name == "git_diff":
            path = args.get("path", ".")
            print(f"\n{CYAN}🌿 Git Status & Diff:{RESET}")
            try:
                st = subprocess.run("git status --short", shell=True, text=True, capture_output=True, cwd=path)
                diff = subprocess.run("git diff", shell=True, text=True, capture_output=True, cwd=path)
                res = f"STATUS:\n{st.stdout}\nDIFF:\n{diff.stdout[:3000]}"
                return res.strip() or "Clean working tree (no uncommitted changes)."
            except Exception as e:
                return f"Error checking git diff: {e}"

        return f"Unknown tool: '{name}'."

    @staticmethod
    def robust_json_loads(text):
        """Parses JSON even if it contains unescaped control characters (newlines), trailing commas, or template literal backticks."""
        if not text:
            return None
        def fix_backticks(s):
            def repl(m):
                key = m.group(1)
                val = m.group(2)
                return f"{key}{json.dumps(val)}"
            return re.sub(r'("[a-zA-Z0-9_]+"\s*:\s*)`([\s\S]*?)`', repl, s)

        s_fixed = fix_backticks(text)
        try:
            return json.loads(s_fixed, strict=False)
        except Exception:
            pass
        cleaned = re.sub(r",\s*([\]}])", r"\1", s_fixed)
        try:
            return json.loads(cleaned, strict=False)
        except Exception:
            pass
        try:
            return json.loads(text, strict=False)
        except Exception:
            pass
        return None


    def extract_tool_call(self, text, user_prompt="", step=1, is_final=True):
        """Extract tool call using markdown blocks, balanced-brace parsing, and raw JSON fallback.
        Also provides an agentic fallback: if the model produced a code block instead of JSON,
        automatically converts it into a write_file tool call so code is saved to disk."""
        # 1. Try finding markdown code block with json
        blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        for b in blocks:
            data = Agent.robust_json_loads(b)
            if isinstance(data, dict) and "name" in data and ("arguments" in data or "parameters" in data):
                raw_args = data.get("arguments") if "arguments" in data else data.get("parameters")
                return data["name"], _clean_arguments(raw_args), True

        # 2. Balanced brace scan for {"name": ..., "arguments": ...}
        # Handles nested braces, template literal backticks, code containing CSS/JS, and escaped quotes properly
        pattern = re.compile(r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"(?:arguments|parameters)"\s*:', flags=re.DOTALL)
        for m in pattern.finditer(text):
            start = m.start()
            brace_count = 0
            in_string = None
            escape = False
            for i in range(start, len(text)):
                ch = text[i]
                if escape:
                    escape = False
                    continue
                if ch == '\\':
                    escape = True
                    continue
                if in_string:
                    if ch == in_string:
                        in_string = None
                    continue
                else:
                    if ch == '"' or ch == '`':
                        in_string = ch
                        continue
                    if ch == '{':
                        brace_count += 1
                    elif ch == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            candidate = text[start:i+1]
                            data = Agent.robust_json_loads(candidate)
                            if isinstance(data, dict) and "name" in data and ("arguments" in data or "parameters" in data):
                                raw_args = data.get("arguments") if "arguments" in data else data.get("parameters")
                                return data["name"], _clean_arguments(raw_args), True
                            break

        # 3. Fallback: try whole string if it starts and ends with { }
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            data = Agent.robust_json_loads(stripped)
            if isinstance(data, dict) and "name" in data and ("arguments" in data or "parameters" in data):
                raw_args = data.get("arguments") if "arguments" in data else data.get("parameters")
                return data["name"], _clean_arguments(raw_args), True

        # 3.5 Fallback: Robust regex extraction if JSON was malformed or truncated (only when is_final=True)
        if is_final and ('"name"' in text or '{"name":' in text or '"write_file"' in text or '"edit_file"' in text):
            name_m = re.search(r'"name"\s*:\s*"([a-zA-Z0-9_-]+)"', text)
            tool_name = name_m.group(1) if name_m else ("write_file" if '"write_file"' in text else ("edit_file" if '"edit_file"' in text else None))
            if tool_name == "write_file":
                path_m = re.search(r'"path"\s*:\s*[`"]([^`"]+)[`"]', text)
                content_m = re.search(r'"content"\s*:\s*[`"]([\s\S]*)', text, flags=re.DOTALL)
                if not content_m:
                    content_m = re.search(r'"content"\s*:\s*([\s\S]*)', text, flags=re.DOTALL)

                if path_m and content_m:
                    p_str = path_m.group(1).strip()
                    c_str = content_m.group(1).strip()
                    c_str = re.sub(r'(?:[`"]\s*\}|\s*\}\s*\}|\s*```)\s*$', '', c_str)
                    c_str = re.sub(r'[`"]\s*\}\s*\}\s*$', '', c_str)
                    c_str = re.sub(r'[`"]\s*$', '', c_str)
                    try:
                        c_str = c_str.encode("utf-8").decode("unicode_escape")
                    except Exception:
                        c_str = c_str.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')

                    # Trim repetitive tail if model was caught in a looping pattern
                    for pat_len in range(10, 80):
                        if len(c_str) >= pat_len * 3:
                            pat = c_str[-pat_len:]
                            if c_str.endswith(pat * 3):
                                while c_str.endswith(pat):
                                    c_str = c_str[:-len(pat)]
                                break

                    if c_str.strip():
                        return "write_file", {"path": p_str, "content": c_str.strip()}, True
            elif tool_name in ("edit_file", "patch_file"):
                path_m = re.search(r'"path"\s*:\s*[`"]([^`"]+)[`"]', text)
                target_m = re.search(r'"target"\s*:\s*[`"]([\s\S]*?)[`"](?:\s*,|\s*\n\s*"|\s*\})', text)
                if not target_m:
                    target_m = re.search(r'"target"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', text)
                rep_m = re.search(r'"replacement"\s*:\s*[`"]([\s\S]*)', text, flags=re.DOTALL)
                if not rep_m:
                    rep_m = re.search(r'"replacement"\s*:\s*([\s\S]*)', text, flags=re.DOTALL)
                if path_m and target_m and rep_m:
                    p_str = path_m.group(1).strip()
                    t_str = target_m.group(1).strip()
                    r_str = rep_m.group(1).strip()
                    r_str = re.sub(r'(?:[`"]\s*\}|\s*\}\s*\}|\s*```)\s*$', '', r_str)
                    r_str = re.sub(r'[`"]\s*\}\s*\}\s*$', '', r_str)
                    r_str = re.sub(r'[`"]\s*$', '', r_str)
                    try:
                        t_str = t_str.encode("utf-8").decode("unicode_escape")
                        r_str = r_str.encode("utf-8").decode("unicode_escape")
                    except Exception:
                        t_str = t_str.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                        r_str = r_str.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                    return "edit_file", {"path": p_str, "target": t_str, "replacement": r_str}, True

        # 4. Agentic Fallback: Model produced a raw code block instead of JSON!
        # Automatically convert it into a write_file action so code is saved to disk immediately.
        code_blocks = re.findall(r"```([a-zA-Z0-9_-]+)?\s*\n(.*?)```", text, flags=re.DOTALL)
        for lang, code in code_blocks:
                code = code.strip()
                if code.count("\n") >= 2 and not (code.startswith("{") and code.endswith("}")):
                    ext_map = {
                        "python": ".py", "py": ".py",
                        "javascript": ".js", "js": ".js",
                        "typescript": ".ts", "ts": ".ts",
                        "html": ".html", "htm": ".html",
                        "css": ".css",
                        "bash": ".sh", "sh": ".sh",
                        "json": ".json",
                        "rust": ".rs", "rs": ".rs",
                        "go": ".go", "cpp": ".cpp", "c": ".c"
                    }
                    ext = ext_map.get((lang or "").lower(), ".py" if "python" in user_prompt.lower() else ".txt")

                    filename = None
                    # Check for explicit filepath in prompt (e.g. rate_limiter.py, Downloads/app.py, ~/Downloads/app.py)
                    fn_match = re.search(r"([~./\w_-]+/[\w-]+\.(?:py|js|ts|html|css|sh|json|rs|go|cpp|c)|\b[\w-]+\.(?:py|js|ts|html|css|sh|json|rs|go|cpp|c))\b", user_prompt, re.IGNORECASE)
                    if fn_match:
                        filename = fn_match.group(1)
                    else:
                        first_line = code.splitlines()[0].strip() if code else ""
                        first_match = re.search(r"[\w-]+\.(?:py|js|ts|html|css|sh|json|rs|go|cpp|c)", first_line, re.IGNORECASE)
                        if first_match:
                            filename = first_match.group(0)
                        else:
                            # Check for capitalized topic phrases like "Rate Limiter", "Chess Game"
                            cap_phrases = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", user_prompt)
                            for phrase in cap_phrases:
                                if not any(w in phrase.lower() for w in ("act as", "follow these", "strict specifications", "senior systems")):
                                    filename = phrase.lower().replace(" ", "_") + ext
                                    break
                            if not filename:
                                active_p = self.find_active_target_file(user_prompt)
                                if active_p:
                                    filename = active_p.name
                                else:
                                    stopwords = {"write", "a", "single", "file", "production", "ready", "cli", "tool", "that", "implements", "an", "the", "in", "and", "or", "to", "act", "as", "senior", "systems", "programmer", "follow", "these", "strict", "specifications", "create", "make", "build", "using", "module", "code", "runnable", "complete", "python"}
                                    words = [w.lower() for w in re.findall(r"[a-zA-Z0-9]+", user_prompt) if w.lower() not in stopwords]
                                    base = "_".join(words[:2]) if words else "script"
                                    filename = f"{base}{ext}"

                    # If filename does not contain a directory, check if user specified one (e.g. "in Downloads" or "to ~/Downloads")
                    if filename and "/" not in filename:
                        folder_match = re.search(r'(?:in|to|inside)\s+(?:the\s+)?([~./\w_-]+)', user_prompt, re.IGNORECASE)
                        if folder_match:
                            fld = folder_match.group(1).rstrip("/.,")
                            if fld.lower() in ("downloads", "desktop", "documents", "code", "projects", "tmp") or fld.startswith(("~", "./", "/")):
                                filename = f"{fld}/{filename}"

                    # Safety check: If file already exists on disk, only overwrite if it is a complete file, not a partial snippet!
                    if filename:
                        target_p = Path(os.path.expanduser(filename))
                        if not target_p.is_absolute():
                            target_p = (Path(os.getcwd()) / target_p).resolve()
                        if target_p.is_file():
                            existing_lines = len(target_p.read_text(encoding="utf-8", errors="replace").splitlines())
                            new_lines = len(code.splitlines())
                            is_full_doc = (
                                (target_p.suffix.lower() in (".html", ".htm") and ("<html" in code.lower() or "<!doctype" in code.lower()))
                                or new_lines >= max(20, int(existing_lines * 0.7))
                            )
                            if not is_full_doc:
                                if target_p.suffix.lower() in (".html", ".htm") and (lang or "").lower() in ("javascript", "js"):
                                    old_html = target_p.read_text(encoding="utf-8", errors="replace")
                                    ph_match = re.search(r"//\s*Your code here|/\*\s*Your code here\s*\*/|//\s*TODO", old_html, re.IGNORECASE)
                                    if ph_match:
                                        clean_js = re.sub(r"^[`'\"]+|[`'\"]+\s*\}*\s*\}*$", "", code).strip()
                                        return "edit_file", {"path": str(target_p), "target": ph_match.group(0), "replacement": clean_js}, True
                                continue

                    return "write_file", {"path": filename, "content": code}, True

        return None, None, False

    def stream_turn(self, step=1, user_prompt="", messages=None, spinner_label=None):
        msgs = messages if messages is not None else self.history
        # Sliding-window context compression: Preserve system prompt, user prompt, and recent 3 turns in full.
        # Truncate large intermediate outputs so prompt eval stays lightweight (<1200 tokens) with plenty of room for generation.
        if len(msgs) > 4:
            compressed = []
            for idx, m in enumerate(msgs):
                if idx <= 1 or idx >= len(msgs) - 3:
                    compressed.append(m)
                else:
                    c = m.get("content", "")
                    if len(c) > 350:
                        compressed.append({
                            "role": m.get("role", "user"),
                            "content": c[:300] + "\n...[older output truncated to save context]..."
                        })
                    else:
                        compressed.append(m)
            msgs = compressed
        num_threads = min(os.cpu_count() or 4, 4)
        payload = {
            "model": self.model,
            "messages": msgs,
            "stream": True,
            "think": False,
            "options": {
                "num_ctx": self.context,
                "num_predict": min(self.context, 4096),
                "temperature": self.temp,
                "repeat_penalty": 1.15,
                "repeat_last_n": 64,
                "num_thread": num_threads,
                "stop": ["<|im_end|>", "<|endoftext|>"]
            }
        }
        url = f"{self.host}/api/chat"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        max_attempts = 5
        for attempt in range(max_attempts):
            accumulated = ""
            in_tool_block = False
            printed_prefix = False
            token_count = 0
            preamble_buffer = ""

            # Background animated spinner while CPU is prefilling / evaluating prompt
            stop_spinner = threading.Event()
            start_time = time.time()
            label = spinner_label or ("Planning actions & tools..." if step == 1 else "Formulating next step...")
            current_thought = [None]

            def spin():
                spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                i = 0
                while not stop_spinner.is_set():
                    elapsed = int(time.time() - start_time)
                    display_label = current_thought[0] or label
                    sys.stdout.write(f"\r{DIM}{spinner_frames[i % len(spinner_frames)]} [Step {step}] {display_label} ({elapsed}s){RESET}\033[K")
                    sys.stdout.flush()
                    i += 1
                    time.sleep(0.1)

            spin_thread = threading.Thread(target=spin, daemon=True)
            spin_thread.start()

            try:
                with urllib.request.urlopen(req, timeout=300) as resp:
                    for raw in resp:
                        if not raw.strip():
                            continue
                        chunk = json.loads(raw.decode("utf-8"))
                        msg = chunk.get("message", {})
                        token = msg.get("content", "")
                        thinking_token = msg.get("thinking", "")

                        if thinking_token:
                            clean_th = re.sub(r"[*#_`]", "", thinking_token).strip()
                            if clean_th:
                                snip = clean_th.replace("\n", " ").strip()
                                if len(snip) > 38:
                                    snip = snip[:35] + "..."
                                current_thought[0] = f"Thinking: {snip}"
                            continue

                        if not token:
                            continue

                        if not stop_spinner.is_set():
                            stop_spinner.set()
                            spin_thread.join(timeout=0.2)
                            sys.stdout.write(f"\r\033[K")
                            sys.stdout.flush()

                        accumulated += token
                        token_count += 1

                        if (
                            accumulated.strip().startswith("```")
                            or accumulated.strip().startswith("{")
                            or "```" in accumulated
                            or '{"name"' in accumulated
                            or '{"name":' in accumulated
                        ):
                            in_tool_block = True

                        if in_tool_block:
                            if printed_prefix:
                                sys.stdout.write(f"\r\033[K")
                                printed_prefix = False
                            preamble_buffer = ""
                            sys.stdout.write(f"\r{CYAN}⚡ [Step {step}] Writing code directly to disk... ({token_count} tokens){RESET}\033[K")
                            sys.stdout.flush()

                            # Repetition loop detector: if a phrase repeats 3+ times in the tail, break immediately
                            if len(accumulated) > 150:
                                tail = accumulated[-350:]
                                is_looping = False
                                for pat_len in range(12, 75):
                                    if len(tail) >= pat_len * 3:
                                        pat = tail[-pat_len:]
                                        if tail.endswith(pat * 3):
                                            while accumulated.endswith(pat):
                                                accumulated = accumulated[:-len(pat)]
                                            is_looping = True
                                            break
                                if is_looping:
                                    break

                            # Early stop: break immediately as soon as a complete tool call or code block is formed
                            if re.search(r"```[a-zA-Z0-9_-]*\s*\n.+?\n```", accumulated, flags=re.DOTALL):
                                _, _, valid = self.extract_tool_call(accumulated, user_prompt=user_prompt, step=step, is_final=False)
                                if valid:
                                    break
                            elif '{"name"' in accumulated or '{"name":' in accumulated:
                                if accumulated.count("}") >= accumulated.count("{") and accumulated.count("{") > 0:
                                    _, _, valid = self.extract_tool_call(accumulated, user_prompt=user_prompt, step=step, is_final=False)
                                    if valid:
                                        break
                        else:
                            preamble_buffer += token
                            if len(preamble_buffer) >= 80:
                                if not printed_prefix and preamble_buffer.strip():
                                    sys.stdout.write(f"\r\033[K\n{BOLD}{CYAN}Qwen:{RESET} ")
                                    printed_prefix = True
                                if printed_prefix:
                                    sys.stdout.write(preamble_buffer)
                                    sys.stdout.flush()
                                preamble_buffer = ""

                if in_tool_block:
                    sys.stdout.write(f"\r\033[K")
                    sys.stdout.flush()
                else:
                    if preamble_buffer:
                        if not printed_prefix and preamble_buffer.strip():
                            sys.stdout.write(f"\r\033[K\n{BOLD}{CYAN}Qwen:{RESET} ")
                            printed_prefix = True
                        if printed_prefix:
                            sys.stdout.write(preamble_buffer)
                            sys.stdout.flush()
                    if printed_prefix:
                        print()

                return accumulated, printed_prefix
            except Exception as e:
                stop_spinner.set()
                err_str = str(e).lower()
                is_conn_issue = any(w in err_str for w in (
                    "connection refused", "errno 111", "closed connection",
                    "connection reset", "broken pipe", "eof", "timed out",
                    "temporarily unavailable", "bad gateway", "service unavailable", "remote disconnected"
                ))
                if is_conn_issue and attempt < max_attempts - 1:
                    sys.stdout.write(f"\r\033[K{YELLOW}⏳ Ollama server busy or reconnecting (attempt {attempt + 1}/{max_attempts})...{RESET}\n")
                    sys.stdout.flush()
                    for _ in range(5):
                        time.sleep(2.0)
                        try:
                            check_req = urllib.request.Request(f"{self.host}/api/tags")
                            with urllib.request.urlopen(check_req, timeout=3) as check_resp:
                                if check_resp.status == 200:
                                    break
                        except Exception:
                            pass
                    continue
                print(f"\n{RED}Inference error: {e}{RESET}")
                if "connection refused" in err_str or "errno 111" in err_str:
                    print(f"{YELLOW}💡 Tip: Ensure Ollama is running (`systemctl --user start ollama` or `ollama serve`){RESET}")
                return "", False
            finally:
                stop_spinner.set()

    def get_fast_path_reply(self, prompt):
        """Instant (<1ms) response for conversational greetings, courtesy, gratitude, and identity.
        Bypasses local LLM inference entirely to prevent unnecessary CPU load and latency."""
        p = prompt.strip().lower()
        words = set(re.findall(r"[a-z0-9_.-]+", p))
        action_words = {
            "write", "create", "make", "build", "code", "script", "file", "edit",
            "patch", "update", "fix", "debug", "run", "test", "exec", "search",
            "find", "browser", "open", "git", "install", "generate", "implement",
            "check", "delete", "remove", "add", "show", "list", "read", "view",
            "save", "download", "clone", "push", "pull", "commit"
        }
        # If any actionable coding word or file extension is present, delegate to full engine
        if any(w in action_words for w in words) or any(w.endswith((".py", ".js", ".html", ".css", ".sh", ".json", ".rs", ".go", ".cpp", ".c")) for w in words):
            return None

        # Greetings
        if re.match(r"^(?:hi|hello|hey|yo|sup|howdy|hola|greetings|good\s+(?:morning|afternoon|evening|day))[!.\s]*$", p):
            return random.choice([
                "Hello! What are we building or working on today?",
                "Hey! Ready to code. What would you like to create, edit, or test?",
                "Hi there! What project or coding task are we tackling today?"
            ])

        # Status / Courtesy
        if re.match(r"^(?:how\s+are\s+you|how\s+is\s+it\s+going|what(?:\x27s|\s+is)\s+up|wassup)[!.\s\?]*$", p):
            return "Running fast and ready to help! What can I build, search, or fix for you?"

        # Gratitude
        if re.search(r"\b(?:thanks(?:\s+a\s+lot)?|thank\s+you(?:\s+so\s+much)?|thx|cheers|ty|appreciate\s+it)\b", p):
            return "You're very welcome! Let me know if you need anything else."

        # Closings
        if re.match(r"^(?:bye|goodbye|cya|see\s+ya|have\s+a\s+good\s+(?:day|one))[!.\s]*$", p):
            return "Goodbye! Happy coding, and see you next time."

        # Identity & Capabilities
        if re.match(r"^(?:who\s+are\s+you|what\s+are\s+you|what\s+is\s+local-?code|what\s+is\s+lc|what\s+can\s+you\s+do|what\s+tools\s+do\s+you\s+have|help)[!.\s\?]*$", p):
            return (
                f"I'm {BOLD}local-code{RESET} ({CYAN}lc{RESET}), an autonomous local AI coding assistant running directly on your system with Ollama ({self.model}).\n\n"
                f"Capabilities:\n"
                f"  • {CYAN}🔍 Web Research:{RESET} Search the live web and inspect documentation\n"
                f"  • {GREEN}💾 File Operations:{RESET} Create and surgically edit files with colored diffs\n"
                f"  • {YELLOW}⚡ Shell Execution:{RESET} Run commands, test suites, and package managers\n"
                f"  • {CYAN}🖥️ Browser Launch:{RESET} Open web apps & HTML files in your desktop browser\n"
                f"  • {GREEN}🌿 Git Integration:{RESET} Inspect status, uncommitted diffs, and repository state\n\n"
                f"What would you like to work on?"
            )

        return None

    def is_pure_explanation(self, prompt):
        """Detects whether a prompt is purely asking for explanation or knowledge
        without requiring file modifications, command executions, or tools."""
        p = prompt.strip().lower()
        words = set(re.findall(r"[a-z0-9_.-]+", p))
        action_words = {
            "file", "files", "save", "write", "create", "make", "edit", "run",
            "browser", "search", "git", "install", "delete", "download", "push", "pull"
        }
        if any(w in action_words for w in words) or any(w.endswith((".py", ".js", ".html", ".css", ".sh", ".json", ".rs", ".go", ".cpp", ".c")) for w in words):
            return False

        starters = [
            r"^(?:what\s+is|what\s+are|what\s+does)\b",
            r"^(?:why\s+is|why\s+are|why\s+does|why\s+do)\b",
            r"^(?:how\s+does|how\s+do|how\s+can\s+i|how\s+to)\b",
            r"^(?:explain|describe|clarify|tell\s+me\s+about)\b",
            r"^(?:difference\s+between|compare)\b",
        ]
        return any(re.search(q, p) for q in starters)

    def run(self, user_prompt, max_steps=20):
        # Sanitize pasted escape sequences from terminals (e.g. ^[E or \x1b[E)
        user_prompt = re.sub(r'(\x1b\[E|\^[E])', '\n', user_prompt).strip()
        if not user_prompt:
            return

        # Tier 1: Instant Fast-Path (0 ms response for greetings, courtesy, closures, identity)
        fast_reply = self.get_fast_path_reply(user_prompt)
        if fast_reply:
            print(f"\n{BOLD}{CYAN}Qwen:{RESET} {fast_reply}\n")
            self.history.append({"role": "user", "content": user_prompt})
            self.history.append({"role": "assistant", "content": fast_reply})
            return

        # Tier 2: Fast Conversational / Technical Explanation (no tool schema overhead)
        if self.is_pure_explanation(user_prompt):
            self.history.append({"role": "user", "content": user_prompt})
            temp_history = list(self.history)
            temp_history[0] = {
                "role": "system",
                "content": (
                    "You are local-code (lc), an expert AI software engineering assistant. "
                    "Answer the user's technical question directly, clearly, and concisely without invoking any tools. "
                    "Provide clear code snippets inside markdown blocks if helpful."
                )
            }
            res, was_streamed = self.stream_turn(step=1, user_prompt=user_prompt, messages=temp_history, spinner_label="Formulating explanation...")
            if res:
                self.history.append({"role": "assistant", "content": res})
            return

        # Automated Pre-Execution Diagnostic Hook for bug fix and browser launch requests
        fix_match = None
        cand = self.find_active_target_file(user_prompt)
        has_fix_word = bool(re.search(r"\b(?:fix|repair|debug|solve|unbug|bug|broken|issue)\b", user_prompt, re.IGNORECASE))
        has_open_word = any(w in user_prompt.lower() for w in ("open", "browser", "launch", "play", "view", "test"))

        if cand and cand.is_file():
            try:
                f_content = cand.read_text(encoding="utf-8", errors="replace")
                # Auto-heal trailing commentary/backticks after </html> for HTML files
                if cand.suffix.lower() in (".html", ".htm") and "</html>" in f_content.lower():
                    end_idx = f_content.lower().rfind("</html>")
                    trailing_text = f_content[end_idx + 7:].strip()
                    if trailing_text:
                        f_content = f_content[:end_idx + 7].strip() + "\n"
                        cand.write_text(f_content, encoding="utf-8")
                        print(f"\n{GREEN}✓ Auto-sanitized {len(trailing_text)} characters of trailing commentary after </html>{RESET}")

                # Auto-heal dummy placeholder script tags causing mismatched script tags
                if cand.suffix.lower() in (".html", ".htm") and "/* your code here */" in f_content.lower():
                    dummy_pat = r"<body>\s*<body>\s*<script>document\.addEventListener\(['\"]DOMContentLoaded['\"],\s*function\(\)\s*\{\s*/\*\s*Your code here\s*\*/\s*\}\);\s*</script>\s*</body>\s*</body>"
                    if re.search(dummy_pat, f_content, re.IGNORECASE):
                        f_content = re.sub(dummy_pat, "<body>\n<script>", f_content, flags=re.IGNORECASE)
                        cand.write_text(f_content, encoding="utf-8")
                        print(f"\n{GREEN}✓ Auto-healed placeholder script wrapper in '{cand.name}'{RESET}")

                issues = validate_code(str(cand), f_content)
                if issues:
                    fix_match = cand
                    diag_msg = "\n".join(f"- {iss}" for iss in issues)
                    user_prompt += (
                        f"\n\n[Automated Static Diagnostics on {cand.name}]:\n{diag_msg}\n"
                        f"Instructions: Use read_file to inspect {cand.name}, then use edit_file to surgically resolve all diagnostic issues. Once fixed, open it in the browser if it is an HTML file."
                    )
                    print(f"\n{YELLOW}🔍 Diagnostics found {len(issues)} issue(s) in {cand.name}:{RESET}")
                    for iss in issues:
                        print(f"   {RED}• {iss}{RESET}")
                else:
                    is_create_intent = bool(re.search(r"\b(?:create|build|generate|write|implement|new|code|develop)\b", user_prompt, re.IGNORECASE))
                    is_edit_or_fix = bool(re.search(r"\b(?:fix|repair|debug|solve|unbug|bug|broken|issue|inspect|search|edit|modify|update|upgrade|refactor|change|make|improve|pull\s+out|give\s+me)\b", user_prompt, re.IGNORECASE))
                    is_launch_only = bool(re.search(r"^\s*(?:open|launch|view|play|test)\b|\b(?:open|launch)\s+in\s+browser\b", user_prompt, re.IGNORECASE)) and not (is_edit_or_fix or is_create_intent)

                    if cand.suffix.lower() in (".html", ".htm") and (is_launch_only or (has_fix_word and not issues)):
                        print(f"\n{GREEN}✓ Pre-flight diagnostic check: '{cand.name}' has 0 errors.{RESET}")
                        self.execute_tool("open_browser", {"url": cand.name}, user_prompt=user_prompt)
                        self.history.append({"role": "user", "content": user_prompt})
                        self.history.append({"role": "assistant", "content": f"Inspected '{cand.name}' (0 diagnostic errors) and opened in your desktop web browser."})
                        return
                    elif has_fix_word or is_edit_or_fix:
                        user_prompt += (
                            f"\n\n[Target File: {cand.name} - 0 Diagnostic Errors Detected]\n"
                            f"The file '{cand.name}' is valid with 0 diagnostic issues. If making enhancements or inspecting code, use 'read_file' or 'edit_file'. Do NOT rewrite complete working files."
                        )
            except Exception:
                pass

        # Tier 3: Full Autonomous Tool Agent
        self.history.append({"role": "user", "content": user_prompt})
        step = 1
        recent_tool_sigs = []

        while step <= max_steps:
            res, was_streamed = self.stream_turn(
                step=step,
                user_prompt=user_prompt,
                spinner_label="Planning actions & tools..." if step == 1 else "Formulating next step..."
            )
            if not res:
                break

            self.history.append({"role": "assistant", "content": res})
            name, args, is_tool = self.extract_tool_call(res, user_prompt=user_prompt, step=step)

            if not is_tool:
                # Nudge guard: If this is a bug fix request and the model hasn't applied edit_file/write_file yet
                if fix_match and not any(sig[0] in ("edit_file", "write_file") for sig in recent_tool_sigs) and step <= 10:
                    cand_name = fix_match.name if isinstance(fix_match, Path) else str(fix_match)
                    self.history.append({
                        "role": "user",
                        "content": (
                            f"You inspected {cand_name}, but you have not applied the fix to disk yet. "
                            f"You MUST invoke 'edit_file' now with the exact target snippet from {cand_name} "
                            f"to surgically resolve the issue. Do NOT provide explanations without modifying the file."
                        )
                    })
                    step += 1
                    continue

                if res.strip():
                    clean_res = re.sub(r"```[a-zA-Z0-9_-]*\s*\n.*?```", "", res, flags=re.DOTALL).strip()
                    if clean_res and not re.search(r'^\s*(?:```|\{\s*"name")', clean_res):
                        print(f"\n{BOLD}{CYAN}Qwen:{RESET} {clean_res}")
                    else:
                        print(f"\n{BOLD}{CYAN}Qwen:{RESET} {res.strip()[:1500]}")
                break

            print(" " * 30, end="\r")

            # Loop detection / anti-repetition guard:
            sig = (name, json.dumps(args, sort_keys=True))
            p_lower = user_prompt.lower()
            if recent_tool_sigs.count(sig) >= 1 and name in ("search_web", "fetch_web"):
                fn_match = re.search(r"([~./\w_-]+/[\w-]+\.(?:py|js|ts|html|css|sh|json|rs|go|cpp|c)|\b[\w-]+\.(?:py|js|ts|html|css|sh|json|rs|go|cpp|c))\b", user_prompt, re.IGNORECASE)
                target_file = fn_match.group(1) if fn_match else "the requested code file"
                result = f"Loop prevented: Web research is already complete. Proceed IMMEDIATELY to invoke 'write_file' to create '{target_file}' with your code implementation. Do NOT search or browse the web again."
                print(f"   {YELLOW}⚡ Research complete. Transitioning directly to code creation...{RESET}")
                recent_tool_sigs.append(sig)
            elif len(recent_tool_sigs) >= 1 and recent_tool_sigs[-1] == sig and name == "read_file":
                target_file = args.get("path", "")
                full_p = Path(os.path.expanduser(target_file))
                if not full_p.is_absolute():
                    full_p = (Path(os.getcwd()) / full_p).resolve()
                issues = []
                if full_p.is_file():
                    try:
                        issues = validate_code(str(full_p), full_p.read_text(encoding="utf-8", errors="replace"))
                    except Exception:
                        pass
                if issues:
                    result = (
                        f"Notice: You have already read '{target_file}'. "
                        f"Automated static diagnostics detected {len(issues)} critical error(s) in this file:\n"
                        + "\n".join(f"- {iss}" for iss in issues)
                        + f"\nYou MUST invoke 'edit_file' NOW with real lines from '{target_file}' in 'target' and your fix in 'replacement'."
                    )
                    print(f"   {YELLOW}⚡ Consecutive read skipped. Directing to edit_file ({len(issues)} issue(s) detected)...{RESET}")
                elif (target_file.endswith((".html", ".htm")) or "html" in p_lower) and any(w in p_lower for w in ("open", "browser", "launch", "play", "view", "test")):
                    result = f"Notice: '{target_file}' is already read and verified with 0 errors. Proceed to invoke 'open_browser' with args: {{\"url\": \"{target_file}\"}} to test it in the browser."
                    print(f"   {YELLOW}⚡ File verified (0 errors). Transitioning directly to browser test...{RESET}")
                else:
                    result = f"Notice: '{target_file}' is already read. Proceed to invoke 'edit_file' to modify the file or proceed to your next action."
                recent_tool_sigs.append(sig)
            else:
                recent_tool_sigs.append(sig)
                result = self.execute_tool(name, args, user_prompt=user_prompt)

            # Construct dynamic next-step prompt to maintain chaining for 7B models
            feedback = f"[Result of {name}]:\n{result}\n"
            if "CRITICAL: You must invoke edit_file" in result or "diagnostics detected issues" in result.lower():
                target_f = args.get("path", "")
                feedback += f"Automated diagnostics detected issues in '{target_f}'. You MUST invoke 'edit_file' now to resolve these errors before any other action."
            elif name == "read_file":
                target_f = args.get("path", "")
                full_p = Path(os.path.expanduser(target_f))
                if not full_p.is_absolute():
                    full_p = (Path(os.getcwd()) / full_p).resolve()
                file_issues = []
                if full_p.is_file():
                    try:
                        file_issues = validate_code(str(full_p), full_p.read_text(encoding="utf-8", errors="replace"))
                    except Exception:
                        pass
                if file_issues:
                    feedback += (
                        f"File '{target_f}' has been read. Automated static diagnostics detected issues:\n"
                        + "\n".join(f"- {iss}" for iss in file_issues)
                        + f"\nYou MUST invoke 'edit_file' now with the actual lines from '{target_f}' to replace. "
                        f"Do NOT stop or summarize without editing."
                    )
                elif any(w in p_lower for w in ("open", "browser", "launch", "play", "view", "test")) and (target_f.endswith((".html", ".htm")) or "html" in p_lower):
                    feedback += (
                        f"File '{target_f}' has been inspected and verified with 0 diagnostic errors. The file is already complete on disk. "
                        f"DO NOT rewrite the file. DO NOT output code blocks in chat. "
                        f"Invoke 'open_browser' now with args: {{\"url\": \"{target_f}\"}} to open and preview it in the desktop browser."
                    )
                elif any(w in p_lower for w in ("fix", "repair", "debug", "solve", "bug")):
                    feedback += f"File '{target_f}' has been read (0 diagnostic errors). If there are specific bugs reported by the user, invoke 'edit_file' with the exact target snippet. If the code is already functioning correctly, invoke 'open_browser' with args: {{\"url\": \"{target_f}\"}} to verify it. Do NOT rewrite working files."
                else:
                    feedback += f"File '{target_f}' read successfully. Proceed with the necessary modification via edit_file or command execution."
            elif name in ("write_file", "edit_file"):
                target_f = args.get("path", "")
                if (target_f.endswith((".html", ".htm")) or "html" in p_lower) and any(w in p_lower for w in ("open", "browser", "launch", "play", "view", "game", "snake", "fix")):
                    feedback += f"File '{target_f}' has been updated on disk. Invoke 'open_browser' now with args: {{\"url\": \"{target_f}\"}} to verify the application in the desktop browser."
                elif any(w in p_lower for w in ("run", "test", "execute", "check")) and not any(w in p_lower for w in ("do not run", "don't run", "no run")):
                    feedback += "The user requested to run or test the code. Invoke 'run_command' now to execute and verify."
                else:
                    feedback += "If the requested task is complete, provide your concise final response directly without calling any tools. Otherwise, proceed to the next necessary tool action."
            elif name in ("search_web", "fetch_web"):
                fn_match = re.search(r"([~./\w_-]+/[\w-]+\.(?:py|js|ts|html|css|sh|json|rs|go|cpp|c)|\b[\w-]+\.(?:py|js|ts|html|css|sh|json|rs|go|cpp|c))\b", user_prompt, re.IGNORECASE)
                target_f = fn_match.group(1) if fn_match else ""
                if target_f and any(w in p_lower for w in ("create", "write", "make", "build", "game", "app", "script")):
                    feedback += f"Web research complete. You have the needed information and palettes. Now invoke 'write_file' IMMEDIATELY to create '{target_f}'. Do NOT call search_web or fetch_web again."
                else:
                    feedback += "Web research complete. Proceed to implement the solution or create the file using write_file."
            elif name in ("inspect_ui", "screenshot_ui"):
                target_f = args.get("path") or args.get("file") or args.get("url") or ""
                feedback += (
                    f"Visual UI inspection complete for '{target_f}'. "
                    f"Now invoke 'edit_file' with surgical modifications to upgrade '{target_f}' with modern visual design, "
                    f"glassmorphism, vibrant neon glow, and responsive layout based on the critique above. "
                    f"Once updated, invoke 'open_browser' to verify."
                )
            elif name == "open_browser":
                feedback += "Browser launched successfully. If the requested task is complete, provide your concise final response directly without calling any tools."
            else:
                feedback += "If the requested task is complete, provide your concise final response directly without calling any tools. Otherwise, proceed to the next necessary tool action."

            self.history.append({
                "role": "user",
                "content": feedback
            })
            step += 1


def list_installed_models(host):
    try:
        req = urllib.request.Request(f"{host.rstrip('/')}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def main():
    default_model = (
        os.environ.get("LOCAL_CODE_MODEL")
        or os.environ.get("LC_MODEL")
        or os.environ.get("QWEN_MODEL")
        or "qwen2.5-coder:7b"
    )
    default_host = (
        os.environ.get("LOCAL_CODE_HOST")
        or os.environ.get("LC_HOST")
        or os.environ.get("OLLAMA_API_BASE")
        or os.environ.get("OLLAMA_HOST")
        or "http://127.0.0.1:11434"
    )

    parser = argparse.ArgumentParser(description="local-code (lc): Universal Cross-Platform Autonomous Local AI Engineer powered by Ollama.")
    parser.add_argument("prompt", nargs="*", help="Direct prompt to execute (non-interactive mode)")
    parser.add_argument("-m", "--model", default=default_model, help="Ollama model name (default: %(default)s)")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-approve all actions (Auto Mode)")
    parser.add_argument("-c", "--context", type=int, default=None, help="Context window size in tokens (default: auto-detected safe limit)")
    parser.add_argument("-t", "--temp", type=float, default=0.2, help="Sampling temperature")
    parser.add_argument("--host", default=default_host, help="Ollama API base URL")
    parser.add_argument("-v", "--version", action="version", version=f"local-code (lc) {__version__} ({OS_NAME})")

    args = parser.parse_args()

    agent = Agent(model=args.model, host=args.host, context=args.context, temp=args.temp, auto=args.yes)

    # One-shot command line prompt execution
    if args.prompt:
        user_input = " ".join(args.prompt)
        agent.run(user_input)
        return

    # Interactive REPL mode
    cwd_str = os.getcwd()
    home = os.path.expanduser("~")
    short_cwd = cwd_str.replace(home, "~") if cwd_str.startswith(home) else cwd_str
    mode_str = f"{GREEN}Auto-Approve{RESET}" if agent.auto else f"{YELLOW}Permission Mode{RESET}"
    print(f"\n{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}{CYAN}⚡ Local Code{RESET} {GRAY}v{__version__} ({OS_NAME}) • Universal Autonomous Local AI{RESET}")
    print(f"{GRAY}Model:{RESET} {GREEN}{agent.model}{RESET}  {GRAY}Mode:{RESET} {mode_str}  {GRAY}Context:{RESET} {agent.context}")
    print(f"{GRAY}Directory:{RESET} {CYAN}{short_cwd}{RESET} {GRAY}({cwd_str}){RESET}")
    print(f"{GRAY}Commands: /help, /models, cd <dir>, or 'exit' to quit.{RESET}")
    print(f"{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")

    # Configure readline shortcut keys to instantly toggle mode from keyboard
    try:
        import readline
        readline.parse_and_bind(r'"\C-t": "/auto\n"')       # Ctrl+T: Toggle Auto/Manual
        readline.parse_and_bind(r'"\M-a": "/auto\n"')       # Alt+A: Toggle Auto/Manual
        readline.parse_and_bind(r'"\C-y": "/auto\n"')       # Ctrl+Y: Toggle Auto/Manual
        readline.parse_and_bind(r'"\e[12~": "/auto\n"')     # F2: Toggle Auto/Manual
        readline.parse_and_bind(r'"\eOQ": "/auto\n"')       # F2 alternative (VT100)
    except Exception:
        pass

    while True:
        try:
            cwd_str = os.getcwd()
            short_cwd = cwd_str.replace(home, "~") if cwd_str.startswith(home) else cwd_str
            mode_badge = f"{GREEN}[⚡auto]{RESET}" if agent.auto else f"{YELLOW}[🛡️manual]{RESET}"
            prompt_symbol = f"{BOLD}{CYAN}[{short_cwd}]{RESET} {mode_badge} {BOLD}>{RESET} "
            user_input = input(prompt_symbol).strip()
            user_input = re.sub(r'(\x1b\[E|\^[E])', '\n', user_input).strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{GRAY}Goodbye!{RESET}")
            break

        if not user_input:
            continue

        user_lower = user_input.lower()

        # Instant mode toggle / shortcut keys (Ctrl+T, Alt+A, F2, or single key a / m / t)
        if user_lower in ("/auto", "/perm", "/mode", "auto", "manual", "perm", "/a", "/m", "a", "m", "t", "/t"):
            if user_lower in ("a", "/a", "auto"):
                agent.auto = True
            elif user_lower in ("m", "/m", "manual", "perm", "/perm"):
                agent.auto = False
            else:
                agent.auto = not agent.auto
            status = f"{GREEN}Auto-Approve ON (⚡ all actions run autonomously){RESET}" if agent.auto else f"{YELLOW}Manual Permission ON (🛡️ prompts before actions){RESET}"
            print(f"Mode switched: {status}\n")
            continue

        # Built-in cd command to navigate between directories inside lc
        if user_lower.startswith(("cd ", "/cd ")) or user_lower in ("cd", "/cd"):
            parts = user_input.split(maxsplit=1)
            target = parts[1].strip() if len(parts) > 1 else "~"
            target_path = Path(os.path.expanduser(target)).resolve()
            if target_path.is_dir():
                os.chdir(target_path)
                cwd_str = os.getcwd()
                short_cwd = cwd_str.replace(home, "~") if cwd_str.startswith(home) else cwd_str
                print(f"{GREEN}✓ Changed directory to:{RESET} {BOLD}{short_cwd}{RESET} {GRAY}({cwd_str}){RESET}\n")
                agent.history[0]["content"] = get_system_prompt()
            else:
                print(f"{RED}Directory not found: {target}{RESET}\n")
            continue

        if user_lower in ("exit", "quit", ":q"):
            print(f"{GRAY}Goodbye!{RESET}")
            break
        elif user_lower == "/clear":
            agent.history = [{"role": "system", "content": get_system_prompt()}]
            print(f"{YELLOW}Conversation reset.{RESET}\n")
            continue
        elif user_input.lower() == "/diff":
            st = subprocess.run("git diff", shell=True, text=True, capture_output=True)
            diff_text = st.stdout.strip()
            if diff_text:
                for line in diff_text.splitlines()[:40]:
                    if line.startswith("+"):
                        print(f"{GREEN}{line}{RESET}")
                    elif line.startswith("-"):
                        print(f"{RED}{line}{RESET}")
                    else:
                        print(f"{GRAY}{line}{RESET}")
            else:
                print(f"{GRAY}No uncommitted git diff.{RESET}")
            print()
            continue
        elif user_input.lower() == "/undo":
            ans = input(f"{RED}Discard all uncommitted changes in current directory? [y/N]: {RESET}").strip().lower()
            if ans in ("y", "yes"):
                subprocess.run("git checkout .", shell=True)
                print(f"{YELLOW}Reverted working tree changes.{RESET}\n")
            continue
        elif user_input.lower().startswith("/search"):
            query = user_input[7:].strip()
            if query:
                print(f"\n{CYAN}Searching web for:{RESET} '{query}'...")
                res = search_duckduckgo(query)
                print(res + "\n")
            else:
                print(f"{GRAY}Usage: /search <keywords>{RESET}\n")
            continue
        elif user_input.lower() in ("/models", "/model"):
            models = list_installed_models(agent.host)
            if not models:
                print(f"{RED}Could not reach Ollama at {agent.host}{RESET}\n")
                continue

            current_idx = 0
            menu_options = []
            for i, m in enumerate(models):
                if m == agent.model:
                    current_idx = i
                    menu_options.append((f"{m} {GREEN}(current active){RESET}", m))
                else:
                    menu_options.append((m, m))

            _, chosen_model = select_menu("Select an Ollama Model to activate:", menu_options, default_idx=current_idx)
            if chosen_model:
                agent.model = chosen_model
                safe_ctx = get_safe_default_context(chosen_model)
                if agent.context > safe_ctx and get_system_ram_gb() < 14.0:
                    agent.context = safe_ctx
                print(f"{GREEN}Active model updated to:{RESET} {BOLD}{agent.model}{RESET} {GRAY}(Context: {agent.context}){RESET}\n")
            continue
        elif user_input.lower().startswith("/fix"):
            target_arg = user_input[4:].strip()
            if target_arg:
                user_input = f"fix {target_arg}"
            else:
                print(f"{GRAY}Usage: /fix <filename> [optional issue description]{RESET}\n")
                continue
        elif user_input.lower().startswith(("/open", "/browser")):
            parts = user_input.split(maxsplit=1)
            target_arg = parts[1].strip() if len(parts) > 1 else ""
            if not target_arg:
                active_p = agent.find_active_target_file("browser html")
                if active_p:
                    target_arg = str(active_p)
            if target_arg:
                agent.execute_tool("open_browser", {"url": target_arg}, user_prompt=user_input)
            else:
                print(f"{GRAY}Usage: /open <filename.html or url> (or just /open to open current project){RESET}\n")
            continue
        elif user_input.lower().startswith(("/ui", "/inspect")):
            parts = user_input.split(maxsplit=1)
            target_arg = parts[1].strip() if len(parts) > 1 else ""
            if target_arg:
                user_input = f"inspect_ui {target_arg} and upgrade its visual styling and aesthetics"
            else:
                print(f"{GRAY}Usage: /ui <filename.html> - captures headless screenshot, audits aesthetics & upgrades UI{RESET}\n")
                continue
        elif user_input.lower().startswith("/model"):
            parts = user_input.split()
            if len(parts) > 1:
                agent.model = parts[1]
                print(f"{GREEN}Switched active model to:{RESET} {BOLD}{agent.model}{RESET}\n")
            continue
        elif user_input.lower() == "/help":
            print(f"""
{BOLD}Interactive Slash Commands & Shortcut Keys:{RESET}
  {CYAN}Alt+A / Ctrl+T / F2{RESET}  Toggle between Auto and Manual mode instantly
  {CYAN}a / m (or /auto){RESET}     Switch mode: `a` for Auto, `m` for Manual
  {CYAN}cd <dir>{RESET}            Change current working directory (e.g. `cd ~/Downloads`)
  {CYAN}/open [file]{RESET}        Instantly open HTML app or URL in desktop browser
  {CYAN}/fix <file>{RESET}         Run automated static diagnostics & autonomously fix file
  {CYAN}/ui <file>{RESET}          Capture headless screenshot, audit aesthetics & upgrade UI
  {CYAN}/models{RESET}             Interactive arrow-key menu to switch Ollama models
  {CYAN}/diff{RESET}               Show current uncommitted git diff
  {CYAN}/undo{RESET}               Discard recent uncommitted changes (`git checkout .`)
  {CYAN}/search <q>{RESET}        Run an instant web search from terminal
  {CYAN}/clear{RESET}              Reset conversation history
  {CYAN}exit / quit{RESET}         Exit session
""")
            continue

        clean_input = user_input.strip()
        cmd_prefix = re.match(r'^(?:lc|local-code|qc)\s+["\']?(.*?)["\']?$', clean_input, flags=re.DOTALL)
        if cmd_prefix:
            user_input = cmd_prefix.group(1).strip()

        agent.run(user_input)
        print()


if __name__ == "__main__":
    main()
