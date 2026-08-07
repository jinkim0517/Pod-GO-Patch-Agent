# POD Go Patch Agent

A local, chat-driven tone engineer for the **Line 6 POD Go**. Describe a sound in plain English (Ex. *"warm strat tone with a little spring,"* *"too muddy, tighten the low end,"* *"more gain and ambience"*) and it edits a preset and hands you a `.pgp` you import in POD Go Edit. You stay in the loop by reacting to what you hear and giving the agent feedback (*"more space,"* *"less fizz"*) and it makes targeted moves.

Two modes:

- **Edit** — load an existing preset and describe changes. The agent edits only what you name.
- **Build** — describe a tone from scratch. The agent selects an amp, cab, and effects, and sets parameters on everything it enables.

**Runs entirely on your machine.** A local model served by [Ollama] does the reasoning. No API keys, no cloud, which allows for secure and free access.

[Ollama]: https://ollama.com

---

## How it works

```
 you ─▶ browser UI ─▶ FastAPI server ─▶ Ollama (local model)
                                              │
                                              ▼
                                     edit operations (json)
                                              │
                                              ▼
                                       patch engine: validates
                                       each op against the real
                                       preset, applies the good
                                       ones to the in-memory patch

 (later, on demand) in-memory patch ─▶ Download .pgp ─▶ file on disk
```

The model never writes a preset directly. It only proposes **edit operations**, such as setting a parameter, bypassing a block, swapping an amp model, setting tempo, and renaming the patch. The patch engine is the guardrail: it applies edits to your actual file and rejects anything that doesn't fit, such as a wrong parameter name, a bad value type, an amp swapped out for a reverb. The worst case is an edit that gets rejected and reported back to you.

Five extra layers of reliability on top of that:

