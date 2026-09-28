"""HTTP surface, end to end through FastAPI with Ollama stubbed out."""
import json

import pytest
from fastapi.testclient import TestClient

import agent
import patch_engine as pe
import server


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(server, "SESSIONS", {})
    return TestClient(server.app)


@pytest.fixture
def stub_turn(monkeypatch):
    """Replace the whole agent turn — these tests are about the HTTP layer."""
    def _install(result=None, error=None):
        calls = []

        def _run_turn(patch, message, history=None, model=None, build_mode=False):
            calls.append({"message": message, "history": list(history or []),
                          "model": model, "build_mode": build_mode})
            if error:
                raise error
            out = dict(result or {"reply": "ok", "applied": [], "rejected": [],
                                  "retried": False})
            if "patch" not in out:
                out["patch"] = patch
            return out

        monkeypatch.setattr(server.agent, "run_turn", _run_turn)
        return calls
    return _install


def new_session(client):
    r = client.post("/api/new")
    assert r.status_code == 200
    return r.json()


class TestHealth:
    def test_reports_ok_and_the_default_model(self, client):
        body = client.get("/api/health").json()
        assert body["ok"] is True and body["default_model"] == agent.DEFAULT_MODEL


class TestIndex:
    def test_serves_the_ui(self, client):
        r = client.get("/")
        assert r.status_code == 200 and "<" in r.text


class TestNewSession:
    def test_returns_a_session_id_and_the_template_chain(self, client):
        body = new_session(client)
        assert body["session_id"]
        assert body["name"] == "New Preset"
        assert len(body["blocks"]) == 10
        assert body["tempo"] == 120

    def test_chain_text_is_ready_to_display(self, client):
        assert "Fender Twin Reverb" in new_session(client)["chain_text"]

    def test_each_call_is_an_independent_session(self, client):
        assert new_session(client)["session_id"] != new_session(client)["session_id"]

    def test_a_missing_template_is_a_500_not_a_traceback(self, client, monkeypatch):
        monkeypatch.setattr(server, "TEMPLATE_PATH", "/nonexistent/template.pgp")
        r = client.post("/api/new")
        assert r.status_code == 500 and "template" in r.json()["detail"].lower()


class TestUpload:
    def test_accepts_a_real_preset(self, client, template_bytes):
        r = client.post("/api/upload",
                        files={"file": ("mine.pgp", template_bytes, "application/octet-stream")})
        assert r.status_code == 200
        body = r.json()
        assert body["filename"] == "mine.pgp" and body["session_id"]
        assert len(body["blocks"]) == 10

    def test_rejects_a_non_preset_with_a_400(self, client):
        r = client.post("/api/upload",
                        files={"file": ("notes.txt", b"hello", "text/plain")})
        assert r.status_code == 400

    def test_a_setlist_gets_the_explanatory_error(self, client):
        r = client.post("/api/upload",
                        files={"file": ("band.pgs", b'{"data":{"setlist":[]}}', "application/json")})
        assert r.status_code == 400 and ".pgs" in r.json()["detail"]

    def test_reports_how_many_models_it_learned(self, client, template_bytes):
        body = client.post("/api/upload",
                           files={"file": ("mine.pgp", template_bytes, "")}).json()
        assert isinstance(body["learned"], int) and body["learned"] >= 0

    def test_a_learning_failure_never_blocks_the_upload(self, client, template_bytes,
                                                        monkeypatch):
        def _boom(patch):
            raise RuntimeError("disk on fire")
        monkeypatch.setattr(server.build_catalog, "learn_from_patch", _boom)
        r = client.post("/api/upload", files={"file": ("mine.pgp", template_bytes, "")})
        assert r.status_code == 200 and r.json()["learned"] == 0


