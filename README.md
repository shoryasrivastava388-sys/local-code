# ⚡ qwen-agent (`qc`)

> **Autonomous local coding and computer agent powered by Qwen on Ollama.**  
> An open-source, 100% private alternative to Claude Code and Antigravity. Zero subscriptions, zero API keys, zero telemetry, and zero heavy dependencies.

---

## ✨ Features

- **💻 Full Computer Access:** Runs bash commands, creates files, applies targeted code patches, searches codebases, and checks git diffs.
- **🌐 Live Web Browsing:** Fetches live documentation, GitHub repositories, and web articles via native `curl` extraction.
- **⚡ Zero External Dependencies:** Pure Python standard library. No bloated frameworks, no slow dependency resolution.
- **🧠 Action-First Persona:** Doesn't lecture you or explain basic programming syntax. Inspects the repo, does the work, runs tests, and delivers concise summaries.
- **🔄 Autonomous Self-Healing:** If a test or command fails, it analyzes the stack trace, patches the file, and re-runs until it works.
- **🏎️ Blazing Fast CPU/GPU Execution:** Bypasses sluggish GBNF grammar DFAs to generate tool calls at full native model speed.

---

## 🚀 Quick Install

### Method 1: One-Line Installer (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/qwen-agent/main/install.sh | bash
```

### Method 2: Via Pip / uv

```bash
git clone https://github.com/YOUR_USERNAME/qwen-agent.git
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

Simply run `qc` (or `qwen-agent`) in any repository:

```bash
qc
```

To auto-approve commands without interactive confirmation prompts:
```bash
qc -y
```

### Non-Interactive / One-Shot Mode

Run a single command directly from your shell:

```bash
qc -y "Find all deprecated function calls in src/ and patch them."
```

```bash
qc -y "Browse https://github.com/fastapi/fastapi and tell me what the latest release changes are."
```

---

## 🧰 Available Tools

| Tool | Description |
|---|---|
| `run_command` | Execute bash commands, test suites, builds, and scripts |
| `read_file` | Read file contents with line offset and count support |
| `write_file` | Create or overwrite files |
| `patch_file` | Surgical search-and-replace code refactoring |
| `list_dir` | Recursive directory tree inspection |
| `search_code` | Codebase-wide regex / keyword search (`ripgrep` / `grep`) |
| `git_diff` | Inspect git status and working tree diffs |
| `fetch_web` | Fetch and extract clean text from any URL |
| `open_browser` | Launch a URL in the desktop web browser |

---

## ⚙️ CLI Options

```text
usage: qc [-h] [-m MODEL] [-y] [-c CONTEXT] [-t TEMP] [--host HOST] [-v] [prompt ...]

positional arguments:
  prompt                Direct prompt to execute (non-interactive mode)

options:
  -h, --help            Show this help message and exit
  -m, --model MODEL     Ollama model (default: qwen2.5-coder:7b)
  -y, --yes             Auto-approve terminal execution
  -c, --context CONTEXT Context size in tokens (default: 4096)
  -t, --temp TEMP       Sampling temperature (default: 0.2)
  --host HOST           Ollama API base URL (default: http://127.0.0.1:11434)
  -v, --version         Show program's version number and exit
```

---

## 📜 In-Chat Commands

While in interactive mode:
- `/auto` — Toggle terminal command auto-approval on/off
- `/clear` — Clear context history and start fresh
- `/help` — Display in-chat options
- `exit` or `quit` — Exit agent

---

## 🛡️ License

Released under the [MIT License](LICENSE).
