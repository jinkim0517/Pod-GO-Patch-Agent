"""apply_edits — the guardrail that stands between the LLM and the preset.

Every test here is about one promise: a bad edit is rejected with a reason and
changes nothing, while good edits in the same batch still land.
"""
import copy
import json

import pytest

import model_db
import patch_engine as pe


def apply(patch, *edits):
    return pe.apply_edits(patch, list(edits))


def only(results):
    assert len(results) == 1
    return results[0]


# ─── Purity ──────────────────────────────────────────────────────

class TestNeverMutatesTheInput:
    def test_input_patch_is_untouched(self, amp_patch):
        before = copy.deepcopy(amp_patch)
        apply(amp_patch, {"op": "set_param", "block": "block0", "param": "Bass", "value": 0.9})
        assert amp_patch == before

    def test_returned_patch_is_a_separate_object(self, amp_patch):
        new, _ = apply(amp_patch, {"op": "rename", "value": "New"})
        new["data"]["tone"]["dsp0"]["block0"]["Bass"] = 0.123
        assert amp_patch["data"]["tone"]["dsp0"]["block0"]["Bass"] != 0.123

    def test_rejected_edits_leave_the_patch_identical(self, amp_patch):
        new, results = apply(amp_patch, {"op": "set_param", "block": "nope",
                                         "param": "Bass", "value": 1})
        assert not only(results)["ok"]
        assert new == amp_patch


# ─── set_param ───────────────────────────────────────────────────

class TestSetParam:
    def test_sets_an_existing_param(self, amp_patch):
        new, results = apply(amp_patch, {"op": "set_param", "block": "block0",
                                         "param": "Bass", "value": 0.7})
        assert only(results)["ok"]
        assert new["data"]["tone"]["dsp0"]["block0"]["Bass"] == 0.7

    def test_detail_reports_the_before_and_after(self, amp_patch):
        _, results = apply(amp_patch, {"op": "set_param", "block": "block0",
                                       "param": "Bass", "value": 0.7})
        assert "0.44" in only(results)["detail"] and "0.7" in only(results)["detail"]

    def test_unknown_block_is_rejected(self, amp_patch):
        _, results = apply(amp_patch, {"op": "set_param", "block": "block99",
                                       "param": "Bass", "value": 0.7})
        r = only(results)
        assert not r["ok"] and "block99" in r["detail"]

    def test_reserved_at_field_is_rejected(self, amp_patch):
        """@enabled must go through set_enabled so the snapshot cascade runs."""
        _, results = apply(amp_patch, {"op": "set_param", "block": "block0",
                                       "param": "@enabled", "value": False})
        r = only(results)
        assert not r["ok"] and "set_enabled" in r["detail"]

    def test_hallucinated_param_on_a_catalogued_model_is_rejected(self, amp_patch):
        _, results = apply(amp_patch, {"op": "set_param", "block": "block0",
                                       "param": "Warmth", "value": 5})
        r = only(results)
        assert not r["ok"] and "Warmth" in r["detail"]

    def test_rejection_lists_the_params_that_do_exist(self, amp_patch):
        """The agent gets one retry with this text — it has to be actionable."""
        if not model_db.official_params("HD2_AmpUSDoubleNrm"):
            pytest.skip("official_catalog.json not generated")
        _, results = apply(amp_patch, {"op": "set_param", "block": "block0",
                                       "param": "Warmth", "value": 5})
        assert "Drive" in only(results)["detail"]

    def test_non_numeric_value_for_a_new_param_is_rejected(self, patch_factory):
        patch = patch_factory({"block0": {"@model": "HD2_NotInAnyCatalog",
                                          "@enabled": True, "@position": 0}})
        _, results = apply(patch, {"op": "set_param", "block": "block0",
                                   "param": "Wobble", "value": "quite a lot"})
        assert not only(results)["ok"]

    def test_good_and_bad_edits_in_one_batch_are_handled_independently(self, amp_patch):
        new, results = pe.apply_edits(amp_patch, [
            {"op": "set_param", "block": "block0", "param": "Bass", "value": 0.7},
            {"op": "set_param", "block": "ghost", "param": "Bass", "value": 0.7},
            {"op": "set_param", "block": "block0", "param": "Treble", "value": 0.6},
        ])
        assert [r["ok"] for r in results] == [True, False, True]
        assert new["data"]["tone"]["dsp0"]["block0"]["Bass"] == 0.7
        assert new["data"]["tone"]["dsp0"]["block0"]["Treble"] == 0.6


