# TermCoder ⚡
> **Terminal-Native AI Coding Assistant for Windows, powered by NVIDIA NIM**

TermCoder is a powerful, autonomous AI pair programmer running directly in your Windows terminal. It is deeply aware of your entire codebase, executes tools (file editing, testing, git workflows), supports runtime NVIDIA NIM API key switching, dynamic free model discovery, and native Windows clipboard shortcuts (Ctrl+C, Ctrl+V).

---

## ✨ Key Features

- **Codebase Awareness**:
  - Automatically scans your project respecting `.gitignore` and `.aiignore`.
  - Generates structural AST repository maps (classes, functions, signatures) so the AI understands your project architecture.
  - Mention syntax: type `@src/app.py` or `@utils` to directly attach file contents to your prompt.
  - Built-in code and regex search across your repository.

- **Autonomous ReAct Agent Loop**:
  - **Explain Complex Functions**: Reads definitions, analyzes dependencies, and provides structured explanations.
  - **Run Tests & Auto-Fix**: Direct command execution (e.g. `pytest`, `npm test`), error parsing, and code repair.
  - **Git Operations**: Inspects `git status` and `git diff`, writes conventional commit messages, stages files, and commits.
  - **Safe Execution**: Prompts for user confirmation before running shell commands, with an auto-approve toggle (`/auto` or `--yes`).

- **NVIDIA NIM Integration & Dynamic Model Discovery**:
  - Direct connection to `https://integrate.api.nvidia.com/v1`.
  - Fetches and displays available free models directly from NVIDIA NIM with `/models`.
  - Default recommendation: `meta/llama-3.3-70b-instruct`, `deepseek-ai/deepseek-r1`, `mistralai/mistral-large-2-instruct`, `nvidia/llama-3.1-nemotron-70b-instruct`.
  - Switch models anytime with `/model <model_id>`.

- **Runtime API Key Modification (`/key`)**:
  - View your masked key anytime: `/key`
  - Change your API key instantly inside the session: `/key nvapi-...`
  - Validates key live against NVIDIA NIM, updates config in `~/.termcoder/config.json`, and seamlessly continues without restarting!

- **Live Token Accounting**:
  - Tracks input/prompt tokens, output/completion tokens, cached tokens, and total tokens.
  - Displays turn token usage after every response and cumulative session metrics (`/tokens`).

- **Rich Terminal UX & Windows Shortcuts**:
  - **Ctrl+V**: Paste text or multi-line code directly from the Windows clipboard.
  - **Ctrl+C**: Copy selected text or cancel current prompt / running agent.
  - **Tab**: Auto-complete commands (`/`), files (`@`), and model names.
  - **Esc + Enter**: Insert newline for multi-line prompts.
  - **Up / Down**: Traverse prompt history.

- **Extensible Plugin System**:
  - Drop custom Python plugins into `~/.termcoder/plugins/` or `.termcoder/plugins/`.
  - Register custom slash commands and custom LLM tools.
  - Scaffold new plugins with `/plugin create <name>`.

---

## 🚀 Easy Installation on Windows

### Option 1: One-Click Batch Installer
Simply double-click `install.bat`.

### Option 2: PowerShell
Run the installer script:
```powershell
.\install.ps1
```

### Option 3: Manual Pip Install
```powershell
pip install -e .
```

Once installed, the global commands `ai` and `termcoder` are available in any terminal!

---

## 🔑 Getting Started with NVIDIA NIM

1. Get your free API key at [build.nvidia.com](https://build.nvidia.com).
2. Launch TermCoder:
   ```powershell
   ai
   ```
3. Set your API key:
   ```text
   ❯ termcoder: /key nvapi-YourKeyHere
   ```
4. Start coding!

---

## ⌨️ Command Reference

| Command | Description |
| :--- | :--- |
| `/key [new_key]` | Inspect or update the NVIDIA NIM API key at runtime |
| `/models [filter]` | Fetch & list available models from NVIDIA NIM |
| `/model <model_id>` | Switch the active AI model |
| `/tokens` | Display token usage statistics (turn & session totals) |
| `/auto` | Toggle auto-approval mode for running terminal commands |
| `/git [status\|diff]` | Run git status or inspect current diffs |
| `/plugins` | View installed plugins and custom commands |
| `/plugin create <name>` | Generate boilerplate for a new custom plugin |
| `/sysinfo` | View system hardware, Python, and disk diagnostics |
| `/clear` | Clear terminal screen |
| `/help` | Show command cheat sheet |
| `/exit` | Exit TermCoder |

---

## 🛠 Developing Plugins

Create a new plugin template:
```text
❯ termcoder: /plugin create my_tool
```

This creates `~/.termcoder/plugins/my_tool.py`:
```python
from termcoder.plugins.base import BasePlugin

class MyToolPlugin(BasePlugin):
    name = "my_tool"
    description = "Custom tool description"

    def register_commands(self):
        return {"mycmd": self.run_cmd}

    def register_tools(self, registry):
        registry.register_custom_tool(
            name="custom_action",
            description="Custom action for the LLM",
            parameters={"type": "object", "properties": {"param": {"type": "string"}}},
            handler=self.run_action,
        )

    def run_cmd(self, args):
        print(f"Executed with args: {args}")

    def run_action(self, param=""):
        return f"Action result for: {param}"
```

---

## 📜 License
MIT License.
