# Setup Guide

## Prerequisites

- Python 3.10+
- Git
- Android SDK (for APK analysis tools)
- An agent/LLM host that reads project instruction files (e.g. Claude Code, Cursor)

## 1. Clone the Repository

```bash
git clone https://github.com/0xgf-18/AGent.git
cd AGent
```

## 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv .agent/scripts/.venv

# Activate (Linux/Mac)
. .agent/scripts/.venv/bin/activate

# Activate (Windows)
.agent\scripts\.venv\Scripts\activate

# Install dependencies
pip install -r .agent/scripts/requirements.txt
```

## 3. Install Development Dependencies (Optional)

```bash
pip install -r requirements-dev.txt
pre-commit install
```

## 4. Set Up Android SDK (Optional)

For APK analysis features, install the Android SDK and set environment variables:

```bash
# Windows
setx ANDROID_HOME "C:\Users\YourName\AppData\Local\Android\Sdk"
setx ANDROID_SDK_ROOT "C:\Users\YourName\AppData\Local\Android\Sdk"

# Linux/Mac
export ANDROID_HOME="$HOME/Android/Sdk"
export ANDROID_SDK_ROOT="$HOME/Android/Sdk"
```

## 5. Verify Installation

```bash
# Check Python dependencies
python -c "import requests, bs4, readability, markdownify, lxml, PIL; print('OK')"

# Check agent scripts
python .agent/scripts/apk_fingerprint.py --help
python .agent/scripts/graph_generator.py --help
```

## 6. Point Your Agent at the Repo

Open the project in your agent host and ask it to:
- `compile <slug>.md` — Process a raw feed into wiki articles
- `search "DexProtector anti-frida"` — Query the knowledge base
- `health-check` — Scan for dead links, orphans, stale stubs
- `analyze <apk>` — Run the research loop on an APK

## 7. Explore the Knowledge Graph

```bash
python .agent/scripts/graph_generator.py --open
```

## Next Steps

- Read [USAGE.md](USAGE.md) for detailed usage instructions
- Read [API.md](API.md) for script API reference
- Read [ARCHITECTURE.md](ARCHITECTURE.md) for system design details
- Read [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines
