"""Adversarial tests for latent control families.

The action alphabet used to identify a control by a per-instance role ordinal inside a
run-local entity type, which merged structurally different controls and split renderings
of one control.  These tests pin the replacement policy at its failure boundaries: a
false merge fabricates lifted semantics, a false split only fragments support, so the
policy must require agreement on structure, on the latent entity the control belongs to,
and on values before two occurrences may share a family.
"""
from types import SimpleNamespace

from semabi.compiler.v2 import controls


class _Node(SimpleNamespace):
    pass


def _node(i, role, parent, name="", options=(), placeholder=None):
    return _Node(i=i, role=role, parent=parent, name=name, options=list(options),
                 placeholder=placeholder, value=None, checked=None)


class _Obs:
    def __init__(self, nodes):
        self.nodes = nodes
        self._by_i = {n.i: n for n in nodes}

    def node(self, i):
        return self._by_i[i]


class _H:
    """Just the surface the family inducer reads: unit roots, templates, paths, groups."""
    def __init__(self, units, tid_of_template):
        self._units = units            # sig -> [(root, template)]
        self.tid_of_template = tid_of_template

    def parse_units(self, sig):
        return [SimpleNamespace(root=root, template=t) for root, t in self._units[sig]]

    def _relpath(self, obs, root, i):
        parts = []
        x = i
        while x != root and x >= 0:
            parts.append(obs.node(x).role)
            x = obs.node(x).parent
        return "/".join(reversed(parts)) or obs.node(i).role


def _induce(observations, units, tid_of_template, data=()):
    G = SimpleNamespace(obs=observations)
    return controls.induce(G, _H(units, tid_of_template), set(data))


def _card(base, template_root_role="group", combobox_options=(), extra_depth=True):
    """A card: root, a wrapper, and a combobox inside the wrapper."""
    root = _node(base, template_root_role, -1)
    wrapper = _node(base + 1, "text" if extra_depth else template_root_role, base)
    box = _node(base + 2, "combobox", base + 1, options=combobox_options)
    return [root, wrapper, box]


def test_two_controls_at_different_paths_are_never_one_family():
    """The climbing collision: a grade selector under `group/` and a wall selector under
    `text/` shared one symbol because both were the first combobox of their instance."""
    grade = _Obs([_node(0, "group", -1), _node(1, "group", 0),
                  _node(2, "combobox", 1, options=["pink", "yellow"])])
    wall = _Obs([_node(0, "group", -1), _node(1, "text", 0),
                 _node(2, "combobox", 1, options=["Cave 0 of 2", "Moon 1 of 2"])])
    families = _induce(
        {"a": grade, "b": wall},
        {"a": [(0, "wall-card")], "b": [(0, "route-card")]},
        {"wall-card": 0, "route-card": 0},      # even merged into one entity type
    )

    assert families.of("a", 2) != families.of("b", 2)
    assert {families.families[f].path for f in families.families} == {"group/combobox", "text/combobox"}


def test_template_variants_of_one_card_share_a_family():
    """A card rendered with and without an extra line is one card; splitting it would only
    fragment support."""
    plain = _Obs(_card(0, combobox_options=["pink", "yellow"]))
    lead = _Obs(_card(0, combobox_options=["yellow", "black"]))
    families = _induce(
        {"a": plain, "b": lead},
        {"a": [(0, "card-plain")], "b": [(0, "card-lead")]},
        {"card-plain": 3, "card-lead": 3},
    )

    assert families.of("a", 2) == families.of("b", 2)
    assert families.families[families.of("a", 2)].templates == frozenset({"card-plain", "card-lead"})


def test_disjoint_option_vocabularies_split_a_shared_path():
    """The datacenter collision: two selectors at the same path in one entity, offering
    values with nothing in common, are different controls."""
    blades = _Obs(_card(0, combobox_options=["blade-02", "blade-04"]))
    pools = _Obs(_card(0, combobox_options=["D1", "D3"]))
    families = _induce(
        {"a": blades, "b": pools},
        {"a": [(0, "panel-ticket")], "b": [(0, "panel-pool")]},
        {"panel-ticket": 5, "panel-pool": 5},
    )

    assert families.of("a", 2) != families.of("b", 2)


