import json
import copy
import model_db


# ─── Load / Save ─────────────────────────────────────────────────

def load_patch(raw_bytes):
    """Parse .pgp bytes into a dict. Tolerates a UTF-8 BOM."""
    text = raw_bytes.decode("utf-8-sig") if isinstance(raw_bytes, (bytes, bytearray)) else raw_bytes
    patch = json.loads(text)
    if "data" not in patch or "tone" not in patch.get("data", {}):
        raise ValueError(
            "This doesn't look like a POD Go/HX preset — expected a top-level "
            "'data' object containing a 'tone'. If you exported a setlist (.pgs) "
            "rather than a single preset (.pgp), export one preset instead."
        )
    return patch


def save_patch(patch):
    """Serialize a patch dict back to bytes. POD Go Edit reads standard JSON."""
    return json.dumps(patch, indent=2).encode("utf-8")


# ─── Build canvas ────────────────────────────────────────────────

# Bypassed defaults that fill empty block slots in build mode, giving the agent
# a full palette of effect categories to enable and configure.
_BUILD_SLOT_DEFAULTS = {
    "block2": {
        "@model": "HD2_DistScream808", "@enabled": False,
        "@position": 2, "@path": 0,
        "Gain": 0.5, "Bass": 0.5, "Treble": 0.5, "Level": 0.5,
    },
    "block3": {
        "@model": "HD2_CompressorRedSqueeze", "@enabled": False,
        "@position": 3, "@path": 0,
        "Sustain": 0.5, "Level": 0.5, "Attack": 0.5,
    },
    "block8": {
        "@model": "HD2_DelaySimpleDelay", "@enabled": False,
        "@position": 8, "@path": 0,
        "Time": 0.35, "Feedback": 0.3, "Mix": 0.25,
    },
    "block9": {
        "@model": "HD2_ReverbHall", "@enabled": False,
        "@position": 9, "@path": 0,
        "Decay": 0.5, "Mix": 0.2, "Predelay": 0.0,
    },
}


_BUILD_SYNTHETIC_MODELS = frozenset(d["@model"] for d in _BUILD_SLOT_DEFAULTS.values())


def prepare_build_canvas(patch):
    """Fill empty block slots with bypassed defaults so build mode has a full
    palette — amp, cab, drive, comp, delay, reverb — for the agent to configure.
    Only fills slots that already exist as empty placeholders in the DSP; does
    not create new blocks in secondary (parallel-path) DSPs like dsp1."""
    p = copy.deepcopy(patch)
    tone = _tone(p)
    for dsp_name in _dsp_names(p):
        dsp = tone.get(dsp_name, {})
        for slot, defaults in _BUILD_SLOT_DEFAULTS.items():
            if slot in dsp and "@model" not in dsp[slot]:
                dsp[slot] = dict(defaults)
    return p


_TONE_CATEGORIES = frozenset({"Amp", "Cab", "Drive", "Comp", "EQ", "Delay",
                               "Reverb", "Mod", "Pitch", "Wah", "Preamp"})

def finalize_build_patch(patch):
    """Before download from build mode: keep only what the agent actively
    enabled with a real model choice.

    Strips:
      - Every bypassed block (agent chose not to use it)
      - Enabled blocks outside tone categories (VolPan / FX Loop template junk)
      - Enabled build-canvas placeholder blocks whose synthetic model ID was
        never swapped by the agent

    Keeps everything else — including agent-swapped models not in our catalog.
    Never strip an amp/cab/effect just because our catalog doesn't know its name.
    """
    p = copy.deepcopy(patch)
    tone = _tone(p)
    for dsp_name in _dsp_names(p):
        dsp = tone.get(dsp_name, {})
        for key, block in list(dsp.items()):
            if not isinstance(block, dict) or "@model" not in block:
                continue
            model = block.get("@model", "")
            if "AppDSP" in model or "DSPFlow" in model:
                continue
            if key.lower() in ("input", "output", "input0", "output0",
                               "split", "join", "splita", "splitb"):
                continue
            cat, _name, _ = model_db.lookup(model)
            # Always keep structural utility blocks (VolPan, FX Loop) — the
            # POD Go requires them in the signal chain regardless of tone.
            if cat == "Utility":
                continue
            # Strip every bypassed block — agent chose not to use it
            if not block.get("@enabled", True):
                dsp[key] = {"@position": block.get("@position", 0)}
                continue
            # Strip any other enabled non-tone blocks
            if cat not in _TONE_CATEGORIES:
                dsp[key] = {"@position": block.get("@position", 0)}
                continue
            # Strip enabled build-canvas placeholders the agent never swapped
            if model in _BUILD_SYNTHETIC_MODELS:
                dsp[key] = {"@position": block.get("@position", 0)}
                continue
            # Strip any enabled block whose model ID isn't in the catalog.
            # With swap_model now rejecting non-catalog IDs, this only hits
            # template blocks with broken inferred IDs (wah, EQ etc.) that
            # the agent enabled without successfully swapping to a real model.
            if _name == model:
                dsp[key] = {"@position": block.get("@position", 0)}
    return p


