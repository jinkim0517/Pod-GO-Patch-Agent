"""run_turn — one conversational turn, including the two retry paths.

Ollama is stubbed throughout (see the no_network rail in conftest), so these
run offline and deterministically.
"""
import json
import urllib.error

import pytest

import agent
import patch_engine as pe


def edit_response(reply="ok", edits=()):
    return {"reply": reply, "edits": list(edits)}


SET_BASS = {"op": "set_param", "block": "block0", "param": "Bass", "value": 0.7}


class TestHappyPath:
    def test_applies_the_edits_and_returns_the_new_patch(self, amp_patch, fake_ollama):
        fake_ollama(edit_response("Warmed it up.", [SET_BASS]))
        result = agent.run_turn(amp_patch, "warmer")
        assert result["reply"] == "Warmed it up."
        assert result["applied"] and not result["rejected"]
        assert result["patch"]["data"]["tone"]["dsp0"]["block0"]["Bass"] == 0.7

    def test_one_model_call_when_the_output_is_good(self, amp_patch, fake_ollama):
        fake = fake_ollama(edit_response("ok", [SET_BASS]))
        agent.run_turn(amp_patch, "warmer")
        assert fake.call_count == 1

    def test_does_not_flag_a_retry_it_did_not_need(self, amp_patch, fake_ollama):
        fake_ollama(edit_response("ok", [SET_BASS]))
        assert agent.run_turn(amp_patch, "warmer")["retried"] is False

    def test_rejections_are_reported_alongside_what_landed(self, amp_patch, fake_ollama):
        fake_ollama(edit_response("ok", [
            SET_BASS, {"op": "set_param", "block": "ghost", "param": "X", "value": 1}]))
        result = agent.run_turn(amp_patch, "warmer")
        assert len(result["applied"]) == 1 and len(result["rejected"]) == 1

    def test_the_original_patch_is_never_mutated(self, amp_patch, fake_ollama):
        fake_ollama(edit_response("ok", [SET_BASS]))
        agent.run_turn(amp_patch, "warmer")
        assert amp_patch["data"]["tone"]["dsp0"]["block0"]["Bass"] == 0.44


class TestClarifyingQuestions:
    def test_a_deliberate_empty_response_is_not_retried(self, amp_patch, fake_ollama):
        """Conforming shape + empty edits = the model asked a question. Retrying
        would burn a second local-model call for nothing."""
        fake = fake_ollama(edit_response("Which amp did you mean?", []))
        result = agent.run_turn(amp_patch, "make it better")
        assert fake.call_count == 1
        assert result["retried"] is False
        assert result["reply"] == "Which amp did you mean?"
        assert result["applied"] == [] and result["patch"] == amp_patch


class TestParseRetry:
    def test_unparseable_output_triggers_exactly_one_retry(self, amp_patch, fake_ollama):
        fake = fake_ollama("I'll make it warmer for you!", edit_response("ok", [SET_BASS]))
        result = agent.run_turn(amp_patch, "warmer")
        assert fake.call_count == 2
        assert result["retried"] is True
        assert result["applied"]

    def test_the_retry_shows_the_model_its_own_bad_output(self, amp_patch, fake_ollama):
        bad = "just some prose"
        fake = fake_ollama(bad, edit_response("ok", [SET_BASS]))
        agent.run_turn(amp_patch, "warmer")
        retry_msgs = fake.calls[1]
        assert retry_msgs[-2] == {"role": "assistant", "content": bad}
        assert "OUTPUT CONTRACT" in retry_msgs[-1]["content"]

    def test_it_gives_up_after_one_retry(self, amp_patch, fake_ollama):
        fake = fake_ollama("prose", "still prose")
        result = agent.run_turn(amp_patch, "warmer")
        assert fake.call_count == 2
        assert result["applied"] == [] and result["patch"] == amp_patch

    def test_a_failed_turn_still_returns_something_to_show_the_user(self, amp_patch,
                                                                   fake_ollama):
        fake_ollama("prose", "still prose")
        result = agent.run_turn(amp_patch, "warmer")
        assert result["reply"] and isinstance(result["reply"], str)


