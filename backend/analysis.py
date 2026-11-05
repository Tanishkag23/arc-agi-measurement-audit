import pandas as pd
import numpy as np
import json
import os
from typing import Dict, List

class ARCAnalysis:
    def __init__(self, scores_path: str = "data/all_scores.csv", labels_path: str = "data/labels.json"):
        self.scores = None
        self.labels = {}
        self.phase_a = {}
        self.phase_b = {}

        if os.path.exists(scores_path):
            self.scores = pd.read_csv(scores_path)

        if os.path.exists(labels_path):
            with open(labels_path) as f:
                data = json.load(f)
                self.labels = {tid: info.get("human_6cat", info.get("category", "Unknown")) 
                              for tid, info in data.get("labels", {}).items()}

    def get_overview(self) -> Dict:
        if self.scores is None:
            return {"tasks": 0, "categories": 0, "solvers": 0}

        labeled = self.scores[self.scores["task_id"].isin(self.labels.keys())]
        return {
            "total_tasks": int(self.scores["task_id"].nunique()),
            "total_runs": len(self.scores),
            "categories": len(self.labels),
            "solvers": self.scores["solver"].nunique() if "solver" in self.scores.columns else 0,
            "versions": self.scores["version"].nunique() if "version" in self.scores.columns else 0,
            "labeled_tasks": int(labeled["task_id"].nunique()) if len(labeled) > 0 else 0
        }

    def get_phase_a(self) -> List[Dict]:
        if self.scores is None or "version" not in self.scores.columns:
            return []

        results = []
        for solver in self.scores["solver"].unique():
            sub = self.scores[self.scores["solver"] == solver]
            v1 = sub[sub["version"] == "v1"]
            v2 = sub[sub["version"] == "v2"]

            if len(v1) == 0 or len(v2) == 0:
                continue

            for metric in ["exact", "cell", "object", "edit"]:
                v1_mean = v1[metric].mean()
                v2_mean = v2[metric].mean()
                drop = v1_mean - v2_mean
                ratio = (v2_mean / v1_mean) if v1_mean > 0 else 0

                verdict = "NEUTRAL"
                if drop > 0.05:
                    verdict = "CLIFF"
                elif drop < -0.05:
                    verdict = "GAIN"

                results.append({
                    "solver": solver,
                    "metric": metric,
                    "v1_mean": round(v1_mean, 4),
                    "v2_mean": round(v2_mean, 4),
                    "drop": round(drop, 4),
                    "ratio": round(ratio, 4),
                    "verdict": verdict
                })
        return results

    def get_phase_b(self) -> List[Dict]:
        if self.scores is None or not self.labels:
            return []

        self.scores["category"] = self.scores["task_id"].map(self.labels)
        labeled = self.scores[self.scores["category"].notna()]

        results = []
        for solver in labeled["solver"].unique():
            for cat in labeled["category"].unique():
                sub = labeled[(labeled["solver"] == solver) & (labeled["category"] == cat)]
                v1 = sub[sub["version"] == "v1"]
                v2 = sub[sub["version"] == "v2"]

                if len(v1) == 0 or len(v2) == 0:
                    continue

                for metric in ["exact", "cell", "object", "edit"]:
                    results.append({
                        "solver": solver,
                        "category": cat,
                        "metric": metric,
                        "v1_mean": round(v1[metric].mean(), 4),
                        "v2_mean": round(v2[metric].mean(), 4),
                        "drop": round(v1[metric].mean() - v2[metric].mean(), 4),
                        "n_v1": len(v1),
                        "n_v2": len(v2)
                    })
        return results

    def get_tasks(self, category: str = None, solver: str = None, version: str = None) -> List[Dict]:
        if self.scores is None:
            return []

        df = self.scores.copy()
        if category and self.labels:
            df["category"] = df["task_id"].map(self.labels)
            df = df[df["category"] == category]
        if solver:
            df = df[df["solver"] == solver]
        if version:
            df = df[df["version"] == version]

        return df.to_dict("records")
