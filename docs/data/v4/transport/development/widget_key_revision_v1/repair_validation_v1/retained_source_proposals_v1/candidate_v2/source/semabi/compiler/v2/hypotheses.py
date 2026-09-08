"""Entity-type hypotheses over recurring unit templates.

Deterministic proposers only (no LLM here):
  * a unit type is a recurring template whose instances carry *own* data tokens
    (tokens not inside a nested unit instance);
  * its key slot is the own slot whose values identify the instance (unique among
    co-present instances under the same parent, non-numeric, recurring over time);
  * two unit types with overlapping key values are the same entity type unless
    that identification is contradicted (one observation would then show one
    entity twice with different attribute values): then the second type is a
    *link* type keyed by (enclosing entity, own key) that references the first;
  * a non-key slot whose values are keys of another type is a reference slot;
  * a unit type nested in another entity type's instances has a containment
    relation to it.
Every decision is recorded with its evidence so that later counterexamples can
revise it.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from semabi.compiler.v2.graph import ObsGraph, node_text, tokens
from semabi.compiler.v2.units import UnitType, collapsed_template, find_unit_types

LEAF_DATA = {"text", "heading", "cell", "listitem", "alert", "status"}
WIDGET = {"button", "link", "checkbox", "radio", "combobox", "textbox"}


REGIONS = ("table", "group", "region", "article", "section", "listitem")


@dataclass
class UnitInstance:
    sig: str
    root: int
    template: str
    slots: dict[str, str]  # own data slot id -> value (first token occurrence)
    slot_nodes: dict[str, int]  # slot id -> node
    nested: list[int]  # roots of nested unit instances (direct)
    parent_root: int | None = None
    # the key did not name this instance: a sibling carried the same value, and the instance
    # was told apart by its position (`name#2`).  A reading whose key needs this has named
    # a position, which the objective charges (`semabi.compiler.v4.objective`).
    positional: bool = False


@dataclass
class SlotStat:
    id: str
    values: Counter = field(default_factory=Counter)
    n: int = 0
    unique_in_parent: int = 0
    crowded: int = 0  # instances whose value is shared by >= 2 siblings (3+ copies): not an identifier
    numeric: int = 0
    n_obs_values: Counter = field(default_factory=Counter)  # value -> observations seen in


@dataclass
class UnitHyp:
    template: str
    instances: list[UnitInstance] = field(default_factory=list)
    slots: dict[str, SlotStat] = field(default_factory=dict)
    key_slot: str | None = None
    key_score: float = 0.0
    max_per_obs: int = 0
    evidence: list[str] = field(default_factory=list)

    def key_values(self) -> set[str]:
        return set(self.slots[self.key_slot].values) if self.key_slot else set()

    def primary_key_values(self) -> set[str]:
        """Values of the first component of the key (the name part of a composite key)."""
        if not self.key_slot:
            return set()
        first = self.key_slot.split("|")[0]
        return set(self.slots[first].values)


@dataclass
class EntityType:
    tid: int
    units: list[str]  # unit templates realising this type
    key_slot: dict[str, str]  # template -> key slot id
    attr_slots: dict[str, set[str]] = field(default_factory=dict)  # template -> own non-key slot ids
    ref_slots: dict[tuple[str, str], int] = field(default_factory=dict)  # (template, slot) -> target tid
    link_parent: dict[str, int] = field(default_factory=dict)  # template -> enclosing tid that is part of the identity
    matrix: set[str] = field(default_factory=set)  # templates whose identity is (enclosing row, column); content is a reference
    contain: dict[str, int] = field(default_factory=dict)  # template -> enclosing entity tid (containment relation)
    evidence: list[str] = field(default_factory=list)


class Hypotheses:
    # A number may key a unit that no word identifies.  See `_choose_key`.
    numeric_keys_as_last_resort: bool = True

    def __init__(self, G: ObsGraph):
        self.G = G
        self.memo: dict = {}
        self.unit_types: dict[str, UnitType] = {}
        self.promoted: set[str] = set()  # V4: leaf templates on trial as objects
        self.units: dict[str, UnitHyp] = {}
        self.entity_types: dict[int, EntityType] = {}
        self.tid_of_template: dict[str, int] = {}
        self.allowed: set[str] | None = None  # unit templates with identity (after fitting)
        self.ctx_split: dict[tuple[str, str | None], str] = {}  # (template, enclosing template) -> split template
        self.transient: set[str] = set()
        self.transient_positions: set[tuple] = set()
        self.mirror_positions: set[tuple] = set()
        self.mirror_keys: set[str] = set()
        self.force_link: set[str] = set()  # refinement: templates whose link/merge decision is flipped
        # pairs of templates whose union by key overlap is withheld: a reading in which two
        # families that name the same values are two kinds of thing (an appointment row
        # names its patient; it is not the patient).  Proposed and judged by the V4 search.
        self.withheld_unions: set[frozenset[str]] = set()
        self._page_instances: dict[str, dict[int, UnitInstance]] = {}  # last parse of each page, by root
        self.alias_map: dict[tuple[str, str], str] = {}  # (template, key value) -> canonical key value (another template's)
        self.key_overrides: dict[tuple[str, str, str], str] = {}  # (observation, template, rendered key) -> associated key
        self.persistent_widgets: set[tuple[str, str]] = set()  # (template, slot) widget values shown to survive reloads
        self._reload_persistent_widgets: set[tuple[str, str]] = set()  # automatic claims, revocable under the current key
        self.slot_attachments: dict[tuple[str, str], str] = {}  # (source template, slot) -> sibling mention template
        self.contextual_identity: set[str] = set()  # mention templates keyed by (enclosing key, own key)
        self.mention_type_assignments: dict[tuple[str, str, str], str] = {}
        # (observation, source template, rendered key) -> target entity template.
        # These are accepted local data-association decisions, not global template merges.
        self.raw_mention_assignments: dict[tuple[str, int], tuple[str, str]] = {}
        # (observation, DOM node) -> (target entity template, associated entity key).
        self.raw_context_assignments: dict[tuple[str, int], tuple[str, str, str]] = {}
        # (observation, DOM node) -> (target entity template, entity key, rendered
        # heading/region context).  Populated only by a verified local intervention.
        self.record_splits: list[dict] = []
        self._split_done = False
        self.frozen = False

    # ------------------------------------------------------------- templates
    def template(self, sig: str, i: int) -> str:
        return collapsed_template(self.G, sig, i, self.memo)

    def is_unit_template(self, t: str, role: str, has_children: bool, header_cell: bool = False) -> bool:
        if role in ("combobox", "textbox") or t in self.transient:
            return False  # input widgets are slots of their enclosing unit, never units
        if t in self.promoted:
            return True   # V4: this leaf is being read as an object rather than as a value of
            # its container, on trial; whether it stays is decided behaviourally
        if not has_children and header_cell is False and role not in WIDGET:
            return False  # a childless text node is a slot of its enclosing unit (header cells of a
            # matrix, whose text varies, are mentions like buttons)
        if self.allowed is not None:
            return t in self.allowed
        return t in self.unit_types

    # ------------------------------------------------------------- instances
    def parse_units(self, sig: str) -> list[UnitInstance]:
        """Unit instances of one observation (all recurring templates; nested allowed)."""
        return self._parse_units(sig)

    def _parse_units(self, sig: str, *, raw_keys: bool = False) -> list[UnitInstance]:
        """The native parser, optionally retaining raw keys without replacing the page cache."""
        obs = self.G.obs[sig]
        insts: list[UnitInstance] = []
        by_root: dict[int, UnitInstance] = {}
        roots_on_path: list[int] = []
        # DFS with explicit stack keeping the chain of enclosing unit roots
        order = []
        stack = [(0, [])]
        while stack:
            i, chain = stack.pop()
            n = obs.node(i)
            t = self.template(sig, i)
            hdr = (sig, i) in self.G.header and not self.G.is_header(sig, i)
            is_unit = n.parent >= 0 and self.is_unit_template(t, n.role, bool(obs.children(i)), hdr) \
                and not self._property_list(obs, sig, i)
            if is_unit:
                parent_t = self.template(sig, chain[-1]) if chain else None
                ui = UnitInstance(sig, i, self.ctx_split.get((t, parent_t), t), {}, {}, [], chain[-1] if chain else None)
                insts.append(ui)
                by_root[i] = ui
                if chain:
                    by_root[chain[-1]].nested.append(i)
                chain = chain + [i]
            order.append((i, chain))
            for c in reversed(obs.children(i)):
                stack.append((c, chain))
        # own tokens: data tokens of nodes whose innermost enclosing unit is this instance
        skip: set[int] = set()
        if self.transient_positions:
            for n in obs.nodes:
                if n.i in skip:
                    continue
                if self._position(obs, n.i) in self.transient_positions:
                    skip.update(obs.subtree(n.i))
        for i, chain in order:
            if not chain or i in skip:
                continue
            owner = by_root[chain[-1]]
            toks = self.G.data_tokens(sig, i)
            if not toks:
                continue
            rel = self._relpath(obs, owner.root, i, sig)
            transient = obs.node(i).role in ("combobox", "textbox")
            prose = self.G.is_prose(sig, i)  # a sentence about entities: neither identity nor attribute
            for k, tok in enumerate(toks):
                base = f"{rel}#{k}"
                sid = base + ("~" if transient else ("!" if prose else ""))
                if transient and (owner.template, base) in self.persistent_widgets:
                    sid = base
                if sid in owner.slots:
                    base = f"{rel}#{k}@{i - owner.root}"
                    sid = base + ("~" if transient else "")
                    # Re-check after disambiguating repeated widget positions.  Previously
                    # only the first combobox in a unit could consume persistence evidence;
                    # later siblings silently regained the transient suffix.
                    if transient and (owner.template, base) in self.persistent_widgets:
                        sid = base
                owner.slots[sid] = tok
                owner.slot_nodes[sid] = i
        # a unit whose only persistent content is one nested mention (a cell holding a tape
        # button and a colour select) is that mention's frame: its slots belong to the mention
        for ui in list(insts):
            own_persistent = [k for k in ui.slots if not k.endswith("~")]
            if own_persistent or len(ui.nested) != 1:
                continue
            child = by_root.get(ui.nested[0])
            if child is None or not ui.slots:
                continue
            for k, v in ui.slots.items():
                nk = f"^{k}"
                if nk.endswith("~") and (child.template, nk[:-1]) in self.persistent_widgets:
                    nk = nk[:-1]
                child.slots[nk] = v
                child.slot_nodes[nk] = ui.slot_nodes[k]
            ui.slots = {}
        # Explicit, evidence-backed attachment refinements.  A widget initially belongs to
        # the enclosing recurring unit because that is the only safe structural default.
        # A refinement may instead attach it to the unique keyed mention sharing its local
        # parent (for example, a button mention paired with one value widget).  The rule is
        # relational and local; it does not name an application or layout family.
        for owner in list(insts):
            for sid in list(owner.slots):
                target_template = self.slot_attachments.get((owner.template, sid.rstrip("~")))
                if target_template is None:
                    continue
                node = owner.slot_nodes[sid]
                parent = obs.node(node).parent
                candidates = [ui for ui in insts if ui.template == target_template and obs.node(ui.root).parent == parent]
                if len(candidates) != 1:
                    continue
                target = candidates[0]
                attached = f"attached:{sid.rstrip('~')}"
                target.slots[attached] = owner.slots.pop(sid)
                target.slot_nodes[attached] = owner.slot_nodes.pop(sid)
        # column context: a cell's header (tables and matrices) is an own slot of the
        # innermost unit that owns the cell
        header_cache: dict[int, list[int] | None] = {}
        for i, chain in order:
            if not chain:
                continue
            n = obs.node(i)
            if n.role != "cell":
                continue
            row = n.parent
            if row < 0 or obs.node(row).role != "row":
                continue
            tbl = obs.node(row).parent
            while tbl >= 0 and obs.node(tbl).role not in ("table",):
                tbl = obs.node(tbl).parent
            if tbl < 0:
                continue
            if tbl not in header_cache:
                rows = sorted(x for x in obs.subtree(tbl) if obs.node(x).role == "row")
                header_cache[tbl] = obs.children(rows[0]) if rows else None
            hdr = header_cache[tbl]
            if not hdr or row == obs.node(hdr[0]).parent:
                continue
            k = obs.children(row).index(i)
            if k >= len(hdr):
                continue
            hn = obs.node(hdr[k])
            spans = self.G.data_tokens(sig, hdr[k])
            val = spans[0] if spans else (node_text(hn) or None)
            if not val:
                continue
            # the unit owning this cell: a unit rooted at or below the cell (matrix cells)
            owner = None
            for ui in insts:
                if ui.root == i or (ui.root in obs.subtree(i)):
                    owner = ui
                    break
            if owner is not None and "col" not in owner.slots:
                owner.slots["col"] = val
                owner.slot_nodes["col"] = i
        # composite keys decided during fitting
        for ui in insts:
            u = self.units.get(ui.template)
            if u and u.key_slot and "|" in u.key_slot:
                parts = u.key_slot.split("|")
                if all(p in ui.slots for p in parts):
                    ui.slots[u.key_slot] = "|".join(ui.slots[p] for p in parts)
                    ui.slot_nodes[u.key_slot] = ui.slot_nodes[parts[0]]
        # aliases (verified correspondences): a key shown under another naming convention
        if not raw_keys and (self.alias_map or self.key_overrides):
            for ui in insts:
                u = self.units.get(ui.template)
                if u and u.key_slot and u.key_slot in ui.slots:
                    ui.slots[u.key_slot] = self._canonical_key(sig, ui.template, ui.slots[u.key_slot])
        # duplicate names among siblings are told apart by position (second copy: "name#2")
        seen: dict[tuple[int | None, str, str], int] = defaultdict(int)
        for ui in insts:
            u = self.units.get(ui.template)
            if not raw_keys and u and u.key_slot and u.key_slot in ui.slots:
                k = (ui.parent_root, ui.template, ui.slots[u.key_slot])
                seen[k] += 1
                if seen[k] > 1:
                    ui.slots[u.key_slot] = f"{ui.slots[u.key_slot]}#{seen[k]}"
                    ui.positional = True
        if not raw_keys:
            self._page_instances[sig] = {ui.root: ui for ui in insts}
        return insts

    def _canonical_key(self, sig: str, template: str, rendered: str) -> str:
        canonical = self.key_overrides.get((sig, template, rendered),
                                           self.alias_map.get((template, rendered)))
        return rendered if canonical is None else canonical

    def _property_list(self, obs, sig: str, i: int) -> bool:
        """A key-value table, its row groups and its rows are fields of their container,
        not units: a value cell is named by its row's header (`ObsGraph.row_header`) and
        flows to the enclosing unit."""
        n = obs.node(i)
        if n.role == "row":
            return any(self.G.row_header(sig, c) for c in obs.children(i))
        if n.role not in ("table", "rowgroup"):
            return False
        rows = [x for x in obs.subtree(i) if obs.node(x).role == "row"]
        labelled = {x for x in rows if self._property_list(obs, sig, x)}
        bare = lambda x: not any(self.G.data_tokens(sig, c) for c in obs.children(x))   # a header row
        return bool(labelled) and all(x in labelled or bare(x) for x in rows)

    def _relpath(self, obs, root: int, i: int, sig: str | None = None) -> str:
        parts = []
        x = i
        while x != root and x >= 0:
            n = obs.node(x)
            header = self.G.cell_header(sig, x) if sig is not None and n.role == "cell" else None
            # a cell under a declared column header is that column wherever it stands, so
            # the slot is named by the header (`cell@Reason#0`) rather than by its offset
            parts.append(f"{n.role}@{header}" if header else n.role)
            x = n.parent
        return "/".join(reversed(parts)) or obs.node(i).role

    # ------------------------------------------------------------- fitting
    def fit(self, rounds: int = 3, step_sigs: list[str] | None = None, reload_pairs: list[tuple[str, str]] | None = None,
            step_targets: list[tuple[str, int | None]] | None = None, step_kinds: list[str] | None = None) -> None:
        """Fixpoint: a recurring template is a unit only if it has identity (a key slot);
        the data of unkeyed parts flows to the enclosing unit. `step_sigs` (the observation
        after every step, in order) lets short-lived templates (feedback lines) be dropped."""
        self.step_sigs = step_sigs or []
        self.unit_types = find_unit_types(self.G)
        self.reload_pairs = reload_pairs or []
        self.step_targets = step_targets or []  # per step: (observation before, clicked node)
        self.step_kinds = step_kinds or []
        self.allowed = None
        for _ in range(rounds):
            self._fit_once()
            self._drop_transient()
            keyed = {t for t, u in self.units.items() if u.key_slot}
            if self.allowed == keyed:
                break
            self.allowed = keyed
        # Association evidence is observation-local, so it cannot safely be folded into
        # the raw token stream before a unit's key slot is known.  Apply supported key
        # correspondences to the fitted instances now, before key overlap proposes entity
        # merges.  Runtime parsing applies the same map in ``parse_units``.
        self._apply_key_associations()
        self._build_entity_types()
        self.frozen = True

    def _apply_key_associations(self) -> None:
        for u in self.units.values():
            if not u.key_slot:
                continue
            changed = 0
            for ui in u.instances:
                rendered = ui.slots.get(u.key_slot)
                if rendered is None:
                    continue
                canonical = self._canonical_key(ui.sig, ui.template, rendered)
                if canonical == rendered:
                    continue
                ui.slots[u.key_slot] = canonical
                changed += 1
            if changed:
                self._slot_stats(u)
                u.evidence.append(
                    f"key association rewrote {changed} fitted instances from supported observation evidence"
                )

    def _drop_transient(self) -> None:
        """Interface state vanishes on reload while the view stays: evidence is pooled per
        node *position* (role path + ordinal under the parent) so that feedback lines with
        different templates share it. A keyed unit rooted at a position whose content was
        never kept across a same-view reload (>= 2 cases) is not an entity."""
        if not self.reload_pairs:
            return
        gone: Counter = Counter()
        kept: Counter = Counter()
        samples: dict[tuple, list[tuple[str, int]]] = defaultdict(list)
        for a, b in self.reload_pairs:
            if a not in self.G.obs or b not in self.G.obs:
                continue
            oa, ob = self.G.obs[a], self.G.obs[b]
            pos_b: dict[tuple[str, int], str] = {}
            for n in ob.nodes:
                pos_b[self._position(ob, n.i)] = self.G.subtree_template_text(b, n.i)
            for n in oa.nodes:
                if not node_text(n) and not oa.children(n.i):
                    continue
                key = self._position(oa, n.i)
                if not self._same_view(a, b, n.i):
                    continue
                if pos_b.get(key) == self.G.subtree_template_text(a, n.i):
                    kept[key] += 1
                else:
                    gone[key] += 1
                    if len(samples[key]) < 4:
                        samples[key].append((a, n.i))
        cleared = {key for key, g in gone.items() if g >= 2 and kept[key] == 0}
        self.mirror_keys |= self._kept_keys(kept)
        mirrors = self._mirror_positions(cleared, samples)
        self.mirror_positions |= mirrors
        self.transient_positions |= cleared - mirrors
        # interface state also fails to survive ordinary actions: a keyed unit whose key is
        # usually gone at the next step although the view stayed (feedback lines in views
        # that a reload never shows)
        fam_of: dict[str, list[UnitHyp]] = {}
        for f in self._families():
            for u in f:
                fam_of[u.template] = f
        for t, u in list(self.units.items()):
            if not u.key_slot or len(u.instances) < 5 or self._names_kept(u):
                continue
            keys_at: dict[str, set[str]] = defaultdict(set)
            for v in fam_of.get(t, [u]):
                for ui in v.instances:
                    keys_at[ui.sig].add(ui.slots.get(v.key_slot))
            k_ = g_ = 0
            roots_at: dict[str, list[int]] = defaultdict(list)
            for v in fam_of.get(t, [u]):
                for ui in v.instances:
                    roots_at[ui.sig].append(ui.root)
            for i, (a, b) in enumerate(zip(self.step_sigs, self.step_sigs[1:])):
                if a not in keys_at or a == b or b not in self.G.obs:
                    continue
                if i + 1 < len(self.step_kinds) and self.step_kinds[i + 1] in ("reset", "reload"):
                    continue  # a new episode shows other entities; reloads are judged separately
                root = next((ui.root for ui in u.instances if ui.sig == a), None)
                if root is None or not self._same_view(a, b, root):
                    continue
                # an action aimed at one of these instances may legitimately remove it
                if i + 1 < len(self.step_targets):
                    bsig, tgt = self.step_targets[i + 1]
                    if tgt is not None and bsig == a and any(tgt in self.G.obs[a].subtree(r) for r in roots_at[a]):
                        continue
                for k in keys_at[a]:
                    if k in keys_at.get(b, ()):
                        k_ += 1
                    else:
                        g_ += 1
            if k_ + g_ >= 5 and k_ / (k_ + g_) < 0.5:
                u.key_slot = None
                u.evidence.append(f"transient: key survives the next step in {k_}/{k_ + g_} cases")
                self.transient.add(t)
                continue
            # a log line: the same key keeps its identity but its values change at most steps
            slots_at: dict[str, dict[str, tuple]] = defaultdict(dict)
            for v in fam_of.get(t, [u]):
                for ui in v.instances:
                    slots_at[ui.sig][ui.slots.get(v.key_slot)] = tuple(sorted((k, x) for k, x in ui.slots.items() if not k.endswith("~") and k != v.key_slot and "|" not in k))
            same = changed = 0
            for i, (a, b) in enumerate(zip(self.step_sigs, self.step_sigs[1:])):
                if a == b or a not in slots_at or b not in slots_at:
                    continue
                if i + 1 < len(self.step_kinds) and self.step_kinds[i + 1] in ("reset", "reload"):
                    continue
                for k, f in slots_at[a].items():
                    if k in slots_at[b]:
                        if slots_at[b][k] == f:
                            same += 1
                        else:
                            changed += 1
            if same + changed >= 5 and changed / (same + changed) > 0.6:
                u.key_slot = None
                u.evidence.append(f"transient: values change at {changed}/{same + changed} steps (a log line)")
                self.transient.add(t)
        for t, u in list(self.units.items()):
            if not u.key_slot:
                continue
            g = k = 0
            for ui in u.instances[:200]:
                key = self._position(self.G.obs[ui.sig], ui.root)
                g += gone[key] if key not in self.mirror_positions else 0
                k += kept[key]
            if g >= 2 and k == 0:
                u.key_slot = None
                u.evidence.append(f"transient: its position is cleared by reload ({g} cases, never kept)")
                self.transient.add(t)

    def _kept_keys(self, kept: Counter) -> set[str]:
        """The keys of units whose content a reload keeps: the persistent objects."""
        out: set[str] = set()
        for u in self.units.values():
            if u.key_slot and any(kept[self._position(self.G.obs[ui.sig], ui.root)] > 0
                                  for ui in u.instances[:50]):
                out |= u.primary_key_values()
        return out

    def _names_kept(self, u: UnitHyp) -> bool:
        """A unit keyed by the keys of persistent objects is a view of them: its key changes
        when the view moves to another object, which is not interface state vanishing."""
        vals = u.primary_key_values()
        return bool(vals) and len(vals & self.mirror_keys) >= max(2, len(vals) / 2)

    def _mirror_positions(self, cleared: set, samples: dict) -> set:
        """Cleared positions that belong to a detail view rather than to the interface: a
        table or group that names at least two persistent objects by their keys, and the
        position is not a sentence.  A feedback line names objects too, in prose."""
        out: set = set()
        for key in cleared:
            for sig, i in samples.get(key, ()):
                obs = self.G.obs[sig]
                if self.G.is_prose(sig, i):
                    break
                x = i
                while x >= 0 and obs.node(x).parent >= 0:
                    if obs.node(x).role in REGIONS and \
                            len({t for _, t in self.G.subtree_data(sig, x)} & self.mirror_keys) >= 2:
                        out.add(key)
                        break
                    x = obs.node(x).parent
                if key in out:
                    break
        return out

    def _position(self, obs, i: int) -> tuple:
        """Indexed role path: (role, leaf-aware ordinal) at every level."""
        out = []
        x = i
        while x >= 0:
            out.append((obs.node(x).role, self._ordinal(obs, x)))
            x = obs.node(x).parent
        return tuple(reversed(out))

    def _ordinal(self, obs, i: int) -> int:
        """Position among siblings of the same role and leafness (optional leaf siblings such
        as feedback lines do not shift the position of structured siblings)."""
        n = obs.node(i)
        if n.parent < 0:
            return 0
        leaf = not obs.children(i)
        sibs = [c for c in obs.children(n.parent) if obs.node(c).role == n.role and (not obs.children(c)) == leaf]
        return sibs.index(i) * 2 + (1 if leaf else 0)

    def _same_view(self, a: str, b: str, root: int) -> bool:
        """Do observations a and b render the same view, ignoring the subtree at root in a?
        (Role-path multisets, Jaccard >= 0.8.)"""
        oa, ob = self.G.obs[a], self.G.obs[b]
        skip = set(oa.subtree(root))
        pa = Counter(self.G.nodes[(a, n.i)].path for n in oa.nodes if n.i not in skip)
        pb = Counter(self.G.nodes[(b, n.i)].path for n in ob.nodes)
        inter = sum((pa & pb).values())
        union = sum((pa | pb).values())
        return union > 0 and inter / union >= 0.8

    def _fit_once(self) -> None:
        self.units = {}
        all_insts: dict[str, list[UnitInstance]] = defaultdict(list)
        for sig in self.G.obs:
            for ui in self.parse_units(sig):
                all_insts[ui.template].append(ui)
        for t, insts in all_insts.items():
            uh = UnitHyp(t, insts)
            per_obs = Counter(ui.sig for ui in insts)
            uh.max_per_obs = max(per_obs.values())
            self._slot_stats(uh)
            self.units[t] = uh
        # drop unit types without own slots
        self.units = {t: u for t, u in self.units.items() if u.slots}
        for uh in self.units.values():
            self._choose_key(uh)
            if uh.key_slot is None and len(uh.slots) >= 2:
                self._add_composite_keys(uh)
                self._choose_key(uh)
        # second pass: prefer keys that connect to other unit types (cross-view identity)
        # a value "connects" if it occurs in units at several distinct root paths (other views/regions)
        paths_of: dict[str, set[str]] = defaultdict(set)
        for uh in self.units.values():
            for ui in uh.instances[:50]:
                path = self.G.nodes[(ui.sig, ui.root)].path
                for sid, v in ui.slots.items():
                    if not sid.endswith("~"):
                        paths_of[v].add(path)
        pool: Counter = Counter({v: len(ps) for v, ps in paths_of.items()})
        for uh in self.units.values():
            self._choose_key(uh, pool)
        self._family_keys()
        self._promote_persistent_widgets()

    def _slot_stats(self, uh: UnitHyp) -> None:
        uh.slots = {}
        groups: dict[tuple[str, int | None], list[UnitInstance]] = defaultdict(list)
        for ui in uh.instances:
            groups[(ui.sig, ui.parent_root)].append(ui)
        for ui in uh.instances:
            for sid, v in ui.slots.items():
                st = uh.slots.setdefault(sid, SlotStat(sid))
                st.values[v] += 1
                st.n += 1
                st.numeric += v[0].isdigit()
                st.n_obs_values[v] += 1
                sibs = [x for x in groups[(ui.sig, ui.parent_root)] if x is not ui]
                same = sum(1 for x in sibs if x.slots.get(sid) == v)
                if same == 0:
                    st.unique_in_parent += 1
                elif same >= 2:
                    st.crowded += 1

    def _add_composite_keys(self, uh: UnitHyp) -> None:
        """Duplicate names: when no single slot identifies an instance among its siblings,
        a pair of persistent own slots may (title + a distinguishing value)."""
        persistent = [s for s in uh.slots if not s.endswith("~") and not s.endswith("!") and "|" not in s]
        for i, a in enumerate(persistent):
            for b in persistent[i + 1:]:
                sid = f"{a}|{b}"
                for ui in uh.instances:
                    if a in ui.slots and b in ui.slots:
                        ui.slots[sid] = f"{ui.slots[a]}|{ui.slots[b]}"
                        ui.slot_nodes[sid] = ui.slot_nodes[a]
        self._slot_stats(uh)

    def _families(self) -> list[list[UnitHyp]]:
        """Templates that differ only by optional parts (a card with / without an occupant)."""
        keyed = [u for u in self.units.values() if u.key_slot]
        parts = {u.template: set(u.template.replace("(", ",").replace(")", ",").split(",")) - {""} for u in keyed}
        fams: list[list[UnitHyp]] = []
        for u in keyed:
            for f in fams:
                if all(self._same_family(u, v) for v in f):  # pairwise, not chained
                    f.append(u)
                    break
            else:
                fams.append([u])
        return fams

    def _family_keys(self) -> None:
        """When a slot identifies instances in every member of a family, all members key
        on it (consistency beats a locally better key)."""
        for f in self._families():
            if len(f) < 2:
                continue
            common = set.intersection(*[set(u.slots) for u in f])
            cands = []
            for sid in common:
                ok = True
                tot = 0.0
                for u in f:
                    st = u.slots[sid]
                    uniq = st.unique_in_parent / st.n if st.n else 0
                    nonnum = 1 - st.numeric / st.n if st.n else 0
                    crowded = st.crowded / st.n if st.n else 1
                    if sid.endswith("~") or sid.endswith("!") or sid == "col" or crowded > 0.1 or uniq < 0.5 or nonnum < 0.8 or len(st.values) < 2:
                        ok = False
                        break
                    tot += uniq * nonnum * self._fd(u, sid)
                if ok:
                    cands.append((tot / len(f), sid))
            if cands:
                best = max(cands)[1]
                for u in f:
                    if u.key_slot != best:
                        u.evidence.append(f"key {best} adopted for family consistency (was {u.key_slot})")
                        u.key_slot = best

    def _promote_persistent_widgets(self) -> None:
        """A widget value inside a unit (a colour select in a cell) is interface state by
        default; when reload probes show it survives a reload for the same instance, it is an
        attribute of the entity (domain state shown in a widget)."""
        if not self.reload_pairs:
            return
        reload_sigs = {sig for pair in self.reload_pairs for sig in pair}
        for t, u in self.units.items():
            if not u.key_slot:
                continue
            trans = [sid for sid in u.slots if sid.endswith("~")]
            if not trans:
                continue
            by_sig: dict[str, dict[str, list[UnitInstance]]] = defaultdict(lambda: defaultdict(list))
            for ui in u.instances:
                k = ui.slots.get(u.key_slot)
                if k is not None:
                    by_sig[ui.sig][k].append(ui)
            # Keys are chosen among siblings. Repeated keys under different parents
            # do not identify the same instance across reloads. Withhold the whole
            # template: other retained keys must not erase an ambiguous counterexample.
            if any(len(matches) > 1 for sig in reload_sigs for matches in by_sig.get(sig, {}).values()):
                u.evidence.append(f"widget persistence withheld: key {u.key_slot} is ambiguous within a reload observation")
                continue
            for sid in trans:
                kept = lost = 0
                for a, b in self.reload_pairs:
                    for k, matches in by_sig.get(a, {}).items():
                        ua = matches[0]
                        after = by_sig.get(b, {}).get(k, [])
                        ub = after[0] if after else None
                        if ub is None or sid not in ua.slots or sid not in ub.slots:
                            continue
                        if ua.slots[sid] == ub.slots[sid]:
                            kept += 1
                        else:
                            lost += 1
                if kept >= 2 and lost == 0:
                    new = sid[:-1]
                    self.persistent_widgets.add((t, new))
                    self._reload_persistent_widgets.add((t, new))
                    for ui in u.instances:
                        if sid in ui.slots:
                            ui.slots[new] = ui.slots.pop(sid)
                            ui.slot_nodes[new] = ui.slot_nodes.pop(sid)
                    u.evidence.append(f"widget slot {sid} survives reloads ({kept}): attribute")
            self._slot_stats(u)

    def _reload_widget_evidence(self, u: UnitHyp, sid: str, raw: dict) -> dict[str, int]:
        """Compare raw values under the current own key, never position-suffixed keys."""
        counts = {"kept": 0, "lost": 0, "ambiguous": 0, "missing": 0, "mismatched": 0}
        by_sig: dict[str, dict[str, list[UnitInstance]]] = defaultdict(lambda: defaultdict(list))
        for (sig, template, _root), ui in raw.items():
            if template == u.template and u.key_slot in ui.slots:
                key = self._canonical_key(sig, template, ui.slots[u.key_slot])
                by_sig[sig][key].append(ui)
        pairs = getattr(self, "reload_pairs", [])
        reload_sigs = {sig for pair in pairs for sig in pair}
        counts["ambiguous"] = sum(len(matches) > 1 for sig in reload_sigs
                                  for matches in by_sig.get(sig, {}).values())
        fitted: dict[tuple, list[UnitInstance]] = defaultdict(list)
        for ui in u.instances:
            if ui.sig in reload_sigs:
                fitted[(ui.sig, ui.template, ui.root)].append(ui)
        sites = set(fitted) | {site for site in raw if site[0] in reload_sigs and site[1] == u.template}
        mismatched = set()
        bound_slots = {sid, u.key_slot} | set(u.key_slot.split("|") if u.key_slot else [])
        for site in sites:
            parsed, fits = raw.get(site), fitted.get(site, [])
            if (site[1] != u.template or parsed is None or len(fits) != 1
                    or fits[0].parent_root != parsed.parent_root):
                mismatched.add(site)
                continue
            fit = fits[0]
            for slot in bound_slots:
                if ((slot in parsed.slots) != (slot in fit.slots)
                        or (slot in parsed.slots and (parsed.slot_nodes.get(slot) is None
                            or parsed.slot_nodes[slot] != fit.slot_nodes.get(slot)))):
                    mismatched.add(site)
        counts["mismatched"] = len(mismatched)

        def value(ui):
            if (ui.sig, ui.template, ui.root) in mismatched:
                return None
            return ui.slots.get(sid)

        for a, b in pairs:
            for key in set(by_sig.get(a, {})) | set(by_sig.get(b, {})):
                left, right = by_sig.get(a, {}).get(key, []), by_sig.get(b, {}).get(key, [])
                if not left or not right:
                    counts["missing"] += 1
                    continue
                if len(left) != 1 or len(right) != 1:
                    continue
                va, vb = value(left[0]), value(right[0])
                if va is None or vb is None:
                    counts["missing"] += 1
                else:
                    counts["kept" if va == vb else "lost"] += 1
        return counts

    def _raw_unit_instances(self) -> dict[tuple[str, str, int], UnitInstance]:
        return {(ui.sig, ui.template, ui.root): ui
                for sig in self.G.obs for ui in self._parse_units(sig, raw_keys=True)}

    def _demote_widget(self, ui: UnitInstance, sid: str, raw: UnitInstance | None) -> None:
        ui.slots.pop(sid, None)
        ui.slot_nodes.pop(sid, None)
        ui.slots.pop(sid + "~", None)
        ui.slot_nodes.pop(sid + "~", None)
        if raw is not None and sid in raw.slots and sid in raw.slot_nodes:
            ui.slots[sid + "~"] = raw.slots[sid]
            ui.slot_nodes[sid + "~"] = raw.slot_nodes[sid]
        for composite in set(ui.slots) | set(ui.slot_nodes):
            if "|" in composite and sid in composite.split("|"):
                ui.slots.pop(composite, None)
                ui.slot_nodes.pop(composite, None)

    def _revoke_unsupported_widgets(self) -> bool:
        owned = self._reload_persistent_widgets & self.persistent_widgets
        if not owned:
            return False
        raw = self._raw_unit_instances()
        rejected = []
        for template, sid in sorted(owned):
            u = self.units.get(template)
            if u is None:
                rejected.append((template, sid))
                continue
            counts = self._reload_widget_evidence(u, sid, raw)
            if counts["kept"] >= 2 and counts["lost"] == counts["ambiguous"] == counts["mismatched"] == 0:
                continue
            reason = ("mismatched raw/fitted binding" if counts["mismatched"] else "ambiguous own key"
                      if counts["ambiguous"] else "reload value changed" if counts["lost"]
                      else "insufficient matched reload values")
            detail = ", ".join(f"{name}={count}" for name, count in counts.items())
            u.evidence.append(f"widget persistence revoked: slot {sid} under key {u.key_slot} ({detail}): {reason}")
            rejected.append((template, sid))
        dependencies = []
        for template, sid in rejected:
            self.persistent_widgets.discard((template, sid))
            self._reload_persistent_widgets.discard((template, sid))
            u = self.units.get(template)
            if u is None:
                continue
            if u.key_slot and sid in u.key_slot.split("|"):
                dependencies.append((template, sid, u.key_slot))
            instances = list(u.instances)
            for ui in u.instances:
                cached = self._page_instances.get(ui.sig, {}).get(ui.root)
                if cached is not None and (cached.sig, cached.template, cached.root) == (ui.sig, template, ui.root):
                    instances.append(cached)
            seen = set()
            for ui in instances:
                if id(ui) not in seen:
                    self._demote_widget(ui, sid, raw.get((ui.sig, template, ui.root)))
                    seen.add(id(ui))
            self._slot_stats(u)
        if dependencies:
            raise ValueError(f"rejected reload widget persistence is required by a selected key: {dependencies}")
        return bool(rejected)

    def _slot_order(self, uh: UnitHyp, sid: str) -> int:
        for ui in uh.instances:
            if sid in ui.slot_nodes:
                return ui.slot_nodes[sid] - ui.root
        return 10 ** 6

    def _fd(self, uh: UnitHyp, k: str) -> float:
        """How well slot k functionally determines the other persistent own slots
        (identity determines attributes): mean over slots of the dominant-value share."""
        others = [s for s in uh.slots if s != k and not s.endswith("~") and not s.endswith("!") and "|" not in s and s not in k.split("|")
                  and uh.slots[s].numeric < 0.5 * max(1, uh.slots[s].n)]  # counters are expected to change
        if not others:
            return 1.0
        scores = []
        for s in others:
            by_k: dict[str, set] = defaultdict(set)
            for ui in uh.instances:
                if k in ui.slots and s in ui.slots:
                    by_k[ui.slots[k]].add(ui.slots[s])
            if not by_k:
                continue
            # distinct (key, value) pairs, not observation counts (a state seen many times
            # must not outweigh a contradiction seen once)
            scores.append(len(by_k) / sum(len(v) for v in by_k.values()))
        return sum(scores) / len(scores) if scores else 1.0

    def _choose_key(self, uh: UnitHyp, pool: Counter | None = None) -> None:
        best = None
        uh.evidence = [e for e in uh.evidence if not e.startswith("key ")]
        n_inst = len(uh.instances)
        for sid, st in uh.slots.items():
            if sid.endswith("~") or sid.endswith("!") or sid == "col" or st.n < 0.8 * n_inst:
                continue  # transient widget value / prose / column context / not present in most instances
            uniq = st.unique_in_parent / st.n
            nonnum = 1 - st.numeric / st.n
            crowded = st.crowded / st.n
            if crowded > 0.1 or uniq < 0.5 or nonnum < 0.8 or len(st.values) < 2:
                continue  # duplicates (pairs) are tolerated and told apart by position

            fd = self._fd(uh, sid)
            score = uniq * nonnum * fd
            if "|" in sid and best is not None and "|" not in best[1]:
                continue  # composites only when no single slot identifies (duplicate names)
            if pool:
                own = set(st.values)
                elsewhere = sum(1 for v in own if pool[v] > 1) / len(own)
                score += 0.5 * elsewhere
            # ties (within 0.05): the slot shown first (identity usually precedes description)
            if best is None or score > best[0] + 0.1 or (abs(score - best[0]) <= 0.1 and self._slot_order(uh, sid) < self._slot_order(uh, best[1])):
                best = (score, sid, fd)
        if best is None and self.numeric_keys_as_last_resort:
            # Nothing textual identifies this unit.  A number may: blend's draw rows carry
            # `Ticket 4`, unique among the rows, the same number standing with the same
            # draw on every page, and the interface acts on the row by that number.  A
            # number is refused above because in most tables it is an amount, and an amount
            # can be unique by coincidence; here it is admitted only where no word does the
            # job, on the same evidence a word is admitted on -- uniqueness among siblings,
            # and determining the rest of the row -- so that a recurring structure with
            # numeric identity is not read as slots of whatever encloses it.
            for sid, st in uh.slots.items():
                if sid.endswith("~") or sid.endswith("!") or sid == "col" or "|" in sid or st.n < 0.8 * n_inst:
                    continue
                uniq = st.unique_in_parent / st.n
                crowded = st.crowded / st.n
                if crowded > 0.1 or uniq < 0.5 or len(st.values) < 2 or st.numeric < st.n:
                    continue
                fd = self._fd(uh, sid)
                score = uniq * fd
                if best is None or score > best[0] + 0.1:
                    best = (score, sid, fd)
            if best:
                uh.evidence.append(f"numeric key {best[1]}: no word identifies this unit")
        if best:
            uh.key_slot = best[1]
            uh.key_score = best[0]
            uh.evidence.append(f"key {best[1]} score {best[0]:.2f} fd {best[2]:.2f} values {len(uh.slots[best[1]].values)}")

    def apply_aliases(self, aliases) -> None:
        """Adopt verified/provisional aliases: B's key values are rewritten to A's, so that the
        key-overlap logic identifies the two representations; then rebuild entity types."""
        for al in aliases:
            self.alias_map[(al.b_template, al.b_key)] = al.a_key
        for u in self.units.values():
            for ui in u.instances:
                if u.key_slot and u.key_slot in ui.slots:
                    canon = self.alias_map.get((ui.template, ui.slots[u.key_slot]))
                    if canon is not None:
                        ui.slots[u.key_slot] = canon
            self._slot_stats(u)
        self._build_entity_types()

    def _split_by_context(self) -> None:
        """One template can realise different things in different containers (a row
        'X loads N' lists hives under a bloom and blooms under a hive): split a keyed unit
        type by enclosing template when the key sets of the contexts barely overlap."""
        for t in list(self.units):
            u = self.units[t]
            if not u.key_slot:
                continue
            fam_root = {}
            for f in self._families():
                for v in f:
                    fam_root[v.template] = f[0].template
            by_ctx: dict[str | None, list[UnitInstance]] = defaultdict(list)
            for ui in u.instances:
                ctx = self.template(ui.sig, ui.parent_root) if ui.parent_root is not None else None
                by_ctx[fam_root.get(ctx, ctx)].append(ui)
            if len(by_ctx) < 2:
                continue
            keysets = {c: {ui.slots.get(u.key_slot) for ui in us} for c, us in by_ctx.items()}
            ctxs = list(by_ctx)
            # contexts whose key sets are disjoint from the largest context's set
            main = max(ctxs, key=lambda c: len(by_ctx[c]))
            for c in ctxs:
                if c == main:
                    continue
                ka, kb = keysets[main], keysets[c]
                if ka and kb and len(ka & kb) / len(ka | kb) < 0.2 and len(by_ctx[c]) >= 2:
                    nt = f"{t}@ctx{len(self.ctx_split)}"
                    for pt, root in fam_root.items():
                        if root == c:
                            self.ctx_split[(t, pt)] = nt
                    self.ctx_split[(t, c)] = nt
                    for source, sid in self._reload_persistent_widgets & self.persistent_widgets:
                        if source == t:
                            self.persistent_widgets.add((nt, sid))
                            self._reload_persistent_widgets.add((nt, sid))
                    for (source, key), canonical in list(self.alias_map.items()):
                        if source == t:
                            self.alias_map.setdefault((nt, key), canonical)
                    for (sig, source, key), canonical in list(self.key_overrides.items()):
                        if source == t:
                            self.key_overrides.setdefault((sig, nt, key), canonical)
                    nu = UnitHyp(nt, by_ctx[c])
                    nu.max_per_obs = u.max_per_obs
                    for ui in by_ctx[c]:
                        ui.template = nt
                    self._slot_stats(nu)
                    self._choose_key(nu)
                    nu.evidence.append(f"split from {t[:40]} by context {str(c)[:40]}")
                    self.units[nt] = nu
                    u.instances = [ui for ui in u.instances if ui.template == t]
            self._slot_stats(u)
            self._choose_key(u)

    def _build_entity_types(self) -> None:
        """Finalize the current identity, removing unsupported automatic widget claims."""
        try:
            if not self._split_done:
                self._split_by_context()
                self._split_done = True
            while True:
                if any(u.key_slot and u.key_slot not in u.slots for u in self.units.values()):
                    raise ValueError("selected key is unavailable after widget persistence revocation")
                self._build_entity_types_once()
                # Splitting happens once; each further pass only removes owned claims.
                if not self._revoke_unsupported_widgets():
                    break
        except Exception:
            self.entity_types = {}
            self.tid_of_template = {}
            self.frozen = False
            raise

    def _build_entity_types_once(self) -> None:
        self.entity_types = {}
        self.tid_of_template = {}
        keyed = [u for u in self.units.values() if u.key_slot]
        # 1. correspondence by key overlap -> union-find over unit types, unless contradicted
        parent: dict[str, str] = {u.template: u.template for u in keyed}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        links: dict[str, str] = {}  # template of a link-like unit -> template whose keys it borrows
        for a in keyed:
            for b in keyed:
                if a.template >= b.template:
                    continue
                ka, kb = a.primary_key_values(), b.primary_key_values()
                if not ka or not kb:
                    continue
                j = len(ka & kb) / min(len(ka), len(kb))  # overlap coefficient: one view may list a subset
                if j < 0.5 or len(ka & kb) < 2:
                    continue
                if (self._numeric_keyed(a.template) or self._numeric_keyed(b.template)) and not (
                        self._names_the_kind(a.template, a.key_slot, b.template)
                        or self._names_the_kind(b.template, b.key_slot, a.template)):
                    continue      # two numbers alike are not two names of one thing
                if frozenset((a.template, b.template)) in self.withheld_unions:
                    a.evidence.append(f"key overlaps {b.template[:40]} but the union is withheld: two kinds")
                    continue
                # contradiction: a unit type whose key repeats within one observation (different
                # parents) cannot be the same entity as one where it does not -> link type;
                # likewise a unit that comes into existence while the other already showed the
                # key (a loan row appearing for an existing artifact) is a new object, not a view
                for u, other in ((a, b), (b, a)):
                    rule = "col" in u.slots or self._repeats_in_obs(u) or self._created_later(u, other)
                    if rule != (u.template in self.force_link):
                        # a matrix cell is a value at (row, column): its content refers to `other`
                        links[u.template] = other.template
                        u.evidence.append(f"key overlaps {other.template[:40]} but repeats within observations: link type")
                        break
                else:
                    parent[find(a.template)] = find(b.template)
                    a.evidence.append(f"same entity as {b.template[:40]} (key jaccard {j:.2f})")
        groups: dict[str, list[UnitHyp]] = defaultdict(list)
        for u in keyed:
            if u.template in links:
                continue
            groups[find(u.template)].append(u)
        tid = 0
        raw_composites = None
        for root, us in groups.items():
            # harmonise composite keys across the templates of one entity type
            comps = [u.key_slot for u in us if "|" in u.key_slot]
            if comps:
                comp = comps[0]
                parts = comp.split("|")
                for u in us:
                    if "|" not in u.key_slot and all(p in u.slots for p in parts):
                        if raw_composites is None:
                            raw_composites = self._raw_unit_instances()
                        for ui in u.instances:
                            parsed = raw_composites.get((ui.sig, u.template, ui.root))
                            if (parsed is None or parsed.parent_root != ui.parent_root
                                    or any(p not in parsed.slots or parsed.slot_nodes.get(p) is None
                                           or parsed.slot_nodes[p] != ui.slot_nodes.get(p) for p in parts)):
                                raise ValueError(f"cannot materialize selected composite key {comp} from its raw instance")
                            # The former key becomes an ordinary raw component. Apply a
                            # correspondence only to the newly selected whole composite.
                            for p in parts:
                                ui.slots[p] = parsed.slots[p]
                            ui.slots[comp] = self._canonical_key(ui.sig, u.template,
                                                                 "|".join(parsed.slots[p] for p in parts))
                            ui.slot_nodes[comp] = parsed.slot_nodes[parts[0]]
                        self._slot_stats(u)
                        u.key_slot = comp
                        u.evidence.append(f"composite key {comp} adopted from a sibling template")
            et = EntityType(tid, [u.template for u in us], {u.template: u.key_slot for u in us})
            for u in us:
                et.attr_slots[u.template] = {s for s in u.slots if s != u.key_slot and not s.endswith("~") and not s.endswith("!") and "|" not in s}
                self.tid_of_template[u.template] = tid
                et.evidence += u.evidence
            self.entity_types[tid] = et
            tid += 1
        # link types: own entity type keyed by (enclosing entity, own key), referencing the overlapped type
        for t, other in links.items():
            u = self.units[t]
            et = EntityType(tid, [t], {t: u.key_slot})
            if "col" in u.slots:
                et.matrix.add(t)
            hops = 0
            while other in links and hops < 5:  # the borrowed keys may themselves be borrowed
                other = links[other]
                hops += 1
            et.attr_slots[t] = {s for s in u.slots if s != u.key_slot and not s.endswith("~") and not s.endswith("!") and "|" not in s}
            et.ref_slots[(t, u.key_slot)] = self.tid_of_template.get(other, -1)
            et.evidence += u.evidence
            self.tid_of_template[t] = tid
            self.entity_types[tid] = et
            tid += 1
        # 2. reference slots: non-key slot values that are keys of another type
        keys_of: dict[int, set[str]] = {et.tid: set() for et in self.entity_types.values()}
        for et in self.entity_types.values():
            for t in et.units:
                keys_of[et.tid] |= self.units[t].key_values()
        # A link type's key is borrowed from the type it overlaps, so a column whose values
        # match the link's keys matches the origin's keys just as well -- and where the link
        # also keys an empty cell, better, which is how harbour's `Current call` column came to
        # reference the call *cells* rather than the calls, and a ship's reference to the call
        # it holds resolved to nothing on every page.  A reference is to the origin.
        origin: dict[int, int] = {}
        for t, other in links.items():
            hops = 0
            while other in links and hops < 5:
                other = links[other]
                hops += 1
            o = self.tid_of_template.get(other)
            if o is not None and t in self.tid_of_template:
                origin[self.tid_of_template[t]] = o
        for et in self.entity_types.values():
            for t in et.units:
                if "col" in self.units[t].slots:
                    et.attr_slots[t].add("col")
                for sid in list(et.attr_slots[t]):
                    if sid in et.key_slot[t].split("|"):
                        continue
                    vals = set(self.units[t].slots[sid].values)
                    best = None
                    for tid2, ks in keys_of.items():
                        if tid2 == et.tid or not ks:
                            continue
                        ov = len(vals & ks) / len(vals)
                        if ov < 0.5 or (best is not None and ov <= best[0]):
                            continue
                        numeric_target = all(self._numeric_keyed(t2)
                                             for t2 in self.entity_types[tid2].units)
                        if numeric_target and not any(
                                self._names_the_kind(t, sid, t2)
                                for t2 in self.entity_types[tid2].units):
                            continue
                        best = (ov, tid2)
                    if best:
                        target = origin.get(best[1], best[1])
                        if target == et.tid:
                            continue
                        et.ref_slots[(t, sid)] = target
                        et.attr_slots[t].discard(sid)
                        et.evidence.append(f"slot {sid} of {t[:30]} references T{target} ({best[0]:.2f})")
        # 3. containment: instances nested in another entity type's instances
        for et in self.entity_types.values():
            for t in et.units:
                enclosing = Counter()
                for ui in self.units[t].instances:
                    p = ui.parent_root
                    if p is None:
                        continue
                    pt = self.template(ui.sig, p)
                    ptid = self.tid_of_template.get(pt)
                    if ptid is not None and ptid != et.tid:
                        enclosing[ptid] += 1
                if enclosing:
                    ptid, c = enclosing.most_common(1)[0]
                    if c >= 0.5 * len(self.units[t].instances):
                        if t in links:
                            et.link_parent[t] = ptid
                        else:
                            et.contain[t] = ptid
                        et.evidence.append(f"{t[:30]} nested in T{ptid} ({c}/{len(self.units[t].instances)})")

    def _slot_labels(self, t: str, sid: str) -> set[str]:
        """The label tokens of the node holding this slot, lower-cased: `Ticket 4` -> {ticket}."""
        u = self.units.get(t)
        if u is None:
            return set()
        for ui in u.instances:
            node = ui.slot_nodes.get(sid)
            if node is not None:
                return {x.lower() for x in self.G.labels(ui.sig, node)}
        return set()

    def _numeric_keyed(self, t: str) -> bool:
        u = self.units.get(t)
        return bool(u and u.key_slot and "|" not in u.key_slot
                    and u.slots[u.key_slot].numeric == u.slots[u.key_slot].n)

    def _names_the_kind(self, t: str, sid: str, other: str) -> bool:
        """Does the slot carry a label the other unit's key carries?  A number names an
        object of a numerically keyed type only where the interface says which kind of
        number it is -- `Return ticket 4` names the draw `Ticket 4`; a blend's committed
        gallons, `4`, overlap the ticket numbers by coincidence and name nothing."""
        ou = self.units.get(other)
        if ou is None or not ou.key_slot:
            return False
        return bool(self._slot_labels(t, sid) & self._slot_labels(other, ou.key_slot))

    def _parent_key(self, ui: UnitInstance) -> str | None:
        """The key of the unit instance enclosing this one, on the page it stands on.

        This searched the fitting instances of the parent's unit type for the page and root,
        and so answered for a fitted page and never for a held-out one: on every page of
        another seed, harbour's call buttons -- link objects keyed by their row and column --
        had no key and were not objects, and a click on one had no owner.  The page being
        read has its own instances (`parse_units` keeps the last parse of each page); the
        fitting instances are consulted first because the fit may have rewritten their keys
        to a canonical spelling, and a held-out parse applies the same aliases itself.
        """
        if ui.parent_root is None:
            return None
        pt = self.template(ui.sig, ui.parent_root)
        pu = self.units.get(pt)
        if pu is None or not pu.key_slot:
            return None
        for x in pu.instances:
            if x.sig == ui.sig and x.root == ui.parent_root:
                return x.slots.get(pu.key_slot)
        parent = self._page_instances.get(ui.sig, {}).get(ui.parent_root)
        if parent is not None:
            return parent.slots.get(pu.key_slot)
        return None

    def _created_later(self, u: UnitHyp, other: UnitHyp) -> bool:
        """Temporal evidence against identity: keys that `other` showed from early on start
        appearing in u only later, although u's region had been rendered before (a loan row
        appearing for an artifact that existed all along). Templates of one family (optional
        parts) are exempt."""
        if not self.step_sigs or self._same_family(u, other) or u.max_per_obs < 2:
            return False  # a detail panel shows keys one at a time by selection: no evidence
        idx: dict[str, int] = {}
        for i, sig in enumerate(self.step_sigs):
            idx.setdefault(sig, i)
        first_other: dict[str, int] = {}
        for ui in other.instances:
            k = ui.slots.get(other.key_slot)
            if ui.sig in idx and k is not None:
                first_other[k] = min(first_other.get(k, 10 ** 9), idx[ui.sig])
        first_u: dict[str, int] = {}
        rendered = []
        for ui in u.instances:
            if ui.sig not in idx:
                continue
            k = ui.slots.get(u.key_slot)
            first_u[k] = min(first_u.get(k, 10 ** 9), idx[ui.sig])
            rendered.append(idx[ui.sig])
        if not rendered:
            return False
        first_render = min(rendered)
        events = sum(1 for k, t in first_u.items() if k in first_other and first_other[k] + 3 < t and first_render + 3 < t)
        if events >= 2:
            u.evidence.append(f"keys of {other.template[:30]} appear in it only later ({events}): not the same entity")
            return True
        return False

    def _same_family(self, a: UnitHyp, b: UnitHyp) -> bool:
        pa = set(a.template.replace("(", ",").replace(")", ",").split(",")) - {""}
        pb = set(b.template.replace("(", ",").replace(")", ",").split(",")) - {""}
        ov = len(pa & pb) / min(len(pa), len(pb))
        if ov >= 0.8:
            return True  # one is the other plus optional parts
        # variants of one thing at one place (a card with / without an occupant, a row with or
        # without a duty): half the parts in common and the same parent positions
        return ov >= 0.5 and bool(self._parent_paths(a) & self._parent_paths(b))

    def _parent_paths(self, u: UnitHyp) -> set[str]:
        out = set()
        for ui in u.instances[:50]:
            if ui.root >= 0:
                p = self.G.obs[ui.sig].node(ui.root).parent
                if p >= 0:
                    out.add(self.G.nodes[(ui.sig, p)].path)
        return out

    def _repeats_in_obs(self, u: UnitHyp) -> bool:
        """One entity cannot carry two values of an attribute at once. Evidence that the
        key alone does not identify an entity (link type): (a) one observation shows two
        instances with the same key and different persistent values; (b) the persistent
        values are a function of (enclosing entity, key) but not of the key alone."""
        per: dict[tuple[str, str], list[tuple]] = defaultdict(list)
        for ui in u.instances:
            per[(ui.sig, ui.slots.get(u.key_slot))].append((ui.parent_root, ui.slots))
        attrs = [sid for sid in u.slots if sid != u.key_slot and not sid.endswith("~") and "|" not in sid]
        for (sig, k), items in per.items():
            if len({p for p, _ in items}) < 2:
                continue  # duplicates under one parent are told apart by position, not a link
            for sid in attrs:
                if len({sl.get(sid) for _, sl in items}) > 1:
                    return True
        if attrs:
            def fd(keyfn):
                scores = []
                for sid in attrs:
                    by: dict = defaultdict(Counter)
                    for ui in u.instances:
                        if sid in ui.slots:
                            by[keyfn(ui)][ui.slots[sid]] += 1
                    tot = sum(sum(c.values()) for c in by.values())
                    if tot:
                        scores.append(sum(c.most_common(1)[0][1] for c in by.values()) / tot)
                return sum(scores) / len(scores) if scores else 1.0
            alone = fd(lambda ui: ui.slots.get(u.key_slot))
            with_parent = fd(lambda ui: (self._parent_key(ui), ui.slots.get(u.key_slot)))
            if with_parent - alone >= 0.2:
                u.evidence.append(f"values depend on the enclosing entity (fd {alone:.2f} -> {with_parent:.2f})")
                return True
        return False

    # ------------------------------------------------------------- report
    def report(self) -> str:
        out = []
        for et in self.entity_types.values():
            out.append(f"T{et.tid}:")
            for t in et.units:
                u = self.units[t]
                out.append(f"   unit {t[:90]}  n={len(u.instances)} key={et.key_slot[t]} attrs={sorted(et.attr_slots[t])}")
            for (t, s), tid2 in et.ref_slots.items():
                out.append(f"   ref {s} -> T{tid2}")
            for t, p in et.contain.items():
                out.append(f"   contained in T{p}")
            for t, p in et.link_parent.items():
                out.append(f"   link under T{p}")
            for e in et.evidence:
                out.append(f"   - {e}")
        return "\n".join(out)