1. **JSON schema enforcement.** The Ollama call includes a formal schema for the `{"reply", "edits"}` response shape. The model physically cannot emit an unrecognized structure.
2. **One retry with feedback.** If the model's output still doesn't parse into that shape (and it wasn't a deliberate empty response, like a clarifying question), the agent replays the bad output back to the model with a short correction and asks it to try again — once.
3. **Repair pass.** If it's still off after the retry, `coerce_to_edits` maps whatever came back onto real blocks and parameters that exist, so the worst case is informative rejections rather than a silent no-op.
4. **Rejection retry.** If the edits parsed fine but the patch engine rejected every single one (e.g. an amp swapped for a reverb), the agent shows the model the specific rejection reasons and asks for a corrected set of edits — once.
5. **Param validation against the official catalog.** When [official_catalog.json](#official-model-catalog) is present, `set_param` rejects param names a model doesn't actually have and clamps numeric values into the device's real min/max range, instead of writing values the firmware would reject.

Parameter tweaks and bypass toggles are always exact, because they only touch keys already in your file. Changes also cascade into snapshots that were in sync with the old value, so your existing snapshots stay coherent.

---

## Setup

**1. Install Ollama and pull a model**

```bash
# install from https://ollama.com, then:
ollama pull llama3.1:8b      # solid default
# alternatives: qwen2.5:7b-instruct, mistral-nemo
ollama serve                 # if it isn't already running
```

> A model with a 16k+ context window is recommended — the full official POD Go catalog (~568 models, see [Official model catalog](#official-model-catalog) below) roughly doubles the size of the swap-target listing. The server requests `num_ctx: 16384` from Ollama automatically.

**2. Install dependencies and start the server**

```bash
pip install -r requirements.txt
python server.py
```

Open **http://localhost:8000**. The model name field (top-right) accepts any model you've pulled with `ollama pull`.

---

## Using it

**Tweak an existing preset**

1. Click **Upload .pgp** and load a preset exported from POD Go Edit.
2. Describe changes in the chat: *"roll off the high-cut on the cab, add a bit more reverb mix."*
3. Each turn shows exactly what changed (✓) and anything declined (⊘).
4. Hit **Download .pgp** when you like it, then import in POD Go Edit.

**Build from scratch**

1. Start a new session (the app opens on the clean template by default).
2. Click **Build** and describe the tone: *"warm Fender-style clean with a spring reverb and a touch of tape echo."*
3. The agent selects an amp and cab, decides which effect slots to enable, swaps each one to an appropriate model, and sets parameters — all in one pass. The preset is auto-named based on your description.
4. Continue tweaking with normal chat turns. Download when done.

Effect slots are flexible: any slot (Drive, Comp, Mod, Delay, Reverb, Pitch) can be swapped to any effect category. Amp and Cab slots stay fixed.

The loop is human-paced by design — there's no way to push a tone to the unit and hear it instantly, so you audition each download yourself.

---

## Teaching it your gear

Parameter tweaks and bypass toggles are always exact. **Model swaps** are the one fuzzy part: a different model brings a different parameter set, and a model's real parameter names (e.g. `Mod Mix`, `Xover`, `BiasX`) aren't documented anywhere — the app can only learn them from real exports.

**It learns automatically.** Every time you upload a `.pgp`, the app harvests the real blocks it contains into `learned_blocks.json` — merging into whatever it already knows, never discarding older learned models. From then on, a cross-category model swap (e.g. Reverb → Drive) pastes in that model's real, known-good parameters instead of leaving the block empty for the agent to guess at. This persists across restarts, so you never lose what it's learned, and re-uploading a preset it's already seen is a no-op.

You can also backfill it in bulk from a whole folder of past exports:

```bash
python build_catalog.py /path/to/your/pgp/files
```

This scans every preset in the folder, reports all models and parameters your unit actually uses, and writes `learned_blocks.json` in one pass. Unlike the automatic per-upload learning, this **overwrites** the file with just that folder's contents — handy for a one-time bulk import, but if you run it again later on a different subset of presets you'll lose models that were only in the earlier run.

None of this is required: without any learned data, cross-category swaps still work, just with the agent filling in parameter names from its own general knowledge rather than a verified template.

### Official model catalog

`learned_blocks.json` only knows what you've personally uploaded. For everything else, the app can pull Line 6's **own** model/parameter list straight out of the POD Go Edit app you already have installed — every model the device can load, with its real parameter names and legal min/max ranges, not just the ones you happen to own presets for.

```bash
python3 build_official_catalog.py
```

This reads POD Go Edit's bundled model definitions (macOS default path baked in; pass a different `Contents/Resources` folder as an argument if yours differs, e.g. on Windows) and writes `official_catalog.json`: `model_id -> {category, name, params: {param_name: {min, max, default, kind}}}`. It's gitignored — the source data is Line 6's proprietary app content, not ours to redistribute, so each user regenerates it locally rather than it being committed.

Once generated, it upgrades the agent in three ways:

- **Swap targets are guaranteed real.** `compact_catalog` prefers the official list over the hand-curated `PODGO_VERIFIED` subset, so every model offered as a swap target is one the device actually supports — no more, no less.
- **Cross-category swaps get real defaults even without learned data.** A swap to a model you've never uploaded a preset for still gets populated with the device's own default parameter values instead of an empty block.
- **`set_param` is validated against the real schema.** Unknown parameter names are rejected outright, and numeric values are clamped into the model's real min/max range before they ever reach the block.

Nothing else changes if you skip this step — the app falls back to `PODGO_VERIFIED` and learned/general-knowledge parameter filling exactly as before.

---

## Repository layout

```
.
├── server.py                  FastAPI app — sessions, upload, chat, download
├── agent.py                   Prompts Ollama, parses JSON, drives patch_engine
├── patch_engine.py            Reads/writes .pgp, validates and applies edits
├── model_db.py                POD Go model catalog (model ID → name → real hardware); PODGO_VERIFIED controls what the agent can propose
├── build_catalog.py           Learns real models/params from your own presets
├── build_official_catalog.py  Extracts Line 6's own model/param list from POD Go Edit
├── template_newpreset.pgp     Clean starting preset (replace with a real export if needed)
├── learned_blocks.json        Written by build_catalog.py — not required, improves swaps
├── official_catalog.json      Written by build_official_catalog.py — gitignored, regenerate locally
├── static/
│   └── index.html             Browser UI
├── samples/                   Example presets (not used by the app)
└── requirements.txt           fastapi, uvicorn, python-multipart
```

### server.py — local web server

Run with `python server.py`, then open http://localhost:8000. Everything stays on your machine: the UI talks to this server, and this server talks to your local Ollama. No data leaves the box.

On every upload, it also calls `build_catalog.learn_from_patch` to fold that preset's real blocks into `learned_blocks.json` — silently, and without ever failing the upload if learning hits an error.

### agent.py — the reasoning layer (hardened)

Turns a natural-language request into validated edit ops by prompting a local model served by Ollama. The model only *proposes* edits; `patch_engine` validates and applies them.

This module fixes a real-world failure: small models tend to invent their own JSON shape (e.g. `{block: {model_id: {params}}}`) instead of the edit grammar. Four defenses:

1. A much stricter prompt with a worked example and an explicit anti-example.
2. One retry with feedback: if the output doesn't parse into `{"reply","edits"}` and wasn't a deliberate empty response (e.g. a clarifying question), the agent shows the model its own bad output plus a short correction and asks it to try again — once.
3. A repair pass (`coerce_to_edits`) that salvages whatever comes back by mapping it onto blocks/params that actually exist, so the worst case is informative rejections rather than a silent "done".
4. A second, separate retry when the output *does* parse but `patch_engine` rejects every edit (e.g. an amp swapped for a reverb): the agent shows the model the specific rejection reasons and asks for a corrected set of edits — once.

### patch_engine.py — read, introspect, and safely edit `.pgp` presets

A POD Go preset is JSON shaped like:

```
{ "data": { "meta": {...}, "tone": {
      "global":   { "@tempo": 120.0, ... },
      "dsp0":     { "block0": { "@model": "HD2_AmpBrit2204",
                                "@enabled": true, "@position": 2,
                                "Gain": 5.0, "Bass": 0.5, ... },
                    "cab0":   { "@model": "HD2_Cab...", ... }, ... },
      "snapshot0": {...}, "controller": {...}, ... } } }
```

**Design principle — preserve and mutate.** We never rebuild a preset from assumptions. We load the user's exact JSON, and every edit touches only the one key it names. A block's parameters are whatever non-`@` keys already exist in that block, so the editable surface is learned from the real file rather than hard-coded. That makes round-tripping faithful even for parameters or models this code has never seen.

### model_db.py — Line 6 POD Go model-ID catalog

Maps internal model identifiers (the `@model` field inside a preset's blocks) to a `(category, display_name, real_hardware)` tuple. Also owns the learned-blocks store: loads `learned_blocks.json` into `LEARNED_BLOCKS` at import, exposes `learned_params(model_id)` (which `patch_engine` uses to fill in real parameter values on a cross-category swap), and `save_learned_blocks(blocks)` to persist updates and swap in the new catalog in memory immediately.

It loads `official_catalog.json` the same way, into `OFFICIAL_MODELS`, and exposes `official_params(model_id)` — the device's own `{param_name: {min, max, default, kind}}` schema, which `patch_engine` uses to validate and clamp `set_param` edits. Both files are optional; everything falls back gracefully to `{}` if they're missing.

Hardware name mappings derived from the community-maintained [GhostNote17/HelixNativePresets](https://github.com/GhostNote17/HelixNativePresets) project (MIT licensed) and the Line 6 Owner's Manuals. Not affiliated with or endorsed by Line 6 / Yamaha Guitar Group.

### build_catalog.py — learn from your own presets

`learn_from_patch(patch)` is what `server.py` calls on every upload: it merges one preset's real blocks into `learned_blocks.json` on top of whatever's already learned, and returns how many models were newly learned (not just refreshed). This is the automatic, incremental path.

`scan(folder)` is the manual CLI entry point for a one-time bulk import from a whole folder of past exports:

```bash
python build_catalog.py /path/to/folder/of/pgp
```

It reports every model id and parameter actually used across the folder, and writes `learned_blocks.json` in one pass — but unlike `learn_from_patch`, it **overwrites** the file with just that folder's contents rather than merging.

### build_official_catalog.py — extract Line 6's own catalog

A one-time (or "run it again after a POD Go Edit update") CLI script — not called automatically by `server.py`. Parses the `.models` files bundled inside the POD Go Edit app itself and writes `official_catalog.json`. See [Official model catalog](#official-model-catalog) above for what this unlocks and why it's gitignored.

```bash
python3 build_official_catalog.py
```

Why any of this helps: parameter tweaks and bypass toggles are always exact because they edit keys already in your file. Model swaps are the one fuzzy part, because a different model has a different parameter set with real firmware-specific key names nothing else in this app knows about. Feeding the agent real blocks harvested from your own presets makes swaps reliable too.

---

## Model Reference

Complete list of models available on the POD Go, sourced from the [official Line 6 model list](https://line6.com/podgo-models/). Without `official_catalog.json` generated, the agent can swap to a subset of these — see `PODGO_VERIFIED` in [model_db.py](model_db.py) for the current set, and run `build_catalog.py` on your own exports to expand it. Generating the [official catalog](#official-model-catalog) instead unlocks the full list above with real parameter schemas for every model.

<details>
<summary>Browse all models</summary>

<details>
<summary><strong>Amp Models — Guitar</strong> &nbsp;(89)</summary>

| Model | Based On |
|-------|----------|
| A30 Fawn Brt | Vox AC-30 Fawn (bright channel) |
| A30 Fawn Nrm | Vox AC-30 Fawn (normal channel) |
| ANGL Meteor | ENGL Fireball 100 |
| Archetype Clean | Paul Reed Smith Archon (clean channel) |
| Archetype Lead | Paul Reed Smith Archon (lead channel) |
| Brit 2203 | Marshall JCM-800 (100 watt) |
| Brit 2204 | Marshall JCM-800 |
| Brit J45 Brt | Marshall JTM-45 (bright channel) |
| Brit J45 Nrm | Marshall JTM-45 (normal channel) |
| Brit P75 Brt | Park 75 (bright channel) |
| Brit P75 Nrm | Park 75 (normal channel) |
| Brit Plexi Brt | Marshall Super Lead 100 (bright channel) |
| Brit Plexi Jump | Marshall Super Lead 100 (jumped) |
| Brit Plexi Nrm | Marshall Super Lead 100 (normal channel) |
| Brit Trem Brt | Marshall JTM-50 (bright channel) |
| Brit Trem Jump | Marshall JTM-50 (jumped) |
| Brit Trem Nrm | Marshall JTM-50 (normal channel) |
| Cali IV Lead | MESA/Boogie Mark IV (lead channel) |
| Cali IV Rhythm 1 | MESA/Boogie Mark IV (channel I) |
| Cali IV Rhythm 2 | MESA/Boogie Mark IV (channel II) |
| Cali Rectifire | MESA/Boogie Dual Rectifier |
| Cali Texas Ch1 | MESA/Boogie Lone Star (clean channel) |
| Cali Texas Ch2 | MESA/Boogie Lone Star (drive channel) |
| Cartographer | Ben Adrian Cartographer |
| Das Benzin Lead | Diezel VH4 (lead channel) |
| Das Benzin Mega | Diezel VH4 (mega channel) |
| Derailed Ingrid | Trainwreck Circuits Express |
| Divided Duo | ÷13 JRT 9/15 |
| Essex A15 | Vox AC-15 |
| Essex A30 | Vox AC-30 with top boost |
| Fullerton Brt | Fender 5C3 Tweed Deluxe (bright channel) |
| Fullerton Jump | Fender 5C3 Tweed Deluxe (jumped channels) |
| Fullerton Nrm | Fender 5C3 Tweed Deluxe (normal channel) |
| German Mahadeva | Bogner Shiva |
| German Ubersonic | Bogner Überschall |
| German Xtra Blue | Bogner Ecstasy 101B (EL34) Blue channel |
| German Xtra Red | Bogner Ecstasy 101B (EL34) Red channel |
| Grammatico GSG | Grammatico GSG100 |
| Grammatico LG Brt | Grammatico LaGrange (bright channel) |
| Grammatico LG Jump | Grammatico LaGrange (jumped channels) |
| Grammatico LG Nrm | Grammatico LaGrange (normal channel) |
| Interstate Zed | Dr Z Route 66 |
| Jazz Rivet 120 | Roland JC-120 Jazz Chorus |
| Line 6 2204 Mod | Line 6 Original |
| Line 6 Aristocrat | Line 6 Original |
| Line 6 Badonk | Line 6 Original |
| Line 6 Carillon | Line 6 Original |
| Line 6 Clarity | Line 6 Original |
| Line 6 Doom | Line 6 Original |
| Line 6 Elektrik | Line 6 Original |
| Line 6 Elmsley | Line 6 Original |
| Line 6 Epic | Line 6 Original |
| Line 6 Fatality | Line 6 Original |
| Line 6 Kinetic | Line 6 Original |
| Line 6 Litigator | Line 6 Original |
| Line 6 Oblivion | Line 6 Original |
| Line 6 Ventoux | Line 6 Original |
| Line 6 Voltage | Line 6 Original |
| Mail Order Twin | Silvertone 1484 |
| Mandarin 80 | Orange OR80 |
| Mandarin Rocker | Orange Rockerverb 100 MKIII |
| Matchstick Ch1 | Matchless DC30 (channel 1) |
| Matchstick Ch2 | Matchless DC30 (channel 2) |
| Matchstick Jump | Matchless DC30 (jumped) |
| Moo)))n Brt | Sunn Model T (bright channel) |
| Moo)))n Jump | Sunn Model T (jumped) |
| Moo)))n Nrm | Sunn Model T (normal channel) |
| PV Panama | Peavey 5150 |
| Placater Clean | Friedman BE-100 (clean channel) |
| Placater Dirty | Friedman BE-100 (BE/HBE channel) |
| Revv Gen Purple | Revv Generator 120 (purple/gain ch. 3) |
| Revv Gen Red | Revv Generator 120 (red/high gain ch. 4) |
| Solo Lead Clean | Soldano SLO-100 (clean channel) |
| Solo Lead Crunch | Soldano SLO-100 (crunch channel) |
| Solo Lead OD | Soldano SLO-100 (overdrive channel) |
| Soup Pro | Supro S6616 |
| Stone Age 185 | Gibson EH-185 |
| Tweed Blues Brt | Fender Bassman (bright channel) |
| Tweed Blues Nrm | Fender Bassman (normal channel) |
| US Deluxe Nrm | Fender Deluxe Reverb (normal channel) |
| US Deluxe Vib | Fender Deluxe Reverb (vibrato channel) |
| US Double Nrm | Fender Twin Reverb (normal channel) |
| US Double Vib | Fender Twin Reverb (vibrato channel) |
| US Princess | Fender Princeton Reverb |
| US Small Tweed | Fender Champ |
| US Super Nrm | Fender Super Reverb (normal channel) |
| US Super Vib | Fender Super Reverb (vibrato channel) |
| Voltage Queen | Victoria Vintage Queen |
| WhoWatt 100 | Hiwatt DR-103 (Brilliant channel) |

