"""Shared fixtures.

Two safety rails are autouse, so no test can touch the network or the
developer's real learned_blocks.json no matter what it calls:

  * `no_network`  — any urllib request raises instead of dialing Ollama.
  * `isolate_learned_blocks` — learned-block writes land in a tmp file.
"""
import copy
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import agent            # noqa: E402
import model_db         # noqa: E402
import patch_engine as pe  # noqa: E402

TEMPLATE_PATH = os.path.join(ROOT, "template_newpreset.pgp")


# ─── Safety rails ────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Fail loudly if anything tries to reach Ollama for real."""
    def _blocked(*a, **k):
        raise AssertionError(
            "test attempted a real network call — stub agent.call_ollama instead")
    monkeypatch.setattr(agent.urllib.request, "urlopen", _blocked)


@pytest.fixture(autouse=True)
def isolate_learned_blocks(monkeypatch, tmp_path):
    """Keep learned-block persistence out of the real repo file."""
    monkeypatch.setattr(model_db, "_LEARNED_BLOCKS_PATH",
                        str(tmp_path / "learned_blocks.json"))
    monkeypatch.setattr(model_db, "LEARNED_BLOCKS",
                        copy.deepcopy(model_db.LEARNED_BLOCKS))


# ─── Patch fixtures ──────────────────────────────────────────────

@pytest.fixture
def template_bytes():
    with open(TEMPLATE_PATH, "rb") as f:
        return f.read()


@pytest.fixture
def template(template_bytes):
    """The real bundled POD Go preset — 10 blocks, 4 snapshots."""
    return pe.load_patch(template_bytes)


def make_patch(blocks=None, snapshots=None, name="Test Preset", tempo=120):
    """A minimal but structurally valid preset, for tests that want to control
    every block rather than inherit the template's ten."""
    dsp0 = {
        "input": {"@model": "P34_AppDSPFlowInput", "@input": 3},
        "output": {"@model": "P34_AppDSPFlowOutput", "@output": 1},
    }
    dsp0.update(blocks or {})
    tone = {
        "dsp0": dsp0,
        "dsp1": {},
        "global": {"@model": "@global_params", "@tempo": tempo},
    }
    for i in range(8):
        snap = (snapshots or {}).get(i)
        tone[f"snapshot{i}"] = snap if snap is not None else {
            "@name": f"SNAPSHOT {i + 1}", "@valid": False,
            "blocks": {"dsp0": {}}, "controllers": {"dsp0": {}},
        }
    return {"data": {"meta": {"name": name}, "tone": tone}, "schema": "L6Preset"}


@pytest.fixture
def patch_factory():
    return make_patch


@pytest.fixture
def amp_patch():
    """One amp, one cab, one bypassed drive — the smallest useful chain."""
    return make_patch({
        "block0": {"@model": "HD2_AmpUSDoubleNrm", "@enabled": True, "@position": 0,
                   "Drive": 0.45, "Bass": 0.44, "Treble": 0.5, "Master": 0.8},
        "block1": {"@model": "HD2_Cab2x12DoubleC12N", "@enabled": True, "@position": 1,
                   "Level": 0.0, "LowCut": 80.0, "HighCut": 8000.0},
        "block2": {"@model": "HD2_DistTeemahMono", "@enabled": False, "@position": 2,
                   "Gain": 5.0, "Tone": 5.0, "Level": 5.0},
    })


# ─── Fake Ollama ─────────────────────────────────────────────────

class FakeOllama:
    """Stands in for agent.call_ollama. Hands back canned responses in order
    and records every message list it was called with, so tests can assert on
    retry behaviour and prompt contents."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, messages, model=None, url=None, timeout=600):
        self.calls.append(messages)
        if not self.responses:
            raise AssertionError("FakeOllama ran out of canned responses")
        resp = self.responses.pop(0)
        return json.dumps(resp) if isinstance(resp, (dict, list)) else resp

    @property
    def call_count(self):
        return len(self.calls)


@pytest.fixture
def fake_ollama(monkeypatch):
    def _install(*responses):
        fake = FakeOllama(responses)
        monkeypatch.setattr(agent, "call_ollama", fake)
        return fake
    return _install
