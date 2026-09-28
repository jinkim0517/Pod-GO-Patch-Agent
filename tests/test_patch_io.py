"""Loading and saving .pgp files."""
import json

import pytest

import patch_engine as pe


class TestLoadPatch:
    def test_loads_the_bundled_template(self, template_bytes):
        patch = pe.load_patch(template_bytes)
        assert patch["schema"] == "L6Preset"
        assert patch["data"]["meta"]["name"] == "New Preset"

    def test_tolerates_utf8_bom(self, template_bytes):
        """POD Go Edit writes a BOM on some platforms."""
        patch = pe.load_patch(b"\xef\xbb\xbf" + template_bytes)
        assert patch["data"]["tone"]["dsp0"]["block4"]["@model"] == "HD2_AmpUSDoubleNrm"

    def test_accepts_a_string_as_well_as_bytes(self, template_bytes):
        assert pe.load_patch(template_bytes.decode("utf-8")) == pe.load_patch(template_bytes)

    def test_rejects_non_json(self):
        with pytest.raises(json.JSONDecodeError):
            pe.load_patch(b"this is not a preset")

    def test_rejects_json_without_a_tone(self):
        with pytest.raises(ValueError, match="POD Go/HX preset"):
            pe.load_patch(b'{"data": {"meta": {"name": "x"}}}')

    def test_rejects_json_without_data(self):
        with pytest.raises(ValueError, match="POD Go/HX preset"):
            pe.load_patch(b'{"tone": {}}')

    def test_setlist_mistake_gets_an_actionable_message(self):
        """Uploading a .pgs setlist is the most common user error — the error
        has to say what to do instead."""
        with pytest.raises(ValueError, match=r"\.pgs"):
            pe.load_patch(b'{"data": {"setlist": []}}')


class TestSavePatch:
    def test_round_trips_without_loss(self, template):
        assert pe.load_patch(pe.save_patch(template)) == template

    def test_output_is_utf8_bytes(self, template):
        data = pe.save_patch(template)
        assert isinstance(data, bytes)
        data.decode("utf-8")

    def test_round_trips_after_editing(self, template):
        edited, _ = pe.apply_edits(template, [
            {"op": "rename", "value": "Round Trip"},
            {"op": "set_param", "block": "block4", "param": "Bass", "value": 0.7},
        ])
        reloaded = pe.load_patch(pe.save_patch(edited))
        assert reloaded["data"]["meta"]["name"] == "Round Trip"
        assert reloaded["data"]["tone"]["dsp0"]["block4"]["Bass"] == 0.7

    def test_unicode_preset_names_survive(self, template):
        edited, _ = pe.apply_edits(template, [{"op": "rename", "value": "Café Tremolo"}])
        assert pe.load_patch(pe.save_patch(edited))["data"]["meta"]["name"] == "Café Tremolo"