</details>

<details>
<summary><strong>Amp Models — Bass</strong> &nbsp;(18)</summary>

| Model | Based On |
|-------|----------|
| Ampeg B-15NF | Ampeg B-15NF Portaflex |
| Ampeg SVT Brt | Ampeg SVT (bright channel) |
| Ampeg SVT Nrm | Ampeg SVT (normal channel) |
| Ampeg SVT-4 Pro | Ampeg SVT-4 PRO |
| Agua 51 | Aguilar DB51 |
| Agua Sledge | Aguilar Tone Hammer |
| Busy One Ch1 | Pearce BC-1 preamp (channel 1) |
| Busy One Ch2 | Pearce BC-1 preamp (channel 2) |
| Busy One Jump | Pearce BC-1 preamp (jumped) |
| Cali 400 Ch1 | MESA/Boogie Bass 400+ (channel 1) |
| Cali 400 Ch2 | MESA/Boogie Bass 400+ (channel 2) |
| Cali Bass | MESA/Boogie M9 Carbine |
| Del Sol 300 | Sunn Coliseum 300 |
| G Cougar 800 | Gallien-Krueger GK 800RB |
| Mandarin 200 | Orange AD200 MkIII |
| Studio Tube Pre | Requisite Y7 mic preamp |
| US Dripman Nrm | Fender Bassman (Silver Panel) |
| Woody Blue | Acoustic 360 |

