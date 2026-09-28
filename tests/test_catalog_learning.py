"""Learning real block definitions from the user's own presets.

Every upload teaches the agent known-good parameter sets for the models that
preset uses, so a later swap lands real values instead of guessed ones.
"""
import json

import build_catalog
import model_db


def block(model_id, **params):
    return dict({"@model": model_id, "@enabled": True, "@position": 0}, **params)


class TestLearnFromPatch:
    def test_learns_the_models_in_a_preset(self, patch_factory, monkeypatch):
        monkeypatch.setattr(model_db, "LEARNED_BLOCKS", {})
        patch = patch_factory({"b0": block("HD2_AmpBritPlexi", Drive=0.6, Bass=0.5)})
        assert build_catalog.learn_from_patch(patch) == 1
        assert model_db.learned_params("HD2_AmpBritPlexi") == {"Drive": 0.6, "Bass": 0.5}

    def test_position_is_not_learned(self, patch_factory, monkeypatch):
        """Position is where this player put it, not part of the model's identity."""
        monkeypatch.setattr(model_db, "LEARNED_BLOCKS", {})
        build_catalog.learn_from_patch(
            patch_factory({"b0": block("HD2_AmpBritPlexi", Drive=0.6)}))
        assert "@position" not in model_db.LEARNED_BLOCKS["HD2_AmpBritPlexi"]

    def test_counts_only_models_it_had_not_seen(self, patch_factory, monkeypatch):
        monkeypatch.setattr(model_db, "LEARNED_BLOCKS", {})
        patch = patch_factory({"b0": block("HD2_AmpBritPlexi", Drive=0.6)})
        assert build_catalog.learn_from_patch(patch) == 1
        assert build_catalog.learn_from_patch(patch) == 0

    def test_a_second_upload_adds_without_forgetting_the_first(self, patch_factory,
                                                               monkeypatch):
        monkeypatch.setattr(model_db, "LEARNED_BLOCKS", {})
        build_catalog.learn_from_patch(
            patch_factory({"b0": block("HD2_AmpBritPlexi", Drive=0.6)}))
        build_catalog.learn_from_patch(
            patch_factory({"b0": block("HD2_ReverbSpringStereo", Mix=0.3)}))
        assert set(model_db.LEARNED_BLOCKS) == {"HD2_AmpBritPlexi", "HD2_ReverbSpringStereo"}

    def test_a_newer_preset_refreshes_the_stored_values(self, patch_factory,
                                                        monkeypatch):
        monkeypatch.setattr(model_db, "LEARNED_BLOCKS", {})
        build_catalog.learn_from_patch(
            patch_factory({"b0": block("HD2_AmpBritPlexi", Drive=0.6)}))
        build_catalog.learn_from_patch(
            patch_factory({"b0": block("HD2_AmpBritPlexi", Drive=0.9)}))
        assert model_db.learned_params("HD2_AmpBritPlexi")["Drive"] == 0.9

    def test_routing_infrastructure_is_not_learned(self, patch_factory, monkeypatch):
        monkeypatch.setattr(model_db, "LEARNED_BLOCKS", {})
        build_catalog.learn_from_patch(patch_factory({}))
        assert model_db.LEARNED_BLOCKS == {}

    def test_learning_the_real_template_picks_up_its_whole_chain(self, template,
                                                                 monkeypatch):
        monkeypatch.setattr(model_db, "LEARNED_BLOCKS", {})
        assert build_catalog.learn_from_patch(template) == 10

    def test_nothing_is_written_when_nothing_changed(self, patch_factory, monkeypatch):
        monkeypatch.setattr(model_db, "LEARNED_BLOCKS", {})
        writes = []
        monkeypatch.setattr(model_db, "save_learned_blocks",
                            lambda b: writes.append(b))
        patch = patch_factory({"b0": block("HD2_AmpBritPlexi", Drive=0.6)})
        build_catalog.learn_from_patch(patch)
        monkeypatch.setattr(model_db, "LEARNED_BLOCKS",
                            {"HD2_AmpBritPlexi": {"@model": "HD2_AmpBritPlexi",
                                                  "@enabled": True, "Drive": 0.6}})
        build_catalog.learn_from_patch(patch)
        assert len(writes) == 1, "an unchanged upload should not rewrite the file"


class TestPersistence:
    def test_saved_blocks_are_readable_json(self, tmp_path, monkeypatch):
        path = tmp_path / "learned.json"
        monkeypatch.setattr(model_db, "_LEARNED_BLOCKS_PATH", str(path))
        model_db.save_learned_blocks({"HD2_X": {"@model": "HD2_X", "Gain": 0.5}})
        assert json.loads(path.read_text())["HD2_X"]["Gain"] == 0.5

    def test_saving_swaps_the_live_catalog_in_without_a_restart(self, tmp_path,
                                                                monkeypatch):
        monkeypatch.setattr(model_db, "_LEARNED_BLOCKS_PATH",
                            str(tmp_path / "learned.json"))
        model_db.save_learned_blocks({"HD2_X": {"@model": "HD2_X", "Gain": 0.5}})
        assert model_db.learned_params("HD2_X") == {"Gain": 0.5}


class TestLearnedParamsFeedSwaps:
    def test_a_swap_uses_what_was_learned_from_the_users_own_preset(self,
                                                                    patch_factory,
                                                                    monkeypatch):
        """The point of the whole learning loop: swapped-in models arrive with
        values that came off a real device, not from the model's imagination."""
        import patch_engine as pe
        monkeypatch.setattr(model_db, "LEARNED_BLOCKS", {})
        build_catalog.learn_from_patch(
            patch_factory({"b0": block("HD2_ReverbSpringStereo", Mix=0.42, Decay=2.5)}))
        patch = patch_factory({"b0": block("HD2_DistTeemahMono", Gain=5.0)})
        new, results = pe.apply_edits(patch, [{"op": "swap_model", "block": "b0",
                                               "model_id": "HD2_ReverbSpringStereo"}])
        assert results[0]["ok"] and "learned catalog" in results[0]["detail"]
        assert new["data"]["tone"]["dsp0"]["b0"]["Mix"] == 0.42
