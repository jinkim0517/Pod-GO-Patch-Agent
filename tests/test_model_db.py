"""The model catalog: id → (category, name, real hardware), and the fuzzy
search that turns a human phrase like "spring reverb" into a real model id."""
import pytest

import model_db


needs_official = pytest.mark.skipif(not model_db.OFFICIAL_MODELS,
                                    reason="official_catalog.json not generated")


class TestLookup:
    def test_curated_entries_carry_the_real_hardware(self, ):
        cat, name, real = model_db.lookup("HD2_AmpUSDoubleNrm")
        assert (cat, name) == ("Amp", "US Double Nrm")
        assert "Fender" in real

    @needs_official
    def test_falls_back_to_the_official_catalog(self):
        cat, name, real = model_db.lookup("HD2_ReverbSpringStereo")
        assert cat == "Reverb" and name and real == ""

    @pytest.mark.parametrize("model_id,category", [
        ("HD2_AmpMysteryBox", "Amp"),
        ("HD2_CabUnknownThing", "Cab"),
        ("HD2_DistSomething", "Drive"),
        ("HD2_DelayWhatever", "Delay"),
        ("HD2_ReverbNewOne", "Reverb"),
        ("HD2_CompressorNew", "Comp"),
        ("HD2_ChorusNew", "Mod"),
        ("HD2_FlangerNew", "Mod"),
        ("HD2_TremoloNew", "Mod"),
        ("HD2_WahNew", "Wah"),
        ("HD2_PitchNew", "Pitch"),
        ("HD2_GateNew", "Gate"),
        ("HD2_VolPanNew", "Utility"),
        ("HD2_FXLoopNew", "Utility"),
    ])
    def test_guesses_the_category_from_the_id_prefix(self, model_id, category):
        assert model_db.lookup(model_id)[0] == category

    @pytest.mark.parametrize("prefix", ["HD2_", "VIC_", "L6SPB_", "HDV_", ""])
    def test_handles_every_vendor_prefix(self, prefix):
        assert model_db.lookup(f"{prefix}ReverbSomething")[0] == "Reverb"

    def test_unrecognisable_ids_are_unknown_not_an_error(self):
        cat, name, real = model_db.lookup("ZZZ_Gibberish")
        assert cat == "Unknown" and name == "ZZZ_Gibberish" and real == ""

    @pytest.mark.parametrize("value", ["", None])
    def test_empty_input_is_handled(self, value):
        assert model_db.lookup(value)[0] == "Unknown"


class TestModelsInCategory:
    @pytest.mark.parametrize("category", ["Amp", "Cab", "Drive", "Delay", "Reverb", "Mod"])
    def test_core_categories_are_populated(self, category):
        assert model_db.models_in_category(category)

    def test_results_are_deduplicated(self):
        ids = model_db.models_in_category("Amp")
        assert len(ids) == len(set(ids))

    def test_curated_entries_come_first(self):
        """They carry the real-hardware mapping, so they're the better fallback
        target when the agent hallucinates an id."""
        first = model_db.models_in_category("Amp")[0]
        assert first in model_db.MODEL_DB

    def test_unknown_category_is_empty_not_an_error(self):
        assert model_db.models_in_category("Bagpipes") == []

    def test_every_returned_id_looks_up_to_that_category(self):
        for mid in model_db.models_in_category("Reverb"):
            assert model_db.lookup(mid)[0] == "Reverb"


