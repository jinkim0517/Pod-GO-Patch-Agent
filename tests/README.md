# Test suite

575 tests across 13 files, 99% statement coverage of the application modules,
full run in ~1.5 s. No network, no Ollama, no device required — every model
response is stubbed, so the suite is deterministic and runs in CI.

```bash
pip install -r requirements-dev.txt
pytest                              # 575 tests
pytest --cov --cov-report=term-missing
```

## Coverage

| Module | Statements | Coverage |
|---|---|---|
| `patch_engine.py` | 277 | 100% |
| `agent.py` | 174 | 100% |
| `server.py` | 100 | 100% |
| `build_catalog.py` | 55 | 100% |
| `model_db.py` | 115 | 96% |
| **total** | **721** | **99%** |

The 5 uncovered lines are the import-time `FileNotFoundError` fallbacks for the
two optional catalog files, which can't execute after import. Their behavioural
consequence — the app running without `official_catalog.json` — is covered by
`test_edge_cases.py::TestCatalogWithoutTheOfficialFile`.

## What each file covers

| File | Tests | Area |
|---|---|---|
| `test_invariants.py` | 185 | Randomized fuzzing + catalog integrity properties |
| `test_patch_edits.py` | 78 | `apply_edits` — the LLM guardrail |
| `test_agent_parsing.py` | 64 | Extracting and repairing model output |
| `test_model_db.py` | 64 | 433-model catalog, lookup, fuzzy search |
| `test_agent_turn.py` | 38 | One turn end to end, both retry paths |
| `test_server_api.py` | 36 | FastAPI endpoints, sessions, downloads |
| `test_patch_introspection.py` | 29 | What the UI and the prompt see |
| `test_edge_cases.py` | 25 | Unusual presets, missing catalogs |
| `test_build_mode.py` | 18 | Build canvas → finalize |
| `test_patch_io.py` / `test_catalog_learning.py` / `test_catalog_cli.py` / `test_snapshot_cascade.py` | 38 | `.pgp` round-trips, learned-block library, snapshot sync |

## The two things worth knowing

**Fuzzing.** `test_invariants.py` runs 180 randomized cases in three families —
malformed edit batches, random model output, and randomly truncated JSON — and
asserts one invariant rather than expected outputs: *whatever comes in, the
preset that comes out still round-trips through the `.pgp` loader and keeps its
signal chain.* This found a real bug: a `NaN` or `Infinity` value reached
`json.dumps`, which writes them as bare literals that aren't valid JSON, so the
exported `.pgp` would have been rejected by POD Go Edit. `patch_engine._finite`
now rejects them at the edit boundary (`TestNonFiniteValues`).

**The malformed-output corpus.** `test_agent_parsing.py` holds 12 response
shapes a local 7–8B model actually emits — fenced JSON, JSON buried in prose,
a bare op, a bare array, blocks-as-keys with and without a nested model id, four
spellings of the model key, a half-hallucinated batch — and asserts each one
still yields at least one edit that applies to the patch. A second set asserts
the other half of the contract: unsalvageable output degrades to a reply and
leaves the preset byte-identical.

## Fixtures

`conftest.py` has two autouse safety rails, so no test can reach the network or
the developer's real `learned_blocks.json` regardless of what it calls:

- `no_network` — any `urllib` request raises instead of dialing Ollama.
- `isolate_learned_blocks` — learned-block writes land in a tmp file.

Plus `fake_ollama`, which hands `run_turn` canned responses in order and records
every message list it was called with, so retry behaviour and prompt contents
are both assertable.
