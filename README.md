# Speech Analysis System

A production-grade AI platform that automatically evaluates recorded speech across 7 communication dimensions. Built for sales coaching, interview preparation, call centre QA, and public speaking development.

Upload any audio file or record live from your browser microphone. The system transcribes your speech, analyzes it across 7 dimensions, scores each 1-5, and generates a PDF coaching report in 10-30 seconds.

---

## What This System Does

Your voice is recorded live or uploaded as a file. The system runs it through:

1. FFmpeg converts any audio format to 16kHz mono WAV
2. DeepFilterNet removes background noise
3. faster-whisper transcribes speech with word-level timestamps
4. Silero VAD detects speech and silence segments
5. 7 AI modules analyze different aspects of communication
6. Parselmouth extracts pitch and tone features
7. A scoring engine produces a 1-5 score per dimension
8. A PDF and HTML report is generated with coaching insights

---

## 7 Analysis Dimensions

| # | Dimension | What It Measures | Formula |
|---|-----------|-----------------|---------|
| 1 | Clarity | How clearly you articulate words | mean(ASR confidence) x 100 |
| 2 | Filler Words | Um, uh, like, basically, you know | fillers / total words x 100 |
| 3 | Pause Patterns | Deliberate vs hesitation pauses | macro pauses / speech minutes |
| 4 | Punctuation Use | Pausing at clause boundaries | correct pauses / boundaries |
| 5 | Language Quality | Vocabulary richness + complexity | 0.6 x MATTR + 0.4 x FK grade |
| 6 | Delivery Quality | Speaking rate and rhythm | WPM + rolling variance |
| 7 | Tone / Demeanor | Friendly/Formal/Energetic/Monotone/Nervous | F0 pitch + sentiment fusion |

---

## Scoring System

Each dimension scores 1 to 5. The composite score is a weighted average based on your selected role profile.

| Score | Grade | Meaning |
|-------|-------|---------|
| 4.5 - 5.0 | A | Outstanding |
| 3.5 - 4.4 | B | Strong performance |
| 2.5 - 3.4 | C | Solid with room to grow |
| 1.5 - 2.4 | D | Needs focused work |
| 1.0 - 1.4 | F | Significant improvement needed |

### Role Profiles

| Role | What Gets Weighted Higher |
|------|--------------------------|
| General | Equal weights across all 7 |
| Sales | Delivery 25% + Tone 20% + Pauses 20% |
| Executive | Language Quality 25% + Clarity 20% + Filler Words 20% |
| Interview | Clarity 20% + Language 20% |
| Coaching | Even development across all dimensions |

---

## User Roles

### Client
- Register with name, email, mobile, username, password
- Wait for admin verification before first login
- Record live voice from browser microphone
- Upload any audio file (MP3, WAV, M4A, OGG, FLAC)
- View scores, radar chart, coaching insights
- Download PDF and HTML reports
- Access all past analysis history

### Admin
- Login instantly with pre-seeded credentials
- View all registered users
- Verify or unverify client accounts
- View all analyses from all clients
- Search reports by username
- Download any client PDF report
- See dashboard statistics

---

## Tech Stack

| Component | Technology | Why Chosen |
|-----------|-----------|------------|
| ASR | faster-whisper small.en GPU float16 | 5x faster than Whisper, 6.65% WER |
| VAD | Silero VAD PyTorch | 87.7% accuracy vs WebRTC 50% |
| Noise Reduction | DeepFilterNet3 | Preserves phase integrity |
| Audio I/O | FFmpeg | Handles any codec without memory issues |
| Pitch Extraction | Parselmouth Praat | 2.8ms per second, clinical-grade |
| NLP Parser | spaCy en_core_web_sm | Cython-optimized, fastest available |
| Vocabulary | MATTR lexical-diversity | Length-bias-free type-token ratio |
| Readability | textstat Flesch-Kincaid | Validated syllable counting |
| Sentiment | VADER with RoBERTa fallback | Conversational speech sentiment |
| Backend | FastAPI + Uvicorn | Async, auto Swagger docs |
| Database | MongoDB Atlas | Cloud-hosted, free tier available |
| Auth | JWT python-jose + bcrypt | Stateless secure token auth |
| Reports | Jinja2 + WeasyPrint | HTML to PDF via headless browser |
| Frontend | React 18 + Vite | Fast HMR, component-based |
| Dependencies | uv Astral | 10-100x faster than pip |

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11.x | Required |
| Node.js | 18 or higher | Required |
| FFmpeg | Any | Required for audio conversion |
| Git | Any | Required |
| uv | Latest | Required |
| MongoDB Atlas | Free tier | Required - create account at mongodb.com |

