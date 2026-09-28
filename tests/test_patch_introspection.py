"""Introspection — what the preset looks like to the UI and to the LLM prompt."""
import pytest

import patch_engine as pe


class TestIterBlocks:
    def test_skips_dsp_routing_infrastructure(self, template):
        keys = [k for _dsp, k, _b in pe.iter_blocks(template)]
        assert "input" not in keys and "output" not in keys

    def test_yields_every_real_block_in_the_template(self, template):
        keys = [k for _dsp, k, _b in pe.iter_blocks(template)]
        assert keys == [f"block{i}" for i in range(10)]

    def test_orders_by_signal_chain_position_not_dict_order(self, patch_factory):
        patch = patch_factory({
            "blockZ": {"@model": "HD2_ReverbSpring", "@enabled": True, "@position": 9},
            "blockA": {"@model": "HD2_AmpUSDoubleNrm", "@enabled": True, "@position": 1},
            "blockM": {"@model": "HD2_DistTeemahMono", "@enabled": True, "@position": 4},
        })
        assert [k for _d, k, _b in pe.iter_blocks(patch)] == ["blockA", "blockM", "blockZ"]

    def test_parallel_path_blocks_sort_after_the_main_path(self, patch_factory):
        patch = patch_factory({
            "par": {"@model": "HD2_ReverbSpring", "@enabled": True,
                    "@position": 0, "@path": 1},
            "main": {"@model": "HD2_AmpUSDoubleNrm", "@enabled": True,
                     "@position": 5, "@path": 0},
        })
        assert [k for _d, k, _b in pe.iter_blocks(patch)] == ["main", "par"]

    def test_empty_placeholder_slots_are_not_blocks(self, patch_factory):
        patch = patch_factory({"block0": {"@position": 0},
                               "block1": {"@model": "HD2_AmpUSDoubleNrm",
                                          "@enabled": True, "@position": 1}})
        assert [k for _d, k, _b in pe.iter_blocks(patch)] == ["block1"]

    def test_reads_dsp1_as_well_as_dsp0(self, template):
        patch = {"data": {"meta": {"name": "x"}, "tone": {
            "dsp0": {"a": {"@model": "HD2_AmpUSDoubleNrm", "@enabled": True, "@position": 0}},
            "dsp1": {"b": {"@model": "HD2_ReverbSpring", "@enabled": True, "@position": 0}},
        }}}
        assert [(d, k) for d, k, _b in pe.iter_blocks(patch)] == [("dsp0", "a"), ("dsp1", "b")]


class TestSummarize:
    def test_reports_name_and_tempo(self, template):
        s = pe.summarize(template)
        assert s["name"] == "New Preset" and s["tempo"] == 120

    def test_lists_only_valid_snapshots(self, template):
        assert pe.summarize(template)["snapshots"] == ["SNAPSHOT 1"]

    def test_resolves_model_ids_to_names_and_real_hardware(self, template):
        amp = next(b for b in pe.summarize(template)["blocks"] if b["category"] == "Amp")
        assert amp["name"] == "US Double Nrm"
        assert amp["based_on"] == "Fender Twin Reverb (Normal)"

    def test_exposes_bypass_state(self, template):
        blocks = {b["block"]: b for b in pe.summarize(template)["blocks"]}
        assert blocks["block4"]["enabled"] is True
        assert blocks["block0"]["enabled"] is False

    def test_params_exclude_meta_fields(self, template):
        amp = next(b for b in pe.summarize(template)["blocks"] if b["block"] == "block4")
        assert not any(k.startswith("@") for k in amp["params"])
        assert "Drive" in amp["params"]

    def test_survives_a_preset_with_no_meta(self):
        patch = {"data": {"tone": {"dsp0": {}}}}
        assert pe.summarize(patch)["name"] == "Untitled"


class TestRounding:
    """Float noise from the 32-bit device values wastes prompt tokens and
    confuses the model about the scale a knob runs on."""

    @pytest.mark.parametrize("raw,expected", [
        (0.44999998807907104, 0.45),
        (0.800000011920929, 0.8),
        (8000.000123, 8000.0),
        (0.0, 0.0),
        (-0.123456789, -0.1235),
    ])
    def test_floats_round_to_four_significant_figures(self, raw, expected):
        assert pe._round_param(raw) == pytest.approx(expected)

    @pytest.mark.parametrize("value", [5, True, False, "Hall", 0])
    def test_non_floats_pass_through_unchanged(self, value):
        assert pe._round_param(value) is value


class TestChainText:
    def test_one_line_per_block(self, template):
        assert len(pe.chain_text(template).splitlines()) == 10

    def test_marks_bypassed_blocks(self, template):
        lines = pe.chain_text(template).splitlines()
        assert "(bypassed)" in lines[0]
        assert "(bypassed)" not in lines[4]

    def test_shows_the_real_hardware_the_model_emulates(self, template):
        assert "Fender Twin Reverb" in pe.chain_text(template)

    def test_empty_chain_reads_as_empty(self, patch_factory):
        assert pe.chain_text(patch_factory({})) == "(empty signal chain)"


class TestEditableSurface:
    def test_keyed_by_the_block_ids_edits_use(self, template):
        surface = pe.editable_surface(template)
        assert set(surface) == {f"block{i}" for i in range(10)}

    def test_each_entry_carries_what_the_prompt_needs(self, template):
        entry = pe.editable_surface(template)["block4"]
        assert set(entry) == {"dsp", "model_id", "category", "name", "enabled", "params"}

    def test_params_match_the_block(self, template):
        assert pe.editable_surface(template)["block4"]["params"]["Master"] == 0.8
