import json
import re
import urllib.request
import urllib.error

import model_db
import patch_engine as pe

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "llama3.1:8b"

# Models offered as swap targets. Trim to speed up the prompt if you like;
# parameter tweaks work regardless of what's listed here.
CORE_CATEGORIES = ["Amp", "Preamp", "Cab", "Drive", "Comp", "Gate",
                   "EQ", "Wah", "Mod", "Delay", "Reverb", "Pitch"]


SYSTEM_PROMPT = r"""You are a guitar-tone engineer driving a Line 6 POD Go preset editor.

Your ONLY job is to output edit operations in an exact JSON format. You do not
write presets. You do not invent blocks. You edit the preset shown to you.

############  OUTPUT CONTRACT (read carefully)  ############
Return EXACTLY one JSON object, nothing else:

{"reply": "<one or two sentences for the user>", "edits": [ <ops> ]}

`edits` is a FLAT ARRAY of operation objects. Each op is exactly one of:

  {"op":"set_param",   "block":"<block id>", "param":"<param name>", "value":<number>}
  {"op":"set_enabled", "block":"<block id>", "value":true|false}
  {"op":"swap_model",  "block":"<block id>", "model_id":"<catalog id>"}
  {"op":"set_tempo",   "value":<bpm>}
  {"op":"rename",      "value":"<short name>"}

HARD RULES - breaking any of these makes the edit fail:
- `block` MUST be a block id copied verbatim from CURRENT PRESET (e.g. "block1",
  "cab0"). Never guess ids like "block7" if they aren't listed.
- For set_param, `param` MUST be a parameter name listed under that exact block
  in CURRENT PRESET, spelled identically. Do NOT invent parameters.
- For swap_model, `model_id` MUST be copied from the CATALOG.
  - Amp blocks must stay Amp, Cab blocks must stay Cab.
  - Every other effect slot (Drive, Comp, Wah, EQ, Mod, Delay, Reverb, Pitch)
    can be freely swapped to ANY effect category. Example: a Reverb slot can
    become Delay, a Mod slot can become Pitch, etc. Use this to get the effect
    the user asked for even if no block of that type exists yet.
- Use the numeric scale you see in the current values. If Bass is shown as 5.0,
  values run roughly 0-10. If a value is shown as 0.5, it runs 0-1. Match it.

############  CORRECT EXAMPLE  ############
CURRENT PRESET:
  block1 [Amp] "US Deluxe Nrml" (HD2_AmpUSDeluxeNrml) ON
      params: Gain=4.0, Bass=5.0, Mid=5.0, Treble=5.5, Presence=5.0, Master=6.0
  cab0 [Cab] "1x12 Blue Bell" (HD2_Cab1x12BlueBell) ON
      params: Level=0.0, LowCut=80.0, HiCut=8000.0
  block4 [Drive] "Scream 808" (HD2_DistScream808) BYPASSED
      params: Gain=5.0, Tone=5.0, Level=5.0
  block5 [Reverb] "Spring" (HD2_ReverbSpring) ON
      params: Mix=16.0, Decay=2.5
REQUEST: warmer and a bit dirty, with more space
CORRECT OUTPUT:
{"reply":"Rolled the treble back and lowered the cab high-cut for warmth, kicked in the overdrive lightly, and lifted the reverb for space.","edits":[
  {"op":"set_param","block":"block1","param":"Treble","value":4.0},
  {"op":"set_param","block":"cab0","param":"HiCut","value":6000.0},
  {"op":"set_enabled","block":"block4","value":true},
  {"op":"set_param","block":"block4","param":"Gain","value":3.5},
  {"op":"set_param","block":"block5","param":"Mix","value":26.0}
]}

############  NEVER DO THIS  ############
Do NOT output blocks-as-keys. This is WRONG and will be rejected:
  {"block1": {"HD2_SomeModel": {"Gain": 0.6, "Bass": 0.5}}}
Do NOT invent model ids or parameter names. Only use what appears in CURRENT
PRESET and CATALOG. Always wrap edits in the {"reply","edits"} object.

If the request is unclear, put a question in `reply` and return "edits": [].
Output the JSON object and nothing else - no markdown, no commentary.
"""


