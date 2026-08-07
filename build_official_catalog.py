import json
import os
import sys

DEFAULT_RESOURCES_DIR = "/Applications/Line6/POD Go Edit.app/Contents/Resources"
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "official_catalog.json")

# .models filename -> our category taxonomy (matches model_db.py's categories).
# The numeric "category" field inside each model entry is the device's own
# internal UI grouping (inconsistent across files) - the filename is the
# reliable signal, so we use that instead.
FILE_CATEGORY = {
    "amp.models": "Amp",
    "preamp.models": "Preamp",
    "cab.models": "Cab",
    "cabmicirs.models": "Cab",
    "distortion.models": "Drive",
    "compressor.models": "Comp",
    "gate.models": "Gate",
    "eq.models": "EQ",
    "filter.models": "Filter",
    "wah.models": "Wah",
    "modulation.models": "Mod",
    "delay.models": "Delay",
    "reverb.models": "Reverb",
    "volumepan.models": "Utility",
    "sendreturn.models": "Utility",
    "io.models": "Routing",
    # pitch-synth.models is split per-model below (Pitch vs Synth).
}

# valueType -> a simple kind label. 0=int/enum, 1=float, 2=bool, 3=string.
VALUE_TYPE_KIND = {0: "int", 1: "float", 2: "bool", 3: "string"}

_SYNTH_HINTS = ("Synth", "Buzz", "Rez", "Seismic", "Ring", "Octi", "Growler")


def _pitch_or_synth(symbolic_id, name):
    text = f"{symbolic_id} {name}"
    return "Synth" if any(h in text for h in _SYNTH_HINTS) else "Pitch"


def _model_category(filename, entry):
    if filename == "pitch-synth.models":
        return _pitch_or_synth(entry.get("symbolicID", ""), entry.get("name", ""))
    return FILE_CATEGORY[filename]


def _parse_params(entry):
    params = {}
    for p in entry.get("params", []):
        pid = p.get("symbolicID", "")
        if not pid or pid.startswith("@"):
            continue  # meta fields (mic select, cursor state, ...), not real knobs
        params[pid] = {
            "name": p.get("name", pid),
            "min": p.get("min"),
            "max": p.get("max"),
            "default": p.get("default"),
            "kind": VALUE_TYPE_KIND.get(p.get("valueType"), "float"),
        }
    return params


def build(resources_dir):
    catalog = {}
    skipped = []
    for filename, category in list(FILE_CATEGORY.items()) + [("pitch-synth.models", None)]:
        path = os.path.join(resources_dir, filename)
        if not os.path.isfile(path):
            skipped.append(filename)
            continue
        with open(path) as f:
            entries = json.load(f)
        for entry in entries:
            model_id = entry.get("symbolicID", "")
            # fixed.models carries one non-model entry ("@global_params") for
            # tempo/snapshot state, not a swappable block - skip it.
            if not model_id or model_id.startswith("@"):
                continue
            catalog[model_id] = {
                "category": _model_category(filename, entry),
                "name": entry.get("name", model_id),
                "params": _parse_params(entry),
            }
    return catalog, skipped


def main():
    resources_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_RESOURCES_DIR
    if not os.path.isdir(resources_dir):
        print(f"Resources folder not found: {resources_dir}")
        print("Pass the POD Go Edit app's Contents/Resources folder as an argument, e.g.:")
        print('  python3 build_official_catalog.py "/Applications/Line6/POD Go Edit.app/Contents/Resources"')
        sys.exit(1)

    catalog, skipped = build(resources_dir)
    with open(OUT_PATH, "w") as f:
        json.dump(catalog, f, indent=2)

    by_cat = {}
    for info in catalog.values():
        by_cat[info["category"]] = by_cat.get(info["category"], 0) + 1
    print(f"Wrote {OUT_PATH} ({len(catalog)} models)")
    for cat in sorted(by_cat):
        print(f"  {cat:10s} {by_cat[cat]}")
    if skipped:
        print(f"Skipped (not found in {resources_dir}): {', '.join(skipped)}")


if __name__ == "__main__":
    main()