# ─── Introspection ───────────────────────────────────────────────

META_KEYS_HIDDEN = {"@model", "@position", "@path", "@type", "@stereo",
                    "@cab", "@enabled", "@valid", "@name"}


def _patch_name(patch):
    return patch.get("data", {}).get("meta", {}).get("name", "Untitled")


def _tone(patch):
    return patch.get("data", {}).get("tone", {})


def _dsp_names(patch):
    """POD Go uses dsp0; full Helix presets may also carry dsp1."""
    tone = _tone(patch)
    return [d for d in ("dsp0", "dsp1") if isinstance(tone.get(d), dict)]


def _round_param(v):
    """Round float params to 4 sig-figs so the LLM sees clean numbers."""
    if isinstance(v, float):
        # 4 significant figures keeps precision while eliminating 32-bit noise
        from math import log10, floor
        if v == 0.0:
            return 0.0
        mag = floor(log10(abs(v)))
        factor = 10 ** (4 - 1 - mag)
        return round(v * factor) / factor
    return v


def _block_params(block):
    """Editable parameters of a block: non-'@' keys with scalar values."""
    params = {}
    for k, v in block.items():
        if k.startswith("@"):
            continue
        if isinstance(v, (int, float, bool, str)):
            params[k] = _round_param(v)
    return params


def iter_blocks(patch):
    """Yield (dsp_name, block_key, block_dict) for every real model block,
    skipping DSP routing/input/output infrastructure, in signal-chain order."""
    tone = _tone(patch)
    for dsp_name in _dsp_names(patch):
        dsp = tone.get(dsp_name, {})
        items = []
        for key, val in dsp.items():
            if not isinstance(val, dict) or "@model" not in val:
                continue
            model = str(val.get("@model", ""))
            # Skip routing/input/output infrastructure across all prefixes
            # (HD2_AppDSP..., P34_AppDSPFlow..., etc.) and by block-key name.
            if "AppDSP" in model or "DSPFlow" in model:
                continue
            if key.lower() in ("input", "output", "input0", "output0",
                               "split", "join", "splita", "splitb"):
                continue
            items.append((val.get("@position", 99), val.get("@path", 0), key, val))
        items.sort(key=lambda t: (t[1], t[0]))
        for _pos, _path, key, val in items:
            yield dsp_name, key, val


def summarize(patch):
    """A structured, human- and LLM-readable view of the preset."""
    tone = _tone(patch)
    glob = tone.get("global", {})
    blocks = []
    for dsp_name, key, block in iter_blocks(patch):
        cat, name, real = model_db.lookup(block.get("@model", ""))
        blocks.append({
            "dsp": dsp_name,
            "block": key,
            "model_id": block.get("@model", ""),
            "category": cat,
            "name": name,
            "based_on": real,
            "enabled": bool(block.get("@enabled", True)),
            "position": block.get("@position", None),
            "params": _block_params(block),
        })
    snapshots = []
    for i in range(8):
        snap = tone.get(f"snapshot{i}", {})
        if isinstance(snap, dict) and snap.get("@valid", False):
            snapshots.append(snap.get("@name", f"Snapshot {i}"))
    return {
        "name": _patch_name(patch),
        "tempo": glob.get("@tempo", None),
        "snapshots": snapshots,
        "blocks": blocks,
    }


def chain_text(patch):
    """One-line-per-block signal chain for display / prompting."""
    lines = []
    for b in summarize(patch)["blocks"]:
        flag = "" if b["enabled"] else "  (bypassed)"
        real = f"  ≈ {b['based_on']}" if b["based_on"] else ""
        lines.append(f"[{b['category']}] {b['name']}{real}{flag}")
    return "\n".join(lines) if lines else "(empty signal chain)"


