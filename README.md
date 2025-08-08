# AI Financial Planner (Local)

A local, Python-based AI financial planner built with Streamlit. Developed iteratively in six steps. This README covers setup and usage for Windows (primary) and Linux/macOS.

## Features (planned across iterations)
- Iteration 1: Project scaffolding, virtual environment, basic Streamlit app shell
- Iteration 2: CSV ingestion and transaction table
- Iteration 3: PDF ingestion via Camelot/Tabula
- Iteration 4: SQLite storage via SQLAlchemy
- Iteration 5: Categorization + dashboard visualizations
- Iteration 6: AI financial advice (OpenAI or local LLaMA)

## Project Structure
```
/workspace
  ├─ app.py                # Streamlit entry point
  ├─ requirements.txt      # Python deps
  ├─ README.md             # This file
  ├─ src/                  # Python modules (ingestion, storage, dashboard, ai)
  ├─ data/                 # Local data storage
  ├─ tests/                # Tests
  └─ examples/             # Example CSV/PDF files for testing (added in later iterations)
```

## Prerequisites
- Python 3.10+ (3.11 recommended)
- Windows 10/11 (primary target) or Linux/macOS
- Optional for PDF ingestion (Iteration 3):
  - Java Runtime (for `tabula-py`)
  - Ghostscript (for some `camelot-py` backends)

On Windows, you can install optional tools with Chocolatey (PowerShell as Administrator):
```
choco install jre8 -y
choco install ghostscript -y
```

## Setup

### Windows (PowerShell)
```
# From the project root
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### Linux/macOS (bash)
```
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Run the App
```
streamlit run app.py
```
Then open the URL shown in the terminal (usually http://localhost:8501).

## Notes
- If you plan to use OpenAI, set `OPENAI_API_KEY` in your environment.
- If you prefer fully local AI, install `llama-cpp-python` (see requirements) and skip any cloud keys.
- We work in small, testable iterations. At the end of each iteration, confirm functionality before proceeding.

## Troubleshooting
- If PDF ingestion fails later, verify Java and Ghostscript are installed and available in PATH.
- If `pip install` fails for `camelot-py` or `tabula-py`, ensure system dependencies are present, or temporarily comment them out to proceed with other iterations.