class TestChat:
    def test_unknown_session_is_a_404(self, client, stub_turn):
        stub_turn()
        r = client.post("/api/chat", json={"session_id": "nope", "message": "hi"})
        assert r.status_code == 404

    def test_returns_the_reply_and_the_updated_chain(self, client, stub_turn,
                                                    template):
        edited, _ = pe.apply_edits(template, [{"op": "rename", "value": "Warm Cleans"}])
        stub_turn({"reply": "Renamed it.", "applied": ["name → Warm Cleans"],
                   "rejected": [], "retried": False, "patch": edited})
        sid = new_session(client)["session_id"]
        body = client.post("/api/chat", json={"session_id": sid, "message": "rename it"}).json()
        assert body["reply"] == "Renamed it."
        assert body["applied"] == ["name → Warm Cleans"]
        assert body["name"] == "Warm Cleans"

    def test_the_edited_patch_persists_into_the_next_turn(self, client, stub_turn,
                                                          template):
        edited, _ = pe.apply_edits(template, [{"op": "rename", "value": "Turn One"}])
        calls = stub_turn({"reply": "ok", "applied": ["x"], "rejected": [],
                           "retried": False, "patch": edited})
        sid = new_session(client)["session_id"]
        client.post("/api/chat", json={"session_id": sid, "message": "first"})
        client.post("/api/chat", json={"session_id": sid, "message": "second"})
        assert server.SESSIONS[sid]["patch"]["data"]["meta"]["name"] == "Turn One"
        assert len(calls) == 2

    def test_history_accumulates_as_user_assistant_pairs(self, client, stub_turn):
        calls = stub_turn({"reply": "done", "applied": [], "rejected": [],
                           "retried": False})
        sid = new_session(client)["session_id"]
        client.post("/api/chat", json={"session_id": sid, "message": "first"})
        client.post("/api/chat", json={"session_id": sid, "message": "second"})
        assert calls[1]["history"] == [{"role": "user", "content": "first"},
                                       {"role": "assistant", "content": "done"}]

    def test_history_is_capped_so_the_prompt_cannot_grow_without_bound(self, client,
                                                                      stub_turn):
        calls = stub_turn({"reply": "done", "applied": [], "rejected": [],
                           "retried": False})
        sid = new_session(client)["session_id"]
        for i in range(12):
            client.post("/api/chat", json={"session_id": sid, "message": f"turn {i}"})
        assert len(calls[-1]["history"]) <= 12
        assert len(server.SESSIONS[sid]["history"]) <= 12

    def test_the_requested_model_is_passed_through(self, client, stub_turn):
        calls = stub_turn()
        sid = new_session(client)["session_id"]
        client.post("/api/chat", json={"session_id": sid, "message": "hi",
                                       "model": "qwen2.5:7b-instruct"})
        assert calls[0]["model"] == "qwen2.5:7b-instruct"

    def test_it_falls_back_to_the_default_model(self, client, stub_turn):
        calls = stub_turn()
        sid = new_session(client)["session_id"]
        client.post("/api/chat", json={"session_id": sid, "message": "hi"})
        assert calls[0]["model"] == agent.DEFAULT_MODEL

    def test_a_dead_ollama_surfaces_as_503_not_500(self, client, stub_turn):
        stub_turn(error=RuntimeError("Couldn't reach Ollama at http://localhost:11434"))
        sid = new_session(client)["session_id"]
        r = client.post("/api/chat", json={"session_id": sid, "message": "hi"})
        assert r.status_code == 503 and "Ollama" in r.json()["detail"]

    def test_the_retried_flag_reaches_the_ui(self, client, stub_turn):
        stub_turn({"reply": "ok", "applied": [], "rejected": [], "retried": True})
        sid = new_session(client)["session_id"]
        assert client.post("/api/chat",
                           json={"session_id": sid, "message": "hi"}).json()["retried"] is True

    def test_a_malformed_body_is_a_422(self, client, stub_turn):
        stub_turn()
        assert client.post("/api/chat", json={"message": "no session"}).status_code == 422


class TestBuildChat:
    def test_build_mode_resets_the_canvas_and_the_history(self, client, stub_turn):
        calls = stub_turn({"reply": "ok", "applied": [], "rejected": [],
                           "retried": False})
        sid = new_session(client)["session_id"]
        client.post("/api/chat", json={"session_id": sid, "message": "first"})
        client.post("/api/chat", json={"session_id": sid, "message": "build me a tone",
                                       "build": True})
        assert calls[1]["build_mode"] is True
        assert calls[1]["history"] == [], "a build starts a fresh conversation"

    def test_an_uploaded_preset_becomes_the_build_base(self, client, stub_turn,
                                                       template_bytes):
        """Its model ids are device-verified, unlike the bundled template's."""
        stub_turn({"reply": "ok", "applied": [], "rejected": [], "retried": False})
        sid = client.post("/api/upload",
                          files={"file": ("mine.pgp", template_bytes, "")}).json()["session_id"]
        client.post("/api/chat", json={"session_id": sid, "message": "build",
                                       "build": True})
        assert server.SESSIONS[sid]["base_patch"] is not None

    def test_build_results_are_finalized_before_they_reach_the_ui(self, client,
                                                                  stub_turn, template):
        """What the chain pane shows has to be what the .pgp will contain."""
        canvas = pe.prepare_build_canvas(template)
        edited, _ = pe.apply_edits(canvas, [
            {"op": "swap_model", "block": "block4", "model_id": "HD2_AmpBritPlexi"}])
        stub_turn({"reply": "built", "applied": ["block4 model → Brit Plexi"],
                   "rejected": [], "retried": False, "patch": edited})
        sid = new_session(client)["session_id"]
        body = client.post("/api/chat", json={"session_id": sid, "message": "crunch",
                                              "build": True}).json()
        shown = {b["block"] for b in body["blocks"]}
        assert "block4" in shown
        assert "block8" not in shown, "a bypassed chorus should be stripped"

    def test_bypass_noise_is_hidden_from_the_build_transcript(self, client, stub_turn):
        stub_turn({"reply": "built",
                   "applied": ["block8 enabled True → False", "block4.Drive 0.4 → 0.7"],
                   "rejected": ["block9 enabled False → False"], "retried": False})
        sid = new_session(client)["session_id"]
        body = client.post("/api/chat", json={"session_id": sid, "message": "crunch",
                                              "build": True}).json()
        assert body["applied"] == ["block4.Drive 0.4 → 0.7"]
        assert body["rejected"] == []

    def test_a_missing_template_fails_the_build_with_a_500(self, client, stub_turn,
                                                          monkeypatch):
        stub_turn()
        sid = new_session(client)["session_id"]
        monkeypatch.setattr(server, "TEMPLATE_PATH", "/nonexistent/template.pgp")
        r = client.post("/api/chat", json={"session_id": sid, "message": "build",
                                          "build": True})
        assert r.status_code == 500 and "template" in r.json()["detail"].lower()

    def test_build_complete_is_only_set_when_something_was_applied(self, client,
                                                                    stub_turn):
        stub_turn({"reply": "which style?", "applied": [], "rejected": [],
                   "retried": False})
        sid = new_session(client)["session_id"]
        body = client.post("/api/chat", json={"session_id": sid, "message": "build",
                                              "build": True}).json()
        assert body["build_complete"] is False