def editable_surface(patch):
    """What the agent is allowed to touch, addressed the way edits name it:
    block id -> {model_id, category, name, enabled, params{name:value}}."""
    surface = {}
    for dsp_name, key, block in iter_blocks(patch):
        cat, name, real = model_db.lookup(block.get("@model", ""))
        surface[key] = {
            "dsp": dsp_name,
            "model_id": block.get("@model", ""),
            "category": cat,
            "name": name,
            "enabled": bool(block.get("@enabled", True)),
            "params": _block_params(block),
        }
    return surface


# ─── Editing ─────────────────────────────────────────────────────

def _find_block_dsp(patch, block_key):
    """Like _find_block but also returns the dsp name, needed for snapshot cascade."""
    tone = _tone(patch)
    for dsp_name in _dsp_names(patch):
        dsp = tone.get(dsp_name, {})
        if block_key in dsp and isinstance(dsp[block_key], dict):
            return dsp_name, dsp[block_key]
    return None, None


def _cascade_param(tone, dsp_name, block_key, param, old_value, new_value):
    """Sync a param change into snapshots that were in sync with the old base value.
    Snapshots with intentionally different values are left untouched."""
    for i in range(8):
        snap = tone.get(f"snapshot{i}")
        if not isinstance(snap, dict) or not snap.get("@valid"):
            continue
        ctrl = snap.get("controllers", {}).get(dsp_name, {})
        if block_key in ctrl and param in ctrl[block_key]:
            if ctrl[block_key][param].get("@value") == old_value:
                ctrl[block_key][param]["@value"] = new_value


def _cascade_enabled(tone, dsp_name, block_key, old_enabled, new_enabled):
    """Sync a bypass-state change into snapshots that matched the old base state.
    Snapshots with intentionally different bypass states are left untouched."""
    for i in range(8):
        snap = tone.get(f"snapshot{i}")
        if not isinstance(snap, dict) or not snap.get("@valid"):
            continue
        blocks = snap.get("blocks", {}).get(dsp_name, {})
        if block_key in blocks and blocks[block_key] == old_enabled:
            blocks[block_key] = new_enabled


def _coerce(old_value, new_value):
    """Coerce new_value to the type of the existing parameter value."""
    if isinstance(old_value, bool):
        if isinstance(new_value, str):
            return new_value.strip().lower() in ("1", "true", "on", "yes")
        return bool(new_value)
    if isinstance(old_value, int) and not isinstance(old_value, bool):
        try:
            return int(round(float(new_value)))
        except (TypeError, ValueError):
            raise ValueError(f"expected a number, got {new_value!r}")
    if isinstance(old_value, float):
        try:
            return float(new_value)
        except (TypeError, ValueError):
            raise ValueError(f"expected a number, got {new_value!r}")
    return new_value  # string params pass through