def _build_preamble(surface):
    """Dynamic build preamble that lists every effect slot by block ID,
    forcing the agent to make an explicit enable/bypass decision on each one."""
    amp_ids  = [b for b, i in surface.items() if i["category"] == "Amp"]
    cab_ids  = [b for b, i in surface.items() if i["category"] == "Cab"]
    fx_lines = []
    for bid, info in surface.items():
        if not info["enabled"] and info["category"] not in ("Unknown", "Utility"):
            fx_lines.append(
                f"     {bid} [effect slot, currently {info['category']}] \"{info['name']}\" — "
                f"swap_model to ANY effect type from CATALOG then set_enabled true, OR set_enabled false")

    amp_str = amp_ids[0] if amp_ids else "the amp block"
    cab_str = cab_ids[0] if cab_ids else "the cab block"
    fx_block = "\n".join(fx_lines) if fx_lines else "     (no available effect slots)"

    return (
        "TASK: Build a complete guitar tone from scratch. You MUST address every point:\n"
        f"  1. SWAP {amp_str} — choose the best amp from the CATALOG for this style\n"
        f"  2. SWAP or keep {cab_str} — update if a different cab suits the style\n"
        "  3. EFFECT BLOCKS — for EACH block below you MUST either:\n"
        "       (a) BYPASS it: output set_enabled false\n"
        "       (b) ENABLE it: output swap_model (pick from CATALOG) + set_enabled true + set all key params\n"
        "       DO NOT enable a block without also providing a swap_model for it.\n"
        f"{fx_block}\n"
        "  4. Set realistic, style-appropriate parameters on every block you enable\n"
        "\n"
        "REQUIRED: Every effect block above needs a set_enabled edit. "
        "Every enabled block must also have a swap_model.\n"
        "Be comprehensive. This is a full build, not a tweak.\n\n"
    )


def build_messages(patch, user_message, history=None, build_mode=False):
    surface = pe.editable_surface(patch)
    surf_lines = []
    for block_id, info in surface.items():
        params = ", ".join(f"{k}={v}" for k, v in info["params"].items()) or "(no editable params)"
        state = "ON" if info["enabled"] else "BYPASSED"
        surf_lines.append(
            f'{block_id} [{info["category"]}] "{info["name"]}" ({info["model_id"]}) {state}\n'
            f'    params: {params}')
    summary = pe.summarize(patch)

    id_list = ", ".join(surface.keys())
    current = (
        f'PRESET NAME: {summary["name"]}\n'
        f'TEMPO: {summary["tempo"]}\n'
        f'VALID BLOCK IDS (use only these): {id_list}\n'
        f'SIGNAL CHAIN (in order):\n' + "\n".join(surf_lines)
    )
    catalog = model_db.compact_catalog(CORE_CATEGORIES)

    sys = SYSTEM_PROMPT + "\n\n############  CATALOG (allowed swap_model ids)  ############\n" + catalog
    msgs = [{"role": "system", "content": sys}]
    for turn in (history or []):
        msgs.append(turn)
    task_label = "=== TONE REQUEST ===" if build_mode else "=== REQUEST ==="
    preamble = _build_preamble(surface) if build_mode else ""
    msgs.append({
        "role": "user",
        "content": (f"{preamble}=== CURRENT PRESET ===\n{current}\n\n{task_label}\n{user_message}\n\n"
                    f"Respond with the JSON object only.")
    })
    return msgs


def _edits_schema():
    """A JSON Schema Ollama enforces on the model's output. With this, the model
    physically cannot emit a freelance shape — every response is
    {"reply": str, "edits": [ <op objects> ]} with only the allowed op fields."""
    op = {
        "type": "object",
        "properties": {
            "op": {"type": "string",
                   "enum": ["set_param", "set_enabled", "swap_model",
                            "set_tempo", "rename"]},
            "block": {"type": "string"},
            "param": {"type": "string"},
            "model_id": {"type": "string"},
            "value": {"type": ["number", "boolean", "string"]},
        },
        "required": ["op"],
    }
    return {
        "type": "object",
        "properties": {
            "reply": {"type": "string"},
            "edits": {"type": "array", "items": op},
        },
        "required": ["reply", "edits"],
    }


def call_ollama(messages, model=DEFAULT_MODEL, url=OLLAMA_URL, timeout=600):
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.2, "num_ctx": 8192},
        # Hard schema constraint — far stronger than "format": "json".
        "format": _edits_schema(),
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body.get("message", {}).get("content", "")
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Couldn't reach Ollama at {url}. Is it running? Start the Ollama app "
            f"(or `ollama serve`) and pull the model (`ollama pull {model}`). "
            f"Details: {e}")


