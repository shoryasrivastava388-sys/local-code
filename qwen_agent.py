#!/usr/bin/env python3
"""
qwen-agent - Local autonomous AI software engineer powered by Ollama.
Autonomous file editing, terminal execution, codebase search, and web browsing.
"""

import argparse
import fnmatch
import json
import os
import re
import signal
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

__version__ = "1.0.0"

# ANSI Terminal Colors
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

SYSTEM_PROMPT = """You are an autonomous senior software engineer operating directly on the local machine.
You have native access to the system via tools to read, edit, execute, search, and browse.

## Tools
To perform actions, output a JSON code block:
```json
{"name": "tool_name", "arguments": {"param": "value"}}
```

Available tools:
- `run_command`: Run a bash command in the terminal.
  args: `{"command": "string", "cwd": "optional_path"}`
- `read_file`: Read file contents with optional line numbers.
  args: `{"path": "string", "start_line": optional_int, "line_count": optional_int}`
- `write_file`: Create or overwrite a file.
  args: `{"path": "string", "content": "string"}`
- `patch_file`: Replace an exact code snippet in an existing file.
  args: `{"path": "string", "target": "old_snippet", "replacement": "new_snippet"}`
- `list_dir`: List files and subdirectories.
  args: `{"path": "optional_path", "max_depth": optional_int}`
- `search_code`: Regex or keyword search across files.
  args: `{"query": "string", "path": "optional_path", "pattern": "optional_glob"}`
- `git_diff`: Show current git status and unstaged/staged diffs.
  args: `{"path": "optional_path"}`
- `fetch_web`: Fetch clean content from any URL or GitHub repo.
  args: `{"url": "https://..."}`
- `open_browser`: Open a URL in the desktop web browser.
  args: `{"url": "https://..."}`

## Core Operational Rules
1. ACTION FIRST: Don't talk about what you plan to do—do it. Use tools immediately.
2. NO CODE EXPLANATIONS: Do NOT teach, lecture, or explain basic programming syntax. Provide only concise, outcome-oriented status and summaries.
3. PERSISTENCE & SELF-HEALING: If a test fails, a build breaks, or a command errors, do NOT stop. Inspect the error trace, patch the file, and re-run tests until it works. Push to the limits to complete the goal.
4. TARGETED PATCHES: Prefer `patch_file` for targeted modifications in existing codebases rather than rewriting entire files.
5. VERIFICATION: Always verify your changes by running tests or executing the code before reporting completion.
"""


