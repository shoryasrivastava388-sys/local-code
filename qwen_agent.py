#!/usr/bin/env python3
"""
qwen-agent - Autonomous Local AI Engineer powered by Ollama.
Supports any Ollama model (Qwen, DeepSeek, Llama, Mistral).
Features: permission & auto modes, file creation without chat spam,
live web browsing, desktop browser launch, and self-healing execution.
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

__version__ = "1.1.0"

# ANSI Terminal Styling
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

SYSTEM_PROMPT = """You are an autonomous senior software engineer operating directly on the local operating system.
You are equipped with live computer tools to browse the web, open the desktop browser, create and edit files, and execute terminal commands.

## Available Tools
To execute an action, output a JSON block:
```json
{"name": "tool_name", "arguments": {"param": "value"}}
```

Tools:
- `fetch_web`: Read and analyze any URL or GitHub repository.
  args: `{"url": "https://..."}`
- `open_browser`: Open a URL in the user's desktop browser (Firefox/Chrome).
  args: `{"url": "https://..."}`
- `write_file`: Create or overwrite a file on disk.
  args: `{"path": "filename", "content": "file text"}`
- `patch_file`: Replace a target snippet in an existing file.
  args: `{"path": "filename", "target": "old_code", "replacement": "new_code"}`
- `read_file`: Read a file's content with line numbers.
  args: `{"path": "filename", "start_line": optional_int, "line_count": optional_int}`
- `run_command`: Run any bash command in the terminal.
  args: `{"command": "command string", "cwd": "optional_path"}`
- `list_dir`: Explore files and directories.
  args: `{"path": "optional_path", "max_depth": optional_int}`
- `search_code`: Search code for keywords or regex.
  args: `{"query": "string", "path": "optional_path"}`
- `git_diff`: View git status and changes.
  args: `{"path": "optional_path"}`

