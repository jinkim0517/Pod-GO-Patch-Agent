"""build_catalog's bulk-scan CLI — pointed at a folder of the player's presets
to seed the learned-block library in one go."""
import json
import os

import pytest

import build_catalog
import model_db
import patch_engine as pe


@pytest.fixture
def preset_folder(tmp_path, template, patch_factory):
    (tmp_path / "one.pgp").write_bytes(pe.save_patch(template))
    custom = patch_factory({"b0": {"@model": "HD2_ReverbSpringStereo", "@enabled": True,
                                   "@position": 0, "Mix": 0.42, "Decay": 2.5}})
    (tmp_path / "two.pgp").write_bytes(pe.save_patch(custom))
    return tmp_path


@pytest.fixture
def in_tmp_cwd(tmp_path, monkeypatch):
    """scan() writes learned_blocks.json into the working directory."""
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.chdir(out)
    return out


class TestScan:
    def test_writes_a_learned_blocks_library(self, preset_folder, in_tmp_cwd, capsys):
        build_catalog.scan(str(preset_folder))
        library = json.loads((in_tmp_cwd / "learned_blocks.json").read_text())
        assert "HD2_AmpUSDoubleNrm" in library
        assert library["HD2_ReverbSpringStereo"]["Mix"] == 0.42

    def test_reports_what_it_found(self, preset_folder, in_tmp_cwd, capsys):
        build_catalog.scan(str(preset_folder))
        out = capsys.readouterr().out
        assert "Scanned 2 file(s)" in out
        assert "US Double Nrm" in out
        assert "learned_blocks.json" in out

    def test_flags_models_the_curated_catalog_has_never_seen(self, tmp_path,
                                                             patch_factory, in_tmp_cwd,
                                                             capsys):
        patch = patch_factory({"b0": {"@model": "HD2_AmpBrandNewInFirmware",
                                      "@enabled": True, "@position": 0, "Drive": 0.5}})
        (tmp_path / "new.pgp").write_bytes(pe.save_patch(patch))
        build_catalog.scan(str(tmp_path))
        assert "*NEW (not in catalog)*" in capsys.readouterr().out

    def test_a_corrupt_file_is_skipped_not_fatal(self, preset_folder, in_tmp_cwd,
                                                 capsys):
        (preset_folder / "broken.pgp").write_text("definitely not json")
        build_catalog.scan(str(preset_folder))
        out = capsys.readouterr().out
        assert "skip broken.pgp" in out
        assert "HD2_AmpUSDoubleNrm" in json.loads(
            (in_tmp_cwd / "learned_blocks.json").read_text())

    def test_an_empty_folder_says_so_and_writes_nothing(self, tmp_path, in_tmp_cwd,
                                                        capsys):
        empty = tmp_path / "empty"
        empty.mkdir()
        build_catalog.scan(str(empty))
        assert "No .pgp files" in capsys.readouterr().out
        assert not (in_tmp_cwd / "learned_blocks.json").exists()

    def test_json_presets_are_scanned_too(self, tmp_path, template, in_tmp_cwd):
        (tmp_path / "exported.json").write_bytes(pe.save_patch(template))
        build_catalog.scan(str(tmp_path))
        assert (in_tmp_cwd / "learned_blocks.json").exists()

    def test_position_is_stripped_so_blocks_are_reusable_anywhere(self, preset_folder,
                                                                   in_tmp_cwd):
        build_catalog.scan(str(preset_folder))
        library = json.loads((in_tmp_cwd / "learned_blocks.json").read_text())
        assert all("@position" not in b for b in library.values())
