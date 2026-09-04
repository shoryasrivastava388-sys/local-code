# ⚡ qwen-agent (`qc`)

> **Turn your local Qwen model into an autonomous AI software engineer with full computer access.**  
> 100% local, 100% private. An open-source alternative to Claude Code and Antigravity. Zero subscriptions, zero API keys, zero telemetry, and zero heavy dependencies.

---

> [!WARNING]
> ### 🚧 Active Development & Work-in-Progress (WIP)
> This project is under active construction. It is currently **specifically tuned and optimized for `qwen2.5-coder:7b`** running locally via Ollama. Continuous updates, multi-model benchmarks, and new capabilities are being rolled out daily.

---

## 🎯 The Problem with Local AI (and Why `qwen-agent` Exists)

When you run an AI model locally (e.g. through `ollama run qwen2.5-coder`, LM Studio, or local web UIs), **the model is trapped in a text box**:

1. **No System Access:** It can write code, but it cannot create files, edit your repository, or run terminal commands.
2. **Manual Copy-Pasting:** You are forced to copy code from the chat, paste it into your editor, run the tests yourself, copy the error trace back to the AI, and repeat the cycle manually.
3. **No Live Web Access:** It has no way to look up recent documentation, check GitHub repos, or search StackOverflow when an API changes.
4. **Tool Bloat & Sluggish Grammars:** Other agent tools often require hundreds of megabytes of dependencies or rely on rigid grammar parsers that cripple local CPU generation speeds.

---

## 💡 The Solution: `qwen-agent` (`qc`)

`qwen-agent` gives your local model **hands and eyes**:

```
 ┌──────────────────────────────────────────────────────────────┐
 │                      Local Qwen Model                        │
 └──────────────┬───────────────────────────────┬───────────────┘
                │                               │
       [Autonomous Tools]              [Interactive Terminal]
                │                               │
 ┌──────────────▼──────────────┐ ┌──────────────▼──────────────┐
 │ 🌐 Live DuckDuckGo Search   │ │ 🛡️ Permission Mode (Y/n/a)  │
 │ 📖 Real-Time Web Scraping   │ │ 🎨 Colored Diff Previews    │
 │ ✏️ Surgical File Editing    │ │ 🌿 Git Diff & Undo Commands │
 │ ⚡ Bash Command Execution   │ │ 🔄 Instant Model Switcher   │
 └─────────────────────────────┘ └─────────────────────────────┘
```

When you give `qwen-agent` a task, it:
1. **Explores the Repo:** Reads your files, checks directory trees, and inspects git status.
2. **Searches the Web:** If it encounters an unfamiliar API or library, it searches DuckDuckGo and reads online documentation.
3. **Applies Surgical Edits:** It modifies only the necessary lines with colored unified diffs—**never** wiping or recreating existing files.
4. **Executes & Self-Heals:** Runs your test suites or scripts, catches errors, patches the code, and re-tests until everything passes.

---

## 📊 Feature Comparison

| Feature | Raw Ollama Chat | Traditional Tools | Claude Code | **`qwen-agent` (`qc`)** |
|---|:---:|:---:|:---:|:---:|
| **100% Free & Local** | ✅ | ⚠️ Partial | ❌ ($20/mo + API) | **✅ Yes (Ollama)** |
| **Complete Privacy (No Cloud)** | ✅ | ⚠️ | ❌ | **✅ 100% Local** |
| **Surgical File Editing** | ❌ (Manual copy-paste) | ⚠️ (Often wipes files) | ✅ | **✅ Unified Diffs** |
| **Terminal Execution** | ❌ | ⚠️ | ✅ | **✅ With Permissions** |
| **Live Web Search** | ❌ | ❌ | ✅ | **✅ DuckDuckGo Lite** |
| **Zero Dependencies** | ❌ | ❌ (Heavy packages) | ❌ (Node / npm) | **✅ Pure Standard Lib** |
| **Optimized for Local CPU/GPU** | ⚠️ | ❌ (Grammar lag) | N/A (Cloud) | **✅ ChatML Streaming** |

