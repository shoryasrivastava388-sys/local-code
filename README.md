# ⚡ qwen-agent (`qc`)

> **Autonomous local coding and computer agent powered by Qwen on Ollama.**  
> An open-source, 100% private alternative to Claude Code and Antigravity. Zero subscriptions, zero API keys, zero telemetry, and zero heavy dependencies.

---

> [!WARNING]
> ### 🚧 Active Construction & Work-in-Progress (WIP)
> This project is currently under active development. It is **specifically tuned and optimized for `qwen2.5-coder:7b`** (and local Ollama Qwen models). More features, benchmark evaluations, and multi-model tuning are actively being rolled out.

---

## ✨ Key Features

- **🌐 Live Web Search & Browsing:** Search the live internet (via DuckDuckGo Lite) and extract documentation/code snippets directly with native `curl`—zero API keys required.
- **✏️ Surgical File Editing:** Inspects code and modifies targeted functions with colored unified diffs. Will **never** overwrite or recreate existing files unless asked.
- **💻 Native Terminal Execution:** Runs test suites, builds, shell scripts, and git commands directly on your system.
- **🛡️ Permission & Auto Modes:** Toggle between interactive approval mode (`[Y/n/a]`) and fully autonomous mode (`qc -y`).
- **🖥️ Desktop Browser Control:** Launches URLs in your desktop browser (Firefox/Chrome) when requested.
- **🧠 Action-First & Persistently Self-Healing:** Catches error traces, debugs broken code, patches files, and re-runs tests until they pass without lecturing you on basic syntax.
- **⚡ Zero External Dependencies:** Pure Python standard library. No bloated frameworks or slow installs.

---

## 🚀 Quick Install

### Method 1: One-Line Installer (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/shoryasrivastava388-sys/qwen-agent/main/install.sh | bash
```

### Method 2: Via Pip / uv

```bash
git clone https://github.com/shoryasrivastava388-sys/qwen-agent.git
cd qwen-agent
pip install -e .
```

Ensure `~/.local/bin` is in your `PATH`:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

---

## 📋 Prerequisites

Ensure [Ollama](https://ollama.com) is installed and running with Qwen:

```bash
ollama run qwen2.5-coder:7b
```

*(You can also use `qwen2.5-coder:14b`, `qwen2.5-coder:32b`, or any local model via `--model`)*

---

## 🛠️ Usage

### Interactive Mode

Simply run `qc` (or `qwen-agent`) in any project directory:

```bash
qc
```

To run in **Auto Mode** (auto-approve all actions):
```bash
qc -y
```

### Non-Interactive / One-Shot Mode

Run single tasks directly from your shell:

```bash
qc -y "Search the web for how to write a FastAPI WebSocket endpoint and implement it in server.py"
```

```bash
qc -y "Run pytest, inspect failing tests, and patch the codebase until all tests pass."
```

---

## 💬 Interactive Slash Commands

Inside interactive chat:

| Command | Description |
|---|---|
| `/auto` or `/perm` | Toggle between Permission Mode and Auto-Approve Mode |
| `/diff` | Display colored git diff of current uncommitted changes |
| `/undo` | Discard recent uncommitted working tree changes (`git checkout .`) |
| `/search <query>` | Perform an instant live web search directly from terminal |
| `/models` | List all local Ollama models installed on the machine |
| `/model <name>` | Switch active model on the fly (e.g. `/model qwen2.5-coder:14b`) |
| `/clear` | Reset context memory and start fresh |
| `exit` / `quit` | Exit session |

---

## 🧰 Available Autonomous Tools

| Tool | Description |
|---|---|
| `search_web` | Search live web for docs, errors, and packages (DuckDuckGo Lite) |
| `fetch_web` | Scrape and extract clean text from any URL or GitHub repo |
| `edit_file` | Surgical search-and-replace code editing with unified diff display |
| `read_file` | Read file contents with line offset and count support |
| `write_file` | Create brand new files on disk |
| `run_command` | Execute bash commands, builds, test suites, and scripts |
| `list_dir` | Recursive directory tree inspection |
| `search_code` | Codebase-wide regex / keyword search (`ripgrep` / `grep`) |
| `git_diff` | Inspect git status and working tree diffs |
| `open_browser` | Open URLs in the user's desktop web browser |

---

## ⚙️ CLI Options

```text
usage: qc [-h] [-m MODEL] [-y] [-c CONTEXT] [-t TEMP] [--host HOST] [-v] [prompt ...]

positional arguments:
  prompt                Direct prompt to execute (non-interactive mode)

options:
  -h, --help            Show this help message and exit
  -m, --model MODEL     Ollama model (default: qwen2.5-coder:7b)
  -y, --yes             Auto-approve all actions (Auto Mode)
  -c, --context CONTEXT Context window size in tokens (default: 4096)
  -t, --temp TEMP       Sampling temperature (default: 0.2)
  --host HOST           Ollama API base URL (default: http://127.0.0.1:11434)
  -v, --version         Show program's version number and exit
```

---

## 🛡️ License

Released under the [MIT License](LICENSE).
