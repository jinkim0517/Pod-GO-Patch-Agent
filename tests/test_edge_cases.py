"""Remaining edges: unusual preset structures and catalog configurations."""
import pytest

import model_db
import patch_engine as pe


class TestUnusualPresetStructures:
    @pytest.mark.parametrize("key", ["split", "join", "splitA", "splitB",
                                     "input0", "output0", "OUTPUT"])
    def test_routing_keys_are_never_treated_as_editable_blocks(self, patch_factory, key):
        patch = patch_factory({key: {"@model": "HD2_AmpUSDoubleNrm", "@enabled": True,
                                     "@position": 0}})
        assert list(pe.iter_blocks(patch)) == []

    def test_a_block_without_a_position_still_appears(self, patch_factory):
        patch = patch_factory({"b": {"@model": "HD2_AmpUSDoubleNrm", "@enabled": True}})
        assert [k for _d, k, _b in pe.iter_blocks(patch)] == ["b"]

    def test_non_dict_entries_in_the_dsp_are_ignored(self, patch_factory):
        patch = patch_factory({"stray": "not a block",
                               "b": {"@model": "HD2_AmpUSDoubleNrm", "@enabled": True,
                                     "@position": 0}})
        assert [k for _d, k, _b in pe.iter_blocks(patch)] == ["b"]

    def test_a_preset_with_no_dsp_at_all_summarises_empty(self):
        patch = {"data": {"meta": {"name": "Bare"}, "tone": {}}}
        summary = pe.summarize(patch)
        assert summary["blocks"] == [] and summary["name"] == "Bare"

    def test_an_edit_against_an_empty_preset_is_rejected_cleanly(self):
        patch = {"data": {"meta": {"name": "Bare"}, "tone": {}}}
        _new, results = pe.apply_edits(patch, [{"op": "set_param", "block": "block0",
                                                "param": "Bass", "value": 1}])
        assert not results[0]["ok"]

    def test_a_block_with_list_valued_fields_exposes_only_scalars(self, patch_factory):
        patch = patch_factory({"b": {"@model": "HD2_AmpUSDoubleNrm", "@enabled": True,
                                     "@position": 0, "Bass": 0.5,
                                     "Curve": [1, 2, 3], "Extra": {"nested": 1}}})
        assert set(pe.editable_surface(patch)["b"]["params"]) == {"Bass"}


class TestParamsOnUncataloguedModels:
    """Without a schema we can't validate names, so the rule is just: numeric
    values only, and the block has to exist."""

    @pytest.fixture
    def patch(self, patch_factory):
        return patch_factory({"b": {"@model": "HD2_AmpBrandNewInFirmware",
                                    "@enabled": True, "@position": 0}})

    def test_a_numeric_value_creates_the_param(self, patch):
        new, results = pe.apply_edits(patch, [{"op": "set_param", "block": "b",
                                               "param": "Wobble", "value": 3}])
        assert results[0]["ok"] and "(new)" in results[0]["detail"]
        assert new["data"]["tone"]["dsp0"]["b"]["Wobble"] == 3.0

    def test_a_boolean_value_creates_the_param(self, patch):
        new, results = pe.apply_edits(patch, [{"op": "set_param", "block": "b",
                                               "param": "Bright", "value": True}])
        assert results[0]["ok"]
        assert new["data"]["tone"]["dsp0"]["b"]["Bright"] is True

    def test_an_int_param_rejects_a_word(self, patch_factory):
        patch = patch_factory({"b": {"@model": "HD2_Unknown", "@enabled": True,
                                     "@position": 0, "Shape": 1}})
        _new, results = pe.apply_edits(patch, [{"op": "set_param", "block": "b",
                                                "param": "Shape", "value": "square"}])
        assert not results[0]["ok"]

    def test_a_string_param_passes_through_unchanged(self, patch_factory):
        patch = patch_factory({"b": {"@model": "HD2_Unknown", "@enabled": True,
                                     "@position": 0, "Label": "lead"}})
        new, results = pe.apply_edits(patch, [{"op": "set_param", "block": "b",
                                               "param": "Label", "value": "rhythm"}])
        assert results[0]["ok"]
        assert new["data"]["tone"]["dsp0"]["b"]["Label"] == "rhythm"


