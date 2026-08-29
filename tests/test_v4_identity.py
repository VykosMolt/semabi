"""Identity readings must carry their own denominator.

The V3 failure was not that V2 picked a bad key by a small margin; it was that a value
which never told two instances apart could be accepted as an identity with a perfect
structural score.  These tests pin the distinction the V4 layer is built on: evidence that
is *absent* is not evidence that is *good*.
"""
from types import SimpleNamespace

from semabi.compiler.v4.identity import family_key, family_readings, readings_for


def _instance(sig, root, **slots):
    return SimpleNamespace(sig=sig, root=root, slots=dict(slots), slot_nodes={k: i for i, k in enumerate(slots)})


def _unit(template, instances, slot_names):
    slots = {name: SimpleNamespace(id=name, n=sum(1 for i in instances if name in i.slots))
             for name in slot_names}
    return SimpleNamespace(template=template, instances=instances, slots=slots)


def test_a_value_that_never_had_a_peer_to_separate_is_unsupported_not_perfect():
    # one instance per observation: the value is constant and nothing ever tested it
    unit = _unit("text[_](textbox[_])",
                 [_instance("s1", 0, label="Name"), _instance("s2", 0, label="Name"),
                  _instance("s3", 0, label="Name")],
                 ["label"])
    readings = readings_for(unit, reload_pairs=[])
    by_slot = {r.key_slot: r for r in readings}
    assert by_slot["label"].status == "UNSUPPORTED"
    assert by_slot["label"].evidence.discrimination is None
    # and with no evidence for it, claiming no identity ranks ahead of claiming one
    assert readings[0].key_slot is None


def test_a_value_that_separates_co_present_peers_is_supported():
    unit = _unit("row[_](cell[_])",
                 [_instance("s1", 1, name="Ada"), _instance("s1", 2, name="Grace"),
                  _instance("s1", 3, name="Alan"), _instance("s2", 1, name="Ada")],
                 ["name"])
    readings = readings_for(unit, reload_pairs=[])
    best = readings[0]
    assert best.key_slot == "name"
    assert best.status == "SUPPORTED"
    assert best.evidence.copresent_pairs == 3 and best.evidence.separated_pairs == 3


def test_a_value_shared_by_every_co_present_peer_is_contradicted():
    unit = _unit("row[_](cell[_])",
                 [_instance("s1", 1, status="open"), _instance("s1", 2, status="open"),
                  _instance("s1", 3, status="open"), _instance("s2", 1, status="shut")],
                 ["status"])
    by_slot = {r.key_slot: r for r in readings_for(unit, reload_pairs=[])}
    assert by_slot["status"].status == "CONTRADICTED"


def test_a_family_is_formed_without_the_tokens_that_split_it():
    a = "row[](cell[_],cell[Annual checkup],cell[_],cell[Dr _])"
    b = "row[](cell[_],cell[Follow-up visit],cell[_],cell[unassigned])"
    assert family_key(a) == family_key(b)
    # and structure still separates genuinely different shapes
    assert family_key(a) != family_key("row[](cell[_],cell[_](combobox[_]))")


def test_family_evidence_restores_the_pairs_that_splitting_hid():
    # apart, neither template ever shows a peer; together they are peers on the same page
    left = _unit("row[_](cell[Annual checkup])", [_instance("s1", 1, who="Ada")], ["who"])
    right = _unit("row[_](cell[Follow-up visit])", [_instance("s1", 2, who="Grace")], ["who"])
    assert readings_for(left, [])[0].key_slot is None
    merged = family_readings([left, right], reload_pairs=[])
    best = merged[0]
    assert best.key_slot == "who" and best.status == "SUPPORTED"
    assert best.evidence.copresent_pairs == 1 and best.evidence.separated_pairs == 1


def test_a_value_that_never_survives_a_reload_is_contradicted():
    unit = _unit("row[_](cell[_])",
                 [_instance("a", 1, v="x"), _instance("a", 2, v="y"),
                  _instance("b", 1, v="p"), _instance("b", 2, v="q")],
                 ["v"])
    by_slot = {r.key_slot: r for r in readings_for(unit, reload_pairs=[("a", "b")])}
    assert by_slot["v"].evidence.reload_stability == 0.0
    assert by_slot["v"].status == "CONTRADICTED"


def test_a_composite_keeps_its_single_components_proposable():
    # no single slot separates every co-present pair, so composites are proposed and rank
    # first; the singles must survive the cut, because a key can need coarsening too
    rows = [("Luna", "Maria", "Annual"), ("Luna", "Maria", "tp79"), ("Peanut", "Sana", "Annual"),
            ("Peanut", "Sana", "Follow-up"), ("Comet", "Ada", "Annual")]
    instances = [_instance("s1", i, a=a, b=b, c=c) for i, (a, b, c) in enumerate(rows)]
    instances += [_instance("s2", i, a=a, b=b, c=c) for i, (a, b, c) in enumerate(rows)]
    unit = _unit("row[_]", instances, ["a", "b", "c"])
    got = readings_for(unit, reload_pairs=[])
    keys = {r.key_slot for r in got}
    assert "a|c" in keys and "b|c" in keys                 # composites that separate
    assert {"a", "b", "c"} <= keys                          # and every component, single
