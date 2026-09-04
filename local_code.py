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
import signal
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

__version__ = "1.4.0"

# Operating System Detection
OS_NAME = platform.system()
IS_WINDOWS = OS_NAME.lower() == "windows"
IS_MACOS = OS_NAME.lower() == "darwin"
IS_LINUX = OS_NAME.lower() == "linux"

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
- `open_browser`: Open a URL in the desktop web browser.
  args: `{"url": "https://..."}`
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

## Core Operational Directives
1. FILE EDITING vs CREATION:
   - When modifying an existing file, NEVER rewrite or recreate the file with `write_file`.
   - ALWAYS read the file with `read_file` first, then use `edit_file` to replace only the targeted snippet.
   - Use `write_file` ONLY when creating brand new files that do not exist on disk.
2. WEB RESEARCH & IMPLEMENTATION:
   - When asked to search, research, or implement external libraries/APIs, use `search_web` to discover solutions, `fetch_web` to inspect details, and then apply the code directly.
3. NATIVE ACCESS & CAPABILITIES:
   - NEVER claim "I am just a language model", "I cannot access the web", or "I cannot do anything outside this text box". You have full system and web access.
4. NO CODE LECTURES:
   - Do NOT lecture the user on basic code syntax or dump long code files into the chat. Apply the changes to the files, verify them, and report concise outcomes.
5. SELF-HEALING:
   - If tests fail, builds break, or commands error, inspect the error trace, patch the code, and re-run tests until passing.