---

## ✨ Key Capabilities

### 🌐 1. Live Web Search & Scraping
* **`search_web`**: Queries DuckDuckGo Lite directly from Python (no API keys or subscriptions needed). Extracts top links and relevant snippets.
* **`fetch_web`**: Downloads and strips clean text from any URL or GitHub repository using native `curl`.
* **In-Chat Search:** Run `/search <query>` anytime directly inside the terminal prompt.

### ✏️ 2. Surgical File Editing (No Recreating Files)
* Modifies existing source files by replacing targeted snippets while keeping surrounding code, formatting, and comments intact.
* Shows a **colorized terminal diff** before applying changes (`+` additions in green, `-` deletions in red).

### 🛡️ 3. Safety First: Permission Mode vs Auto Mode
* **Permission Mode (Default):** Prompts for confirmation before running commands, modifying files, or launching browsers (`Allow action? [Y/n/a]`).
* **Auto Mode (`qc -y`):** Autonomously executes actions in a continuous self-healing loop for fast hands-off debugging.
* Toggle between modes inside the chat anytime with `/auto` or `/perm`.

### 🔄 4. Persistence & Self-Healing Loop
* When a command fails or tests throw an `AssertionError`, `qwen-agent` analyzes the traceback, inspects the failing files, patches the bug, and re-executes until the tests pass.

---

## 🚀 Quick Install

### Method 1: One-Line Installer (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/shoryasrivastava388-sys/qwen-agent/main/install.sh | bash
```

### Method 2: Via Git & Pip

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

Ensure [Ollama](https://ollama.com) is running locally with Qwen:

```bash
ollama run qwen2.5-coder:7b
```

*(You can also use `qwen2.5-coder:14b`, `qwen2.5-coder:32b`, or any installed Ollama model via `--model`)*

---

## 🛠️ Usage Examples

### 1. Interactive Agent Mode

Launch the interactive REPL in any project directory:

```bash
qc
```
*(or run `qc -y` to auto-approve actions)*

### 2. Autonomous Debugging

```bash
qc -y "Run pytest, find all failing tests, patch the source code, and verify they pass."
```

### 3. Web Research & Implementation

```bash
qc -y "Search the web for how to implement WebSocket connection pooling in FastAPI and add it to src/server.py."
```

### 4. Codebase Exploration & Refactoring

```bash
qc "Find all deprecated function calls in this repository and refactor them."
```

---

## 💬 In-Chat Slash Commands

Inside the interactive chat:

| Command | Action |
|---|---|
| `/auto` or `/perm` | Toggle between **Permission Mode** and **Auto Mode** |
| `/diff` | Display colored git diff of current uncommitted changes |
| `/undo` | Discard recent uncommitted changes (`git checkout .`) |
| `/search <query>` | Run an instant live web search directly from the prompt |
| `/models` | List all local Ollama models installed on your machine |
| `/model <name>` | Switch active model on the fly (e.g. `/model qwen2.5-coder:14b`) |
| `/clear` | Reset conversation context memory |
| `exit` / `quit` | Exit session |

---

## 🧰 Built-In Autonomous Tools

| Tool | Description |
|---|---|
| `search_web` | Searches the live web for documentation, packages, and solutions |
| `fetch_web` | Scrapes and extracts clean readable text from any URL or GitHub repo |
| `edit_file` | Surgically edits existing files with unified diff previews |
| `read_file` | Reads files with optional line offsets and limits |
| `write_file` | Creates brand new files on disk |
| `run_command` | Executes bash commands, builds, test suites, and scripts |
| `list_dir` | Recursive directory tree inspection |
| `search_code` | Codebase-wide regex / keyword search (`ripgrep` / `grep`) |
| `git_diff` | Inspects current git status and working tree diffs |
| `open_browser` | Opens URLs in the user's desktop browser (Firefox/Chrome) |

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
