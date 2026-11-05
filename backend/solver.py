import numpy as np
from collections import Counter
from typing import List, Dict, Optional, Tuple
import json, os, glob

class ARCSolver:
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache = {}
        self.cache_dir = cache_dir
        self._load_cache()

    def _load_cache(self):
        """Load NVIDIA predictions from cache files"""
        if not os.path.exists(self.cache_dir):
            return
        for f in glob.glob(f"{self.cache_dir}/*.json"):
            try:
                with open(f) as fp:
                    d = json.load(fp)
                fname = os.path.basename(f)[:-5]
                parts = fname.split('_')
                task_id = parts[-1]
                version = parts[-2]
                solver = '_'.join(parts[:-2])
                key = f"{solver}_{version}_{task_id}"
                self.cache[key] = {
                    "task_id": task_id,
                    "version": version,
                    "solver": solver,
                    "pred": d.get('pred', []),
                    "gt": d.get('gt', [])
                }
            except Exception as e:
                pass

        # Also try compact cache
        compact = os.path.join(self.cache_dir, "cache_compact.json")
        if os.path.exists(compact):
            with open(compact) as f:
                data = json.load(f)
                self.cache.update(data)

    def cache_lookup(self, task_id: str) -> Optional[Dict]:
        """Find any cached prediction for this task"""
        for key, val in self.cache.items():
            if val.get("task_id") == task_id:
                return val
        return None

    def solve(self, task: dict, strategy: Optional[str] = None) -> Tuple[Optional[List], str]:
        train = task.get("train", [])
        test_in = task.get("test", [{}])[0].get("input", []) if task.get("test") else []

        if not train or not test_in:
            return None, "failed"

        strategies = [
            ("identity", self._solve_identity),
            ("color_map", self._solve_color_map),
            ("symmetry_h", self._solve_symmetry_h),
            ("symmetry_v", self._solve_symmetry_v),
            ("background", self._solve_background),
            ("constant", self._solve_constant),
        ]

        if strategy and strategy != "auto":
            fn = dict(strategies).get(strategy)
            if fn:
                result = fn(train, test_in)
                return (result, strategy) if result is not None else (None, "failed")
            return None, "failed"

        for name, fn in strategies:
            result = fn(train, test_in)
            if result is not None:
                return result, name

        return None, "failed"

    def _solve_identity(self, train, test_in):
        all_id = all(
            np.array(ex.get("input", [])).tolist() == np.array(ex.get("output", [])).tolist()
            for ex in train
        )
        return np.array(test_in).tolist() if all_id else None

    def _solve_color_map(self, train, test_in):
        color_map = {}
        for ex in train:
            inp = np.array(ex.get("input", []))
            out = np.array(ex.get("output", []))
            if inp.shape != out.shape:
                return None
            for i in range(inp.shape[0]):
                for j in range(inp.shape[1]):
                    a, b = int(inp[i,j]), int(out[i,j])
                    if a in color_map and color_map[a] != b:
                        return None
                    color_map[a] = b
        if not color_map:
            return None
        arr = np.array(test_in)
        # Unseen colours must pass through unchanged. Starting from zeros_like
        # silently blanked every colour the training pairs never showed.
        if not set(np.unique(arr).tolist()).issubset(color_map.keys()):
            return None
        result = arr.copy()
        for a, b in color_map.items():
            result[arr == a] = b
        return result.tolist()

    def _solve_symmetry_h(self, train, test_in):
        valid = True
        for ex in train:
            inp = np.array(ex.get("input", []))
            out = np.array(ex.get("output", []))
            if inp.shape != out.shape or not np.array_equal(np.fliplr(inp), out):
                valid = False
                break
        return np.fliplr(np.array(test_in)).tolist() if valid else None

    def _solve_symmetry_v(self, train, test_in):
        valid = True
        for ex in train:
            inp = np.array(ex.get("input", []))
            out = np.array(ex.get("output", []))
            if inp.shape != out.shape or not np.array_equal(np.flipud(inp), out):
                valid = False
                break
        return np.flipud(np.array(test_in)).tolist() if valid else None

    def _solve_constant(self, train, test_in):
        colors = []
        for ex in train:
            colors.extend(np.array(ex.get("output", [])).flatten().tolist())
        if not colors:
            return None
        most = Counter(colors).most_common(1)[0][0]
        h, w = len(test_in), len(test_in[0])
        return [[int(most)] * w for _ in range(h)]

    def _solve_background(self, train, test_in):
        colors = []
        for ex in train:
            for c in np.array(ex.get("output", [])).flatten().tolist():
                if c != 0:
                    colors.append(c)
        if not colors:
            return None
        most = Counter(colors).most_common(1)[0][0]
        arr = np.array(test_in)
        result = np.where(arr == 0, int(most), arr)
        return result.tolist()


def _pad(a, b):
    a, b = np.array(a), np.array(b)
    H, W = max(a.shape[0], b.shape[0]), max(a.shape[1], b.shape[1])
    A = np.full((H, W), -1)
    B = np.full((H, W), -1)
    A[:a.shape[0], :a.shape[1]] = a
    B[:b.shape[0], :b.shape[1]] = b
    return A, B

def score_all(pred, gt):
    pred, gt = np.array(pred), np.array(gt)

    # exact
    exact = float(pred.shape == gt.shape and (pred == gt).all())

    # cell
    A, B = _pad(pred, gt)
    cell = float((A == B).sum() / max(A.size, 1))

    # object
    mask = (B != 0) | (A != 0)
    object_score = float((A[mask] == B[mask]).mean()) if mask.any() else cell

    # edit
    diff = (A != B).sum()
    shape_pen = abs(pred.size - gt.size)
    edit = float(max(0.0, 1 - (diff + shape_pen) / max(A.size, 1)))

    return {"exact": exact, "cell": cell, "object": object_score, "edit": edit}