class TestValueCoercion:
    """The LLM emits loose JSON types; the device needs the file's own types."""

    def test_int_param_stays_int(self, patch_factory):
        patch = patch_factory({"b": {"@model": "HD2_ChorusStereo", "@enabled": True,
                                     "@position": 0, "WaveShape": 0}})
        new, results = apply(patch, {"op": "set_param", "block": "b",
                                     "param": "WaveShape", "value": 2.7})
        assert only(results)["ok"]
        value = new["data"]["tone"]["dsp0"]["b"]["WaveShape"]
        assert value == 3 and isinstance(value, int)

    def test_float_param_accepts_an_int(self, amp_patch):
        new, _ = apply(amp_patch, {"op": "set_param", "block": "block1",
                                   "param": "LowCut", "value": 120})
        value = new["data"]["tone"]["dsp0"]["block1"]["LowCut"]
        assert value == 120.0 and isinstance(value, float)

    def test_float_param_accepts_a_numeric_string(self, amp_patch):
        new, results = apply(amp_patch, {"op": "set_param", "block": "block1",
                                         "param": "LowCut", "value": "150"})
        assert only(results)["ok"]
        assert new["data"]["tone"]["dsp0"]["block1"]["LowCut"] == 150.0

    def test_float_param_rejects_a_word(self, amp_patch):
        _, results = apply(amp_patch, {"op": "set_param", "block": "block1",
                                       "param": "LowCut", "value": "warmer"})
        assert not only(results)["ok"]

    @pytest.mark.parametrize("given,expected", [
        ("true", True), ("True", True), ("on", True), ("yes", True), ("1", True),
        ("false", False), ("off", False), ("no", False), ("0", False),
    ])
    def test_bool_param_accepts_the_words_models_actually_emit(self, patch_factory,
                                                               given, expected):
        patch = patch_factory({"b": {"@model": "HD2_VolPanVolStereo", "@enabled": True,
                                     "@position": 0, "VolumeTaper": False}})
        new, _ = apply(patch, {"op": "set_param", "block": "b",
                               "param": "VolumeTaper", "value": given})
        assert new["data"]["tone"]["dsp0"]["b"]["VolumeTaper"] is expected


class TestNonFiniteValues:
    """Found by the fuzzer in tests/test_invariants.py: json.dumps writes NaN
    and Infinity as bare literals, which aren't valid JSON — POD Go Edit
    refuses the resulting .pgp. They have to be rejected at the edit boundary."""

    @pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity",
                                       float("nan"), float("inf"), float("-inf")])
    def test_a_non_finite_tempo_is_rejected(self, amp_patch, value):
        new, results = apply(amp_patch, {"op": "set_tempo", "value": value})
        assert not only(results)["ok"]
        assert new == amp_patch

    @pytest.mark.parametrize("value", ["NaN", "Infinity", float("nan"), float("inf")])
    def test_a_non_finite_param_is_rejected(self, amp_patch, value):
        new, results = apply(amp_patch, {"op": "set_param", "block": "block0",
                                         "param": "Bass", "value": value})
        assert not only(results)["ok"]
        assert new == amp_patch

    def test_a_non_finite_value_cannot_create_a_new_param(self, patch_factory):
        patch = patch_factory({"b": {"@model": "HD2_NotInAnyCatalog",
                                     "@enabled": True, "@position": 0}})
        _, results = apply(patch, {"op": "set_param", "block": "b",
                                   "param": "Wobble", "value": float("inf")})
        assert not only(results)["ok"]

    def test_the_saved_file_is_always_strict_json(self, amp_patch):
        new, _ = pe.apply_edits(amp_patch, [
            {"op": "set_tempo", "value": "NaN"},
            {"op": "set_param", "block": "block0", "param": "Bass", "value": "Infinity"},
            {"op": "set_param", "block": "block0", "param": "Treble", "value": 0.6},
        ])
        def _reject(literal):
            raise AssertionError(f"non-standard JSON literal in the .pgp: {literal}")
        json.loads(pe.save_patch(new).decode("utf-8"), parse_constant=_reject)

    def test_ordinary_numbers_are_unaffected(self, amp_patch):
        new, results = apply(amp_patch, {"op": "set_tempo", "value": 92})
        assert only(results)["ok"]
        assert new["data"]["tone"]["global"]["@tempo"] == 92.0


