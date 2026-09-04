# ⚡ Local Code (`lc`)

> **Autonomous Local AI Coding & Computer Agent powered by Ollama.**  
> 100% private, 100% local. Works natively on **Linux, macOS, and Windows**. A universal open-source alternative to Claude Code and Antigravity. Zero subscriptions, zero API keys, zero telemetry, and zero heavy dependencies.

---

> [!WARNING]
> ### 🚧 Active Development & Work-in-Progress (WIP)
> This project is under active continuous development. Features, multi-model optimizations, and tool integrations are updated daily.

---

## 💻 Cross-Platform Support

`local-code` (`lc`) is built from the ground up to run natively across all three operating systems:

* 🐧 **Linux:** Native Bash / Zsh execution, `curl` & `urllib` networking, native browser control.
* 🍎 **macOS:** Native Zsh / Apple Silicon GPU acceleration (`mps`), default browser launch.
* 🪟 **Windows:** Native Command Prompt & PowerShell execution, ANSI colors, recursive file walker fallback, Windows default browser launch, and batch wrappers (`lc.cmd`, `local-code.cmd`).

---

## 🚀 Foolproof 2-Minute Quickstart

Follow these 3 simple steps to get running immediately:

### Step 1: Install Ollama & Download a Model

1. Download and install **[Ollama](https://ollama.com/download)** (available for Linux, macOS, and Windows).
2. Open your terminal and pull any model of your choice:

```bash
# Recommended default (Best balance of speed and intelligence on laptops):
ollama run qwen2.5-coder:7b

# OR choose any other model:
ollama run deepseek-r1:8b        # DeepSeek reasoning
ollama run llama3.1:8b           # Meta Llama
ollama run qwen2.5-coder:14b     # High-reasoning Qwen
```

---

### Step 2: Install `lc` in 1 Line

Choose the command for your operating system:

#### 🐧 Linux & 🍎 macOS (Terminal)
```bash
curl -fsSL https://raw.githubusercontent.com/shoryasrivastava388-sys/local-code/main/install.sh | bash
```

#### 🪟 Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/shoryasrivastava388-sys/local-code/main/install.ps1 | iex
```

#### 📦 Universal via Pip / uv (All Platforms)
```bash
pip install git+https://github.com/shoryasrivastava388-sys/local-code.git
```

Ensure `~/.local/bin` (or `%USERPROFILE%\.local\bin` on Windows) is in your `PATH`.

---

### Step 3: Run Anywhere!

In any project repository, simply run:

```bash
lc
```

*(or run `lc -y` to auto-approve all actions)*

---

## 🧠 Supported Local Models Matrix

`local-code` works with **any model running on Ollama**. Pick the model that fits your hardware:

| Category | Model Name | VRAM / RAM Required | Best Suited For | Launch Command |
|---|---|:---:|---|---|
| **⭐ Recommended (Default)** | `qwen2.5-coder:7b` | ~5–8 GB | Laptops, budget GPUs, fast debugging & tool use | `lc` |
| **🧠 Deep Reasoning** | `deepseek-r1:8b` | ~6–8 GB | Complex algorithm logic & math tasks | `lc -m deepseek-r1:8b` |
| **🌐 General Coding** | `llama3.1:8b` | ~6–8 GB | Code generation, bash automation, general chat | `lc -m llama3.1:8b` |
| **🚀 Powerful Workstation** | `qwen2.5-coder:14b` | ~10–14 GB | High-level refactoring & large repositories | `lc -m qwen2.5-coder:14b` |
| **👑 Flagship Intelligence** | `qwen2.5-coder:32b` | ~20–24 GB | Near Claude 3.5 Sonnet level local intelligence | `lc -m qwen2.5-coder:32b` |
| **🔬 Advanced Reasoning** | `deepseek-coder-v2` | ~10–16 GB | DeepSeek MoE code intelligence | `lc -m deepseek-coder-v2` |
| **🪶 Ultra-Lightweight** | `qwen2.5-coder:1.5b` | ~2–3 GB | Low-spec laptops & budget CPUs | `lc -m qwen2.5-coder:1.5b` |

---

## 🔄 Dynamic Model Switching

You can switch models anytime without restarting:

1. **Interactive Keyboard Selector (Inside Chat):**
   * Type `/models` $\rightarrow$ Opens an interactive terminal menu navigated with **`↑` / `↓` Arrow Keys** and **`Enter`** to instantly select and activate any locally installed Ollama model.
2. **Direct Command (Inside Chat):**
   * `/model <name>` $\rightarrow$ Switches active model directly (e.g. `/model deepseek-r1:8b`).
3. **At launch:**
   ```bash
   lc -m deepseek-r1:8b
   ```
4. **Permanent default via environment:**
   ```bash
   export LC_MODEL="deepseek-r1:8b"
   ```

---

## 🎯 The Problem with Local AI (and Why `lc` Exists)

When you run an AI model locally (e.g. through `ollama run ...`, LM Studio, or web UIs), **the model is trapped in a text box**:

1. **No System Access:** It can write code, but it cannot create files, edit your repository, or run terminal commands.
2. **Manual Copy-Pasting:** You are forced to copy code from the chat, paste it into your editor, run the tests yourself, copy the error trace back to the AI, and repeat the cycle manually.
3. **No Live Web Access:** It has no way to look up recent documentation, check GitHub repos, or search StackOverflow when an API changes.
4. **Tool Bloat & Sluggish Grammars:** Other agent tools often require hundreds of megabytes of dependencies or rely on rigid grammar parsers that cripple local CPU generation speeds.

---

## 💡 The Solution: `local-code` (`lc`)

`local-code` gives your local model **hands and eyes**:

```
 ┌──────────────────────────────────────────────────────────────┐
 │                  Any Local Ollama Model                      │
 └──────────────┬───────────────────────────────┬───────────────┘
                │                               │
       [Autonomous Tools]              [Interactive Terminal]
                │                               │
 ┌──────────────▼──────────────┐ ┌──────────────▼──────────────┐
 │ 🌐 Live DuckDuckGo Search   │ │ 🛡️ Permission Mode (Y/n/a)  │
 │ 📖 Real-Time Web Scraping   │ │ 🎨 Colored Diff Previews    │
 │ ✏️ Surgical File Editing    │ │ 🌿 Git Diff & Undo Commands │
 │ ⚡ Bash/CMD/PS Execution    │ │ 🔄 Instant Model Switcher   │
 └─────────────────────────────┘ └─────────────────────────────┘
```

When you give `local-code` a task, it:
1. **Explores the Repo:** Reads your files, checks directory trees, and inspects git status.
2. **Searches the Web:** If it encounters an unfamiliar API or library, it searches DuckDuckGo and reads online documentation.
3. **Applies Surgical Edits:** It modifies only the necessary lines with colored unified diffs—**never** wiping or recreating existing files.
4. **Executes & Self-Heals:** Runs your test suites or scripts, catches errors, patches the code, and re-tests until everything passes.

---

## 📊 Feature Comparison

| Feature | Raw Ollama Chat | Traditional Tools | Claude Code | **`local-code` (`lc`)** |
|---|:---:|:---:|:---:|:---:|
| **100% Free & Local** | ✅ | ⚠️ Partial | ❌ ($20/mo + API) | **✅ Yes (Ollama)** |
| **Complete Privacy (No Cloud)** | ✅ | ⚠️ | ❌ | **✅ 100% Local** |
| **Cross-Platform (Linux/Mac/Win)** | ✅ | ⚠️ | ⚠️ | **✅ Linux, Mac, Win** |
| **Surgical File Editing** | ❌ (Manual copy-paste) | ⚠️ (Often wipes files) | ✅ | **✅ Unified Diffs** |
| **Terminal Execution** | ❌ | ⚠️ | ✅ | **✅ With Permissions** |
| **Live Web Search** | ❌ | ❌ | ✅ | **✅ DuckDuckGo Lite** |
| **Zero Dependencies** | ❌ | ❌ (Heavy packages) | ❌ (Node / npm) | **✅ Pure Standard Lib** |
| **Optimized for Local CPU/GPU** | ⚠️ | ❌ (Grammar lag) | N/A (Cloud) | **✅ ChatML Streaming** |

---

## 🛠️ Usage Examples

### 1. Interactive Agent Mode

Launch the interactive REPL in any project directory:

```bash
lc
```
*(or run `lc -y` to auto-approve actions)*

### 2. Autonomous Debugging

```bash
lc -y "Run pytest, find all failing tests, patch the source code, and verify they pass."
```

### 3. Web Research & Implementation

```bash
lc -y "Search the web for how to implement WebSocket connection pooling in FastAPI and add it to src/server.py."
```

### 4. Codebase Exploration & Refactoring

```bash
lc "Find all deprecated function calls in this repository and refactor them."
```

---

## 💬 In-Chat Slash Commands

Inside the interactive chat:

| Command | Action |
|---|---|
| `/models` | Interactive arrow-key menu to switch Ollama models |
| `/model <name>` | Switch active model directly (e.g. `/model deepseek-r1:8b`) |
| `/auto` or `/perm` | Toggle between **Permission Mode** and **Auto Mode** |
| `/diff` | Display colored git diff of current uncommitted changes |
| `/undo` | Discard recent uncommitted changes (`git checkout .`) |
| `/search <query>` | Run an instant live web search directly from the prompt |
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
| `run_command` | Executes bash / cmd / powershell commands, builds, test suites, and scripts |
| `list_dir` | Recursive directory tree inspection |
| `search_code` | Codebase-wide regex / keyword search (`ripgrep` / `grep` / pure Python) |
| `git_diff` | Inspects current git status and working tree diffs |
| `open_browser` | Opens URLs in the user's desktop browser (Firefox/Chrome/Edge/Safari) |

---

## ⚙️ CLI Options

```text
usage: lc [-h] [-m MODEL] [-y] [-c CONTEXT] [-t TEMP] [--host HOST] [-v] [prompt ...]

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