class TestDownload:
    def test_returns_a_loadable_preset(self, client):
        sid = new_session(client)["session_id"]
        r = client.get(f"/api/download/{sid}")
        assert r.status_code == 200
        assert pe.load_patch(r.content)["data"]["meta"]["name"] == "New Preset"

    def test_filename_comes_from_the_preset_name(self, client, stub_turn, template):
        edited, _ = pe.apply_edits(template, [{"op": "rename", "value": "Warm Cleans"}])
        stub_turn({"reply": "ok", "applied": ["x"], "rejected": [], "retried": False,
                   "patch": edited})
        sid = new_session(client)["session_id"]
        client.post("/api/chat", json={"session_id": sid, "message": "rename"})
        r = client.get(f"/api/download/{sid}")
        assert 'filename="Warm Cleans.pgp"' in r.headers["content-disposition"]

    @pytest.mark.parametrize("name,expected", [
        ("Warm/Cleans", "WarmCleans.pgp"),
        ("../../etc/passwd", "etcpasswd.pgp"),
        ("!!!", "patch.pgp"),
        ("Lead: Solo #1", "Lead Solo 1.pgp"),
    ])
    def test_preset_names_are_sanitised_into_safe_filenames(self, client, stub_turn,
                                                            template, name, expected):
        edited, _ = pe.apply_edits(template, [{"op": "rename", "value": name}])
        stub_turn({"reply": "ok", "applied": ["x"], "rejected": [], "retried": False,
                   "patch": edited})
        sid = new_session(client)["session_id"]
        client.post("/api/chat", json={"session_id": sid, "message": "rename"})
        r = client.get(f"/api/download/{sid}")
        assert f'filename="{expected}"' in r.headers["content-disposition"]

    def test_unknown_session_is_a_404(self, client):
        assert client.get("/api/download/deadbeef").status_code == 404

    def test_the_download_matches_what_the_ui_last_showed(self, client, stub_turn,
                                                          template):
        canvas = pe.prepare_build_canvas(template)
        edited, _ = pe.apply_edits(canvas, [
            {"op": "swap_model", "block": "block4", "model_id": "HD2_AmpBritPlexi"}])
        stub_turn({"reply": "built", "applied": ["x"], "rejected": [],
                   "retried": False, "patch": edited})
        sid = new_session(client)["session_id"]
        shown = client.post("/api/chat", json={"session_id": sid, "message": "crunch",
                                               "build": True}).json()
        downloaded = pe.load_patch(client.get(f"/api/download/{sid}").content)
        assert {b["block"] for b in shown["blocks"]} == \
               {k for _d, k, _b in pe.iter_blocks(downloaded)}


class TestSessionIsolation:
    def test_edits_in_one_session_do_not_leak_into_another(self, client, stub_turn,
                                                            template):
        edited, _ = pe.apply_edits(template, [{"op": "rename", "value": "Session A"}])
        stub_turn({"reply": "ok", "applied": ["x"], "rejected": [], "retried": False,
                   "patch": edited})
        a = new_session(client)["session_id"]
        b = new_session(client)["session_id"]
        client.post("/api/chat", json={"session_id": a, "message": "rename"})
        assert pe.load_patch(client.get(f"/api/download/{b}").content) \
            ["data"]["meta"]["name"] == "New Preset"
