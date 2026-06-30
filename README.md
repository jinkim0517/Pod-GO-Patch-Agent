# POD Go Patch Agent

A local, chat-driven tone engineer for the **Line 6 POD Go**. Describe a sound
in plain English — *“warm blackface clean with a little spring,”* *“too muddy,
tighten the low end,”* *“more gain and ambience”* — and it edits a preset and
hands you a `.pgp` you import in POD Go Edit. You stay in the loop: react to what
you hear (*“more space,”* *“less fizz”*) and it makes targeted moves, one round
at a time.

**Runs entirely on your machine.** A local model served by [Ollama] does the
reasoning. No API keys, no tokens, no cloud, nothing leaves your computer.

[Ollama]: https://ollama.com

---

## How it works

```
 you ───▶ browser chat UI ───▶ local server (FastAPI) ───▶ local model (Ollama)
                                      │
                                      ▼
                           patch engine: validates the
                           model's proposed edits against
                           the REAL preset, applies them,
                           writes a downloadable .pgp
```

The model never writes a preset directly. It only proposes **edit operations**
(*set this parameter, bypass that block, swap this amp*). The patch engine is the
guardrail: it applies edits to your actual file and **rejects anything that
doesn’t fit** — a wrong parameter name, an out-of-type value, an amp-for-reverb
swap. So even a small local model can’t corrupt a patch; the worst case is an
edit that gets rejected and reported back to you.

Parameter tweaks and bypass toggles are **always exact**, because they only touch
keys that already exist in your file.

---

## Setup

**1. Install Ollama and pull a model**

```bash
# install from https://ollama.com, then:
ollama pull llama3.1:8b      # solid default
# alternatives that work well: qwen2.5:7b-instruct, mistral-nemo
ollama serve                 # if it isn't already running
```

**2. Install and run this app**

```bash
pip install -r requirements.txt
python server.py
```

Open **http://localhost:8000**. You can change the model name (top-right) to any
model you’ve pulled.

> A model with an **8k+ context window** is recommended — the amp/cab/effects
> catalog is sizeable. The server already requests `num_ctx: 8192` from Ollama.

---

## Using it

- The app opens on a **clean template** (a Fender-style amp into a spring reverb)
  with a tube screamer, EQ, and delay sitting bypassed, ready to switch on.
- **Create from scratch:** describe the tone. It sets the amp/cab and key
  parameters and enables the blocks it needs.
- **Work from your own:** click **Upload .pgp** and load a preset exported from
  POD Go Edit, then describe changes.
- Watch the **signal chain** on the right update live. Each turn lists exactly
  what changed (✓) and anything it declined (⊘).
- Hit **Download .pgp** whenever you like it, then import in POD Go Edit.

The loop is human-paced by design: there’s no way to push a tone to the unit and
hear it instantly, so you audition each download yourself. Make each round count.

---

## Two honest caveats

**1. The bundled template is structurally correct but inferred.** It’s built to
match the POD Go/HX preset shape and round-trips cleanly, but it was not exported
from a real unit. For a guaranteed-loadable starting point, export a **“New
Preset”** from POD Go Edit, save it over `template_newpreset.pgp`, and you’re on
rails. Better yet, just **upload your own presets** — editing a real file is
always faithful, because the app preserves your exact JSON and changes only the
keys each edit names.

**2. Model swaps are the one fuzzy part.** Swapping a block to a different model
changes its parameter set, and this code can’t know a model’s defaults it has
never seen. Parameter tweaks and bypasses are exact; swaps are best-effort and
flagged *“verify on device.”* To make swaps reliable, **teach it your gear:**

```bash
python build_catalog.py /path/to/folder/of/your/pgp/files
```

This reports every model and parameter your unit actually uses and writes
`learned_blocks.json` — real, known-good block definitions harvested from your
own presets that the agent can paste in for clean swaps.

---

## Files

| File | What it is |
|------|-----------|
| `server.py` | FastAPI app: sessions, upload, chat, download |
| `agent.py` | Prompts the local model, parses its JSON, applies validated edits |
| `patch_engine.py` | Reads/writes `.pgp`, introspects blocks, validates & applies edits |
| `model_db.py` | 342-model HX/POD Go catalog (id → name → real hardware) + lookups |
| `build_catalog.py` | Learns real models/params/blocks from your own presets |
| `template_newpreset.pgp` | Clean starting preset (replace with a real export) |
| `static/index.html` | The chat GUI |

---

## Notes & credits

- POD Go shares the HX modeling engine and model IDs with the Helix family, so
  the catalog applies; POD Go exposes a subset, and the app picks up anything
  POD Go-specific from the presets you upload.
- Model-ID → hardware mappings derive from the community
  [GhostNote17/HelixNativePresets](https://github.com/GhostNote17/HelixNativePresets)
  project (MIT) and the Line 6 Owner’s Manuals.
- Not affiliated with or endorsed by Line 6 / Yamaha Guitar Group. “POD Go,”
  “Helix,” and “HX” are trademarks of their respective owners. Back up your
  presets; use at your own risk.
