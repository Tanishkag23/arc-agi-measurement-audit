#!/usr/bin/env python3
"""
Prepare data folder for local Mac development.
Place your downloaded files in downloads/ then run this.
"""

import shutil
import os

os.makedirs('backend/data/cache', exist_ok=True)

# Move files from downloads to backend/data
files = {
    'downloads/arc_cache_compact.json': 'backend/data/cache/cache_compact.json',
    'downloads/all_scores.csv': 'backend/data/all_scores.csv',
    'downloads/labels.json': 'backend/data/labels.json',
}

for src, dst in files.items():
    if os.path.exists(src):
        shutil.copy(src, dst)
        print(f"✅ {src} → {dst}")
    else:
        print(f"⚠️  Missing: {src}")

print("\n🚀 Ready to run: python backend/main.py")