class TestRangeClamping:
    """Out-of-range values would be rejected by the firmware, so clamp them to
    the device's own min/max from the official catalog."""

    def setup_method(self):
        self.schema = model_db.official_params("HD2_AmpUSDoubleNrm")

    def test_above_max_is_clamped_down(self, amp_patch):
        if not self.schema:
            pytest.skip("official_catalog.json not generated")
        hi = self.schema["Drive"]["max"]
        new, results = apply(amp_patch, {"op": "set_param", "block": "block0",
                                         "param": "Drive", "value": hi + 1000})
        assert only(results)["ok"]
        assert new["data"]["tone"]["dsp0"]["block0"]["Drive"] == hi

    def test_below_min_is_clamped_up(self, amp_patch):
        if not self.schema:
            pytest.skip("official_catalog.json not generated")
        lo = self.schema["Drive"]["min"]
        new, _ = apply(amp_patch, {"op": "set_param", "block": "block0",
                                   "param": "Drive", "value": lo - 1000})
        assert new["data"]["tone"]["dsp0"]["block0"]["Drive"] == lo

    def test_in_range_value_passes_through_untouched(self, amp_patch):
        if not self.schema:
            pytest.skip("official_catalog.json not generated")
        lo, hi = self.schema["Drive"]["min"], self.schema["Drive"]["max"]
        mid = (lo + hi) / 2
        new, _ = apply(amp_patch, {"op": "set_param", "block": "block0",
                                   "param": "Drive", "value": mid})
        assert new["data"]["tone"]["dsp0"]["block0"]["Drive"] == mid

    @pytest.mark.parametrize("schema", [None, {}, {"kind": "enum"}, {"kind": "float"}])
    def test_clamp_is_a_no_op_without_a_usable_schema(self, schema):
        assert pe._clamp_to_schema(9999.0, schema) == 9999.0

    def test_booleans_are_never_clamped_as_numbers(self):
        schema = {"kind": "float", "min": 0.0, "max": 1.0}
        assert pe._clamp_to_schema(True, schema) is True


# ─── set_enabled ─────────────────────────────────────────────────

class TestSetEnabled:
    def test_enables_a_bypassed_block(self, amp_patch):
        new, results = apply(amp_patch, {"op": "set_enabled", "block": "block2", "value": True})
        assert only(results)["ok"]
        assert new["data"]["tone"]["dsp0"]["block2"]["@enabled"] is True

    def test_bypasses_an_enabled_block(self, amp_patch):
        new, _ = apply(amp_patch, {"op": "set_enabled", "block": "block0", "value": False})
        assert new["data"]["tone"]["dsp0"]["block0"]["@enabled"] is False

    def test_unknown_block_is_rejected(self, amp_patch):
        _, results = apply(amp_patch, {"op": "set_enabled", "block": "nope", "value": True})
        assert not only(results)["ok"]


# ─── swap_model ──────────────────────────────────────────────────