</details>

<details>
<summary><strong>Cab Models</strong> &nbsp;(55)</summary>

| Model | Based On |
|-------|----------|
| 1x10 US Princess | 1x10" Fender Princeton Reverb |
| 1x12 Blue Bell | 1x12" Vox AC-15 Blue Alnico |
| 1x12 Cali EXT | 1x12" Mesa Boogie Extension Cab |
| 1x12 Cali IV | 1x12" MESA/Boogie Mk IV combo |
| 1x12 Celest 12H | 1x12" ÷13 JRT 9/15 G12 H30 |
| 1x12 Del Sol | 1x12" Sunn Coliseum |
| 1x12 Field Coil | 1x12" Gibson EH185 |
| 1x12 Fullerton | 1x12" Fender 5C3 Tweed Deluxe |
| 1x12 Grammatico | 1x12" Grammatico LaGrange |
| 1x12 Lead 80 | 1x12" Bogner Shiva CL80 |
| 1x12 Open Cast | 1x12" custom open-back EVM12L |
| 1x12 Open Cream | 1x12" custom open-back G12M-65 |
| 1x12 US Deluxe | 1x12" Fender Deluxe Oxford |
| 1x12 US Princess | 1x12" Fender Princeton Reverb |
| 1x12 Epicenter | 1x12" Epifani Ultralight series |
| 1x15 Ampeg B-15 | 1x15" Ampeg B-15 |
| 1x18 Del Sol | 1x18" Sunn Coliseum |
| 1x18 Woody Blue | 1x18" Acoustic 360 |
| 1x8 Small Tweed | 1x8" Fender Champ |
| 2x12 Blue Bell | 2x12" Vox AC-30 Fawn Blue |
| 2x12 Double C12N | 2x12" Fender Twin C12N |
| 2x12 Interstate | 2x12" Dr Z Z Best V30 |
| 2x12 Jazz Rivet | 2x12" Roland JC-120 |
| 2x12 Mail C12Q | 2x12" Silvertone 1484 |
| 2x12 Mandarin 30 | 2x12" Orange PPC212 V30 |
| 2x12 Match G25 | 2x12" Matchless DC-30 Greenback 25 |
| 2x12 Match H30 | 2x12" Matchless DC-30 G12H30 |
| 2x12 Silver Bell | 2x12" Vox AC-30TB Silver Alnico |
| 2x15 Brute | 2x15" MESA/Boogie 2x15 EV |
| 2x15 Dripman | 2x15" Fender Bassman JBL D130 |
| 4x10 Ampeg HLF | 4x10" Ampeg SVT 410HLF |
| 4x10 Ampeg Pro | 4x10" Ampeg PR-410HLF |
| 4x10 Garden | 4x10" Eden D410XLT |
| 4x10 Tweed P10R | 4x10" Fender Bassman P10R |
| 4x10 US Super | 4x10" Fender Super Reverb |
| 4x12 1960 T75 | 4x12" Marshall 1960 AT75 |
| 4x12 Blackback 30 | 4x12" Park 75 G12 H30 |
| 4x12 Brit V30 | 4x12" Marshall 1960AV V30 |
| 4x12 Cali V30 | 4x12" MESA/Boogie 4FB V30 |
| 4x12 Cartog C90 | 4x12" Lee Jackson w/ Mesa C90 |
| 4x12 Cartog Guv | 4x12" Lee Jackson w/ Eminence Governor |
| 4x12 Greenback 20 | 4x12" Marshall Basketweave G12M-20 |
| 4x12 Greenback 25 | 4x12" Marshall Basketweave G12 M25 |
| 4x12 Greenback 30 | 4x12" Marshall "basketweave" G12H-30 |
| 4x12 MOO)))N T75 | 4x12" Sunn Cab w/ G75T |
| 4x12 Mandarin EM | 4x12" Orange Eminence |
| 4x12 SoloLead EM | 4x12" Soldano |
| 4x12 Uber T75 | 4x12" Bogner Uberkab T75 |
| 4x12 Uber V30 | 4x12" Bogner Uberkab V30 |
| 4x12 WhoWatt 100 | 4x12" Hiwatt AP Fane |
| 4x12 XXL V30 | 4x12" ENGL XXL V30 |
| 6x10 Cali Power | 6x10" MESA/Boogie Power House |
| 8x10 Ampeg SVT E | 8x10" Ampeg SVT |
| 8x10 SVT AV | 8x10" Ampeg SVT 810AV Heritage |
| Soup Pro Ellipse | 1x6x9" Supro S6616 |

