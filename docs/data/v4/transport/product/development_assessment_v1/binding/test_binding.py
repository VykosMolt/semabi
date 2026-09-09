from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

import binding


def operation(*, replacing=False, label="Visible editor value", name="value"):
    prop = {"type": "string", "description": label, "minLength": 1}
    props = {name: prop}
    if replacing:
        props["target"] = {**prop, "description": "Exact current local anchor: " + label}
    return {
        "id": "op_replace" if replacing else "op_create", "version": 1, "status": "ACTIVE",
        "kind": binding.REPLACE if replacing else binding.CREATE,
        "argument_schema": {"type": "object", "properties": props, "required": list(props),
                            "additionalProperties": False},
        "output_schema": {"type": "object"}, "procedure": {"opaque": "learned recipe"},
        "scope": {"operation_family": "local exact-value replacement" if replacing else "local form creation"},
        "support": {"evidence": "synthetic artifact"},
    }


def create(value="A fresh sentence.", *, key="content", entity="entry"):
    return f"Save a new {entity} with this exact {binding._key(key)['label']}: {value}", {key: value}


def replace(old="The complete old sentence.", new="The complete new sentence.",
            *, old_key="existing_content", new_key="replacement_content", entity="record"):
    label = binding._key(old_key)["label"]
    return (f'Replace the {entity} whose full {label} is "{old}" with "{new}".',
            {old_key: old, new_key: new})


def bind(request, ops=None):
    return binding.bind_request(*request, [operation()] if ops is None else ops)


def unsupported(result):
    assert result["status"] == "UNSUPPORTED"
    assert result["call"] is None
    assert result["goal_support"] == "GOAL_PLANNING_UNESTABLISHED"
    assert result["uncovered_clauses"]
    assert result["browser_started"] is False
    assert result["browser_actions"] == 0
    assert result["execution_result"] == "NOT_STARTED"


@pytest.mark.parametrize("key", ["content", "text", "body", "value", "new_content", "exact_content"])
def test_single_unnamed_payload_prior_and_exact_call(key):
    op = operation()
    result = bind(create(key=key), [op])
    assert result["status"] == "ELIGIBLE"
    assert result["call"] == {"operation": op, "arguments": {"value": "A fresh sentence."}}
    assert result["call"]["operation"] is not op
    assert result["mapping"][0]["basis"] == "sole_unnamed_text_payload_prior"
    result["call"]["operation"]["procedure"]["opaque"] = "changed"
    assert op["procedure"]["opaque"] == "learned recipe"


@pytest.mark.parametrize("old_key,new_key", [
    ("old_content", "new_content"), ("current_text", "replacement_text"),
    ("existing_body", "new_body"), ("exact_content", "new_content"),
    ("full_value", "replacement_value"), ("existing_exact_content", "replacement_content"),
])
def test_explicit_current_and_replacement_roles(old_key, new_key):
    result = bind(replace(old_key=old_key, new_key=new_key), [operation(replacing=True)])
    assert result["status"] == "ELIGIBLE"
    assert result["call"]["arguments"] == {"target": "The complete old sentence.",
                                         "value": "The complete new sentence."}
    assert {item["role"] for item in result["mapping"]} == {"current", "replacement"}


def test_named_label_normalization_and_value_case_are_distinct():
    goal, args = create("Keep THIS Case.", key="record_title")
    result = bind((goal.replace("record title", "Record-Title"), args),
                  [operation(label="Record Title", name="record_title")])
    assert result["status"] == "ELIGIBLE"
    assert result["call"]["arguments"] == {"record_title": "Keep THIS Case."}
    assert result["mapping"][0]["basis"] == "exact_normalized_learned_label"
    unsupported(bind((goal.lower(), args), [operation(label="Record Title", name="record_title")]))


def test_named_replacement_uses_label_and_current_anchor():
    result = bind(replace(old_key="current_title", new_key="new_title"),
                  [operation(replacing=True, label="Title", name="title")])
    assert result["status"] == "ELIGIBLE"
    assert set(result["call"]["arguments"]) == {"target", "title"}


@pytest.mark.parametrize("suffix", [
    " Then find it through its tag.", " Return the content and visible tags.",
    " Keep it private.", " Mark it unread.", " Mark it read.",
    " Ensure there are no other matching records.", " Search the entire account first.",
    " Keep its URL, tags, and unread state.", " And return an empty result if absent.",
])
def test_trailing_goal_clauses_cannot_be_dropped(suffix):
    goal, args = create()
    unsupported(bind((goal + suffix, args)))


@pytest.mark.parametrize("qualifier", [
    "private entry", "unread entry", "tagged entry", "first entry", "private-entry", "unread_entry",
])
def test_entity_qualifiers_are_outside_complete_grammar(qualifier):
    unsupported(bind(create(entity=qualifier)))


def test_instruction_words_inside_exact_payload_are_not_a_second_goal():
    text = 'Search for "green". Then mark it unread; keep #orchard.'
    result = bind(create(text))
    assert result["status"] == "ELIGIBLE"
    assert result["call"]["arguments"]["value"] == text


@pytest.mark.parametrize("extra", [
    {"unread": False}, {"tags": ["orchard"]}, {"search_scope": "all records"},
    {"output": "tags"}, {"additional_visible_content": "keeper"}, {"tag": "orchard"},
    {"another_content": "A fresh sentence."},
])
def test_extra_arguments_are_never_discarded(extra):
    goal, args = create()
    unsupported(bind((goal, {**args, **extra})))