class TestFindModel:
    @pytest.mark.parametrize("query,expect_category", [
        ("spring reverb", "Reverb"),
        ("tape echo", "Delay"),
        ("tube screamer", "Drive"),
        ("big muff fuzz", "Drive"),
        ("optical compressor", "Comp"),
        ("chorus", "Mod"),
        ("phaser", "Mod"),
        ("cry baby wah", "Wah"),
    ])
    def test_a_phrase_lands_in_the_right_block_category(self, query, expect_category):
        mid = model_db.find_model(query)
        assert mid, f"no match for {query!r}"
        assert model_db.lookup(mid)[0] == expect_category

    def test_matches_a_display_name_exactly(self):
        assert model_db.lookup(model_db.find_model("US Double Nrm"))[1] == "US Double Nrm"

    def test_matching_is_case_insensitive(self):
        assert model_db.find_model("us double nrm") == model_db.find_model("US DOUBLE NRM")

    def test_matches_on_the_real_hardware_name(self):
        """Players ask for "Marshall", not "Brit Plexi"."""
        _cat, _name, real = model_db.lookup(model_db.find_model("marshall plexi"))
        assert "Marshall" in real

    def test_short_substrings_do_not_create_false_matches(self):
        """'marshall' contains 'hall' — it must not land on the Hall reverb."""
        assert model_db.lookup(model_db.find_model("marshall"))[0] == "Amp"

    def test_category_words_beat_coincidental_name_overlap(self):
        assert model_db.lookup(model_db.find_model("plate reverb"))[0] == "Reverb"

    @pytest.mark.parametrize("query", ["", "   ", None, "!!", "a b"])
    def test_junk_queries_return_nothing_rather_than_a_wrong_answer(self, query):
        assert model_db.find_model(query) is None

    def test_no_match_returns_none(self):
        assert model_db.find_model("didgeridoo bagpipe accordion") is None


class TestParamSchemas:
    @needs_official
    def test_official_params_describe_range_and_default(self):
        drive = model_db.official_params("HD2_AmpUSDoubleNrm")["Drive"]
        assert {"min", "max", "default", "kind"} <= set(drive)
        assert drive["min"] <= drive["default"] <= drive["max"]

    def test_unknown_model_has_no_official_params(self):
        assert model_db.official_params("ZZZ_Nope") is None

    def test_learned_params_exclude_meta_fields(self):
        learned = next((model_db.learned_params(m) for m in model_db.LEARNED_BLOCKS
                        if model_db.learned_params(m)), None)
        if learned is None:
            pytest.skip("no learned blocks available")
        assert not any(k.startswith("@") for k in learned)

    def test_unknown_model_has_no_learned_params(self):
        assert model_db.learned_params("ZZZ_Nope") is None

    def test_a_meta_only_block_counts_as_nothing_learned(self, monkeypatch):
        monkeypatch.setitem(model_db.LEARNED_BLOCKS, "HD2_MetaOnly",
                            {"@model": "HD2_MetaOnly", "@enabled": True})
        assert model_db.learned_params("HD2_MetaOnly") is None


class TestCompactCatalog:
    def test_groups_by_category_heading(self):
        text = model_db.compact_catalog(["Amp", "Reverb"])
        assert "## Amp" in text and "## Reverb" in text

    def test_every_line_offers_a_usable_model_id(self):
        for line in model_db.compact_catalog(["Reverb"]).splitlines():
            if line.startswith("##"):
                continue
            mid = line.split("|")[0].strip()
            assert model_db.lookup(mid)[0] != "Unknown", f"{mid} is not resolvable"

    def test_omits_categories_with_nothing_to_offer(self):
        assert model_db.compact_catalog(["Bagpipes"]) == ""

    def test_defaults_to_every_category(self):
        text = model_db.compact_catalog()
        assert text.count("## ") == len([c for c in model_db.CATEGORIES
                                         if model_db.compact_catalog([c])])

    def test_learned_only_prefers_models_harvested_from_real_presets(self, monkeypatch):
        learned_amp = next((m for m in model_db.LEARNED_BLOCKS
                            if model_db.lookup(m)[0] == "Amp"), None)
        if not learned_amp:
            pytest.skip("no learned amps available")
        text = model_db.compact_catalog(["Amp"], learned_only=True)
        ids = [l.split("|")[0].strip() for l in text.splitlines() if not l.startswith("##")]
        assert all(i in model_db.LEARNED_BLOCKS for i in ids)

    def test_learned_only_never_empties_a_category(self, monkeypatch):
        """Build mode must not offer an empty catalog just because the user
        hasn't uploaded a preset with that effect type yet."""
        monkeypatch.setattr(model_db, "LEARNED_BLOCKS", {})
        assert model_db.compact_catalog(["Amp"], learned_only=True).strip()