</details>

<details>
<summary><strong>Distortion / Drive</strong> &nbsp;(55)</summary>

| Model | Based On |
|-------|----------|
| Alpaca Rogue | Way Huge Red Llama (modded) |
| Ampeg Scrambler | Ampeg Scrambler Bass Overdrive |
| Arbitrator Fuzz | Arbiter FuzzFace |
| Ballistic Fuzz | Euthymia ICBM Fuzz |
| Bighorn Fuzz | '73 EHX Ram's Head Big Muff Pi |
| Bitcrusher | Line 6 Original |
| Bronze Master | Maestro Bass Brassmaster |
| Buzz Saw | Maestro Fuzz Tone |
| Classic Dist | ProCo RAT |
| Colordrive | Colorsound Overdriver |
| Compulsive Drive | Fulltone OCD |
| Dark Dove Fuzz | Electro-Harmonix Russian Big Muff |
| Deez One Mod | BOSS DS-1 (Keeley modded) |
| Deez One Vintage | BOSS DS-1 (Made-in-Japan) |
| Deranged Master | Dallas Rangemaster Treble Booster |
| Dhyana Drive | Hermida Zendrive |
| Facial Fuzz | Arbiter Fuzz Face |
| Fuzz Pi | Electro-Harmonix Big Muff Pi |
| Heavy Dist | BOSS Metal Zone |
| Hedgehog D9 | MAXON SD9 Sonic Distortion |
| Heir Apparent | Analogman Prince of Tone |
| Horizon Drive | Horizon Precision Drive |
| Industrial Fuzz | Z.Vex Fuzz Factory |
| Jet Fuzz | Roland Jet Phaser |
| Jumbo Fuzz | Vox Tone Bender |
| KWB | Benadrian Kowloon Walled Bunny Distortion |
| Killer Z | BOSS Metal Zone MT-2 |
| Kinky Boost | Xotic EP Booster |
| L6 Distortion | Line 6 Original |
| L6 Drive | Colorsound Overdriver (modded) |
| Megaphone | Megaphone |
| Minotaur | Klon Centaur |
| Obsidian 7000 | Darkglass Microtubes B7K Ultra |
| Octave Fuzz | Tycobrahe Octavia |
| Overdrive | DOD Overdrive/Preamp 250 |
| Pillars OD | Earthquaker Devices Plumes |
| Pocket Fuzz | Jordan Boss Tone Fuzz |
| Ram's Head | EHX Ram's Head Big Muff Pi |
| Ratatouille Dist | Pro Co RAT |
| Regal Bass DI | Nobel Preamp bass DI |
| Scream 808 | Ibanez TS808 Tube Screamer |
| Screamer | Ibanez Tube Screamer |
| Stupor OD | BOSS SD-1 Overdrive |
| Sub Oct Fuzz | PAiA Roctave Divider |
| Swedish Chainsaw | Boss HM-2 Heavy Metal (MIJ) |
| Teemah! | Paul Cochrane Timmy Overdrive |
| Thrifter Fuzz | Line 6 Original |
| Top Secret OD | DOD OD-250 |
| Triangle Fuzz | Electro-Harmonix Big Muff Pi |
| Tube Drive | Chandler Tube Driver |
| Tycoctavia Fuzz | Tycobrahe Octavia |
| Valve Driver | Chandler Tube Driver |
| Vermin Dist | Pro Co RAT |
| Wringer Fuzz | Garbage's modded BOSS FZ-2 |
| Xenomorph Fuzz | Subdecay Harmonic Antagonizer |
| ZeroAmp Bass DI | Tech 21 SansAmp Bass Driver DI V1 |

