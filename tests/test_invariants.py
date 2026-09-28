"""Invariants under adversarial input.

The guardrail's promise is unconditional: whatever the model emits, the preset
that comes out the other side still loads on the device. These tests hammer
apply_edits with randomized junk and assert that promise rather than any
particular outcome.
"""
import copy
import json
import random
import string

import pytest

import agent
import model_db
import patch_engine as pe

SEEDS = list(range(60))

OPS = ["set_param", "set_enabled", "swap_model", "set_tempo", "rename",
       "delete", "", "SET_PARAM", None, 42]

BLOCK_IDS = ["block0", "block1", "block2", "block99", "", "amp", None,
             "../../etc", "block0; DROP TABLE"]

PARAMS = ["Bass", "Drive", "@enabled", "@model", "Sparkle", "", None, "Mix", 7]

VALUES = [0.5, -1e9, 1e9, 0, "warmer", "0.7", True, False, None, [], {},
          float("inf"), "∞", "NaN"]

MODEL_IDS = ["HD2_AmpBritPlexi", "HD2_ReverbSpring", "HD2_NotReal",
             "ZZZ_Gibberish", "", None, 5, "HD2_" + "x" * 500]


def random_edit(rnd):
    return {k: v for k, v in {
        "op": rnd.choice(OPS),
        "block": rnd.choice(BLOCK_IDS),
        "param": rnd.choice(PARAMS),
        "model_id": rnd.choice(MODEL_IDS),
        "value": rnd.choice(VALUES),
    }.items() if rnd.random() > 0.2}


@pytest.mark.parametrize("seed", SEEDS)
def test_random_edit_batches_never_corrupt_the_preset(seed, template):
    """Fuzz: a batch of up to 8 randomly malformed ops must leave a preset that
    still round-trips through the .pgp loader."""
    rnd = random.Random(seed)
    edits = [random_edit(rnd) for _ in range(rnd.randint(1, 8))]
    original = copy.deepcopy(template)

    new, results = pe.apply_edits(template, edits)

    assert template == original, "the input patch was mutated"
    assert len(results) == len(edits), "every edit must get a verdict"
    assert all({"ok", "edit", "detail"} == set(r) for r in results)
    assert all(isinstance(r["detail"], str) and r["detail"] for r in results)

    reloaded = pe.load_patch(pe.save_patch(new))
    assert reloaded == new, "the result no longer survives a save/load round trip"
    assert pe.summarize(new)["blocks"], "the signal chain was destroyed"


@pytest.mark.parametrize("seed", SEEDS)
def test_random_llm_text_never_crashes_the_parser(seed, amp_patch):
    """Fuzz the other end: arbitrary model output must parse to a reply string
    and a list, never an exception."""
    rnd = random.Random(seed)
    alphabet = string.printable + "{}[]\",:"
    raw = "".join(rnd.choice(alphabet) for _ in range(rnd.randint(0, 400)))
    surface = pe.editable_surface(amp_patch)

    reply, edits = agent.parse_model_output(raw, surface)

    assert isinstance(reply, str) and reply
    assert isinstance(edits, list)
    new, results = pe.apply_edits(amp_patch, edits)
    assert len(results) == len(edits)
    assert pe.load_patch(pe.save_patch(new))


@pytest.mark.parametrize("seed", SEEDS)
def test_randomly_truncated_json_is_handled(seed):
    """Local models get cut off by the context window mid-object all the time."""
    full = json.dumps({"reply": "Warmed it up nicely for you.",
                       "edits": [{"op": "set_param", "block": "block0",
                                  "param": "Bass", "value": 0.7}]})
    cut = random.Random(seed).randint(0, len(full))
    reply, edits = agent.parse_model_output(full[:cut], {})
    assert isinstance(reply, str) and isinstance(edits, list)


class TestCatalogIntegrity:
    """Properties the catalog itself must hold, checked across all 400+ entries."""

    def test_every_curated_entry_is_a_well_formed_triple(self):
        for mid, entry in model_db.MODEL_DB.items():
            assert isinstance(mid, str) and mid
            assert len(entry) == 3
            cat, name, real = entry
            assert cat in model_db.CATEGORIES, f"{mid} has unknown category {cat}"
            assert name and isinstance(name, str)
            assert isinstance(real, str)

    def test_every_curated_id_looks_itself_up(self):
        for mid in model_db.MODEL_DB:
            assert model_db.lookup(mid) == model_db.MODEL_DB[mid]

    def test_every_verified_podgo_model_exists_in_the_catalog(self):
        missing = model_db.PODGO_VERIFIED - set(model_db.MODEL_DB)
        assert not missing, f"PODGO_VERIFIED references unknown ids: {sorted(missing)[:5]}"

    def test_every_catalog_entry_offered_to_the_llm_is_swappable(self, patch_factory):
        """Anything listed in the prompt must actually apply — a catalog line
        the engine then rejects is the worst kind of dead end."""
        patch = patch_factory({"fx": {"@model": "HD2_DistTeemahMono", "@enabled": True,
                                      "@position": 0, "Gain": 5.0}})
        listed = [line.split("|")[0].strip()
                  for line in model_db.compact_catalog(["Reverb", "Delay", "Mod"]).splitlines()
                  if not line.startswith("##")]
        assert listed
        for mid in listed:
            _new, results = pe.apply_edits(patch, [{"op": "swap_model", "block": "fx",
                                                    "model_id": mid}])
            assert results[0]["ok"], f"{mid} is offered but rejected: {results[0]['detail']}"

    def test_the_build_canvas_defaults_are_real_models(self):
        for slot, defaults in pe._BUILD_SLOT_DEFAULTS.items():
            cat = model_db.lookup(defaults["@model"])[0]
            assert cat != "Unknown", f"{slot} default is not a resolvable model"