"""


def get_system_prompt():
    return SYSTEM_PROMPT_TEMPLATE.replace("{os_name}", OS_NAME)


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
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    r, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if r:
                        ch2 = sys.stdin.read(1)
                        if ch2 == '[':
                            ch3 = sys.stdin.read(1)
                            if ch3 == 'A': return 'up'
                            if ch3 == 'B': return 'down'
                            if ch3 == 'C': return 'right'
                            if ch3 == 'D': return 'left'
                    return 'esc'
                if ch in ('\r', '\n'): return 'enter'
                if ch == '\x03': return 'ctrl_c'
                return ch.lower()
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
            if key is None:
                break

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


class Agent:
    def __init__(self, model="qwen2.5-coder:7b", host="http://127.0.0.1:11434", context=4096, temp=0.2, auto=False):
        self.model = model
        self.host = host.rstrip("/")
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

    def execute_tool(self, name, args):
        if name == "search_web":
            query = args.get("query", "")
            print(f"\n{CYAN}🔍 Web Search:{RESET} '{query}'")
            res = search_duckduckgo(query)
            print(f"   {GRAY}Search complete. Formulating next step...{RESET}")
            return res

        elif name == "fetch_web":
            url = args.get("url", "")
            print(f"\n{CYAN}🌐 Browsing:{RESET} {url}")
            try:
                preview, total_chars = fetch_url_content(url)
                print(f"   {GRAY}Retrieved {total_chars} characters.{RESET}")
                return preview
            except Exception as e:
                return f"Error browsing '{url}': {e}"

        elif name == "open_browser":
            url = args.get("url", "")
            print(f"\n{CYAN}🖥️  Launch Browser:{RESET} {url}")
            if not self.ask_permission(f"opening '{url}' in desktop browser"):
                return f"Opening browser for '{url}' skipped by user."
            try:
                webbrowser.open(url)
                print(f"   {GREEN}✓ Opened in default web browser{RESET}")
                return f"Successfully opened '{url}' in default browser."
            except Exception as e:
                return f"Error opening browser: {e}"

        elif name in ("edit_file", "patch_file"):
            path = args.get("path", "")
            target = args.get("target", "")
            replacement = args.get("replacement", "")
            print(f"\n{MAGENTA}✏️  Edit File:{RESET} {BOLD}{path}{RESET}")
            try:
                p = Path(path)
                if not p.is_file():
                    return f"Error: File '{path}' does not exist. Use write_file for new files."
                old_text = p.read_text(encoding="utf-8", errors="replace")
                
                # Normalize line endings for reliable cross-platform matching (CRLF vs LF)
                target_norm = target.replace("\r\n", "\n")
                old_text_norm = old_text.replace("\r\n", "\n")
                replacement_norm = replacement.replace("\r\n", "\n")

                if target_norm not in old_text_norm:
                    norm_target = "\n".join(line.strip() for line in target_norm.strip().splitlines())
                    norm_file = "\n".join(line.strip() for line in old_text_norm.splitlines())
                    if norm_target not in norm_file:
                        return f"Error: Target snippet not found in '{path}'. Please read the file with read_file first to see the exact lines."

                if old_text_norm.count(target_norm) > 1:
                    return f"Error: Target snippet occurs {old_text_norm.count(target_norm)} times in '{path}'. Include more surrounding context lines to make it unique."

                new_text = old_text_norm.replace(target_norm, replacement_norm, 1)

                # Show colored diff before applying
                print_diff(old_text_norm, new_text, path)

                if not self.ask_permission(f"modifications to '{path}'"):
                    return f"Editing '{path}' skipped by user."

                p.write_text(new_text, encoding="utf-8")
                print(f"   {GREEN}✓ Successfully updated '{path}'{RESET}")
                return f"File '{path}' successfully edited."
            except Exception as e:
                return f"Error editing '{path}': {e}"

        elif name == "write_file":
            path = args.get("path", "")
            content = args.get("content", "")
            p = Path(path)
            is_new = not p.exists()
            label = "Create New File" if is_new else "Overwrite Entire File"
            print(f"\n{GREEN}💾 {label}:{RESET} {BOLD}{path}{RESET} {GRAY}({len(content)} bytes){RESET}")
            if not self.ask_permission(f"{label.lower()} '{path}'"):
                return f"Writing '{path}' skipped by user."
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
                print(f"   {GREEN}✓ Written '{path}'{RESET}")
                return f"File '{path}' written successfully ({len(content)} bytes)."
            except Exception as e:
                return f"Error writing file '{path}': {e}"

        elif name == "read_file":
            path = args.get("path", "")
            start = args.get("start_line", 1)
            count = args.get("line_count", None)
            print(f"\n{BLUE}📖 Reading:{RESET} {path}")
            try:
                p = Path(path)
                if not p.is_file():
                    return f"Error: File '{path}' does not exist."
                lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
                total = len(lines)
                if start and start > 1:
                    lines = lines[start - 1:]
                if count:
                    lines = lines[:count]
                numbered = [f"{i + (start or 1):4d} | {line}" for i, line in enumerate(lines)]
                print(f"   {GRAY}Read {len(lines)}/{total} lines{RESET}")
                return "\n".join(numbered) or "(empty file)"
            except Exception as e:
                return f"Error reading file '{path}': {e}"

        elif name == "run_command":
            cmd = args.get("command", "").strip()
            cwd = args.get("cwd", None)
            print(f"\n{YELLOW}⚡ Command:{RESET} {BOLD}{cmd}{RESET}" + (f" {GRAY}(in {cwd}){RESET}" if cwd else ""))
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
            print(f"\n{CYAN}📁 Listing:{RESET} {path}")
            try:
                root = Path(path)
                if not root.exists():
                    return f"Error: Path '{path}' not found."
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
                return f"Error listing directory '{path}': {e}"

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

    def extract_tool_call(self, text):
        """Extract tool call using markdown blocks, balanced-brace parsing, and raw JSON fallback."""
        # 1. Try finding markdown code block with json
        blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        for b in blocks:
            try:
                data = json.loads(b)
                if isinstance(data, dict) and "name" in data and "arguments" in data:
                    return data["name"], data.get("arguments", {}), True
            except Exception:
                pass

        # 2. Balanced brace scan for {"name": ..., "arguments": ...}
        # Handles nested braces, code containing CSS/JS, and escaped quotes properly
        pattern = re.compile(r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:', flags=re.DOTALL)
        for m in pattern.finditer(text):
            start = m.start()
            brace_count = 0
            in_string = False
            escape = False
            for i in range(start, len(text)):
                ch = text[i]
                if escape:
                    escape = False
                    continue
                if ch == '\\':
                    escape = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if not in_string:
                    if ch == '{':
                        brace_count += 1
                    elif ch == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            candidate = text[start:i+1]
                            try:
                                data = json.loads(candidate)
                                if isinstance(data, dict) and "name" in data and "arguments" in data:
                                    return data["name"], data.get("arguments", {}), True
                            except Exception:
                                pass
                            break

        # 3. Fallback: try whole string if it starts and ends with { }
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                data = json.loads(stripped)
                if isinstance(data, dict) and "name" in data and "arguments" in data:
                    return data["name"], data.get("arguments", {}), True
            except Exception:
                pass

        return None, None, False

    def stream_turn(self, step=1):
        num_threads = min(os.cpu_count() or 4, 4)
        payload = {
            "model": self.model,
            "messages": self.history,
            "stream": True,
            "options": {
                "num_ctx": self.context,
                "temperature": self.temp,
                "num_thread": num_threads
            }
        }
        url = f"{self.host}/api/chat"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        accumulated = ""
        in_tool_block = False
        printed_prefix = False
        token_count = 0

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                for raw in resp:
                    if not raw.strip():
                        continue
                    chunk = json.loads(raw.decode("utf-8"))
                    token = chunk.get("message", {}).get("content", "")
                    if not token:
                        continue
                    
                    accumulated += token
                    token_count += 1

                    if "```json" in accumulated or '{"name"' in accumulated or '{"name":' in accumulated:
                        in_tool_block = True

                    if in_tool_block:
                        sys.stdout.write(f"\r{CYAN}⚡ [Step {step}] Generating action... ({token_count} tokens){RESET}\033[K")
                        sys.stdout.flush()
                    else:
                        if not printed_prefix and accumulated.strip():
                            sys.stdout.write(f"\r\033[K\n{BOLD}{CYAN}Qwen:{RESET} ")
                            printed_prefix = True
                        if printed_prefix:
                            sys.stdout.write(token)
                            sys.stdout.flush()

            if in_tool_block:
                sys.stdout.write(f"\r\033[K")
                sys.stdout.flush()
            elif printed_prefix:
                print()

            return accumulated
        except Exception as e:
            print(f"\n{RED}Inference error: {e}{RESET}")
            return ""

    def run(self, user_prompt, max_steps=20):
        self.history.append({"role": "user", "content": user_prompt})
        step = 1

        while step <= max_steps:
            print(f"{DIM}[Step {step}] Thinking...{RESET}", end="\r", flush=True)
            res = self.stream_turn(step=step)
            if not res:
                break

            self.history.append({"role": "assistant", "content": res})
            name, args, is_tool = self.extract_tool_call(res)

            if not is_tool:
                break

            print(" " * 30, end="\r")
            result = self.execute_tool(name, args)
            self.history.append({
                "role": "user",
                "content": f"[Result of {name}]:\n{result}\nProceed directly to next action or concise final outcome summary."
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
    parser.add_argument("-c", "--context", type=int, default=4096, help="Context window size in tokens")
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
    mode_str = f"{GREEN}Auto-Approve{RESET}" if agent.auto else f"{YELLOW}Permission Mode{RESET}"
    print(f"\n{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}{CYAN}⚡ Local Code{RESET} {GRAY}v{__version__} ({OS_NAME}) • Universal Autonomous Local AI{RESET}")
    print(f"{GRAY}Model:{RESET} {GREEN}{agent.model}{RESET}  {GRAY}Mode:{RESET} {mode_str}  {GRAY}Context:{RESET} {agent.context}")
    print(f"{GRAY}Type /help for options, /models to select models, or 'exit' to quit.{RESET}")
    print(f"{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")

    while True:
        try:
            cwd_name = Path.cwd().name
            prompt_symbol = f"{BOLD}{GREEN}[{cwd_name}] >{RESET} "
            user_input = input(prompt_symbol).strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{GRAY}Goodbye!{RESET}")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", ":q"):
            print(f"{GRAY}Goodbye!{RESET}")
            break
        elif user_input.lower() == "/clear":
            agent.history = [{"role": "system", "content": get_system_prompt()}]
            print(f"{YELLOW}Conversation reset.{RESET}\n")
            continue
        elif user_input.lower() in ("/auto", "/perm"):
            agent.auto = not agent.auto
            status = f"{GREEN}Auto-Approve ON{RESET}" if agent.auto else f"{YELLOW}Permission Mode ON{RESET}"
            print(f"Mode switched: {status}\n")
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
                print(f"{GREEN}Active model updated to:{RESET} {BOLD}{agent.model}{RESET}\n")
            continue
        elif user_input.lower().startswith("/model"):
            parts = user_input.split()
            if len(parts) > 1:
                agent.model = parts[1]
                print(f"{GREEN}Switched active model to:{RESET} {BOLD}{agent.model}{RESET}\n")
            continue
        elif user_input.lower() == "/help":
            print(f"""
{BOLD}Interactive Slash Commands:{RESET}
  {CYAN}/models{RESET}        Interactive arrow-key menu to switch Ollama models
  {CYAN}/auto{RESET}          Toggle between Permission Mode and Auto-Approve Mode
  {CYAN}/diff{RESET}          Show current uncommitted git diff
  {CYAN}/undo{RESET}          Discard recent uncommitted changes (`git checkout .`)
  {CYAN}/search <q>{RESET}   Run an instant web search from terminal
  {CYAN}/clear{RESET}         Reset conversation history
  {CYAN}exit / quit{RESET}    Exit session
""")
            continue

        agent.run(user_input)
        print()


if __name__ == "__main__":
    main()
