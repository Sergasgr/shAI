# 🚀 shAI - Your AI-Powered Local Terminal Assistant

![Python](https://img.shields.io/badge/python-3.12-blue.svg)
![Typer](https://img.shields.io/badge/CLI-Typer-black.svg)
![Ollama](https://img.shields.io/badge/LLM-Ollama-white.svg)
![MLOps](https://img.shields.io/badge/MLOps-End--to--End-green.svg)

**shAI** is a CLI tool that translates natural language into executable Linux commands and bash scripts. Built from scratch with an End-to-End MLOps pipeline, it runs **100% locally** preserving your privacy, and uses **RAG** (Retrieval-Augmented Generation) to learn your corporate documentation.

---

## 🎥 Demo

![shAI Demo](docs/render1777482232590.gif)

---

## ✨ Core Features

* 🔒 **100% Local & Private:** Powered by Ollama and Qwen 2.5. No internet connection required, no data leaves your machine.
* 🧠 **RAG-Powered Memory:** Ingest your own internal documentation (`shai learn`) so the AI prioritizes your company's scripts over general knowledge.
* 💻 **Zero-Shot Bash Scripts:** Generate production-ready bash scripts with brief explanations (`--bash`, `--explain`).
* 🔄 **Continuous Learning Pipeline:** Integrated SQLite telemetry to log executions and feedback for future LoRA fine-tuning.

---

## 🏗️ MLOps Architecture

This project is not just a wrapper; it includes a full Machine Learning lifecycle:
1. **Data Collection:** `telemetry.py` logs user prompts, generated commands, and OS context into a local SQLite database.
2. **Fine-Tuning:** Custom Python scripts to extract feedback, generate a `.jsonl` dataset, and train a **LoRA adapter** using HuggingFace `trl` and `peft`.
> ⚙️ **Note on Quantization:** To convert trained models to GGUF format, you must clone and build [llama.cpp](https://github.com/ggerganov/llama.cpp) inside the `scripts/` directory. This dependency is excluded from the repository to keep it lightweight.
3. **Evaluation:** Automated benchmarking (`run_evals.py`) calculating exact match and latency against a ground truth dataset.
4. **Vector Database:** LangChain and ChromaDB integration for semantic search of local documentation.

---

## 🚀 Installation & Setup

We use `uv` for lightning-fast, isolated installation.

```bash
# 1. Clone the repository
git clone https://github.com/[YourUser]/shai.git
cd shai

# 2. Install globally using uv
uv tool install .

# 3. Initialize the environment (Downloads the embedding model)
shai setup
```

---

## 🕹️ Usage

`shAI` provides three main commands to interact with your system: `ask`, `learn`, and `setup`.

### 1. `shai ask` (Core Engine)
Translates your natural language prompt into an executable Linux command or Bash script.

**Flags & Options:**
* `--explain` / `-e`: Generates a detailed, step-by-step explanation of the generated command or script.
* `--bash` / `-b`: Outputs a complete, raw Bash script (`#!/bin/bash`) instead of a single-line command.
* `--alias <name>` / `-a`: Automatically creates a permanent shell alias for the generated command in your `.bashrc` or `.zshrc`.
* `--save <path>` / `-s`: Saves the generated output (and explanation, if requested) to a specified file.
* `--append` / `-ap`: Used with `--save` to append the output to an existing file instead of overwriting it.
* `--yes` / `-y`: Bypasses the confirmation prompt and executes the generated command immediately.

**Examples:**
```bash
# Generate a script, explain it, and save it to a file
shai ask "monitor CPU usage every 2 seconds" -b -e --save monitor.sh

# Generate a command, save it as an alias, and execute it
shai ask "update system and clean orphans" -a update_all -y
```

### 2. `shai learn` (RAG Knowledge Ingestion)
Reads a local text file containing your personal or corporate snippets, splits it into chunks, and saves it into the local ChromaDB vector database. The AI will prioritize this knowledge in future prompts.

```bash
shai learn doc.txt
```

### 3. `shai setup` (Environment Initialization)
Initializes the local SQLite telemetry database and pulls the required `nomic-embed-text` embedding models from Ollama for the RAG engine.

```bash
shai setup
```

---

> ⚠️ **Disclaimer**
>
> **shAI** generates system commands using Artificial Intelligence. The user is strictly responsible for reviewing all commands before execution. The creator assumes no liability for any system damage or data loss.

---

### 👨‍💻 About the Author

**Sergio Graciá, Sergas.** *LinkedIn:* [https://www.linkedin.com/in/sergio-gracia-](https://www.linkedin.com/in/sergio-gracia-)