class Agent:
    def __init__(self, model="qwen2.5-coder:7b", host="http://127.0.0.1:11434", context=4096, temp=0.2, auto=False):
        self.model = model
        self.host = host.rstrip("/")
        self.context = context
        self.temp = temp
        self.auto = auto
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]

    def execute_tool(self, name, args):
        if name == "run_command":
            cmd = args.get("command", "").strip()
            cwd = args.get("cwd", None)
            print(f"\n{YELLOW}⚡ Running:{RESET} {BOLD}{cmd}{RESET}" + (f" {GRAY}(in {cwd}){RESET}" if cwd else ""))
            
            if not self.auto:
                try:
                    ans = input(f"   {GRAY}Approve execution? [Y/n/a(all)]: {RESET}").strip().lower()
                    if ans == "a":
                        self.auto = True
                    elif ans not in ("", "y", "yes"):
                        print(f"   {RED}Skipped.{RESET}")
                        return "Command skipped by user."
                except (EOFError, KeyboardInterrupt):
                    return "Command cancelled by user."
            
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
                    print(f"   {GRAY}(No output, exit code: {res.returncode}){RESET}")
                return clean or "(Command executed with no output)"
            except subprocess.TimeoutExpired:
                return "Error: Command timed out after 180 seconds."
            except Exception as e:
                return f"Error executing command: {e}"

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

        elif name == "write_file":
            path = args.get("path", "")
            content = args.get("content", "")
            print(f"\n{GREEN}💾 Writing:{RESET} {BOLD}{path}{RESET} {GRAY}({len(content)} bytes){RESET}")
            try:
                p = Path(path)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
                print(f"   {GREEN}✓ Written{RESET}")
                return f"Successfully written to '{path}'."
            except Exception as e:
                return f"Error writing file: {e}"

        elif name == "patch_file":
            path = args.get("path", "")
            target = args.get("target", "")
            replacement = args.get("replacement", "")
            print(f"\n{MAGENTA}✏️  Patching:{RESET} {BOLD}{path}{RESET}")
            try:
                p = Path(path)
                if not p.is_file():
                    return f"Error: File '{path}' not found."
                text = p.read_text(encoding="utf-8")
                if target not in text:
                    return f"Error: Target snippet not found in '{path}'."
                if text.count(target) > 1:
                    return f"Error: Target snippet is not unique in '{path}'. Include more surrounding lines."
                new_text = text.replace(target, replacement, 1)
                p.write_text(new_text, encoding="utf-8")
                print(f"   {GREEN}✓ Patched{RESET}")
                return f"Successfully patched '{path}'."
            except Exception as e:
                return f"Error patching '{path}': {e}"

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
                return "\n".join(tree[:100]) or "(empty directory)"
            except Exception as e:
                return f"Error listing '{path}': {e}"

        elif name == "search_code":
            query = args.get("query", "")
            search_path = args.get("path", ".")
            pat = args.get("pattern", "*")
            print(f"\n{CYAN}🔍 Searching:{RESET} '{query}' in {search_path}")
            try:
                # Fast path using ripgrep or grep if available
                cmd = f"rg -n -i --max-count 40 '{query}' {search_path} 2>/dev/null || grep -rnI --exclude-dir=.git '{query}' {search_path} 2>/dev/null"
                res = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=15)
                lines = (res.stdout or "").strip().splitlines()[:40]
                if lines:
                    print(f"   {GRAY}{len(lines)} matches found{RESET}")
                    return "\n".join(lines)
                return f"No matches found for '{query}'."
            except Exception as e:
                return f"Error searching: {e}"

        elif name == "git_diff":
            path = args.get("path", ".")
            print(f"\n{CYAN}🌿 Git Status & Diff:{RESET}")
            try:
                st = subprocess.run("git status --short", shell=True, text=True, capture_output=True, cwd=path)
                diff = subprocess.run("git diff", shell=True, text=True, capture_output=True, cwd=path)
                res = f"STATUS:\n{st.stdout}\nDIFF:\n{diff.stdout[:3000]}"
                return res.strip() or "Clean git working tree."
            except Exception as e:
                return f"Error running git: {e}"

        elif name == "fetch_web":
            url = args.get("url", "")
            print(f"\n{CYAN}🌐 Browsing:{RESET} {url}")
            try:
                res = subprocess.run(
                    ["curl", "-sL", "-A", "Mozilla/5.0 (X11; Linux x86_64)", "--max-time", "15", url],
                    capture_output=True, text=True
                )
                html = res.stdout if res.returncode == 0 and res.stdout else ""
                if not html:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        html = resp.read().decode("utf-8", errors="replace")
                
                text = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
                preview = text[:5000]
                print(f"   {GRAY}Retrieved {len(text)} characters{RESET}")
                return preview + ("\n...(content truncated)" if len(text) > 5000 else "")
            except Exception as e:
                return f"Error browsing '{url}': {e}"

        elif name == "open_browser":
            url = args.get("url", "")
            print(f"\n{CYAN}🖥️  Launching browser:{RESET} {url}")
            try:
                subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Opened {url} in default browser."
            except Exception as e:
                return f"Error opening browser: {e}"

        return f"Unknown tool '{name}'."

    def extract_tool_call(self, text):
        match = re.search(r"```(?:json)?\s*(\{\s*\"name\"\s*:\s*\"([^\"]+)\"\s*,\s*\"arguments\"\s*:\s*(\{.*?\})\s*\})\s*```", text, flags=re.DOTALL)
        if match:
            try:
                return match.group(2), json.loads(match.group(3)), True
            except Exception:
                pass
        match = re.search(r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{.*?\})\s*\}', text, flags=re.DOTALL)
        if match:
            try:
                return match.group(1), json.loads(match.group(2)), True
            except Exception:
                pass
        return None, None, False

    def stream_turn(self):
        payload = {
            "model": self.model,
            "messages": self.history,
            "stream": True,
            "options": {
                "num_ctx": self.context,
                "temperature": self.temp
            }
        }
        url = f"{self.host}/api/chat"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        accumulated = ""
        is_tool = None
        printed_prefix = False

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

                    if is_tool is None:
                        s = accumulated.strip()
                        if len(s) >= 4:
                            if s.startswith("```") or s.startswith("{"):
                                is_tool = True
                            else:
                                is_tool = False
                                if not printed_prefix:
                                    print(f"\n{BOLD}{CYAN}Qwen:{RESET} ", end="", flush=True)
                                    printed_prefix = True
                                print(accumulated, end="", flush=True)
                    elif is_tool is False:
                        print(token, end="", flush=True)

            if printed_prefix:
                print()

            return accumulated
        except Exception as e:
            print(f"\n{RED}Inference error: {e}{RESET}")
            return ""

    def run(self, user_prompt, max_steps=20):
        self.history.append({"role": "user", "content": user_prompt})
        step = 1

        while step <= max_steps:
            print(f"{DIM}Thinking...{RESET}", end="\r", flush=True)
            res = self.stream_turn()
            if not res:
                break

            self.history.append({"role": "assistant", "content": res})
            name, args, is_tool = self.extract_tool_call(res)

            if not is_tool:
                break

            print(" " * 20, end="\r")
            result = self.execute_tool(name, args)
            self.history.append({
                "role": "user",
                "content": f"[Result of {name}]:\n{result}\nContinue directly with next action or concise final report."
            })
            step += 1