---

## Mac Setup

Open Terminal and run each command one at a time.

### 1. Install Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install Python 3.11

```bash
brew install python@3.11
python3.11 --version
```

### 3. Install FFmpeg

```bash
brew install ffmpeg
ffmpeg -version
```

### 4. Install Node.js

```bash
brew install node
node --version
```

### 5. Install GTK3 for PDF generation

```bash
brew install pango gdk-pixbuf libffi gobject-introspection
```

### 6. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc
uv --version
```

### 7. Clone the repository

```bash
git clone https://github.com/daschirag/voice.git
cd voice
```

### 8. Install Python dependencies

```bash
uv sync
```

This takes 5 to 10 minutes on first run. It downloads PyTorch and all ML models (about 2GB total).

### 9. Install spaCy language model

```bash
uv run python -m spacy download en_core_web_sm
```

### 10. Set up environment variables

```bash
cp .env.example .env
```

Open the .env file and update these values:
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
MONGODB_URI=your_mongodb_atlas_connection_string_here
MONGODB_DB_NAME=speech_analysis_db
ADMIN_USERNAME=atlasAdmin
ADMIN_PASSWORD=admin
ADMIN_EMAIL=admin@yourcompany.com

### 11. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 12. Verify installation

```bash
uv run python -c "
import importlib
packages = ['fastapi','faster_whisper','torch','silero_vad','df','parselmouth','spacy','textstat','jinja2','weasyprint','motor']
for p in packages:
    try:
        importlib.import_module(p)
        print('OK   ' + p)
    except Exception as e:
        print('FAIL ' + p + ' -- ' + str(e))
