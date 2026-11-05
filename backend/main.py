#!/usr/bin/env python3
"""
ARC Audit API — FastAPI Backend
Handles: health, analysis, tasks, live solver, uploads
"""

import json, os, csv, io
from typing import Optional
from fastapi import FastAPI, Request, UploadFile, File, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from solver import score_all

# ─── Paths ─────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "cache_compact.json")
SCORES_FILE = os.path.join(DATA_DIR, "all_scores.csv")
LABELS_FILE = os.path.join(DATA_DIR, "labels.json")

# Phase A verdict threshold (pre-registered: |drop| below this is NEUTRAL)
CLIFF_THRESHOLD = 0.05

# ─── Ensure dirs ───────────────────────────────────────────────
os.makedirs(CACHE_DIR, exist_ok=True)

# ─── Load data ─────────────────────────────────────────────────
cache_data = {}
scores_data = []
labels_data = {}

def load_all():
    global cache_data, scores_data, labels_data
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                cache_data = json.load(f)
        except Exception as e:
            print(f"Cache load error: {e}")
            cache_data = {}
    if os.path.exists(SCORES_FILE):
        try:
            with open(SCORES_FILE, newline='') as f:
                reader = csv.DictReader(f)
                scores_data = [{k.strip().lower(): v for k, v in row.items()} for row in reader]
        except Exception as e:
            print(f"Scores load error: {e}")
            scores_data = []
    if os.path.exists(LABELS_FILE):
        try:
            with open(LABELS_FILE) as f:
                labels_data = json.load(f)
        except Exception as e:
            print(f"Labels load error: {e}")
            labels_data = {}

load_all()

# ─── App ───────────────────────────────────────────────────────
app = FastAPI(title="ARC Audit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(json.JSONDecodeError)
async def json_error_handler(request: Request, exc: json.JSONDecodeError):
    return JSONResponse(status_code=422, content={"detail": f"Malformed JSON: {exc}"})

# ─── Helpers ───────────────────────────────────────────────────
def row_task_id(row):
    return row.get('task_id', '') or row.get('task', '') or 'unknown'

def row_solver(row):
    return row.get('solver', '') or row.get('paradigm', '') or row.get('model', '') or 'unknown'

def row_version(row):
    return row.get('version', '') or 'v1'

def row_metric(row, metric):
    """Read a metric from a scores row, tolerating _score / _mean suffixes."""
    for key in (metric, f"{metric}_score", f"{metric}_mean"):
        if key in row and row[key] not in ('', None):
            try:
                return float(row[key])
            except (TypeError, ValueError):
                continue
    return None

def get_solver_list():
    return sorted({row_solver(r) for r in scores_data if row_solver(r) != 'unknown'})

def get_task_categories():
    """task_id -> human category, from labels.json"""
    out = {}
    for tid, info in labels_data.get('labels', {}).items():
        out[tid] = info.get('human_6cat', 'Unknown') if isinstance(info, dict) else str(info)
    return out

def get_categories():
    return sorted({c for c in get_task_categories().values() if c})

def normalise_version(v):
    v = str(v).strip().lower()
    return 'v2' if ('v2' in v or v == '2') else 'v1'

def verdict_for(drop: float) -> str:
    """drop = v1 - v2. Positive means v2 scored lower, i.e. a cliff."""
    if drop > CLIFF_THRESHOLD:
        return "CLIFF"
    if drop < -CLIFF_THRESHOLD:
        return "GAIN"
    return "NEUTRAL"

# ─── API Routes ────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "cache_loaded": len(cache_data),
        "scores_loaded": len(scores_data) > 0,
        "scores_rows": len(scores_data),
        "labels_loaded": bool(labels_data),
        "version": "1.1.0"
    }

@app.get("/api/analysis/overview")
def overview():
    versions = {normalise_version(row_version(r)) for r in scores_data}
    tasks = {row_task_id(r) for r in scores_data}
    return {
        "total_tasks": len(tasks),
        "total_runs": len(scores_data),
        "categories": len(get_categories()),
        "solvers": len(get_solver_list()),
        "versions": len(versions),
        "labeled_tasks": len(labels_data.get('labels', {})),
        "cache_predictions": len(cache_data)
    }

