# 🔬 ARC Audit Project

**Abstraction Cliff + Emergence Audit** — A complete full-stack project with Phase A/B analysis dashboard and live ARC solver.

---

## 📁 Project Structure

```
arc-audit-project/
├── backend/
│   ├── main.py              # FastAPI server (API + static files)
│   ├── solver.py            # ARC solver strategies + scoring
│   ├── analysis.py          # Phase A/B analysis engine
│   ├── models.py            # Pydantic request/response models
│   ├── requirements.txt     # Python dependencies
│   └── data/                # [YOU ADD FILES HERE]
│       ├── cache/           # NVIDIA predictions
│       ├── all_scores.csv   # Scored results
│       └── labels.json      # 60-task ground truth
├── frontend/
│   ├── index.html           # Main dashboard UI
│   └── static/
│       ├── css/style.css    # Dark theme styles
│       └── js/app.js        # Frontend controller
├── scripts/
│   ├── extract_nvidia_cache.py   # Run on NVIDIA server
│   └── prepare_data.py           # Run on Mac after download
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 🚀 Quick Start (Mac Local)

### Step 1: Install Dependencies

```bash
cd arc-audit-project
pip install -r backend/requirements.txt
```

### Step 2: Add Your NVIDIA Data

You need 3 files from your NVIDIA server (see **NVIDIA Extraction** below):

1. `arc_cache_compact.json` → `backend/data/cache/cache_compact.json`
2. `all_scores.csv` → `backend/data/all_scores.csv`
3. `labels.json` → `backend/data/labels.json`

Or use the helper:

```bash
# Place downloaded files in a 'downloads/' folder first
python scripts/prepare_data.py
```

### Step 3: Run Server

```bash
python backend/main.py
```

Open: **http://localhost:8000**

---

## 🐳 Docker (Alternative)

```bash
docker-compose up --build
```

Open: **http://localhost:8000**

---

## 🔧 NVIDIA Server Extraction (Do This First!)

Your NVIDIA server expires in 1 week. Run this **now**:

### Option A: Script (Recommended)

Upload `scripts/extract_nvidia_cache.py` to your NVIDIA Jupyter and run:

```bash
python extract_nvidia_cache.py
```

This creates 3 files in `/workspace/`:
- `arc_cache_compact.json` — 1680 predictions
- `all_scores.csv` — scored results
- `labels.json` — ground truth labels

Download all 3 from Jupyter sidebar.

### Option B: Manual (Jupyter Cells)

```python
# Cell 1: Extract cache
import json, glob, os

files = glob.glob('/root/arc_audit/outputs/*.json')
cache = {}
for f in files:
    try:
        with open(f) as fp:
            d = json.load(fp)
        fname = os.path.basename(f)[:-5]
        parts = fname.split('_')
        task_id = parts[-1]
        version = parts[-2]
        solver = '_'.join(parts[:-2])
        cache[f"{solver}_{version}_{task_id}"] = {
            "task_id": task_id, "version": version,
            "solver": solver, "pred": d.get('pred', []), "gt": d.get('gt', [])
        }
    except: pass

with open('/workspace/arc_cache_compact.json', 'w') as f:
    json.dump(cache, f)
print(f"Extracted {len(cache)} predictions")

# Cell 2: Copy scores & labels
import shutil
shutil.copy('/root/arc_audit/results/all_scores.csv', '/workspace/all_scores.csv')
shutil.copy('/workspace/final_60task_groundtruth.json', '/workspace/labels.json')

# Cell 3: Download links
from IPython.display import FileLink
FileLink('/workspace/arc_cache_compact.json')
FileLink('/workspace/all_scores.csv')
FileLink('/workspace/labels.json')
```

Click each blue link to download.

---

## 🎯 Features

### 📊 Dashboard
- Total tasks, categories, solvers, cache count
- Quick stats overview

### 📉 Phase A — Cross-Version Drop
- Per-solver, per-metric comparison (v1 vs v2)
- Drop calculation + verdict (CLIFF / GAIN / NEUTRAL)

### 🎯 Phase B — Category Decomposition
- Category-wise accuracy breakdown
- Difficulty rankings
- Abstraction cliff identification

### 📋 Task Browser
- Filter by category, solver, version
- View exact/cell/object/edit scores

### 🧪 Live Solver
- **Cache lookup**: Instant if task was NVIDIA-trained
- **Rule-based fallback**: Identity, Color Map, Symmetry (H/V), Constant Fill, Background Fill
- **Strategy comparison**: Run all strategies side-by-side
- **Real scoring**: Computes exact/cell/object/edit metrics

### 📤 Upload Panel
- Drag-and-drop file upload
- No terminal commands needed after initial setup

---

## 🧠 Solver Strategies

| Priority | Strategy | When It Works |
|----------|----------|---------------|
| 1 | **Cache** | Task was in your NVIDIA training set |
| 2 | **Identity** | Output = Input (preservation tasks) |
| 3 | **Color Map** | Consistent 1:1 color transformation |
| 4 | **Symmetry H** | Horizontal flip matches train |
| 5 | **Symmetry V** | Vertical flip matches train |
| 6 | **Background Fill** | Fill zeros with dominant color |
| 7 | **Constant Fill** | Entire grid = most common color |

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard UI |
| GET | `/api/health` | Backend status |
| POST | `/api/solve` | Solve single task |
| POST | `/api/solve/all-strategies` | Compare all strategies |
| GET | `/api/analysis/overview` | Dashboard stats |
| GET | `/api/analysis/phase-a` | Cross-version drop |
| GET | `/api/analysis/phase-b` | Category breakdown |
| GET | `/api/tasks` | Browse tasks (with filters) |
| POST | `/api/upload/cache` | Upload cache JSON |
| POST | `/api/upload/scores` | Upload scores CSV |
| POST | `/api/upload/labels` | Upload labels JSON |

---

## 🎓 For Professor Evaluation

This project demonstrates:

1. **Real-world ML pipeline**: Data extraction → scoring → analysis → deployment
2. **Full-stack architecture**: FastAPI backend + connected HTML/JS frontend
3. **Multi-paradigm solver comparison**: Program synthesis, LLM, TTT
4. **Statistical analysis**: Cross-version drop, category decomposition
5. **Production readiness**: Docker, CORS, file upload, error handling

---

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, Pandas, NumPy
- **Frontend**: Vanilla JS, CSS Grid/Flexbox (no frameworks)
- **Deployment**: Docker, Docker Compose
- **Data**: JSON cache, CSV scores, Pydantic models

---

## ⚠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | Run `pip install -r backend/requirements.txt` |
| Port 8000 in use | Change port in `backend/main.py` or `docker-compose.yml` |
| No data showing | Upload files via **📤 Upload Data** tab or place in `backend/data/` |
| Cache not loading | Ensure file is named `cache_compact.json` in `backend/data/cache/` |
| CORS error | Backend must run on same origin, or update `allow_origins` in `main.py` |

---

## 📄 License

Student Project — ARC-AGI Abstraction Cliff Audit 2026

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

24 tests covering the four-metric scoring layer (exact, cell, object, edit),
grid padding for mismatched shapes, and the rule-based solver strategies.

## Note on data

The required data files are already included in `backend/data/`.
The NVIDIA extraction section below is retained for provenance only —
you do not need to run it.
