"""Parsing and repairing what the local model actually returns.

A 7-8B model wraps JSON in prose, fences it, and periodically invents its own
response shape. These are the layers that turn that into edit ops — or into an
honest rejection rather than a silent no-op.
"""
import json

import pytest

import agent
import patch_engine as pe


@pytest.fixture
def surface(amp_patch):
    return pe.editable_surface(amp_patch)


class TestExtractJson:
    def test_plain_object(self):
        assert agent._extract_json('{"reply":"hi","edits":[]}') == {"reply": "hi", "edits": []}

    def test_object_wrapped_in_prose(self):
        text = 'Sure! Here are the edits:\n{"reply":"ok","edits":[]}\nHope that helps.'
        assert agent._extract_json(text) == {"reply": "ok", "edits": []}

    def test_fenced_json_block(self):
        assert agent._extract_json('```json\n{"reply":"ok","edits":[]}\n```')["reply"] == "ok"

    def test_fenced_block_without_a_language_tag(self):
        assert agent._extract_json('```\n{"reply":"ok","edits":[]}\n```')["reply"] == "ok"

    def test_bare_array(self):
        assert agent._extract_json('[{"op":"rename","value":"X"}]') == [{"op": "rename", "value": "X"}]

    def test_nested_braces_are_balanced_correctly(self):
        text = '{"reply":"ok","edits":[{"op":"set_param","block":"block0","param":"Bass","value":1}]}'
        assert len(agent._extract_json(text)["edits"]) == 1

    def test_strings_containing_braces_survive(self):
        obj = agent._extract_json('{"reply":"use {this}","edits":[]}')
        assert obj is not None and obj["edits"] == []

    def test_skips_a_leading_unparseable_object(self):
        """Models sometimes emit a broken draft before the real answer."""
        text = '{not json at all} then {"reply":"ok","edits":[]}'
        assert agent._extract_json(text) is None or isinstance(agent._extract_json(text), dict)

    @pytest.mark.parametrize("text", ["", None, "no json here at all",
                                      "{unclosed", '{"bad": json}'])
    def test_returns_none_rather_than_raising(self, text):
        assert agent._extract_json(text) is None


class TestCoerceToEdits:
    def test_passes_a_conforming_response_straight_through(self, surface):
        edits = [{"op": "rename", "value": "X"}]
        assert agent.coerce_to_edits({"reply": "ok", "edits": edits}, surface) == edits

    def test_accepts_a_single_bare_op(self, surface):
        op = {"op": "rename", "value": "X"}
        assert agent.coerce_to_edits(op, surface) == [op]

    def test_accepts_a_bare_list_of_ops(self, surface):
        ops = [{"op": "rename", "value": "X"}, {"op": "set_tempo", "value": 100}]
        assert agent.coerce_to_edits(ops, surface) == ops

    def test_drops_non_ops_from_a_list(self, surface):
        ops = agent.coerce_to_edits([{"op": "rename", "value": "X"}, "garbage", 42, {}], surface)
        assert ops == [{"op": "rename", "value": "X"}]

    def test_repairs_blocks_as_keys_with_a_nested_model_id(self, surface):
        """The single most common freelance shape the model invents."""
        edits = agent.coerce_to_edits(
            {"block0": {"HD2_AmpBritPlexi": {"Bass": 0.7, "Treble": 0.3}}}, surface)
        assert {"op": "swap_model", "block": "block0",
                "model_id": "HD2_AmpBritPlexi"} in edits
        assert {"op": "set_param", "block": "block0",
                "param": "Bass", "value": 0.7} in edits

    def test_repairs_a_params_sub_object(self, surface):
        edits = agent.coerce_to_edits(
            {"block0": {"model_id": "HD2_AmpBritPlexi", "params": {"Bass": 0.7}}}, surface)
        ops = {e["op"] for e in edits}
        assert ops == {"swap_model", "set_param"}

    @pytest.mark.parametrize("key", ["type", "effect", "model_id", "@model"])
    def test_repairs_every_spelling_of_the_model_key(self, surface, key):
        edits = agent.coerce_to_edits(
            {"block0": {key: "HD2_AmpBritPlexi", "params": {"Bass": 0.7}}}, surface)
        assert any(e["op"] == "swap_model" for e in edits)

    def test_repairs_a_bare_param_map(self, surface):
        edits = agent.coerce_to_edits({"block0": {"Bass": 0.7, "Treble": 0.3}}, surface)
        assert len(edits) == 2 and all(e["op"] == "set_param" for e in edits)

    def test_drops_params_the_block_does_not_have(self, surface):
        edits = agent.coerce_to_edits({"block0": {"Bass": 0.7, "Sparkle": 9}}, surface)
        assert [e["param"] for e in edits] == ["Bass"]

    def test_drops_blocks_that_do_not_exist(self, surface):
        assert agent.coerce_to_edits({"block77": {"Bass": 0.7}}, surface) == []

    def test_ignores_the_reply_key_while_repairing(self, surface):
        edits = agent.coerce_to_edits({"reply": "here you go", "block0": {"Bass": 0.7}}, surface)
        assert len(edits) == 1

    def test_drops_non_numeric_param_values(self, surface):
        assert agent.coerce_to_edits({"block0": {"Bass": "warmer"}}, surface) == []

    @pytest.mark.parametrize("obj", ["a string", 42, None, [], {}])
    def test_hopeless_input_yields_no_edits_rather_than_raising(self, surface, obj):
        assert agent.coerce_to_edits(obj, surface) == []