def _extract_json(text):
    """Pull the first JSON object/array out of text, tolerating fences/prose."""
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*([\[{].*?[\]}])\s*```", text, re.DOTALL)
    if fence:
        chunk = fence.group(1)
    else:
        starts = [i for i, c in enumerate(text) if c in "{["]
        chunk = None
        for start in starts:
            opener = text[start]
            closer = "}" if opener == "{" else "]"
            depth = 0
            for i in range(start, len(text)):
                if text[i] == opener:
                    depth += 1
                elif text[i] == closer:
                    depth -= 1
                    if depth == 0:
                        chunk = text[start:i + 1]
                        break
            if chunk:
                break
    if not chunk:
        return None
    try:
        return json.loads(chunk)
    except json.JSONDecodeError:
        return None


def coerce_to_edits(obj, surface):
    """Salvage common non-conforming shapes into edit ops.

    Handles proper {"reply","edits":[...]}, a single op, a bare list of ops, and
    freelance {block: {model_id: {param:val}}} / {block: {param:val}}. Only emits
    ops whose block/param actually exist, so junk self-filters."""
    if isinstance(obj, dict) and isinstance(obj.get("edits"), list):
        return obj["edits"]
    if isinstance(obj, dict) and "op" in obj:
        return [obj]
    if isinstance(obj, list):
        return [e for e in obj if isinstance(e, dict) and "op" in e]

    edits = []
    if isinstance(obj, dict):
        for block_id, val in obj.items():
            if block_id in ("reply", "edits") or not isinstance(val, dict):
                continue
            if block_id not in surface:
                continue
            inner = val
            # Shape A: {"type"|"effect"|"model_id": "<id>", "params": {...}}
            if "params" in val and isinstance(val["params"], dict):
                mid = (val.get("type") or val.get("effect")
                       or val.get("model_id") or val.get("@model"))
                if isinstance(mid, str) and re.search(r"_|HD2|HDV|VIC|L6|P34", mid):
                    edits.append({"op": "swap_model", "block": block_id, "model_id": mid})
                inner = val["params"]
            # Shape B: {"<model_id>": {...}}
            elif len(val) == 1:
                only_key, only_val = next(iter(val.items()))
                if isinstance(only_val, dict) and re.search(r"_|HD2|HDV|VIC|L6|P34", only_key):
                    edits.append({"op": "swap_model", "block": block_id, "model_id": only_key})
                    inner = only_val
            allowed = surface[block_id]["params"]
            for pname, pval in inner.items():
                if pname in allowed and isinstance(pval, (int, float, bool)):
                    edits.append({"op": "set_param", "block": block_id,
                                  "param": pname, "value": pval})
    return edits


def parse_model_output(text, surface=None):
    """Return (reply, edits). Uses repair when the shape is off."""
    obj = _extract_json(text)
    if obj is None:
        return (text.strip() if text else "(no response)", [])
    reply = ""
    if isinstance(obj, dict):
        reply = (obj.get("reply") or "").strip()
    edits = coerce_to_edits(obj, surface or {})
    if not reply:
        reply = "Applied your changes." if edits else "(no changes - try a more specific instruction)"
    return (reply, edits)


def _generate_preset_name(user_message, model=DEFAULT_MODEL, url=OLLAMA_URL):
    """Ask the model for a short preset name based on the build description."""
    msgs = [
        {"role": "system", "content":
            "You name guitar presets. Reply with ONLY 1-4 words, no punctuation, no quotes. "
            "Examples: Classic Crunch, Warm Jazz Clean, Metal Mayhem, Chimey Blues"},
        {"role": "user", "content":
            f"Name a guitar preset for this tone: {user_message}"}
    ]
    schema = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
    payload = {"model": model, "messages": msgs, "stream": False,
               "options": {"temperature": 0.7, "num_ctx": 512}, "format": schema}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        raw = body.get("message", {}).get("content", "")
        obj = json.loads(raw) if raw else {}
        name = obj.get("name", "").strip()[:32]
        return name if name else None
    except Exception:
        return None


def run_turn(patch, user_message, history=None, model=DEFAULT_MODEL, url=OLLAMA_URL, build_mode=False):
    surface = pe.editable_surface(patch)
    messages = build_messages(patch, user_message, history, build_mode=build_mode)
    raw = call_ollama(messages, model=model, url=url)
    # Uncomment to debug exactly what the model returned:
    # print("\n=== RAW MODEL OUTPUT ===\n", raw, "\n=======================\n")
    reply, edits = parse_model_output(raw, surface)

    if not edits:
        return {"reply": reply, "applied": [], "rejected": [], "patch": patch, "raw": raw}

    new_patch, results = pe.apply_edits(patch, edits)
    applied = [r["detail"] for r in results if r["ok"]]
    rejected = [r["detail"] for r in results if not r["ok"]]
    out_patch = new_patch if applied else patch

    if build_mode and applied:
        name = _generate_preset_name(user_message, model=model, url=url)
        if name:
            out_patch, name_results = pe.apply_edits(out_patch, [{"op": "rename", "value": name}])
            applied += [r["detail"] for r in name_results if r["ok"]]
    return {"reply": reply, "applied": applied, "rejected": rejected,
            "patch": out_patch, "raw": raw}