class TestCatalogWithoutTheOfficialFile:
    """official_catalog.json is generated from the POD Go Edit app and isn't
    committed, so a fresh clone runs without it. Everything must still work."""

    @pytest.fixture(autouse=True)
    def no_official_catalog(self, monkeypatch):
        monkeypatch.setattr(model_db, "OFFICIAL_MODELS", {})
        monkeypatch.setattr(model_db, "_OFFICIAL_BY_CATEGORY", {})

    def test_the_catalog_falls_back_to_the_verified_subset(self):
        text = model_db.compact_catalog(["Amp"])
        ids = [l.split("|")[0].strip() for l in text.splitlines() if not l.startswith("##")]
        assert ids and all(i in model_db.PODGO_VERIFIED for i in ids)

    def test_lookup_still_resolves_curated_models(self):
        assert model_db.lookup("HD2_AmpUSDoubleNrm")[1] == "US Double Nrm"

    def test_param_validation_degrades_to_accepting_existing_params(self, amp_patch):
        new, results = pe.apply_edits(amp_patch, [{"op": "set_param", "block": "block0",
                                                   "param": "Bass", "value": 0.9}])
        assert results[0]["ok"]
        assert new["data"]["tone"]["dsp0"]["block0"]["Bass"] == 0.9

    def test_values_are_no_longer_clamped_without_a_schema(self, amp_patch):
        new, results = pe.apply_edits(amp_patch, [{"op": "set_param", "block": "block0",
                                                   "param": "Bass", "value": 99.0}])
        assert results[0]["ok"]
        assert new["data"]["tone"]["dsp0"]["block0"]["Bass"] == 99.0

    def test_swaps_still_work(self, amp_patch):
        _new, results = pe.apply_edits(amp_patch, [{"op": "swap_model", "block": "block0",
                                                    "model_id": "HD2_AmpBritPlexi"}])
        assert results[0]["ok"]


class TestFinalizeEdges:
    def test_routing_blocks_survive_finalization(self, patch_factory):
        patch = patch_factory({"split": {"@model": "HD2_AmpUSDoubleNrm",
                                         "@enabled": False, "@position": 0}})
        finalized = pe.finalize_build_patch(patch)
        assert finalized["data"]["tone"]["dsp0"]["split"]["@model"] == "HD2_AmpUSDoubleNrm"

    def test_an_enabled_non_tone_effect_is_stripped(self, patch_factory):
        """A synth or filter block is template junk on a guitar preset — the
        agent never asked for it, so it doesn't ship in the download."""
        patch = patch_factory({"b": {"@model": "HD2_SynthSomething", "@enabled": True,
                                     "@position": 0}})
        assert pe.finalize_build_patch(patch)["data"]["tone"]["dsp0"]["b"] == {"@position": 0}


class TestBooleanCoercion:
    def test_a_non_string_value_becomes_a_bool(self, patch_factory):
        patch = patch_factory({"b": {"@model": "HD2_VolPanVolStereo", "@enabled": True,
                                     "@position": 0, "VolumeTaper": False}})
        new, results = pe.apply_edits(patch, [{"op": "set_param", "block": "b",
                                               "param": "VolumeTaper", "value": 1}])
        assert results[0]["ok"]
        assert new["data"]["tone"]["dsp0"]["b"]["VolumeTaper"] is True


class TestLearningEdges:
    def test_a_block_with_an_empty_model_id_is_not_learned(self, patch_factory,
                                                           monkeypatch):
        import build_catalog
        monkeypatch.setattr(model_db, "LEARNED_BLOCKS", {})
        patch = patch_factory({"b": {"@model": "", "@enabled": True, "@position": 0,
                                     "Gain": 0.5}})
        assert build_catalog.learn_from_patch(patch) == 0
        assert model_db.LEARNED_BLOCKS == {}
