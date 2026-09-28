"""Snapshot cascade.

A POD Go preset stores up to 8 snapshots, each holding its own copy of block
bypass states and any parameter a footswitch controls. Editing the base patch
has to follow through into the snapshots that were in sync with the old value,
without flattening snapshots the player deliberately set differently.
"""
import patch_engine as pe


def snapshot(name="SNAPSHOT 1", valid=True, blocks=None, controllers=None):
    return {"@name": name, "@valid": valid, "@tempo": 120,
            "blocks": {"dsp0": blocks or {}},
            "controllers": {"dsp0": controllers or {}}}


def controlled(block, param, value):
    return {block: {param: {"@value": value}}}


class TestParamCascade:
    def test_a_snapshot_in_sync_follows_the_edit(self, patch_factory):
        patch = patch_factory(
            {"block0": {"@model": "HD2_AmpUSDoubleNrm", "@enabled": True,
                        "@position": 0, "Bass": 0.5}},
            snapshots={0: snapshot(controllers=controlled("block0", "Bass", 0.5))})
        new, _ = pe.apply_edits(patch, [{"op": "set_param", "block": "block0",
                                         "param": "Bass", "value": 0.8}])
        ctrl = new["data"]["tone"]["snapshot0"]["controllers"]["dsp0"]
        assert ctrl["block0"]["Bass"]["@value"] == 0.8

    def test_a_deliberately_different_snapshot_is_left_alone(self, patch_factory):
        """This is the whole point of the cascade being conditional — a lead
        snapshot set to a different value is an intentional choice."""
        patch = patch_factory(
            {"block0": {"@model": "HD2_AmpUSDoubleNrm", "@enabled": True,
                        "@position": 0, "Bass": 0.5}},
            snapshots={0: snapshot(controllers=controlled("block0", "Bass", 0.9))})
        new, _ = pe.apply_edits(patch, [{"op": "set_param", "block": "block0",
                                         "param": "Bass", "value": 0.8}])
        ctrl = new["data"]["tone"]["snapshot0"]["controllers"]["dsp0"]
        assert ctrl["block0"]["Bass"]["@value"] == 0.9

    def test_invalid_snapshots_are_skipped(self, patch_factory):
        patch = patch_factory(
            {"block0": {"@model": "HD2_AmpUSDoubleNrm", "@enabled": True,
                        "@position": 0, "Bass": 0.5}},
            snapshots={0: snapshot(valid=False,
                                   controllers=controlled("block0", "Bass", 0.5))})
        new, _ = pe.apply_edits(patch, [{"op": "set_param", "block": "block0",
                                         "param": "Bass", "value": 0.8}])
        ctrl = new["data"]["tone"]["snapshot0"]["controllers"]["dsp0"]
        assert ctrl["block0"]["Bass"]["@value"] == 0.5

    def test_cascade_reaches_every_valid_snapshot(self, patch_factory):
        snaps = {i: snapshot(f"SNAP {i}", True,
                             controllers=controlled("block0", "Bass", 0.5))
                 for i in range(8)}
        patch = patch_factory(
            {"block0": {"@model": "HD2_AmpUSDoubleNrm", "@enabled": True,
                        "@position": 0, "Bass": 0.5}}, snapshots=snaps)
        new, _ = pe.apply_edits(patch, [{"op": "set_param", "block": "block0",
                                         "param": "Bass", "value": 0.8}])
        values = [new["data"]["tone"][f"snapshot{i}"]["controllers"]["dsp0"]
                  ["block0"]["Bass"]["@value"] for i in range(8)]
        assert values == [0.8] * 8

    def test_params_the_snapshot_does_not_control_are_untouched(self, patch_factory):
        patch = patch_factory(
            {"block0": {"@model": "HD2_AmpUSDoubleNrm", "@enabled": True,
                        "@position": 0, "Bass": 0.5, "Treble": 0.5}},
            snapshots={0: snapshot(controllers=controlled("block0", "Bass", 0.5))})
        new, _ = pe.apply_edits(patch, [{"op": "set_param", "block": "block0",
                                         "param": "Treble", "value": 0.9}])
        ctrl = new["data"]["tone"]["snapshot0"]["controllers"]["dsp0"]["block0"]
        assert "Treble" not in ctrl and ctrl["Bass"]["@value"] == 0.5


class TestBypassCascade:
    def test_a_snapshot_matching_the_old_state_follows(self, patch_factory):
        patch = patch_factory(
            {"block2": {"@model": "HD2_DistTeemahMono", "@enabled": False,
                        "@position": 2, "Gain": 5.0}},
            snapshots={0: snapshot(blocks={"block2": False})})
        new, _ = pe.apply_edits(patch, [{"op": "set_enabled", "block": "block2",
                                         "value": True}])
        assert new["data"]["tone"]["snapshot0"]["blocks"]["dsp0"]["block2"] is True

    def test_a_snapshot_with_its_own_bypass_choice_is_preserved(self, patch_factory):
        patch = patch_factory(
            {"block2": {"@model": "HD2_DistTeemahMono", "@enabled": False,
                        "@position": 2, "Gain": 5.0}},
            snapshots={0: snapshot(blocks={"block2": True})})
        new, _ = pe.apply_edits(patch, [{"op": "set_enabled", "block": "block2",
                                         "value": True}])
        assert new["data"]["tone"]["snapshot0"]["blocks"]["dsp0"]["block2"] is True

    def test_invalid_snapshots_are_skipped(self, patch_factory):
        patch = patch_factory(
            {"block2": {"@model": "HD2_DistTeemahMono", "@enabled": False,
                        "@position": 2}},
            snapshots={0: snapshot(valid=False, blocks={"block2": False})})
        new, _ = pe.apply_edits(patch, [{"op": "set_enabled", "block": "block2",
                                         "value": True}])
        assert new["data"]["tone"]["snapshot0"]["blocks"]["dsp0"]["block2"] is False

    def test_the_real_template_cascades_correctly(self, template):
        """snapshot0 is the only valid snapshot in the bundled template and it
        has block0 bypassed, matching the base patch."""
        new, _ = pe.apply_edits(template, [{"op": "set_enabled", "block": "block0",
                                            "value": True}])
        tone = new["data"]["tone"]
        assert tone["snapshot0"]["blocks"]["dsp0"]["block0"] is True
        assert tone["snapshot1"]["blocks"]["dsp0"]["block0"] is False, "invalid snapshot"