</details>

<details>
<summary><strong>EQ</strong> &nbsp;(8)</summary>

| Model | Based On |
|-------|----------|
| 10 Band Graphic | MXR 10-Band Graphic EQ |
| Acoustic Sim | Line 6 Original |
| Cali Q Graphic | MESA/Boogie Mark IV Graphic EQ |
| Low and High Cut | Line 6 Original |
| Low/High Shelf | Line 6 Original |
| Parametric | Line 6 Original |
| Simple EQ | Line 6 Original |
| Tilt | Line 6 Original |

</details>

<details>
<summary><strong>Dynamics / Compressor</strong> &nbsp;(18)</summary>

| Model | Based On |
|-------|----------|
| 3-Band Comp | Line 6 Original |
| Ampeg Opto Comp | Ampeg Octo Comp compressor |
| Autoswell | Line 6 Original |
| Blue Comp | BOSS CS-1 |
| Blue Comp Treb | BOSS CS-1 (Treble switch on) |
| Boost Comp | MXR Micro Amp |
| Deluxe Comp | Line 6 Original |
| Hard Gate | Line 6 Original |
| Horizon Gate | Horizon Precision Drive — Gate Circuit |
| Kinky Comp | Xotic SP Compressor |
| LA Studio Comp | Teletronix LA-2A |
| Noise Gate | Line 6 Original |
| Red Comp | MXR Dyna Comp |
| Red Squeeze | MXR Dyna Comp |
| Rochester Comp | Ashly CLX-52 |
| Tube Comp | Teletronix LA-2A |
| Vetta Comp | Line 6 Original |
| Vetta Juice | Line 6 Original |

