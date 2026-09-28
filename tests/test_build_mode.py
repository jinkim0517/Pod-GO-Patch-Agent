"""Build mode — filling a blank canvas, then stripping it back down.

prepare_build_canvas gives the agent a palette of bypassed effect slots;
finalize_build_patch throws away everything the agent didn't actively choose,
so the downloaded .pgp contains the tone and nothing else.
"""
import patch_engine as pe


def models_in(patch):
    return {k: b.get("@model") for _d, k, b in pe.iter_blocks(patch)}


class TestPrepareBuildCanvas:
    def test_fills_empty_placeholder_slots(self, patch_factory):
        patch = patch_factory({"block2": {"@position": 2}, "block9": {"@position": 9}})
        canvas = pe.prepare_build_canvas(patch)
        dsp0 = canvas["data"]["tone"]["dsp0"]
        assert dsp0["block2"]["@model"] == "HD2_DistScream808"
        assert dsp0["block9"]["@model"] == "HD2_ReverbHall"

    def test_filled_slots_arrive_bypassed(self, patch_factory):
        canvas = pe.prepare_build_canvas(patch_factory({"block9": {"@position": 9}}))
        assert canvas["data"]["tone"]["dsp0"]["block9"]["@enabled"] is False

    def test_filled_slots_arrive_with_knobs_to_set(self, patch_factory):
        canvas = pe.prepare_build_canvas(patch_factory({"block9": {"@position": 9}}))
        block = canvas["data"]["tone"]["dsp0"]["block9"]
        assert {"Decay", "Mix", "Predelay"} <= set(block)

    def test_never_overwrites_a_slot_that_already_has_a_model(self, template):
        canvas = pe.prepare_build_canvas(template)
        assert models_in(canvas) == models_in(template)

    def test_does_not_invent_slots_the_dsp_lacks(self, patch_factory):
        canvas = pe.prepare_build_canvas(patch_factory({"block2": {"@position": 2}}))
        assert "block9" not in canvas["data"]["tone"]["dsp0"]

    def test_leaves_the_input_patch_untouched(self, patch_factory):
        patch = patch_factory({"block2": {"@position": 2}})
        pe.prepare_build_canvas(patch)
        assert patch["data"]["tone"]["dsp0"]["block2"] == {"@position": 2}


class TestFinalizeBuildPatch:
    def test_strips_bypassed_blocks(self, patch_factory):
        patch = patch_factory({
            "block0": {"@model": "HD2_AmpUSDoubleNrm", "@enabled": True, "@position": 0},
            "block1": {"@model": "HD2_ReverbSpringStereo", "@enabled": False, "@position": 1},
        })
        assert list(models_in(pe.finalize_build_patch(patch))) == ["block0"]

    def test_stripped_slots_keep_their_position_placeholder(self, patch_factory):
        patch = patch_factory({"b": {"@model": "HD2_ReverbSpringStereo",
                                     "@enabled": False, "@position": 7}})
        assert pe.finalize_build_patch(patch)["data"]["tone"]["dsp0"]["b"] == {"@position": 7}

    def test_keeps_enabled_tone_blocks(self, patch_factory):
        patch = patch_factory({
            "a": {"@model": "HD2_AmpUSDoubleNrm", "@enabled": True, "@position": 0},
            "c": {"@model": "HD2_Cab2x12DoubleC12N", "@enabled": True, "@position": 1},
            "d": {"@model": "HD2_DistTeemahMono", "@enabled": True, "@position": 2},
        })
        assert set(models_in(pe.finalize_build_patch(patch))) == {"a", "c", "d"}

    def test_keeps_utility_blocks_the_device_requires(self, patch_factory):
        """VolPan and the FX loop are structural — the POD Go wants them in the
        chain whether or not they shape the tone."""
        patch = patch_factory({"v": {"@model": "HD2_VolPanVolStereo",
                                     "@enabled": True, "@position": 3}})
        assert "v" in models_in(pe.finalize_build_patch(patch))

    def test_strips_enabled_placeholders_the_agent_never_swapped(self, patch_factory):
        """A canvas default left enabled but never swapped means the agent
        forgot to choose a model — that's template junk, not a tone decision."""
        patch = patch_factory({"block9": {"@model": "HD2_ReverbHall", "@enabled": True,
                                          "@position": 9, "Decay": 0.5}})
        assert "block9" not in models_in(pe.finalize_build_patch(patch))

    def test_keeps_a_swapped_in_model_even_when_the_catalog_never_heard_of_it(self,
                                                                             patch_factory):
        """Never drop an amp just because our catalog is incomplete — but a
        genuinely unresolvable id has no place in a downloaded preset."""
        patch = patch_factory({"a": {"@model": "HD2_ReverbSpringStereo",
                                     "@enabled": True, "@position": 0}})
        assert "a" in models_in(pe.finalize_build_patch(patch))

    def test_strips_enabled_blocks_with_unresolvable_model_ids(self, patch_factory):
        patch = patch_factory({"a": {"@model": "HD2_AmpNotARealThing",
                                     "@enabled": True, "@position": 0}})
        assert "a" not in models_in(pe.finalize_build_patch(patch))

    def test_leaves_routing_infrastructure_alone(self, patch_factory):
        finalized = pe.finalize_build_patch(patch_factory({}))
        assert "@model" in finalized["data"]["tone"]["dsp0"]["input"]

    def test_leaves_the_input_patch_untouched(self, patch_factory):
        patch = patch_factory({"b": {"@model": "HD2_ReverbSpringStereo",
                                     "@enabled": False, "@position": 0}})
        pe.finalize_build_patch(patch)
        assert patch["data"]["tone"]["dsp0"]["b"]["@model"] == "HD2_ReverbSpringStereo"

    def test_finalizing_twice_changes_nothing_further(self, template):
        once = pe.finalize_build_patch(pe.prepare_build_canvas(template))
        assert pe.finalize_build_patch(once) == once

    def test_output_still_loads_as_a_valid_preset(self, template):
        finalized = pe.finalize_build_patch(pe.prepare_build_canvas(template))
        assert pe.load_patch(pe.save_patch(finalized)) == finalized


class TestFullBuildRound:
    def test_a_realistic_build_keeps_exactly_what_the_agent_enabled(self, template):
        """Canvas → agent edits → finalize, the path every build download takes."""
        canvas = pe.prepare_build_canvas(template)
        edited, results = pe.apply_edits(canvas, [
            {"op": "swap_model", "block": "block4", "model_id": "HD2_AmpBritPlexi"},
            {"op": "swap_model", "block": "block9", "model_id": "HD2_ReverbSpringStereo"},
            {"op": "set_enabled", "block": "block9", "value": True},
            {"op": "set_enabled", "block": "block8", "value": False},
            {"op": "rename", "value": "Plexi Spring"},
        ])
        assert all(r["ok"] for r in results), [r["detail"] for r in results if not r["ok"]]
        final = pe.finalize_build_patch(edited)
        kept = models_in(final)
        assert kept["block4"] == "HD2_AmpBritPlexi"
        assert kept["block9"] == "HD2_ReverbSpringStereo"
        assert "block8" not in kept, "bypassed chorus should be gone"
        assert final["data"]["meta"]["name"] == "Plexi Spring"