def apply_edits(patch, edits):
    """Apply a list of edit ops to a *copy* of the patch.

    Supported ops (each a dict with an "op" field):
      {"op":"set_param",   "block":"block0", "param":"Bass", "value":4.0}
      {"op":"set_enabled", "block":"block3", "value":false}
      {"op":"swap_model",  "block":"block0", "model_id":"HD2_AmpBrit2204"}
      {"op":"set_tempo",   "value":120.0}
      {"op":"rename",      "value":"Warm Cleans"}

    Returns (new_patch, results) where results is a list of
    {"ok":bool, "edit":..., "detail":str}. Unknown/invalid ops are rejected
    individually; valid ones still apply.
    """
    p = copy.deepcopy(patch)
    results = []

    for edit in edits:
        op = (edit or {}).get("op")
        try:
            if op == "set_tempo":
                glob = _tone(p).setdefault("global", {})
                old = glob.get("@tempo")
                glob["@tempo"] = float(edit["value"])
                results.append(_ok(edit, f"tempo {old} → {glob['@tempo']}"))

            elif op == "rename":
                meta = p.setdefault("data", {}).setdefault("meta", {})
                old = meta.get("name", "")
                name = str(edit["value"])[:32]   # POD Go preset names are short
                meta["name"] = name
                results.append(_ok(edit, f"name '{old}' → '{name}'"))

            elif op in ("set_param", "set_enabled", "swap_model"):
                block_key = edit.get("block", "")
                dsp_name, block = _find_block_dsp(p, block_key)
                if block is None:
                    results.append(_fail(edit, f"no block '{block_key}'"))
                    continue

                if op == "set_enabled":
                    old = bool(block.get("@enabled", True))
                    block["@enabled"] = bool(edit["value"])
                    _cascade_enabled(_tone(p), dsp_name, block_key, old, block["@enabled"])
                    results.append(_ok(edit, f"{block_key} enabled {old} → {block['@enabled']}"))

                elif op == "swap_model":
                    new_id = str(edit.get("model_id", ""))
                    cat_old, name_old, _ = model_db.lookup(block.get("@model", ""))
                    cat_new, name_new, based_on = model_db.lookup(new_id)
                    fallback_note = ""
                    # If the model ID isn't in the catalog the agent hallucinated
                    # it. Try to find the closest real catalog model in the same
                    # category (semantic search first, then first-in-category)
                    # so the effect still ends up in the chain.
                    if name_new == new_id:
                        import re as _re
                        # Split camelCase so "AmpMarshallJCM800" → "Amp Marshall JCM800"
                        # before semantic search — model IDs won't tokenize otherwise.
                        _split = _re.sub(r'([a-z])([A-Z])', r'\1 \2', new_id)
                        sem = model_db.find_model(_split)
                        sem_cat = model_db.lookup(sem)[0] if sem else "Unknown"
                        if sem and sem_cat == cat_new:
                            fallback_id = sem
                        else:
                            candidates = model_db.models_in_category(cat_new)
                            fallback_id = candidates[0] if candidates else None
                        if fallback_id:
                            cat_new, fallback_name, based_on = model_db.lookup(fallback_id)
                            fallback_note = (
                                f" ['{new_id}' not in catalog; "
                                f"used '{fallback_name}' as nearest {cat_new} match]")
                            new_id = fallback_id
                            name_new = fallback_name
                        else:
                            results.append(_fail(
                                edit,
                                f"'{new_id}' not in catalog and no {cat_new} fallback "
                                f"available — copy a model_id from the CATALOG list."))
                            continue
                    # Amp and Cab slots are fixed — don't let them swap to
                    # another category. Effect slots (Drive, Mod, Delay …) are
                    # flexible; any effect type can live in any effect slot.
                    _FIXED_CATS = {"Amp", "Cab", "Preamp"}
                    if (cat_old in _FIXED_CATS and cat_new not in _FIXED_CATS
                            and cat_new != "Unknown"):
                        results.append(_fail(
                            edit,
                            f"won't replace a {cat_old} block with a {cat_new} model "
                            f"({name_new}) — use a {cat_old} model instead"))
                        continue
                    block["@model"] = new_id
                    # When swapping to a different effect category, clear the
                    # old params — they belong to the previous model type and
                    # would corrupt the block on the device. Same-category swaps
                    # keep params (same knobs, different character).
                    cross_category = (cat_new != cat_old and cat_old not in ("Unknown",)
                                       and cat_new not in ("Unknown",))
                    params_note = ""
                    if cross_category:
                        for pk in list(block.keys()):
                            if not pk.startswith("@"):
                                del block[pk]
                        # Paste in real, known-good params harvested from the
                        # user's own presets (build_catalog.py) if we have them
                        # for this exact model, instead of leaving it empty for
                        # the agent to guess param names from scratch.
                        learned = model_db.learned_params(new_id)
                        if learned:
                            block.update(learned)
                            params_note = " Params filled in from your learned catalog."
                        else:
                            params_note = " Params cleared — set new ones for this effect type."
                    results.append(_ok(
                        edit,
                        f"{block_key} model {name_old} → {name_new}."
                        f"{fallback_note}{params_note}"))

                else:  # set_param
                    param = edit["param"]
                    if param.startswith("@"):
                        results.append(_fail(edit, f"'{param}' is a reserved field; use set_enabled instead"))
                        continue
                    if param not in block:
                        # Allow creating params on blocks that were just cross-category
                        # swapped (old params cleared, new ones not yet populated).
                        val = edit["value"]
                        if not isinstance(val, (int, float, bool)):
                            results.append(_fail(edit, f"'{param}' doesn't exist on {block_key} and value must be numeric to create it"))
                            continue
                        block[param] = float(val) if isinstance(val, (int, float)) else val
                        results.append(_ok(edit, f"{block_key}.{param} (new) → {block[param]}"))
                        continue
                    old = block[param]
                    block[param] = _coerce(old, edit["value"])
                    _cascade_param(_tone(p), dsp_name, block_key, param, old, block[param])
                    results.append(_ok(edit, f"{block_key}.{param} {old} → {block[param]}"))
            else:
                results.append(_fail(edit, f"unknown op '{op}'"))
        except (KeyError, ValueError, TypeError) as e:
            results.append(_fail(edit, str(e)))

    return p, results


def _ok(edit, detail):
    return {"ok": True, "edit": edit, "detail": detail}


def _fail(edit, detail):
    return {"ok": False, "edit": edit, "detail": detail}