class TestSwapModel:
    def test_same_category_swap_keeps_the_params(self, amp_patch):
        target = model_db.models_in_category("Amp")[0]
        new, results = apply(amp_patch, {"op": "swap_model", "block": "block0",
                                         "model_id": target})
        assert only(results)["ok"]
        block = new["data"]["tone"]["dsp0"]["block0"]
        assert block["@model"] == target
        assert "Drive" in block, "same-category swaps share knobs — keep the values"

    def test_amp_slot_refuses_a_reverb(self, amp_patch):
        _, results = apply(amp_patch, {"op": "swap_model", "block": "block0",
                                       "model_id": "HD2_ReverbSpring"})
        r = only(results)
        assert not r["ok"] and "Amp" in r["detail"] and "Reverb" in r["detail"]

    def test_cab_slot_refuses_a_drive(self, amp_patch):
        _, results = apply(amp_patch, {"op": "swap_model", "block": "block1",
                                       "model_id": "HD2_DistScream808"})
        assert not only(results)["ok"]

    def test_amp_slot_still_accepts_an_amp(self, amp_patch):
        _, results = apply(amp_patch, {"op": "swap_model", "block": "block0",
                                       "model_id": "HD2_AmpBritPlexi"})
        assert only(results)["ok"]

    def test_effect_slot_accepts_a_different_effect_category(self, amp_patch):
        """Drive → Reverb is legal; effect slots are interchangeable."""
        new, results = apply(amp_patch, {"op": "swap_model", "block": "block2",
                                         "model_id": "HD2_ReverbSpring"})
        assert only(results)["ok"]
        assert new["data"]["tone"]["dsp0"]["block2"]["@model"] == "HD2_ReverbSpring"

    def test_cross_category_swap_clears_the_old_knobs(self, amp_patch):
        """Drive knobs on a reverb block would corrupt it on the device."""
        new, _ = apply(amp_patch, {"op": "swap_model", "block": "block2",
                                   "model_id": "HD2_ReverbSpring"})
        assert "Tone" not in new["data"]["tone"]["dsp0"]["block2"]

    def test_cross_category_swap_repopulates_real_params(self, amp_patch):
        """A cleared block is useless to the agent, so refill it from the
        learned or official catalog when we have a schema for the model."""
        target = "HD2_ReverbSpringStereo"
        if not (model_db.official_params(target) or model_db.learned_params(target)):
            pytest.skip("no param schema available for the swap target")
        new, results = apply(amp_patch, {"op": "swap_model", "block": "block2",
                                         "model_id": target})
        block = new["data"]["tone"]["dsp0"]["block2"]
        knobs = [k for k in block if not k.startswith("@")]
        assert knobs, "a swapped-in effect must arrive with usable knobs"
        assert "Params filled in" in only(results)["detail"]

    def test_swap_to_a_model_with_no_schema_says_so_instead_of_guessing(self, amp_patch):
        """Better an empty block the agent is told to fill than invented knobs."""
        target = "HD2_ReverbSpring"
        if model_db.official_params(target) or model_db.learned_params(target):
            pytest.skip("this model now has a schema")
        _, results = apply(amp_patch, {"op": "swap_model", "block": "block2",
                                       "model_id": target})
        assert "Params cleared" in only(results)["detail"]

    def test_params_can_be_created_on_a_freshly_swapped_block(self, amp_patch):
        """After a cross-category swap the agent must be able to dial the new
        effect in, even though those param names weren't on the old block."""
        swapped, _ = apply(amp_patch, {"op": "swap_model", "block": "block2",
                                       "model_id": "HD2_ReverbSpringStereo"})
        new, results = apply(swapped, {"op": "set_param", "block": "block2",
                                       "param": "Mix", "value": 0.3})
        assert only(results)["ok"]
        assert new["data"]["tone"]["dsp0"]["block2"]["Mix"] == 0.3

    def test_hallucinated_id_falls_back_to_the_nearest_real_model(self, amp_patch):
        """Models invent plausible ids like HD2_AmpMarshallJCM800. Rather than
        dead-ending, find the closest real amp so the tone still lands."""
        new, results = apply(amp_patch, {"op": "swap_model", "block": "block0",
                                         "model_id": "HD2_AmpMarshallJCM800"})
        r = only(results)
        assert r["ok"] and "not in catalog" in r["detail"]
        swapped = new["data"]["tone"]["dsp0"]["block0"]["@model"]
        assert model_db.lookup(swapped)[0] == "Amp", "fallback stayed in category"
        assert swapped != "HD2_AmpMarshallJCM800"

    def test_fallback_uses_semantic_search_not_just_the_first_amp(self, amp_patch):
        """'JCM800' should reach the Brit 2204 (Marshall JCM-800), not a
        first-in-list default."""
        new, _ = apply(amp_patch, {"op": "swap_model", "block": "block0",
                                   "model_id": "HD2_AmpMarshallJCM800"})
        _cat, _name, real = model_db.lookup(new["data"]["tone"]["dsp0"]["block0"]["@model"])
        assert "Marshall" in real

    def test_unrecognisable_id_in_an_unknown_category_is_rejected(self, patch_factory):
        patch = patch_factory({"b": {"@model": "HD2_ReverbSpring", "@enabled": True,
                                     "@position": 0, "Mix": 0.2}})
        _, results = apply(patch, {"op": "swap_model", "block": "b",
                                   "model_id": "ZZZ_CompletelyUnparseable"})
        r = only(results)
        assert not r["ok"] and "CATALOG" in r["detail"]

    def test_unknown_block_is_rejected(self, amp_patch):
        _, results = apply(amp_patch, {"op": "swap_model", "block": "nope",
                                       "model_id": "HD2_AmpBritPlexi"})
        assert not only(results)["ok"]


