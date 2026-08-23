from semabi.compiler.browser import Primitive
from semabi.compiler.observation import Node, Observation
from semabi.eval.v1_browser_replay import resolve_target


def test_replay_relocates_unique_semantic_target_when_index_moved():
    obs = Observation([
        Node(0, -1, "document", ""),
        Node(1, 0, "text", "new decoration"),
        Node(2, 0, "button", "Apply"),
    ])
    historical = Primitive("click", 1, target_desc={"role": "button", "name": "Apply", "placeholder": None})

    replayed, note = resolve_target(obs, historical)

    assert replayed.target == 2
    assert "relocated" in note
    assert historical.target == 1