class TestRejectionRetry:
    def test_a_fully_rejected_batch_is_retried_with_the_reasons(self, amp_patch,
                                                                fake_ollama):
        """Parsing was fine; the decision was wrong. The model gets the specific
        rejection text rather than the user getting a dead end."""
        bad_swap = {"op": "swap_model", "block": "block0", "model_id": "HD2_ReverbSpring"}
        fake = fake_ollama(edit_response("swapping", [bad_swap]),
                           edit_response("fixed", [SET_BASS]))
        result = agent.run_turn(amp_patch, "add reverb")
        assert fake.call_count == 2
        feedback = fake.calls[1][-1]["content"]
        assert "Every edit was rejected" in feedback
        assert "won't replace a Amp block" in feedback
        assert result["applied"] and not result["rejected"]

    def test_a_partial_success_is_not_retried(self, amp_patch, fake_ollama):
        fake = fake_ollama(edit_response("ok", [
            SET_BASS, {"op": "set_param", "block": "ghost", "param": "X", "value": 1}]))
        agent.run_turn(amp_patch, "warmer")
        assert fake.call_count == 1

    def test_a_retry_that_also_fails_keeps_the_original_patch(self, amp_patch,
                                                              fake_ollama):
        bad = {"op": "swap_model", "block": "block0", "model_id": "HD2_ReverbSpring"}
        fake_ollama(edit_response("a", [bad]), edit_response("b", [bad]))
        result = agent.run_turn(amp_patch, "add reverb")
        assert result["applied"] == [] and result["rejected"]
        assert result["patch"] == amp_patch


class TestBuildMode:
    def test_the_build_preamble_names_every_free_effect_slot(self, template):
        canvas = pe.prepare_build_canvas(template)
        msgs = agent.build_messages(canvas, "warm blues tone", build_mode=True)
        prompt = msgs[-1]["content"]
        assert "TASK: Build a complete guitar tone" in prompt
        for bid in ("block0", "block2", "block7", "block8", "block9"):
            assert bid in prompt, f"{bid} was not offered to the agent"

    def test_edit_mode_gets_no_build_preamble(self, amp_patch):
        prompt = agent.build_messages(amp_patch, "warmer")[-1]["content"]
        assert "TASK: Build a complete guitar tone" not in prompt

    def test_a_successful_build_gets_an_auto_generated_name(self, template,
                                                            fake_ollama, monkeypatch):
        canvas = pe.prepare_build_canvas(template)
        fake_ollama(edit_response("built", [
            {"op": "set_param", "block": "block4", "param": "Drive", "value": 0.6}]))
        monkeypatch.setattr(agent, "_generate_preset_name", lambda *a, **k: "Blues Burner")
        result = agent.run_turn(canvas, "warm blues", build_mode=True)
        assert result["patch"]["data"]["meta"]["name"] == "Blues Burner"
        assert any("Blues Burner" in a for a in result["applied"])

    def test_a_naming_failure_does_not_lose_the_build(self, template, fake_ollama,
                                                      monkeypatch):
        canvas = pe.prepare_build_canvas(template)
        fake_ollama(edit_response("built", [
            {"op": "set_param", "block": "block4", "param": "Drive", "value": 0.6}]))
        monkeypatch.setattr(agent, "_generate_preset_name", lambda *a, **k: None)
        result = agent.run_turn(canvas, "warm blues", build_mode=True)
        assert result["applied"]
        assert result["patch"]["data"]["tone"]["dsp0"]["block4"]["Drive"] == 0.6

    def test_no_name_is_generated_when_nothing_was_applied(self, template, fake_ollama,
                                                           monkeypatch):
        called = []
        monkeypatch.setattr(agent, "_generate_preset_name",
                            lambda *a, **k: called.append(1) or "X")
        fake_ollama(edit_response("Which style?", []))
        agent.run_turn(pe.prepare_build_canvas(template), "hmm", build_mode=True)
        assert not called


class TestPromptConstruction:
    def test_lists_every_valid_block_id(self, template):
        prompt = agent.build_messages(template, "warmer")[-1]["content"]
        assert "VALID BLOCK IDS" in prompt
        for i in range(10):
            assert f"block{i}" in prompt

    def test_shows_current_values_so_the_model_matches_the_scale(self, template):
        prompt = agent.build_messages(template, "warmer")[-1]["content"]
        assert "Drive=0.45" in prompt

    def test_marks_bypassed_blocks(self, template):
        prompt = agent.build_messages(template, "warmer")[-1]["content"]
        assert "BYPASSED" in prompt and "ON" in prompt

    def test_the_catalog_rides_in_the_system_message(self, template):
        msgs = agent.build_messages(template, "warmer")
        assert msgs[0]["role"] == "system"
        assert "CATALOG (allowed swap_model ids)" in msgs[0]["content"]
        assert "## Amp" in msgs[0]["content"]

    def test_conversation_history_is_carried_between_system_and_request(self, template):
        history = [{"role": "user", "content": "more gain"},
                   {"role": "assistant", "content": "done"}]
        msgs = agent.build_messages(template, "now warmer", history=history)
        assert msgs[1:3] == history
        assert msgs[-1]["role"] == "user" and "now warmer" in msgs[-1]["content"]

    def test_a_block_with_no_knobs_says_so_rather_than_showing_nothing(self,
                                                                       patch_factory):
        patch = patch_factory({"b": {"@model": "HD2_AmpUSDoubleNrm", "@enabled": True,
                                     "@position": 0}})
        assert "(no editable params)" in agent.build_messages(patch, "x")[-1]["content"]


