# AlchemyX - AlchemAI

AlchemAI is a Streamlit research assistant for searching a local document corpus with hybrid retrieval (Chroma plus BM25), reranking evidence, checking sufficiency, resolving conflicts, and generating cited answers.

This guide starts from a Windows PC with no project libraries installed.

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer (Python 3.11 or 3.12 recommended)
- Internet access while installing packages and while using Voyage AI/OpenRouter
- Voyage AI and OpenRouter API keys
- Enough disk space for the corpus and local indexes

Optional for scanned PDFs:

- Tesseract OCR
- Poppler, required by `pdf2image`

Text PDFs do not normally require these OCR tools.

## Install Python

Download Python from [python.org](https://www.python.org/downloads/) and enable **Add Python to PATH** during installation. Open a new Command Prompt and check it:

```bat
python --version
```

## Install AlchemAI

Open Command Prompt in the project folder:

```bat
cd /d "C:\path\to\AlchemAI"
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The virtual environment keeps AlchemAI's libraries separate from other Python projects. Activate it again whenever you open a new terminal.

## Configure API Keys and Corpus

Use `.env` in the project root for API keys and the corpus path. Create it from the safe template:

```bat
copy .env.example .env
```

Open `.env` in a text editor and set the required API keys:

```dotenv
VOYAGE_API_KEY=your_voyage_key_here
OPENROUTER_API_KEY=your_openrouter_key_here
ALCHEMYX_CORPUS_PATH=Archive_test
```

For a corpus outside the project, use an absolute Windows path, for example:

```dotenv
ALCHEMYX_CORPUS_PATH=C:\data\my_archive
```

Model choices and optional OCR tool paths are configured in `src\alchemyx\config.py`, not `.env`.

`.env` is ignored by Git. Never put real keys in Python files, the README, Streamlit code, or `API-KEY-VOYAGE-AI.txt`; that old text file is ignored and should not be used as configuration.

## Add or Replace Documents

The ingestion pipeline supports `.txt`, `.md`, `.docx`, `.pdf`, and `.csv` files. Put the files under the configured corpus directory.

## Build or Rebuild Indexes

After adding or replacing documents, run:

```bat
.venv\Scripts\activate
python scripts\build_indexes.py
```

This creates or updates the Chroma and BM25 indexes and the document registry. Re-run it after corpus changes. If a file fails ingestion, fix that file and run the command again.

## Start Streamlit

From the project root, with the virtual environment active:

```bat
.venv\Scripts\activate
python -m streamlit run app\streamlit_app.py
```

Open `http://localhost:8501` in a browser. Keep the terminal open while using the app. Press `Ctrl+C` in that terminal to stop it. Build the indexes first if the app reports that they are missing or empty.

## Run Tests and Checks

```bat
.venv\Scripts\activate
python -m pytest -q
python -m compileall src app tests
```

## Project Layout

- `app\streamlit_app.py` - Streamlit interface
- `src\alchemyx` - application, retrieval, agent, ingestion, and generation code
- `scripts\build_indexes.py` - corpus indexing command
- `requirements.txt` - Python packages required by the application
- `.env.example` - safe configuration template
- `.env` - private API keys and corpus path
- `data` - local data and generated index storage, where applicable

## Common Problems

**Missing API key:** confirm the file is named exactly `.env`, is in the project root, and contains both provider keys. Restart the Streamlit process after changing it.

**OpenRouter model unavailable:** choose a model available to your OpenRouter account by changing `OPENROUTER_MODEL` in `src\alchemyx\config.py`.

**Scanned PDF extraction fails:** install Tesseract and Poppler. If Tesseract is not installed at its standard Windows location, set `TESSERACT_CMD` in `src\alchemyx\config.py`.

**No useful evidence:** confirm `ALCHEMYX_CORPUS_PATH` in `.env` points to the intended directory, then rebuild the indexes.
