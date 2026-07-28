import json
import os
import sys
from collections import defaultdict

import patch_engine as pe
import model_db


def scan(folder):
    models = defaultdict(lambda: {"count": 0, "params": defaultdict(set)})
    library = {}        # model_id -> a representative real block dict
    files = [f for f in os.listdir(folder) if f.lower().endswith((".pgp", ".json"))]
    if not files:
        print(f"No .pgp files in {folder}")
        return
    for fn in sorted(files):
        try:
            patch = pe.load_patch(open(os.path.join(folder, fn), "rb").read())
        except Exception as e:
            print(f"  skip {fn}: {e}")
            continue
        for _dsp, _key, block in pe.iter_blocks(patch):
            mid = block.get("@model", "")
            rec = models[mid]
            rec["count"] += 1
            for k, v in block.items():
                if not k.startswith("@") and isinstance(v, (int, float, bool, str)):
                    rec["params"][k].add(type(v).__name__)
            library.setdefault(mid, {k: v for k, v in block.items()
                                     if k not in ("@position", "@path")})

    print(f"\nScanned {len(files)} file(s). Found {len(models)} distinct models:\n")
    for mid, rec in sorted(models.items(), key=lambda kv: -kv[1]["count"]):
        cat, name, real = model_db.lookup(mid)
        known = "" if mid in model_db.MODEL_DB else "  *NEW (not in catalog)*"
        print(f"  {rec['count']:3d}×  [{cat:7s}] {name:22s} {mid}{known}")
        print(f"         params: {', '.join(sorted(rec['params']))}")

    with open("learned_blocks.json", "w") as f:
        json.dump(library, f, indent=2)
    print(f"\nWrote learned_blocks.json ({len(library)} block templates).")
    print("The agent will use these as known-good definitions for model swaps.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python build_catalog.py /path/to/folder/of/pgp")
        sys.exit(1)
    scan(sys.argv[1])