class TestOutputSchema:
    def test_only_the_five_real_ops_are_allowed(self):
        schema = agent._edits_schema()
        ops = schema["properties"]["edits"]["items"]["properties"]["op"]["enum"]
        assert set(ops) == {"set_param", "set_enabled", "swap_model", "set_tempo", "rename"}

    def test_reply_and_edits_are_both_required(self):
        assert set(agent._edits_schema()["required"]) == {"reply", "edits"}

    def test_the_schema_is_json_serialisable_for_the_ollama_payload(self):
        json.dumps(agent._edits_schema())


class TestCallOllama:
    def _stub_urlopen(self, monkeypatch, content=None, error=None, captured=None):
        class Resp:
            def __enter__(self_inner): return self_inner
            def __exit__(self_inner, *a): return False
            def read(self_inner):
                return json.dumps({"message": {"content": content}}).encode()

        def _urlopen(req, timeout=None):
            if captured is not None:
                captured.append(json.loads(req.data.decode()))
            if error:
                raise error
            return Resp()
        monkeypatch.setattr(agent.urllib.request, "urlopen", _urlopen)

    def test_returns_the_message_content(self, monkeypatch):
        self._stub_urlopen(monkeypatch, content='{"reply":"ok","edits":[]}')
        assert agent.call_ollama([], model="m") == '{"reply":"ok","edits":[]}'

    def test_sends_the_schema_and_a_context_window_big_enough_for_the_catalog(self,
                                                                             monkeypatch):
        sent = []
        self._stub_urlopen(monkeypatch, content="{}", captured=sent)
        agent.call_ollama([{"role": "user", "content": "hi"}], model="llama3.1:8b")
        payload = sent[0]
        assert payload["stream"] is False
        assert payload["format"] == agent._edits_schema()
        assert payload["options"]["num_ctx"] >= 16384

    def test_a_dead_ollama_becomes_an_actionable_error(self, monkeypatch):
        self._stub_urlopen(monkeypatch, error=urllib.error.URLError("refused"))
        with pytest.raises(RuntimeError) as exc:
            agent.call_ollama([], model="llama3.1:8b")
        message = str(exc.value)
        assert "ollama serve" in message and "ollama pull llama3.1:8b" in message


class TestGeneratePresetName:
    def _stub(self, monkeypatch, content):
        class Resp:
            def __enter__(self_inner): return self_inner
            def __exit__(self_inner, *a): return False
            def read(self_inner):
                return json.dumps({"message": {"content": content}}).encode()
        monkeypatch.setattr(agent.urllib.request, "urlopen", lambda *a, **k: Resp())

    def test_returns_the_name(self, monkeypatch):
        self._stub(monkeypatch, '{"name": "Classic Crunch"}')
        assert agent._generate_preset_name("crunchy rock") == "Classic Crunch"

    def test_truncates_to_the_device_limit(self, monkeypatch):
        self._stub(monkeypatch, json.dumps({"name": "N" * 100}))
        assert len(agent._generate_preset_name("x")) == 32

    @pytest.mark.parametrize("content", ['{"name": ""}', '{"name": "   "}',
                                         "not json", "", "{}"])
    def test_a_bad_naming_response_returns_none_rather_than_a_junk_name(self,
                                                                       monkeypatch,
                                                                       content):
        self._stub(monkeypatch, content)
        assert agent._generate_preset_name("x") is None

    def test_a_dead_ollama_returns_none_rather_than_failing_the_build(self, monkeypatch):
        def _boom(*a, **k):
            raise urllib.error.URLError("refused")
        monkeypatch.setattr(agent.urllib.request, "urlopen", _boom)
        assert agent._generate_preset_name("x") is None