@app.get("/api/analysis/phase-a")
def phase_a():
    """Cross-version drop analysis. drop = v1 - v2; positive = v2 harder = CLIFF."""
    if not scores_data:
        return {"data": [], "threshold": CLIFF_THRESHOLD}

    from collections import defaultdict
    groups = defaultdict(lambda: {'v1': [], 'v2': []})

    for row in scores_data:
        solver = row_solver(row)
        version = normalise_version(row_version(row))
        for metric in ['exact', 'cell', 'object', 'edit']:
            val = row_metric(row, metric)
            if val is None:
                continue
            groups[(solver, metric)][version].append(val)

    results = []
    for (solver, metric), vals in groups.items():
        if not vals['v1'] or not vals['v2']:
            continue
        v1 = sum(vals['v1']) / len(vals['v1'])
        v2 = sum(vals['v2']) / len(vals['v2'])
        drop = v1 - v2
        results.append({
            "solver": solver,
            "metric": metric,
            "v1_score": round(v1, 3),
            "v2_score": round(v2, 3),
            "v1_n": len(vals['v1']),
            "v2_n": len(vals['v2']),
            "drop": round(drop, 3),
            "verdict": verdict_for(drop)
        })

    results.sort(key=lambda x: x['drop'], reverse=True)
    return {"data": results, "threshold": CLIFF_THRESHOLD}

@app.get("/api/analysis/phase-b")
def phase_b(rank_by: str = Query("cell", pattern="^(exact|cell|object|edit)$")):
    """Category decomposition. Rankings use rank_by (default cell, since exact is degenerate)."""
    if not scores_data or not labels_data:
        return {"categories": [], "rankings": [], "rank_by": rank_by}

    task_cats = get_task_categories()

    from collections import defaultdict
    cat_rows = defaultdict(list)
    cat_solver = defaultdict(lambda: defaultdict(list))

    for row in scores_data:
        cat = task_cats.get(row_task_id(row))
        if not cat:
            continue
        cat_rows[cat].append(row)
        val = row_metric(row, rank_by)
        if val is not None:
            cat_solver[cat][row_solver(row)].append(val)

    categories, rankings = [], []

    for cat in sorted(cat_rows.keys()):
        rows = cat_rows[cat]

        def avg(metric):
            vals = [v for v in (row_metric(r, metric) for r in rows) if v is not None]
            return round(sum(vals) / len(vals), 3) if vals else 0.0

        categories.append({
            "name": cat,
            "task_count": len({row_task_id(r) for r in rows}),
            "run_count": len(rows),
            "avg_exact": avg('exact'),
            "avg_cell": avg('cell'),
            "avg_object": avg('object'),
            "avg_edit": avg('edit')
        })

        solver_avgs = {s: sum(v) / len(v) for s, v in cat_solver[cat].items() if v}
        if solver_avgs:
            best = max(solver_avgs, key=solver_avgs.get)
            worst = min(solver_avgs, key=solver_avgs.get)
            rankings.append({
                "category": cat,
                "metric": rank_by,
                "best_solver": best,
                "best_score": round(solver_avgs[best], 3),
                "worst_solver": worst,
                "worst_score": round(solver_avgs[worst], 3)
            })

    return {"categories": categories, "rankings": rankings, "rank_by": rank_by}

@app.get("/api/tasks")
def tasks(
    category: Optional[str] = Query(None, description="Filter by human_6cat category"),
    solver: Optional[str] = Query(None, description="Filter by solver name"),
    version: Optional[str] = Query(None, description="Filter by version (v1 or v2)"),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
):
    """Return scored task runs, filterable by category, solver and version."""
    if not scores_data:
        return {"tasks": [], "total": 0, "returned": 0, "offset": offset}

    task_cats = get_task_categories()

    seen = set()
    rows = []
    for row in scores_data:
        tid = row_task_id(row)
        slv = row_solver(row)
        ver = normalise_version(row_version(row))
        key = (tid, slv, ver)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "task_id": tid,
            "solver": slv,
            "version": ver,
            "exact_score": row_metric(row, 'exact') or 0.0,
            "cell_score": row_metric(row, 'cell') or 0.0,
            "object_score": row_metric(row, 'object') or 0.0,
            "edit_score": row_metric(row, 'edit') or 0.0,
            "category": task_cats.get(tid, '-')
        })

    if category:
        rows = [r for r in rows if r['category'].lower() == category.lower()]
    if solver:
        rows = [r for r in rows if r['solver'].lower() == solver.lower()]
    if version:
        want = normalise_version(version)
        rows = [r for r in rows if r['version'] == want]

    total = len(rows)
    page = rows[offset:offset + limit]
    return {"tasks": page, "total": total, "returned": len(page), "offset": offset}

@app.get("/api/filters")
def filters():
    """Values the /api/tasks filters accept, for populating dropdowns."""
    return {
        "categories": get_categories(),
        "solvers": get_solver_list(),
        "versions": sorted({normalise_version(row_version(r)) for r in scores_data}),
    }

