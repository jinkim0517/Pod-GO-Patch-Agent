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


def learn_from_patch(patch):
    """Merge one already-loaded preset's real blocks into the persistent
    learned-blocks library (learned_blocks.json), on top of whatever's already
    there. Unlike scan(), this never discards previously learned models — each
    upload only adds to or refreshes the store. Returns how many models were
    newly learned (not just refreshed)."""
    library = dict(model_db.LEARNED_BLOCKS)
    added = 0
    changed = False
    for _dsp, _key, block in pe.iter_blocks(patch):
        mid = block.get("@model", "")
        if not mid:
            continue
        entry = {k: v for k, v in block.items() if k not in ("@position", "@path")}
        if mid not in library:
            added += 1
            changed = True
        elif library[mid] != entry:
            changed = True
        library[mid] = entry
    if changed:
        model_db.save_learned_blocks(library)
    return added


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python build_catalog.py /path/to/folder/of/pgp")
        sys.exit(1)
    scan(sys.argv[1])