# ─── Global ops ──────────────────────────────────────────────────

class TestGlobalOps:
    def test_set_tempo(self, amp_patch):
        new, results = apply(amp_patch, {"op": "set_tempo", "value": 92})
        assert only(results)["ok"]
        assert new["data"]["tone"]["global"]["@tempo"] == 92.0

    def test_set_tempo_rejects_a_word(self, amp_patch):
        _, results = apply(amp_patch, {"op": "set_tempo", "value": "brisk"})
        assert not only(results)["ok"]

    def test_rename(self, amp_patch):
        new, results = apply(amp_patch, {"op": "rename", "value": "Warm Cleans"})
        assert only(results)["ok"]
        assert new["data"]["meta"]["name"] == "Warm Cleans"

    def test_rename_truncates_to_the_device_limit(self, amp_patch):
        new, _ = apply(amp_patch, {"op": "rename", "value": "X" * 200})
        assert len(new["data"]["meta"]["name"]) == 32


# ─── Malformed ops ───────────────────────────────────────────────

class TestMalformedOps:
    @pytest.mark.parametrize("edit", [
        {"op": "delete_block", "block": "block0"},
        {"op": ""},
        {},
        {"block": "block0", "param": "Bass", "value": 1},
        {"op": "set_param"},
        {"op": "set_param", "block": "block0"},
        {"op": "set_enabled", "block": "block0"},
        {"op": "set_tempo"},
        {"op": "rename"},
        None,
    ])
    def test_every_malformed_op_is_rejected_without_raising(self, amp_patch, edit):
        before = copy.deepcopy(amp_patch)
        new, results = pe.apply_edits(amp_patch, [edit])
        assert not only(results)["ok"]
        assert new == before

    def test_an_empty_edit_list_is_a_no_op(self, amp_patch):
        new, results = pe.apply_edits(amp_patch, [])
        assert results == [] and new == amp_patch

    def test_a_single_bad_op_does_not_abort_the_rest_of_the_batch(self, amp_patch):
        new, results = pe.apply_edits(amp_patch, [
            {"op": "nonsense"},
            {"op": "rename", "value": "Survivor"},
        ])
        assert [r["ok"] for r in results] == [False, True]
        assert new["data"]["meta"]["name"] == "Survivor"

    def test_every_result_carries_the_edit_that_produced_it(self, amp_patch):
        edits = [{"op": "rename", "value": "A"}, {"op": "bogus"}]
        _, results = pe.apply_edits(amp_patch, edits)
        assert [r["edit"] for r in results] == edits