@app.post("/api/solve")
async def solve(request: Request):
    """Live solver with cache lookup + rule-based strategies, scored against ground truth."""
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Malformed JSON: {e}")

    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="Body must be a JSON object")

    train = body.get('train')
    test = body.get('test')
    if not isinstance(train, list) or not train:
        raise HTTPException(status_code=422, detail="'train' must be a non-empty list of {input, output} pairs")
    if not isinstance(test, list) or not test or not isinstance(test[0], dict):
        raise HTTPException(status_code=422, detail="'test' must be a non-empty list, with 'input' on the first item")

    test_input = test[0].get('input')
    if not isinstance(test_input, list) or not test_input or not isinstance(test_input[0], list):
        raise HTTPException(status_code=422, detail="'test[0].input' must be a non-empty 2-D grid")

    all_strategies = bool(body.get('all_strategies', False))
    task_id = body.get('task_id')
    ground_truth = test[0].get('output')  # may be absent; scores are null if so

    def scored(pred):
        if ground_truth:
            try:
                return score_all(pred, ground_truth)
            except Exception:
                return {"exact": None, "cell": None, "object": None, "edit": None}
        return {"exact": None, "cell": None, "object": None, "edit": None}

    predictions = []

    # Cache lookup: match on task_id only. Never claim a hit without one.
    cache_hit = False
    cache_solver = cache_version = None
    if task_id:
        for val in cache_data.values():
            if val.get('task_id') == task_id:
                cache_pred = val.get('pred', [])
                if not cache_pred:
                    continue
                cache_hit = True
                cache_solver = val.get('solver', 'unknown')
                cache_version = val.get('version', 'v1')
                s = scored(cache_pred)
                predictions.append({
                    "strategy": f"Cache ({cache_solver} {cache_version})",
                    "pred": cache_pred,
                    "exact_score": s["exact"], "cell_score": s["cell"],
                    "object_score": s["object"], "edit_score": s["edit"]
                })
                break

    # Rule-based strategies
    strategies = [("Identity", test_input)]
    strategies.append(("Color Map", [[1 - x if x in (0, 1) else x for x in r] for r in test_input]))
    strategies.append(("H-Flip", [list(reversed(r)) for r in test_input]))
    strategies.append(("V-Flip", list(reversed(test_input))))

    from collections import Counter
    nonzero = [c for r in test_input for c in r if c != 0]
    fill = Counter(nonzero).most_common(1)[0][0] if nonzero else 1
    strategies.append(("Background Fill", [[fill if c == 0 else c for c in r] for r in test_input]))
    strategies.append(("Constant Fill", [[1] * len(r) for r in test_input]))

    if not all_strategies:
        strategies = strategies[:3]

    for name, pred in strategies:
        s = scored(pred)
        predictions.append({
            "strategy": name,
            "pred": pred,
            "exact_score": s["exact"], "cell_score": s["cell"],
            "object_score": s["object"], "edit_score": s["edit"]
        })

    if ground_truth:
        predictions.sort(key=lambda p: (p["cell_score"] or 0), reverse=True)

    return {
        "cache_hit": cache_hit,
        "solver": cache_solver,
        "version": cache_version,
        "scored": bool(ground_truth),
        "all_strategies": all_strategies,
        "predictions": predictions
    }

@app.post("/api/upload/cache")
async def upload_cache(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Malformed JSON: {e}")
    global cache_data
    if isinstance(data, dict):
        cache_data.update(data)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and 'task_id' in item:
                k = f"{item.get('solver','unknown')}_{item.get('version','v1')}_{item['task_id']}"
                cache_data[k] = item
    else:
        raise HTTPException(status_code=422, detail="Cache must be a JSON object or list")
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache_data, f)
    return {"status": "ok", "count": len(cache_data)}

@app.post("/api/upload/scores")
async def upload_scores(file: UploadFile = File(...)):
    global scores_data
    content = await file.read()
    decoded = content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(decoded))
    scores_data = [{k.strip().lower(): v for k, v in row.items()} for row in reader]
    with open(SCORES_FILE, 'w', newline='') as f:
        f.write(decoded)
    return {"status": "ok", "rows_loaded": len(scores_data)}

@app.post("/api/upload/labels")
async def upload_labels(file: UploadFile = File(...)):
    global labels_data
    content = await file.read()
    decoded = content.decode('utf-8')
    try:
        labels_data = json.loads(decoded)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Malformed JSON: {e}")
    with open(LABELS_FILE, 'w') as f:
        json.dump(labels_data, f, indent=2)
    return {"status": "ok", "labels_loaded": len(labels_data.get('labels', {}))}

# ─── Static Files ──────────────────────────────────────────────
frontend_path = os.path.join(BASE, "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    print("ARC Audit API")
    print(f"   Cache: {len(cache_data)} predictions")
    print(f"   Scores: {'OK' if scores_data else 'MISSING'} ({len(scores_data)} rows)")
    print(f"   Labels: {'OK' if labels_data else 'MISSING'}")
    print("   -> http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)