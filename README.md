# 🎙️ Speech Analysis System

> **Production-grade AI system that automatically evaluates recorded speech across 7 communication dimensions using local GPU-accelerated models.**

Built with faster-whisper · Silero VAD · DeepFilterNet · Parselmouth · spaCy · FastAPI · React

---

## 📋 Table of Contents

- [What This Does](#-what-this-does)
- [7 Analysis Dimensions](#-7-analysis-dimensions)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Mac Setup (Step by Step)](#-mac-setup-step-by-step)
- [Windows Setup](#-windows-setup)
- [Running the System](#-running-the-system)
- [Using the API](#-using-the-api)
- [Project Structure](#-project-structure)
- [Scoring Formulas](#-scoring-formulas)
- [Environment Variables](#-environment-variables)
- [Troubleshooting](#-troubleshooting)

---

## 🧠 What This Does

Upload any audio file (MP3, WAV, M4A, OGG, FLAC — up to 60 minutes) and the system:

1. **Converts** audio to 16kHz mono WAV using FFmpeg
2. **Denoises** using DeepFilterNet neural noise reduction
3. **Transcribes** speech using faster-whisper with word-level timestamps
4. **Detects** speech/silence segments using Silero VAD
5. **Analyzes** 7 communication dimensions
6. **Scores** each dimension 1–5 with coaching insights
7. **Generates** JSON + HTML + PDF reports with radar charts

**Processing time:** ~10–12 seconds for a 5-minute clip on GPU · ~25–30 seconds on CPU

---

## 📊 7 Analysis Dimensions

| # | Dimension | Signal | Formula |
|---|-----------|--------|---------|
| 1 | **Clarity** | ASR confidence | `mean(word_confidence) × 100` |
| 2 | **Filler Words** | Token matching | `(filler_count / total_words) × 100` |
| 3 | **Pause Patterns** | Silero VAD | `macro_pauses / net_speech_minutes` |
| 4 | **Punctuation Use** | spaCy + VAD | `correctly_placed_pauses / clause_boundaries` |
| 5 | **Language Quality** | MATTR + FK Grade | `0.6 × TTR_score + 0.4 × FK_score` |
| 6 | **Delivery Quality** | WPM + variance | `words / net_speech_minutes` + rolling std dev |
| 7 | **Tone / Demeanor** | F0 pitch + RoBERTa | Fusion of acoustic + semantic signals |

**Scoring:** 1 (needs work) → 5 (excellent) per dimension  
**Composite:** Weighted average with 5 role profiles (General, Sales, Executive, Interview, Coaching)

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| ASR | faster-whisper (small.en, float16/int8) |
| VAD | Silero VAD (PyTorch) |
| Noise Reduction | DeepFilterNet3 |
| Audio I/O | FFmpeg + soundfile |
| Pitch Extraction | Parselmouth (Praat) |
| NLP | spaCy en_core_web_sm |
| Lexical Diversity | MATTR (lexical-diversity) |
| Readability | textstat (Flesch-Kincaid) |
| Sentiment | cardiffnlp/twitter-roberta + VADER |
| Backend | FastAPI + Uvicorn |
| Frontend | React 18 + Vite |
| Reports | Jinja2 + WeasyPrint + SVG |
| Dep Manager | uv (Astral) |
| Logging | Loguru |

---

## ✅ Prerequisites

### Mac Requirements

| Tool | Version | Check Command |
|------|---------|---------------|
| Python | 3.11.x | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| FFmpeg | Any | `ffmpeg -version` |
| Git | Any | `git --version` |
| uv | Latest | `uv --version` |

> **Note:** Mac does not have NVIDIA GPU support. The system runs on CPU automatically. Processing will take ~25–30 seconds per 5-minute clip instead of ~10 seconds.

---

## 🍎 Mac Setup (Step by Step)

Follow every step in order. Do not skip.

### Step 1 — Install Homebrew (Mac package manager)

Open **Terminal** and run:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After install, follow any instructions it shows to add Homebrew to your PATH. Then verify:

```bash
brew --version
```

---

### Step 2 — Install Python 3.11

```bash
brew install python@3.11
```

Verify:

```bash
python3.11 --version
# Should show: Python 3.11.x
```

---

### Step 3 — Install FFmpeg

FFmpeg is required for audio format conversion (M4A, MP3, OGG → WAV).

```bash
brew install ffmpeg
```

Verify:

```bash
ffmpeg -version
# Should show: ffmpeg version 7.x.x
```

---

### Step 4 — Install Node.js (for React frontend)

```bash
brew install node
```

Verify:

```bash
node --version   # Should show: v18.x.x or higher
npm --version    # Should show: 9.x.x or higher
```

---

### Step 5 — Install uv (Python dependency manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen Terminal, then verify:

```bash
uv --version
```

---

### Step 6 — Install GTK3 (required for WeasyPrint PDF generation)

```bash
brew install pango
brew install gdk-pixbuf
brew install libffi
```

---

### Step 7 — Clone the repository

```bash
git clone https://github.com/daschirag/voice.git
cd voice
```

---

### Step 8 — Set up Python environment

```bash
# Create virtual environment and install all Python dependencies
uv sync
```

This will take **5–10 minutes** on first run (downloads PyTorch, faster-whisper, etc. ~2GB total).

---

### Step 9 — Install the spaCy English language model

```bash
uv run python -m spacy download en_core_web_sm
```

---

### Step 10 — Configure environment variables

```bash
cp .env.example .env
```

Open `.env` in any text editor:

```bash
nano .env
# or
open -e .env
```

**Change these values for Mac (CPU mode):**

```env
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

Leave everything else as default for now. Save and close.

---

### Step 11 — Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

---

### Step 12 — Verify everything is installed correctly

```bash
uv run python -c "
import importlib
packages = {
    'FastAPI': 'fastapi', 'faster-whisper': 'faster_whisper',
    'Torch': 'torch', 'Silero-VAD': 'silero_vad',
    'DeepFilterNet': 'df', 'Parselmouth': 'parselmouth',
    'spaCy': 'spacy', 'Textstat': 'textstat',
    'Jinja2': 'jinja2', 'WeasyPrint': 'weasyprint',
}
all_ok = True
for name, mod in packages.items():
    try:
        importlib.import_module(mod)
        print(f'  OK   {name}')
    except ImportError as e:
        print(f'  FAIL {name} -- {e}')
        all_ok = False
print()
print('All good!' if all_ok else 'Some packages failed - see above.')
"
```

All lines should show `OK`.

---

## 🪟 Windows Setup

### Prerequisites

| Tool | How to Install |
|------|---------------|
| Python 3.11 | https://www.python.org/downloads/ |
| Node.js 18+ | https://nodejs.org/ |
| FFmpeg | `winget install ffmpeg` |
| Git | https://git-scm.com/download/win |
| uv | `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` |
| GTK3 Runtime | https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases |

### Windows Steps

```powershell
# Clone repo
git clone https://github.com/daschirag/voice.git
cd voice

# Install Python dependencies
uv sync

# Install spaCy model
uv run python -m spacy download en_core_web_sm

# Copy environment file
copy .env.example .env

# Install frontend dependencies
cd frontend
npm install
cd ..
```

For GPU (NVIDIA only) — add to `.env`:
```env
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
```

---

## ▶️ Running the System

You need **two terminals open** simultaneously.

### Terminal 1 — Start the Backend API

**Mac:**
```bash
cd voice
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Windows:**
```powershell
cd voice
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Wait until you see:
```
SUCCESS  | Speech Analysis System READY
INFO     | Uvicorn running on http://0.0.0.0:8000
```

> **First startup takes ~60 seconds** — it downloads the Whisper model (~500MB) on first run only. Every run after that is instant.

### Terminal 2 — Start the Frontend

```bash
cd voice/frontend
npm run dev
```

Wait until you see:
```
  VITE v5.x.x  ready in 300ms
  ➜  Local:   http://localhost:3000/
```

### Open in Browser

| URL | Purpose |
|-----|---------|
| http://localhost:3000 | React Frontend Dashboard |
| http://localhost:8000/docs | Interactive API Documentation (Swagger UI) |
| http://localhost:8000/api/v1/health | System health check |
| http://localhost:8000/redoc | Alternative API docs |

---

## 📡 Using the API

### Upload and analyze an audio file

```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -F "file=@/path/to/your/audio.mp3" \
  -F "role=general"
```

### Check job status

```bash
curl "http://localhost:8000/api/v1/status/{job_id}"
```

### Get the full report

```bash
curl "http://localhost:8000/api/v1/report/{job_id}"
```

### Download PDF report

```bash
curl -O "http://localhost:8000/api/v1/report/{job_id}/pdf"
```

### Available scoring roles

```bash
curl "http://localhost:8000/api/v1/roles"
```

**Roles:** `general` · `sales` · `executive` · `interview` · `coaching`

### Python example

```python
import httpx

# Upload audio file
with open("my_recording.mp3", "rb") as f:
    response = httpx.post(
        "http://localhost:8000/api/v1/analyze",
        files={"file": ("my_recording.mp3", f, "audio/mpeg")},
        data={"role": "general"},
        timeout=120.0,
    )

result = response.json()
job_id = result["job_id"]
print(f"Job ID: {job_id}")

# Get report
report = httpx.get(f"http://localhost:8000/api/v1/report/{job_id}").json()
print(f"Score: {report['results']['composite_score']}/5.0")
print(f"Grade: {report['results']['grade']}")
```

---

## 📁 Project Structure

```
voice/
├── src/
│   ├── main.py                    # FastAPI app entry point
│   ├── api/
│   │   ├── routes.py              # All API endpoints
│   │   └── schemas.py             # Pydantic request/response models
│   ├── core/
│   │   ├── config.py              # Settings from .env
│   │   └── logger.py              # Loguru logging setup
│   ├── workers/
│   │   └── tasks.py               # Celery task definitions
│   └── analysis/
│       ├── audio_dsp/
│       │   ├── preprocessor.py    # FFmpeg + DeepFilterNet + normalize
│       │   └── vad.py             # Silero VAD pause detection
│       ├── asr/
│       │   ├── transcriber.py     # faster-whisper transcription
│       │   ├── circuit_breaker.py # Fault tolerance pattern
│       │   └── fallback.py        # Cloud API fallback
│       ├── nlp/
│       │   ├── clarity.py         # ASR confidence scoring
│       │   ├── filler_words.py    # Filler word detection
│       │   ├── pauses.py          # Pause pattern analysis
│       │   ├── punctuation.py     # Clause boundary mapping
│       │   ├── language_quality.py # MATTR + Flesch-Kincaid
│       │   ├── delivery.py        # WPM + rhythm variance
│       │   └── tone.py            # F0 pitch + sentiment fusion
│       └── scoring/
│           ├── normalizer.py      # 1-5 score normalization
│           ├── weights.py         # Role-based weight matrix
│           ├── composite.py       # Weighted composite score
│           ├── report_builder.py  # Assemble report object
│           └── generator.py       # JSON + HTML + PDF output
├── frontend/
│   └── src/
│       ├── App.jsx                # Main app + routing
│       ├── UploadPanel.jsx        # Drag-drop upload + role select
│       ├── ProgressPanel.jsx      # Live progress tracking
│       ├── ResultsPanel.jsx       # Scores + radar chart + insights
│       ├── RadarChart.jsx         # Pure SVG radar chart
│       └── api.js                 # Axios API client
├── templates/
│   └── report.html                # Jinja2 HTML/PDF report template
├── models/                        # Downloaded model weights (auto)
├── uploads/                       # Temporary audio files
├── reports/                       # Generated JSON/HTML/PDF reports
├── logs/                          # Application logs
├── .env.example                   # Environment variable template
├── pyproject.toml                 # Python dependencies (uv)
├── Dockerfile                     # Container definition
├── docker-compose.yml             # Full stack deployment
└── start.bat                      # Windows one-click start
```

---

## 📐 Scoring Formulas

### Clarity
```
Score (%) = mean(word_confidence_i) × 100
< 70% → 1  |  70–79% → 2  |  80–87% → 3  |  88–94% → 4  |  ≥ 95% → 5
```

### Filler Words
```
Rate = (filler_count / total_words) × 100
0 → 5  |  1–4 → 4  |  5–9 → 3  |  10–14 → 2  |  ≥15 → 1
```

### Pause Patterns
```
Net Speech Duration = Total Duration - Cumulative Silence
Pause Frequency = Macro Pauses / (Net Speech Minutes)
Ideal: 4–8 pauses/min, 0.5–1.5s avg → Score 5
```

### Language Quality
```
MATTR = (1/N) × Σ TTR_i  (50-word sliding window)
FK Grade = 0.39 × (Words/Sentences) + 11.8 × (Syllables/Words) − 15.59
Final = 0.6 × TTR_score + 0.4 × FK_score
```

### Delivery
```
WPM = Total Words / Net Speech Minutes
Rhythm Variance = std_dev(WPM in rolling 10s windows)
130–160 WPM + variance < 20 → Score 5
```

### Composite Score
```
normalized_i = (score_i - 1) / 4
composite = 1 + (Σ normalized_i × weight_i) × 4
```

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# App
APP_ENV=development

# ASR — use 'cpu' + 'int8' on Mac, 'cuda' + 'float16' on NVIDIA GPU
WHISPER_DEVICE=cpu
WHISPER_MODEL_SIZE=small.en
WHISPER_COMPUTE_TYPE=int8

# Confidence threshold for circuit breaker
ASR_CONFIDENCE_THRESHOLD=0.75

# Cloud ASR fallback (optional — leave empty to disable)
DEEPGRAM_API_KEY=
ASSEMBLYAI_API_KEY=

# Task queue (optional — system works without these)
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Storage paths
UPLOAD_DIR=uploads
REPORTS_DIR=reports
MODELS_DIR=models

# Scoring
DEFAULT_ROLE=general
```

---

## 🔧 Troubleshooting

### ❌ "ffmpeg not found"
```bash
# Mac
brew install ffmpeg

# Verify
ffmpeg -version
```

### ❌ "No module named spacy" or spaCy model missing
```bash
uv run python -m spacy download en_core_web_sm
```

### ❌ WeasyPrint errors on Mac (PDF generation fails)
```bash
brew install pango libffi gdk-pixbuf gobject-introspection
```

If it still fails, set this in your terminal before running:
```bash
export DYLD_LIBRARY_PATH=$(brew --prefix)/lib:$DYLD_LIBRARY_PATH
```

### ❌ "OMP: Error #15" (OpenMP conflict on Mac/Windows)
Add this to your `.env`:
```env
KMP_DUPLICATE_LIB_OK=TRUE
```

### ❌ Whisper model downloading every time
The model downloads once to `models/whisper/`. If this folder is missing, it re-downloads. Make sure you do not delete the `models/` folder.

### ❌ Frontend shows "connection refused"
Make sure the backend is running first (Terminal 1) before starting the frontend (Terminal 2).

### ❌ "uv: command not found" after install
```bash
# Mac/Linux — add to shell profile
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### ❌ Processing is very slow on Mac
This is expected — Mac uses CPU only. For a 5-minute clip expect 25–30 seconds. For a 1-minute clip expect ~6 seconds. Consider using `tiny.en` model for faster but less accurate results:
```env
WHISPER_MODEL_SIZE=tiny.en
```

### ❌ Port 8000 already in use
```bash
# Find what's using port 8000
lsof -i :8000

# Kill it (replace PID with the number shown)
kill -9 PID
```

---

## 🐳 Docker Setup (Optional)

If you have Docker installed, you can run everything with one command:

```bash
docker-compose up --build
```

This starts:
- FastAPI backend on port 8000
- Redis on port 6379
- RabbitMQ on port 5672 (management UI: port 15672)

> Note: GPU passthrough requires `nvidia-container-toolkit` installed on the host.

---

## 📊 Performance Reference

| Audio Length | GPU (RTX 4050) | CPU (Mac M2) | CPU (Intel i7) |
|-------------|----------------|--------------|----------------|
| 30 seconds | ~3s | ~8s | ~12s |
| 5 minutes | ~10–12s | ~25–30s | ~35–45s |
| 30 minutes | ~55–65s | ~150–180s | ~200–240s |
| 60 minutes | ~110–130s | ~300–360s | ~400–480s |

---

## 📝 Supported Audio Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| MP3 | `.mp3` | Most common, fully supported |
| WAV | `.wav` | Best quality, largest files |
| M4A | `.m4a` | iPhone recordings, fully supported |
| OGG | `.ogg` | Open format, fully supported |
| FLAC | `.flac` | Lossless, fully supported |
| AAC | `.aac` | Fully supported |

**Maximum duration:** 60 minutes per clip  
**Recommended SNR:** ≥ 10 dB (system auto-denoises below 30 dB)

---

## 🗺️ Roadmap

- [ ] Real-time streaming analysis (live microphone)
- [ ] Multi-speaker diarisation
- [ ] Multilingual support (Hindi, Tamil, Spanish)
- [ ] User authentication + MongoDB storage
- [ ] Admin dashboard with user management
- [ ] GDPR-compliant auto-deletion (90-day policy)
- [ ] Video file support (extract audio from MP4)

---

## 👤 Author

**Chirag**  
B.Tech Information Technology — VIT Vellore  
Tech Lead, AI Engineering — Audix Technologies  
GitHub: [@daschirag](https://github.com/daschirag)

---

## 📄 License

This project is proprietary and confidential.  
© 2026 Audix Technologies. All rights reserved.

---

*Built with faster-whisper · Silero VAD · DeepFilterNet · Parselmouth · spaCy · FastAPI · React*