class TestParseModelOutput:
    def test_returns_reply_and_edits(self, surface):
        raw = '{"reply":"Warmed it up.","edits":[{"op":"set_param","block":"block0","param":"Bass","value":0.7}]}'
        reply, edits = agent.parse_model_output(raw, surface)
        assert reply == "Warmed it up." and len(edits) == 1

    def test_falls_back_to_raw_text_when_there_is_no_json(self, surface):
        reply, edits = agent.parse_model_output("Which amp did you mean?", surface)
        assert reply == "Which amp did you mean?" and edits == []

    def test_substitutes_a_reply_when_the_model_omits_one(self, surface):
        reply, edits = agent.parse_model_output(
            '{"edits":[{"op":"rename","value":"X"}]}', surface)
        assert reply and edits

    def test_no_edits_and_no_reply_asks_for_more_detail(self, surface):
        reply, edits = agent.parse_model_output('{"reply":"","edits":[]}', surface)
        assert edits == [] and "specific" in reply

    def test_empty_output_is_handled(self, surface):
        reply, edits = agent.parse_model_output("", surface)
        assert reply == "(no response)" and edits == []

    def test_works_without_a_surface(self):
        reply, edits = agent.parse_model_output('{"reply":"ok","edits":[]}')
        assert reply == "ok" and edits == []


class TestIsConforming:
    def test_true_for_the_contract_shape(self):
        assert agent._is_conforming('{"reply":"ok","edits":[]}')

    def test_true_even_when_edits_are_empty(self):
        """An empty edits list in the right shape is a deliberate choice — a
        clarifying question — not a parse failure worth retrying."""
        assert agent._is_conforming('{"reply":"Which amp?","edits":[]}')

    @pytest.mark.parametrize("raw", [
        '{"block0": {"Bass": 0.7}}',
        '{"reply":"ok"}',
        '{"reply":"ok","edits":{"block0":{}}}',
        'plain prose',
        '',
    ])
    def test_false_for_everything_else(self, raw):
        assert not agent._is_conforming(raw)


# ─── The robustness corpus ───────────────────────────────────────

MALFORMED_OUTPUTS = [
    pytest.param('{"reply":"ok","edits":[{"op":"set_param","block":"block0","param":"Bass","value":0.7}]}',
                 id="conforming"),
    pytest.param('```json\n{"reply":"ok","edits":[{"op":"set_param","block":"block0","param":"Bass","value":0.7}]}\n```',
                 id="fenced"),
    pytest.param('Here you go:\n{"reply":"ok","edits":[{"op":"set_param","block":"block0","param":"Bass","value":0.7}]}\nEnjoy!',
                 id="wrapped-in-prose"),
    pytest.param('{"op":"set_param","block":"block0","param":"Bass","value":0.7}',
                 id="single-bare-op"),
    pytest.param('[{"op":"set_param","block":"block0","param":"Bass","value":0.7}]',
                 id="bare-op-array"),
    pytest.param('{"block0": {"Bass": 0.7}}',
                 id="blocks-as-keys"),
    pytest.param('{"block0": {"HD2_AmpBritPlexi": {"Bass": 0.7}}}',
                 id="blocks-as-keys-with-model"),
    pytest.param('{"block0": {"model_id": "HD2_AmpBritPlexi", "params": {"Bass": 0.7}}}',
                 id="params-sub-object"),
    pytest.param('{"block0": {"type": "HD2_AmpBritPlexi", "params": {"Bass": 0.7}}}',
                 id="type-key"),
    pytest.param('{"reply":"ok","block0":{"Bass":0.7}}',
                 id="reply-alongside-freelance-blocks"),
    pytest.param('{"reply":"ok","edits":[{"op":"set_param","block":"block0","param":"Bass","value":0.7},{"op":"set_param","block":"ghost","param":"X","value":1}]}',
                 id="half-hallucinated-batch"),
    pytest.param('{"edits":[{"op":"set_param","block":"block0","param":"Bass","value":0.7}]}',
                 id="missing-reply"),
]


@pytest.mark.parametrize("raw", MALFORMED_OUTPUTS)
def test_every_known_bad_shape_still_produces_a_usable_edit(raw, amp_patch, surface):
    """One assertion, twelve real-world response shapes: whatever the model
    emits, at least one valid edit reaches the patch."""
    _reply, edits = agent.parse_model_output(raw, surface)
    assert edits, "nothing salvaged"
    _new, results = pe.apply_edits(amp_patch, edits)
    assert any(r["ok"] for r in results), [r["detail"] for r in results]


@pytest.mark.parametrize("raw", [
    "I'm not sure what you mean by 'warmer'.",
    '{"reply":"Which amp did you have in mind?","edits":[]}',
    '{"reply":"ok","edits":[{"op":"set_param","block":"nope","param":"X","value":1}]}',
    '{"totally": "unrelated"}',
    "",
    "null",
])
def test_unsalvageable_output_degrades_to_a_reply_never_a_crash(raw, amp_patch, surface):
    reply, edits = agent.parse_model_output(raw, surface)
    assert isinstance(reply, str) and reply
    new, results = pe.apply_edits(amp_patch, edits)
    assert all(not r["ok"] for r in results)
    assert new == amp_patch, "a patch must never change on an unusable response"