"
```

All lines should show OK.

---

## Windows Setup

Open PowerShell as Administrator for all steps.

### 1. Install Python 3.11

Download from https://www.python.org/downloads/ and run the installer.
Check the box that says "Add Python to PATH" during installation.

```powershell
python --version
```

### 2. Install FFmpeg

```powershell
winget install ffmpeg
```

Close and reopen PowerShell after this step.

### 3. Install Node.js

Download the LTS version from https://nodejs.org and install it.

```powershell
node --version
```

### 4. Install GTK3 Runtime for PDF generation

Download and run the installer from:
https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases

During installation check the box to add GTK to PATH. Restart PowerShell after.

### 5. Install uv

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen PowerShell.

```powershell
uv --version
```

### 6. Clone the repository

```powershell
git clone https://github.com/daschirag/voice.git
cd voice
```

### 7. Install Python dependencies

```powershell
uv sync
```

For NVIDIA GPU users only, also run this:

```powershell
.venv\Scripts\python.exe -m pip install torch==2.3.0+cu121 torchaudio==2.3.0+cu121 --index-url https://download.pytorch.org/whl/cu121
```

### 8. Install spaCy language model

```powershell
uv run python -m spacy download en_core_web_sm
```

### 9. Set up environment variables

```powershell
copy .env.example .env
```

Open .env in Notepad and set these values:

For CPU only (no NVIDIA GPU):
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8

For NVIDIA GPU:
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16

Also set your MongoDB connection:
MONGODB_URI=your_mongodb_atlas_connection_string_here
MONGODB_DB_NAME=speech_analysis_db
ADMIN_USERNAME=atlasAdmin
ADMIN_PASSWORD=admin
ADMIN_EMAIL=admin@yourcompany.com

### 10. Install frontend dependencies

```powershell
cd frontend
npm install
cd ..
```

---

## Running the System

You need two terminals open at the same time.

### Terminal 1 - Start the Backend

Mac:
```bash
cd voice
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Windows:
```powershell
cd voice
.venv\Scripts\Activate.ps1
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Wait until you see all of these lines:
SUCCESS  | Connected to MongoDB Atlas: speech_analysis_db
SUCCESS  | Admin account created: atlasAdmin
SUCCESS  | Speech Analysis System v2.0 READY
INFO     | Application startup complete.

The first startup takes about 60 seconds because it downloads the Whisper model (500MB). Every run after that is instant.

### Terminal 2 - Start the Frontend

Mac:
```bash
cd voice/frontend
npm run dev
```

Windows:
```powershell
cd voice\frontend
npm run dev
```

Wait until you see:
VITE ready
Local: http://localhost:3000/

---

## Using the System

Open your browser and go to http://localhost:3000

### Admin Login
URL      : http://localhost:3000/login
Username : atlasAdmin
Password : admin

The admin dashboard shows:
- Overview with total users, analyses count, average score
- User Management to verify or unverify client accounts
- All Reports to search by username and download PDFs

### Client Registration Flow

1. Go to http://localhost:3000/register
2. Fill in Full Name, Email, Mobile Number, Username, Password
3. Submit the form
4. Admin must log in and verify your account before you can use it
5. Go to User Management, find your username, click Verify

### Client Analysis Flow

1. Go to http://localhost:3000/login
2. Login with your username and password
3. Choose Record Live or Upload File
4. Record Live: Click Start Recording, speak, click Stop Recording
5. Upload File: Drag and drop or click to browse
6. Select a scoring role from the dropdown
7. Click Analyze
8. Wait 10 to 30 seconds for results
9. View your scores, radar chart, and coaching insights
10. Download PDF or HTML report

---

## API Reference

Base URL: http://localhost:8000

Interactive documentation: http://localhost:8000/docs

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| POST | /api/v1/auth/register | No | Create new account |
| POST | /api/v1/auth/login | No | Get JWT access token |
| GET | /api/v1/auth/me | Yes | Get current user info |
| POST | /api/v1/analyze | Verified client | Analyze audio file |
| GET | /api/v1/my-reports | Verified client | Get my analyses |
| GET | /api/v1/report/{id} | Yes | Get full JSON report |
| GET | /api/v1/report/{id}/pdf | No | Download PDF report |
| GET | /api/v1/admin/users | Admin | List all users |
| PUT | /api/v1/admin/verify/{id} | Admin | Verify a user |
| DELETE | /api/v1/admin/users/{id} | Admin | Delete a user |
| GET | /api/v1/admin/reports | Admin | All analyses |
| GET | /api/v1/admin/stats | Admin | Dashboard stats |
| GET | /api/v1/health | No | System health check |

---

## Supported Audio Formats

| Format | Extension | Best For |
|--------|-----------|----------|
| MP3 | .mp3 | General recordings |
| WAV | .wav | Best quality |
| M4A | .m4a | iPhone voice memos |
| OGG | .ogg | Open source format |
| FLAC | .flac | Lossless quality |
| WebM | .webm | Browser recordings |

Maximum duration: 60 minutes per clip

---

## Performance Reference

| Audio Duration | GPU RTX 4050 | Mac CPU M2 | CPU Intel i7 |
|----------------|--------------|------------|--------------|
| 30 seconds | 3 seconds | 8 seconds | 12 seconds |
| 5 minutes | 10-12 seconds | 25-30 seconds | 35-45 seconds |
| 30 minutes | 55-65 seconds | 150-180 seconds | 200-240 seconds |

---

## Project Structure
voice/
├── src/
│   ├── main.py                    FastAPI application entry point
│   ├── api/
│   │   ├── routes.py              All API endpoints
│   │   ├── auth.py                JWT authentication system
│   │   └── schemas.py             Request and response models
│   ├── core/
│   │   ├── config.py              Settings loaded from .env
│   │   └── logger.py              Loguru logging setup
│   ├── db/
│   │   └── mongodb.py             MongoDB Atlas connection and seeding
│   └── analysis/
│       ├── audio_dsp/
│       │   ├── preprocessor.py    FFmpeg conversion and DeepFilterNet
│       │   └── vad.py             Silero VAD pause detection
│       ├── asr/
│       │   ├── transcriber.py     faster-whisper transcription
│       │   ├── circuit_breaker.py Fault tolerance pattern
│       │   └── fallback.py        Cloud API fallback
│       ├── nlp/
│       │   ├── clarity.py         ASR confidence scoring
│       │   ├── filler_words.py    Regex filler word detection
│       │   ├── pauses.py          Pause pattern analysis
│       │   ├── punctuation.py     Clause boundary mapping
│       │   ├── language_quality.py MATTR and Flesch-Kincaid
│       │   ├── delivery.py        WPM and rhythm variance
│       │   └── tone.py            F0 pitch and sentiment fusion
│       └── scoring/
│           ├── normalizer.py      1-5 score normalization
│           ├── weights.py         Role-based weight matrix
│           ├── composite.py       Weighted composite score
│           ├── report_builder.py  Assemble report data
│           └── generator.py       JSON HTML and PDF output
├── frontend/
│   └── src/
│       ├── App.jsx                Main app with routing
│       ├── AuthContext.jsx        JWT auth state management
│       ├── Login.jsx              Login page
│       ├── Register.jsx           Registration page
│       ├── ClientDashboard.jsx    Client portal with recorder
│       ├── AdminDashboard.jsx     Admin panel
│       ├── RadarChart.jsx         Pure SVG radar chart
│       └── api.js                 Axios API client
├── templates/
│   └── report.html                Jinja2 report template
├── .env.example                   Environment variable template
├── pyproject.toml                 Python dependencies
├── docker-compose.yml             Docker deployment
└── README.md                      This file

---

## Environment Variables Reference

Copy .env.example to .env and fill in your values.
APP_ENV=development
SECRET_KEY=change-this-to-a-random-secret-string
WHISPER_DEVICE=cpu
WHISPER_MODEL_SIZE=small.en
WHISPER_COMPUTE_TYPE=int8
ASR_CONFIDENCE_THRESHOLD=0.75
CIRCUIT_BREAKER_FAILURE_COUNT=3
CIRCUIT_BREAKER_COOLDOWN_SECONDS=60
DEEPGRAM_API_KEY=
ASSEMBLYAI_API_KEY=
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/
MONGODB_DB_NAME=speech_analysis_db
ADMIN_USERNAME=atlasAdmin
ADMIN_PASSWORD=admin
ADMIN_EMAIL=admin@yourcompany.com
UPLOAD_DIR=uploads
REPORTS_DIR=reports
MODELS_DIR=models
MAX_UPLOAD_DURATION_MINUTES=60
DEFAULT_ROLE=general
KMP_DUPLICATE_LIB_OK=TRUE
HF_HUB_DISABLE_SYMLINKS_WARNING=1

---

## Troubleshooting

### FFmpeg not found
Mac: brew install ffmpeg
Windows: winget install ffmpeg then restart PowerShell

### spaCy model not found
```bash
uv run python -m spacy download en_core_web_sm
```

### WeasyPrint PDF errors on Mac
```bash
brew install pango libffi gdk-pixbuf gobject-introspection
export DYLD_LIBRARY_PATH=$(brew --prefix)/lib:$DYLD_LIBRARY_PATH
```

### Port 8000 already in use
Mac: lsof -i :8000 then kill -9 PID
Windows: netstat -ano | findstr :8000 then taskkill /PID xxxx /F

### Microphone not working
Allow microphone access when the browser asks. Chrome works best.

### MongoDB connection failed
Check MONGODB_URI in .env is correct. Make sure your IP address is whitelisted in MongoDB Atlas under Network Access.

### First startup very slow
Normal. Whisper model downloads once on first run (500MB). Every run after is instant.

### Processing slow on Mac
Mac uses CPU mode. Use a smaller model for faster results:
WHISPER_MODEL_SIZE=tiny.en

---

## Author

Chirag
B.Tech Information Technology, VIT Vellore
Tech Lead AI Engineering, Audix Technologies
GitHub: https://github.com/daschirag

---

## License

Proprietary and confidential.
2026 Audix Technologies. All rights reserved.