def main():
    parser = argparse.ArgumentParser(description="qwen-agent: Local autonomous coding & computer agent.")
    parser.add_argument("prompt", nargs="*", help="Direct prompt to execute (non-interactive mode)")
    parser.add_argument("-m", "--model", default=os.environ.get("QWEN_MODEL", "qwen2.5-coder:7b"), help="Ollama model")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-approve terminal commands")
    parser.add_argument("-c", "--context", type=int, default=4096, help="Context size in tokens")
    parser.add_argument("-t", "--temp", type=float, default=0.2, help="Sampling temperature")
    parser.add_argument("--host", default=os.environ.get("OLLAMA_API_BASE", "http://127.0.0.1:11434"), help="Ollama host")
    parser.add_argument("-v", "--version", action="version", version=f"qwen-agent {__version__}")

    args = parser.parse_args()

    agent = Agent(model=args.model, host=args.host, context=args.context, temp=args.temp, auto=args.yes)

    # One-shot command line prompt execution
    if args.prompt:
        user_input = " ".join(args.prompt)
        agent.run(user_input)
        return

    # Interactive REPL mode
    print(f"\n{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}{CYAN}⚡ Qwen Code Agent{RESET} {GRAY}v{__version__} • Local Autonomous Engineer{RESET}")
    print(f"{GRAY}Model:{RESET} {GREEN}{args.model}{RESET}  {GRAY}Auto-Run:{RESET} {'ON' if args.yes else 'OFF'}  {GRAY}Context:{RESET} {args.context}")
    print(f"{GRAY}Type /help for options, or 'exit' to quit.{RESET}")
    print(f"{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")

    while True:
        try:
            cwd_name = Path.cwd().name
            user_input = input(f"{BOLD}{GREEN}[{cwd_name}] >{RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{GRAY}Goodbye!{RESET}")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", ":q"):
            print(f"{GRAY}Goodbye!{RESET}")
            break
        elif user_input.lower() == "/clear":
            agent.history = [{"role": "system", "content": SYSTEM_PROMPT}]
            print(f"{YELLOW}Conversation reset.{RESET}\n")
            continue
        elif user_input.lower() == "/auto":
            agent.auto = not agent.auto
            print(f"{YELLOW}Auto-run commands: {'ON' if agent.auto else 'OFF'}{RESET}\n")
            continue
        elif user_input.lower() == "/help":
            print(f"""
{BOLD}Commands:{RESET}
  {CYAN}/auto{RESET}          Toggle command auto-approval on/off
  {CYAN}/clear{RESET}         Reset conversation context
  {CYAN}exit / quit{RESET}    Exit agent
""")
            continue

        agent.run(user_input)
        print()


if __name__ == "__main__":
    main()
