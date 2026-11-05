#!/usr/bin/env python3
"""
Extract NVIDIA predictions into compact cache for the ARC Audit Dashboard.
Run this on your NVIDIA Jupyter server before it expires.

Usage:
    python extract_nvidia_cache.py
    # Then download arc_cache_compact.json from /workspace/
"""

import json
import glob
import os
import shutil

def extract_cache():
    files = glob.glob('/root/arc_audit/outputs/*.json')
    print(f"Found {len(files)} prediction files")

    cache = {}
    for f in files:
        try:
            with open(f) as fp:
                d = json.load(fp)

            fname = os.path.basename(f)[:-5]  # remove .json
            parts = fname.split('_')
            task_id = parts[-1]
            version = parts[-2]
            solver = '_'.join(parts[:-2])

            key = f"{solver}_{version}_{task_id}"
            cache[key] = {
                "task_id": task_id,
                "version": version,
                "solver": solver,
                "pred": d.get('pred', []),
                "gt": d.get('gt', [])
            }
        except Exception as e:
            pass

    output_path = '/workspace/arc_cache_compact.json'
    with open(output_path, 'w') as f:
        json.dump(cache, f)

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"✅ Extracted {len(cache)} predictions to {output_path}")
    print(f"📦 File size: {size_mb:.2f} MB")
    print("\n👉 Download this file from Jupyter sidebar and place it in backend/data/cache/")

def copy_scores_and_labels():
    """Also copy all_scores.csv and labels if they exist"""
    src_scores = '/root/arc_audit/results/all_scores.csv'
    src_labels = '/workspace/final_60task_groundtruth.json'

    if os.path.exists(src_scores):
        shutil.copy(src_scores, '/workspace/all_scores.csv')
        print(f"✅ Copied all_scores.csv ({os.path.getsize(src_scores)/1024:.1f} KB)")

    if os.path.exists(src_labels):
        shutil.copy(src_labels, '/workspace/labels.json')
        print(f"✅ Copied labels.json ({os.path.getsize(src_labels)/1024:.1f} KB)")

if __name__ == "__main__":
    extract_cache()
    copy_scores_and_labels()
    print("\n🎯 All files ready in /workspace/ for download!")