@pytest.mark.parametrize("value", [True, False, ["one"], {"text": "one"}, 1, None])
def test_non_string_payloads_are_not_coerced(value):
    unsupported(bind(("Save a new entry with this exact content: one", {"content": value})))


@pytest.mark.parametrize("ordinary_request", [
    ("Search all entries for blue and return content.", {"content": "blue"}),
    ("Find the entry tagged blue and replace its content.", {"tag": "blue", "new_content": "fresh"}),
    ('Replace the entry containing "old" with "new".', {"old_content": "old", "new_content": "new"}),
    ("Save an entry with this exact content: one", {"content": "one"}),
    ("Please organize these records.", {"content": "one"}),
])
def test_unimplemented_planning_is_explicit(ordinary_request):
    unsupported(bind(ordinary_request, [operation(), operation(replacing=True)]))


def test_equal_old_and_new_values_do_not_create_a_positional_binding():
    unsupported(bind(replace("same", "same"), [operation(replacing=True)]))


@pytest.mark.parametrize("arguments", [
    {"content": "old", "value": "new"},
    {"new_content": "old", "existing_content": "new"},
    {"old_new_content": "old", "new_content": "new"},
    {"exact_content": "old", "full_content": "new"},
])
def test_missing_conflicting_or_reversed_key_roles_are_unestablished(arguments):
    goal = 'Replace the entry whose full content is "old" with "new".'
    unsupported(bind((goal, arguments), [operation(replacing=True)]))


def test_required_properties_cannot_be_defaulted_or_read_merged():
    op = operation()
    op["argument_schema"]["properties"]["tags"] = {"type": "string", "minLength": 1, "description": "Tags"}
    op["argument_schema"]["required"].append("tags")
    result = bind(create(), [op])
    unsupported(result)
    assert "complete required-property set" in result["candidate_rejections"][0]["reason"]


@pytest.mark.parametrize("change", [
    {"type": "boolean"}, {"type": "array"}, {"minLength": 100}, {"maxLength": 2},
    {"pattern": "^safe$"}, {"enum": ["safe"]}, {"default": "invented"}, {"format": "date"},
])
def test_schema_types_limits_and_unknown_constraints_fail_closed(change):
    op = operation()
    op["argument_schema"]["properties"]["value"].update(change)
    unsupported(bind(create(), [op]))


@pytest.mark.parametrize("value", ["", " padded", "two  spaces", "line\nbreak", "tab\tvalue"])
def test_arguments_are_preserved_or_rejected_never_normalized(value):
    unsupported(bind(create(value)))


@pytest.mark.parametrize("format_name,label,value,eligible", [
    ("uri", "URL", "https://example.invalid/item", True),
    ("uri", "URL", "https://example.invalid:8443/item", True),
    ("uri", "URL", "https://example.invalid:invalid/item", False),
    ("uri", "URL", "https:///missing-host", False),
    ("uri", "URL", "ftp://example.invalid/item", False),
    ("email", "Email", "person@example.invalid", True),
    ("email", "Email", "not-an-address", False),
])
def test_supported_formats_are_checked_without_conversion(format_name, label, value, eligible):
    op = operation(label=label, name=label.lower())
    op["argument_schema"]["properties"][label.lower()]["format"] = format_name
    result = bind(create(value, key=label.lower()), [op])
    if eligible:
        assert result["status"] == "ELIGIBLE"
        assert result["call"]["arguments"] == {label.lower(): value}
    else:
        unsupported(result)


def test_multiple_compatible_operations_are_ambiguous_in_any_order():
    first, second = operation(), operation()
    second["id"] = "another_operation"
    results = [bind(create(), ops) for ops in ([first, second], [second, first])]
    for result in results:
        unsupported(result)
        assert result["reasons"] == ["Multiple active learned operations are compatible."]
    assert results[0]["operation_catalog_sha256"] == results[1]["operation_catalog_sha256"]


def test_inactive_missing_and_wrong_scope_operations_do_not_qualify():
    for ops in ([], [{**operation(), "status": "STALE"}],
                [{**operation(), "scope": {"operation_family": "global update"}}],
                [operation(replacing=True)]):
        unsupported(bind(create(), ops))
    update = operation(replacing=True)
    update["scope"]["operation_family"] = "local record update"
    unsupported(bind(replace(), [update]))


def test_unknown_unnamed_payload_term_is_not_an_application_alias():
    unsupported(bind(create(key="message")))
    unsupported(bind(create(), [operation(label="Password", name="password")]))


def test_hashes_bind_the_exact_request_artifact_policy_and_source():
    request, op = create(), operation()
    before = deepcopy((request, op))
    result = bind(request, [op])
    assert result["request_sha256"] == binding.digest({"ordinary_goal": request[0], "arguments": request[1]})
    assert result["operation_sha256"] == binding.digest(op)
    assert result["policy_sha256"] == hashlib.sha256(Path(binding.__file__).with_name("policy.md").read_bytes()).hexdigest()
    assert result["binder_source_sha256"] == hashlib.sha256(Path(binding.__file__).read_bytes()).hexdigest()
    assert (request, op) == before
    assert result["browser_started"] is False
    assert result["execution_result"] == "NOT_STARTED"
    assert result["general_goal_planning"] == "UNESTABLISHED"
    assert result["coordinator_interventions"] == "NOT_ASSESSED"
    modified = deepcopy(op)
    modified["procedure"]["opaque"] = "different learned recipe"
    assert bind(request, [modified])["operation_sha256"] != result["operation_sha256"]
    assert bind(create("Different content."), [op])["request_sha256"] != result["request_sha256"]