</details>

<details>
<summary><strong>Reverb</strong> &nbsp;(23)</summary>

| Model | Based On |
|-------|----------|
| '63 Spring | Line 6 Original |
| Cave | Line 6 Original |
| Chamber | Line 6 Original |
| Double Tank | Line 6 Original |
| Ducking | Line 6 Original |
| Dynamic Ambience | Line 6 Original |
| Dynamic Hall | Line 6 Original |
| Dynamic Plate | Line 6 Original |
| Dynamic Room | Line 6 Original |
| Echo | Line 6 Original |
| Ganymede | Line 6 Original |
| Glitz | Line 6 Original |
| Hall | Line 6 Original |
| Hot Springs | Line 6 Original |
| HX Spring | Line 6 Original |
| Octo | Line 6 Original |
| Particle Verb | Line 6 Original |
| Plate | Line 6 Original |
| Plateaux | Line 6 Original |
| Room | Line 6 Original |
| Searchlights | Line 6 Original |
| Shimmer | Line 6 Original |
| Spring | Line 6 Original |
| Tile | Line 6 Original |

</details>

<details>
<summary><strong>Modulation</strong> &nbsp;(55)</summary>

| Model | Based On |
|-------|----------|
| 122 Rotary | Leslie 122 |
| 145 Rotary | Leslie 145 |
| 4-Voice Chorus | Line 6 Original |
| 60s Bias Trem | Vox AC-15 Tremolo |
| 70s Chorus | BOSS CE-1 |
| 80A Flanger | A/DA Flanger |
| AC Flanger | MXR Flanger |
| AM Ring Mod | Line 6 Original |
| Ampeg Liquifier | Ampeg Liquifier Chorus |
| Analog Chorus | BOSS CE-1 |
| Analog Flanger | MXR Flanger |
| Barberpole | Line 6 Original |
| Bias Tremolo | Vox AC-15 Tremolo |
| Bleat Chop Trem | Lightfoot Labs Goatkeeper |
| Bubble Vibrato | BOSS VB-2 Vibrato |
| Chorus | Line 6 Original |
| Courtesan Flange | Electro-Harmonix Deluxe EM |
| Deluxe Phaser | Line 6 Original |
| Dimension | Roland Dimension D |
| Double Take | Line 6 Original |
| Dual Phaser | Mu-Tron Bi-Phase |
| Dynamix Flanger | Line 6 Original |
| FlexoVibe | Line 6 Original |
| Frequency Shift | Line 6 Original |
| Gray Flanger | MXR 117 Flanger |
| Harmonic Flanger | A/DA Flanger |
| Harmonic Tremolo | Line 6 Original |
| Jet Flanger | A/DA Flanger |
| Optical Trem | Fender optical tremolo circuit |
| Opto Tremolo | Fender Deluxe Reverb |
| Panned Phaser | Ibanez Flying Pan |
| Panner | Line 6 Original |
| Pattern Tremolo | Line 6 Original |
| Pebble Phaser | Electro-Harmonix Small Stone |
| Phaser | MXR Phase 90 |
| Pitch Ring Mod | Line 6 Original |
| Pitch Vibrato | BOSS VB-2 |
| PlastiChorus | Modded Arion SCH-Z chorus |
| Random S&H | Line 6 Original |
| Retro Reel | Line 6 Original |
| Ring Modulator | Line 6 Original |
| Rotary Drum | Fender Vibratone |
| Rotary Drum/Horn | Leslie 145 |
| Script Mod Phase | MXR Phase 90 |
| Script Phase | MXR Phase 90 (script logo version) |
| Sweeper | Line 6 Original |
| Tape Eater | Line 6 Original |
| Tremolo/Autopan | BOSS PN-2 |
| Tri Chorus | Dytronics Tri-Stereo Chorus |
| Triple Rotary | Yamaha RA-200 rotary speaker |
| Trinity Chorus | Dytronics Tri-Stereo Chorus |
| U-Vibe | Shin-ei Uni-Vibe |
| Ubiquitous Vibe | Shin-ei Uni-Vibe |
| Vibe Rotary | Fender Vibratone |
| Warble-Matic | Line 6 Original |

</details>

<details>
<summary><strong>Delay</strong> &nbsp;(40)</summary>