def test_templates_the_entity_layer_keeps_apart_are_not_merged():
    """`button[Hang on _]` and a route-name mention are both unlabelled buttons at path
    `button`; only the entity grouping distinguishes them."""
    action = _Obs([_node(0, "button", -1, name="Hang on Cave")])
    mention = _Obs([_node(0, "button", -1, name="R1")])
    families = _induce(
        {"a": action, "b": mention},
        {"a": [(0, "button[Hang on _]")], "b": [(0, "button[_]")]},
        {"button[Hang on _]": 0, "button[_]": 1},
        data=("cave", "r1"),
    )

    assert families.of("a", 0) != families.of("b", 0)


def test_a_control_outside_every_unit_keeps_its_existing_identity():
    """View/navigation controls are untouched: they are not part of any recurring unit."""
    obs = _Obs([_node(0, "group", -1), _node(1, "button", 0, name="Walls")])
    families = _induce({"a": obs}, {"a": []}, {})

    assert families.of("a", 1) is None
    assert families.families == {}


def test_family_ids_do_not_depend_on_observation_order_or_hash_seed():
    a = _Obs(_card(0, combobox_options=["pink"]))
    b = _Obs(_card(0, combobox_options=["yellow"]))
    forward = _induce({"a": a, "b": b}, {"a": [(0, "t1")], "b": [(0, "t2")]}, {"t1": 1, "t2": 1})
    backward = _induce({"b": b, "a": a}, {"b": [(0, "t2")], "a": [(0, "t1")]}, {"t2": 1, "t1": 1})

    assert sorted(forward.families) == sorted(backward.families)
    assert forward.of("a", 2) == backward.of("a", 2)


def test_family_ids_are_run_local_and_are_aligned_across_runs_by_descriptor():
    """A run that never rendered one variant needs no disambiguating suffix, so the two
    runs give the same family different names.  Cross-run comparison must therefore match
    descriptors and overlapping templates, never the run-local string -- the same rule the
    validator already applies to entity type ids."""
    from semabi.compiler.v2.validation import family_compatibility

    blades = _Obs(_card(0, combobox_options=["blade-02"]))
    pools = _Obs(_card(0, combobox_options=["D1"]))
    both = _induce({"a": blades, "b": pools}, {"a": [(0, "p1")], "b": [(0, "p2")]},
                   {"p1": 5, "p2": 5})
    only_pools = _induce({"b": pools}, {"b": [(0, "p2")]}, {"p2": 5})
    assert both.of("b", 2) != only_pools.of("b", 2)

    compatible = family_compatibility(both, only_pools)
    assert compatible(both.of("b", 2), only_pools.of("b", 2))
    # the other family of the split must not align with it: no shared template
    assert not compatible(both.of("a", 2), only_pools.of("b", 2))


def test_alignment_needs_a_shared_template_not_just_a_matching_descriptor():
    from semabi.compiler.v2.validation import family_compatibility

    here = _induce({"a": _Obs(_card(0, combobox_options=["x"]))}, {"a": [(0, "t1")]}, {"t1": 1})
    there = _induce({"a": _Obs(_card(0, combobox_options=["x"]))}, {"a": [(0, "t9")]}, {"t9": 1})
    compatible = family_compatibility(here, there)

    # identical run-local names, but the two runs never rendered a common template
    assert here.of("a", 2) == there.of("a", 2)
    assert compatible(here.of("a", 2), there.of("a", 2))   # equal names are accepted as-is
    renamed = dict(there.families)
    renamed["other"] = renamed.pop(there.of("a", 2))
    other = controls.ControlFamilies(renamed, there.by_node)
    assert not family_compatibility(here, other)(here.of("a", 2), "other")


def test_the_same_control_rendered_in_another_view_is_one_family():
    """Two observations, same card template and same position: one control, whatever view
    the survey reached it through."""
    a = _Obs(_card(0, combobox_options=["pink"]))
    b = _Obs([_node(9, "group", -1), _node(10, "text", 9), _node(11, "combobox", 10, options=["pink"])])
    families = _induce({"a": a, "b": b}, {"a": [(0, "card")], "b": [(9, "card")]}, {"card": 2})

    assert families.of("a", 2) == families.of("b", 11)
    assert len(families.families) == 1


def test_one_family_covers_several_entity_bindings():
    """Family identity says which control; which entity it acts on is the locator's owner,
    not part of the control's identity."""
    two_cards = _Obs([
        _node(0, "group", -1), _node(1, "text", 0), _node(2, "combobox", 1, options=["pink"]),
        _node(3, "group", -1), _node(4, "text", 3), _node(5, "combobox", 4, options=["yellow"]),
    ])
    families = _induce({"a": two_cards}, {"a": [(0, "card"), (3, "card")]}, {"card": 2})

    assert families.of("a", 2) == families.of("a", 5)