## Critical Operating Directives
1. NATIVE SYSTEM ACCESS: NEVER claim "I am just a language model", "I cannot access the web", or "I cannot do anything outside this text box". You have full native tools. If asked to browse, use `fetch_web`. If asked to open the browser, use `open_browser`.
2. DO NOT DUMP FULL CODE IN CHAT: When asked to write or create code, put the code directly into files using `write_file` or `patch_file`. Do NOT paste large walls of code in the conversation unless the user explicitly asks: "show me the code" or "print the code".
3. NO TUTORIALS / FLUFF: Do not teach or lecture the user on basic code syntax. Deliver crisp, outcome-oriented status and summaries.
4. SELF-HEALING & PERSISTENCE: If a build, command, or test fails, do NOT stop. Inspect the error trace, patch the file, and re-test until it works. Push to the limits to accomplish the objective.
"""


class Agent:
    def __init__(self, model="qwen2.5-coder:7b", host="http://127.0.0.1:11434", context=4096, temp=0.2, auto=False):
        self.model = model
        self.host = host.rstrip("/")
        self.context = context
        self.temp = temp
        self.auto = auto
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]

    def ask_permission(self, action_desc):
        """Prompts user for approval unless in auto mode."""
        if self.auto:
            return True
        try:
            prompt = f"   {GRAY}Allow {action_desc}? [Y/n/a(auto-all)]: {RESET}"
            ans = input(prompt).strip().lower()
            if ans == "a":
                self.auto = True
                print(f"   {YELLOW}⚡ Auto-mode enabled for remaining actions.{RESET}")
                return True
            elif ans in ("", "y", "yes"):
                return True
            else:
                print(f"   {RED}Action skipped by user.{RESET}")
                return False
        except (EOFError, KeyboardInterrupt):
            print(f"\n   {RED}Action cancelled.{RESET}")
            return False

    def execute_tool(self, name, args):
        if name == "run_command":
            cmd = args.get("command", "").strip()
            cwd = args.get("cwd", None)
            print(f"\n{YELLOW}⚡ Command:{RESET} {BOLD}{cmd}{RESET}" + (f" {GRAY}(in {cwd}){RESET}" if cwd else ""))
            if not self.ask_permission("command execution"):
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

        elif name == "write_file":
            path = args.get("path", "")
            content = args.get("content", "")
            print(f"\n{GREEN}💾 Write File:{RESET} {BOLD}{path}{RESET} {GRAY}({len(content)} bytes){RESET}")
            if not self.ask_permission(f"writing '{path}'"):
                return f"Writing '{path}' skipped by user."
            try:
                p = Path(path)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
                print(f"   {GREEN}✓ Created/updated '{path}'{RESET}")
                return f"File '{path}' successfully written ({len(content)} bytes)."
            except Exception as e:
                return f"Error writing file '{path}': {e}"

        elif name == "patch_file":
            path = args.get("path", "")
            target = args.get("target", "")
            replacement = args.get("replacement", "")
            print(f"\n{MAGENTA}✏️  Patch File:{RESET} {BOLD}{path}{RESET}")
            if not self.ask_permission(f"patching '{path}'"):
                return f"Patching '{path}' skipped by user."
            try:
                p = Path(path)
                if not p.is_file():
                    return f"Error: File '{path}' does not exist."
                text = p.read_text(encoding="utf-8")
                if target not in text:
                    return f"Error: Target snippet not found in '{path}'."
                if text.count(target) > 1:
                    return f"Error: Target snippet is not unique in '{path}'. Provide more context lines."
                new_text = text.replace(target, replacement, 1)
                p.write_text(new_text, encoding="utf-8")
                print(f"   {GREEN}✓ Patched '{path}'{RESET}")
                return f"Successfully patched '{path}'."
            except Exception as e:
                return f"Error patching '{path}': {e}"

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

        elif name == "open_browser":
            url = args.get("url", "")
            print(f"\n{CYAN}🖥️  Launch Browser:{RESET} {url}")
            if not self.ask_permission(f"opening browser for '{url}'"):
                return f"Opening browser for '{url}' skipped by user."
            try:
                subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"   {GREEN}✓ Opened {url} in desktop browser{RESET}")
                return f"Successfully opened {url} in desktop browser."
            except Exception as e:
                return f"Error opening browser: {e}"

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
                print(f"   {GRAY}Retrieved {len(text)} characters. Formulating answer...{RESET}")
                return preview + ("\n...(content truncated)" if len(text) > 5000 else "")
            except Exception as e:
                return f"Error browsing '{url}': {e}"

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
            print(f"\n{CYAN}🔍 Searching:{RESET} '{query}' in {search_path}")
            try:
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
                return f"Error checking git: {e}"

        return f"Unknown tool: '{name}'."

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
                "content": f"[Result of {name}]:\n{result}\nProceed directly to next action or concise outcome summary."
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
    parser = argparse.ArgumentParser(description="qwen-agent: Local autonomous coding & computer agent.")
    parser.add_argument("prompt", nargs="*", help="Direct prompt to execute")
    parser.add_argument("-m", "--model", default=os.environ.get("QWEN_MODEL", "qwen2.5-coder:7b"), help="Ollama model")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-approve all actions (Auto Mode)")
    parser.add_argument("-c", "--context", type=int, default=4096, help="Context size in tokens")
    parser.add_argument("-t", "--temp", type=float, default=0.2, help="Sampling temperature")
    parser.add_argument("--host", default=os.environ.get("OLLAMA_API_BASE", "http://127.0.0.1:11434"), help="Ollama host")
    parser.add_argument("-v", "--version", action="version", version=f"qwen-agent {__version__}")

    args = parser.parse_args()

    agent = Agent(model=args.model, host=args.host, context=args.context, temp=args.temp, auto=args.yes)

    # One-shot execution
    if args.prompt:
        user_input = " ".join(args.prompt)
        agent.run(user_input)
        return

    # Interactive REPL
    mode_str = f"{GREEN}Auto-Approve{RESET}" if agent.auto else f"{YELLOW}Permission Mode{RESET}"
    print(f"\n{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}{CYAN}⚡ Qwen Code Agent{RESET} {GRAY}v{__version__} • Local Autonomous Engineer{RESET}")
    print(f"{GRAY}Model:{RESET} {GREEN}{agent.model}{RESET}  {GRAY}Mode:{RESET} {mode_str}  {GRAY}Context:{RESET} {agent.context}")
    print(f"{GRAY}Type /help for options, /models to list models, or 'exit' to quit.{RESET}")
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
            agent.history = [{"role": "system", "content": SYSTEM_PROMPT}]
            print(f"{YELLOW}Conversation reset.{RESET}\n")
            continue
        elif user_input.lower() in ("/auto", "/perm"):
            agent.auto = not agent.auto
            status = f"{GREEN}Auto-Approve ON{RESET}" if agent.auto else f"{YELLOW}Permission Mode ON{RESET}"
            print(f"Mode switched: {status}\n")
            continue
        elif user_input.lower() == "/models":
            models = list_installed_models(agent.host)
            if models:
                print(f"{BOLD}Installed Ollama Models:{RESET}")
                for m in models:
                    cur = f" {GREEN}(current){RESET}" if m == agent.model else ""
                    print(f"  • {m}{cur}")
                print(f"{GRAY}Use '/model <name>' to switch models.{RESET}\n")
            else:
                print(f"{RED}Could not reach Ollama at {agent.host}{RESET}\n")
            continue
        elif user_input.lower().startswith("/model"):
            parts = user_input.split()
            if len(parts) > 1:
                agent.model = parts[1]
                print(f"{GREEN}Switched model to:{RESET} {BOLD}{agent.model}{RESET}\n")
            else:
                print(f"{GRAY}Current model: {agent.model}. Usage: /model <model_name>{RESET}\n")
            continue
        elif user_input.lower() == "/help":
            print(f"""
{BOLD}Interactive Commands:{RESET}
  {CYAN}/auto{RESET}          Toggle between Permission Mode and Auto-Approve Mode
  {CYAN}/models{RESET}        List all available Ollama models installed locally
  {CYAN}/model <name>{RESET} Switch active model on the fly (e.g. /model deepseek-v4-pro:cloud)
  {CYAN}/clear{RESET}         Reset conversation history
  {CYAN}exit / quit{RESET}    Exit session
""")
            continue

        agent.run(user_input)
        print()


if __name__ == "__main__":
    main()