| Model | Based On |
|-------|----------|
| ADT | Line 6 Original (automatic double tracker) |
| Adriatic Delay | BOSS DM-2 w/ Adrian Mod |
| Adriatic Swell | Line 6 Original |
| Analog Echo | BOSS DM-2 |
| Analog w/Mod | Electro-Harmonix Deluxe Memory Man |
| Auto-Volume Echo | Line 6 Original |
| Bucket Brigade | BOSS DM-2 |
| Bubble Echo | Line 6 Original |
| Crisscross | Line 6 Original |
| Dig w/Mod | Line 6 Original |
| Digital | Line 6 Original |
| Dual Delay | Line 6 Original |
| Ducked Delay | TC Electronic 2290 |
| Dynamic | TC Electronic 2290 |
| Echo Platter | Binson EchoRec |
| Elephant Man | Electro-Harmonix Deluxe Memory Man |
| Euclidean Delay | Line 6 Original |
| Glitch Delay | Line 6 Original |
| Harmony Delay | Line 6 Original |
| Lo Res | Line 6 Original |
| Mod/Chorus Echo | Line 6 Original |
| Multi Pass | Line 6 Original |
| Multi-Head | Roland RE-101 Space Echo |
| Multitap 4 | Line 6 Original |
| Multitap 6 | Line 6 Original |
| Phaze Eko | Line 6 Original |
| Ping Pong | Line 6 Original |
| Pitch Echo | Line 6 Original |
| Ratchet | Line 6 Original |
| Reverse | Line 6 Original |
| Reverse Delay | Line 6 Original |
| Simple Delay | Line 6 Original |
| Stereo | Line 6 Original |
| Sweep Echo | Line 6 Original |
| Tape Echo | Maestro Echoplex EP-3 |
| Tesselator | Line 6 Original |
| Transistor Tape | Maestro Echoplex EP-3 |
| Tube Echo | Maestro Echoplex EP-1 |
| Vintage Digital | Line 6 Original |
| Vintage Swell | Line 6 Original |

</details>

<details>
<summary><strong>Pitch / Synth</strong> &nbsp;(24)</summary>

| Model | Based On |
|-------|----------|
| 3 Note Generator | Line 6 Original |
| 4 OSC Generator | Line 6 Original |
| Analog Synth | Line 6 Original |
| Attack Synth | Korg X911 Guitar Synth |
| Bass Octaver | EBS OctaBass |
| Boctaver | BOSS OC-2 Octaver |
| Buzz Wave | Line 6 Original |
| Double Bass | Line 6 Original |
| Dual Pitch | Line 6 Original |
| Growler | Line 6 Original |
| Octi Synth | Line 6 Original |
| Pitch Wham | Digitech Whammy |
| Rez Synth | Line 6 Original |
| Saturn 5 Ring Mod | Line 6 Original |
| Seismik Synth | Line 6 Original |
| Simple Pitch | Line 6 Original |
| Smart Harmony | Eventide H3000 |
| String Theory | Line 6 Original |
| Synth FX | Line 6 Original |
| Synth Harmony | Line 6 Original |
| Synth Lead | Line 6 Original |
| Synth O Matic | Line 6 Original |
| Synth String | Roland GR700 Guitar Synth |
| Twin Harmony | Eventide H3000 |

</details>

<details>
<summary><strong>Filter</strong> &nbsp;(15)</summary>

| Model | Based On |
|-------|----------|
| Asheville Pattrn | Moog Moogerfooger MF-105M MuRF Filter |
| Autofilter | Line 6 Original |
| Comet Trails | Line 6 Original |
| Mystery Filter | Korg A3 |
| Mutant Filter | Musitronics Mu-Tron III |
| Obi Wah | Oberheim voltage-controlled S&H filter |
| Q Filter | Line 6 Original |
| Seeker | Z Vex Seek Wah |
| Slow Filter | Line 6 Original |
| Spin Cycle | Craig Anderton's Wah/Anti-Wah |
| Throbber | Electrix Filter Factory |
| Tron Down | Musitronics Mu-Tron III (down) |
| Tron Up | Musitronics Mu-Tron III (up) |
| V Tron | Musitronics Mu-Tron III |
| Voice Box | Line 6 Original |

</details>

<details>
<summary><strong>Wah</strong> &nbsp;(11)</summary>

| Model | Based On |
|-------|----------|
| Chrome | Vox V847 |
| Chrome Custom | Modded Vox V847 |
| Colorful | Colorsound Wah-fuzz |
| Conductor | Maestro Boomerang |
| Fassel | Dunlop Cry Baby Super |
| Teardrop 310 | Dunlop Cry Baby Fasel model 310 |
| Teardrop Bass Q | Dunlop 105Q bass wah |
| Throaty | RMC Real McCoy 1 |
| UK Wah 846 | Vox V846 |
| Vetta Wah | Line 6 Original |
| Weeper | Arbiter Cry Baby |

</details>

</details>

---

## Caveats

**The bundled template is structurally correct but inferred.** It matches the POD Go/HX preset shape and round-trips cleanly, but it was not exported from a real unit. For a guaranteed-loadable starting point, export a **"New Preset"** from POD Go Edit and save it over `template_newpreset.pgp`. Better yet, just **upload your own presets** — editing a real file is always faithful, because the app preserves your exact JSON and changes only the keys each edit names.

**Model swaps on blocks the app has never seen are best-effort.** If the model proposes an ID not in the catalog, the engine tries a semantic match first, then falls back to the nearest model in the same effect category. The result is flagged in the change list. Running `build_catalog.py` on your presets eliminates most of these cases.
