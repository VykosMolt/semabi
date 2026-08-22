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


@dataclass
class UnitInstance:
    sig: str
    root: int
    template: str
    slots: dict[str, str]  # own data slot id -> value (first token occurrence)
    slot_nodes: dict[str, int]  # slot id -> node
    nested: list[int]  # roots of nested unit instances (direct)
    parent_root: int | None = None


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
    contain: dict[str, int] = field(default_factory=dict)  # template -> enclosing entity tid (containment relation)
    evidence: list[str] = field(default_factory=list)


class Hypotheses:
    def __init__(self, G: ObsGraph):
        self.G = G
        self.memo: dict = {}
        self.unit_types: dict[str, UnitType] = {}
        self.units: dict[str, UnitHyp] = {}
        self.entity_types: dict[int, EntityType] = {}
        self.tid_of_template: dict[str, int] = {}
        self.allowed: set[str] | None = None  # unit templates with identity (after fitting)
        self.ctx_split: dict[tuple[str, str | None], str] = {}  # (template, enclosing template) -> split template
        self.transient: set[str] = set()
        self.transient_positions: set[tuple] = set()
        self.frozen = False

    # ------------------------------------------------------------- templates
    def template(self, sig: str, i: int) -> str:
        return collapsed_template(self.G, sig, i, self.memo)

    def is_unit_template(self, t: str, role: str, has_children: bool) -> bool:
        if role in ("combobox", "textbox") or t in self.transient:
            return False  # input widgets are slots of their enclosing unit, never units
        if not has_children and role not in WIDGET:
            return False  # a childless text node is a slot of its enclosing unit
        if self.allowed is not None:
            return t in self.allowed
        return t in self.unit_types

    # ------------------------------------------------------------- instances
    def parse_units(self, sig: str) -> list[UnitInstance]:
        """Unit instances of one observation (all recurring templates; nested allowed)."""
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
            is_unit = n.parent >= 0 and self.is_unit_template(t, n.role, bool(obs.children(i)))
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
            rel = self._relpath(obs, owner.root, i)
            transient = obs.node(i).role in ("combobox", "textbox")
            prose = self.G.is_prose(sig, i)  # a sentence about entities: neither identity nor attribute
            for k, tok in enumerate(toks):
                sid = f"{rel}#{k}" + ("~" if transient else ("!" if prose else ""))
                if sid in owner.slots:
                    sid = f"{rel}#{k}@{i - owner.root}" + ("~" if transient else "")
                owner.slots[sid] = tok
                owner.slot_nodes[sid] = i
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
                rows = [x for x in obs.subtree(tbl) if obs.node(x).role == "row"]
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
        # duplicate names among siblings are told apart by position (second copy: "name#2")
        seen: dict[tuple[int | None, str, str], int] = defaultdict(int)
        for ui in insts:
            u = self.units.get(ui.template)
            if u and u.key_slot and u.key_slot in ui.slots:
                k = (ui.parent_root, ui.template, ui.slots[u.key_slot])
                seen[k] += 1
                if seen[k] > 1:
                    ui.slots[u.key_slot] = f"{ui.slots[u.key_slot]}#{seen[k]}"
        return insts

    def _relpath(self, obs, root: int, i: int) -> str:
        parts = []
        x = i
        while x != root and x >= 0:
            n = obs.node(x)
            parts.append(n.role)
            x = n.parent
        return "/".join(reversed(parts)) or obs.node(i).role

    # ------------------------------------------------------------- fitting
    def fit(self, rounds: int = 3, step_sigs: list[str] | None = None, reload_pairs: list[tuple[str, str]] | None = None) -> None:
        """Fixpoint: a recurring template is a unit only if it has identity (a key slot);
        the data of unkeyed parts flows to the enclosing unit. `step_sigs` (the observation
        after every step, in order) lets short-lived templates (feedback lines) be dropped."""
        self.unit_types = find_unit_types(self.G)
        self.step_sigs = step_sigs or []
        self.reload_pairs = reload_pairs or []
        self.allowed = None
        for _ in range(rounds):
            self._fit_once()
            self._drop_transient()
            keyed = {t for t, u in self.units.items() if u.key_slot}
            if self.allowed == keyed:
                break
            self.allowed = keyed
        self._build_entity_types()
        self.frozen = True

    def _drop_transient(self) -> None:
        """Interface state vanishes on reload while the view stays: evidence is pooled per
        node *position* (role path + ordinal under the parent) so that feedback lines with
        different templates share it. A keyed unit rooted at a position whose content was
        never kept across a same-view reload (>= 2 cases) is not an entity."""
        if not self.reload_pairs:
            return
        gone: Counter = Counter()
        kept: Counter = Counter()
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
        for key, g in gone.items():
            if g >= 2 and kept[key] == 0:
                self.transient_positions.add(key)
        # interface state also fails to survive ordinary actions: a keyed unit whose key is
        # usually gone at the next step although the view stayed (feedback lines in views
        # that a reload never shows)
        fam_of: dict[str, list[UnitHyp]] = {}
        for f in self._families():
            for u in f:
                fam_of[u.template] = f
        for t, u in list(self.units.items()):
            if not u.key_slot or len(u.instances) < 5:
                continue
            keys_at: dict[str, set[str]] = defaultdict(set)
            for v in fam_of.get(t, [u]):
                for ui in v.instances:
                    keys_at[ui.sig].add(ui.slots.get(v.key_slot))
            k_ = g_ = 0
            for a, b in zip(self.step_sigs, self.step_sigs[1:]):
                if a not in keys_at or a == b or b not in self.G.obs:
                    continue
                root = next((ui.root for ui in u.instances if ui.sig == a), None)
                if root is None or not self._same_view(a, b, root):
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
            for a, b in zip(self.step_sigs, self.step_sigs[1:]):
                if a == b or a not in slots_at or b not in slots_at:
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
                g += gone[key]
                k += kept[key]
            if g >= 2 and k == 0:
                u.key_slot = None
                u.evidence.append(f"transient: its position is cleared by reload ({g} cases, never kept)")
                self.transient.add(t)

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
                if any(len(parts[u.template] & parts[v.template]) / min(len(parts[u.template]), len(parts[v.template])) >= 0.8 for v in f):
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
            by_k: dict[str, Counter] = defaultdict(Counter)
            for ui in uh.instances:
                if k in ui.slots and s in ui.slots:
                    by_k[ui.slots[k]][ui.slots[s]] += 1
            tot = sum(sum(c.values()) for c in by_k.values())
            if not tot:
                continue
            scores.append(sum(c.most_common(1)[0][1] for c in by_k.values()) / tot)
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
        if best:
            uh.key_slot = best[1]
            uh.key_score = best[0]
            uh.evidence.append(f"key {best[1]} score {best[0]:.2f} fd {best[2]:.2f} values {len(uh.slots[best[1]].values)}")

    def _split_by_context(self) -> None:
        """One template can realise different things in different containers (a row
        'X loads N' lists hives under a bloom and blooms under a hive): split a keyed unit
        type by enclosing template when the key sets of the contexts barely overlap."""
        for t in list(self.units):
            u = self.units[t]
            if not u.key_slot:
                continue
            by_ctx: dict[str | None, list[UnitInstance]] = defaultdict(list)
            for ui in u.instances:
                ctx = self.template(ui.sig, ui.parent_root) if ui.parent_root is not None else None
                by_ctx[ctx].append(ui)
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
                    self.ctx_split[(t, c)] = nt
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
        self._split_by_context()
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
                # contradiction: a unit type whose key repeats within one observation (different
                # parents) cannot be the same entity as one where it does not -> link type;
                # likewise a unit that comes into existence while the other already showed the
                # key (a loan row appearing for an existing artifact) is a new object, not a view
                for u, other in ((a, b), (b, a)):
                    if self._repeats_in_obs(u) or self._created_later(u, other):
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
        for root, us in groups.items():
            # harmonise composite keys across the templates of one entity type
            comps = [u.key_slot for u in us if "|" in u.key_slot]
            if comps:
                comp = comps[0]
                parts = comp.split("|")
                for u in us:
                    if "|" not in u.key_slot and all(p in u.slots for p in parts):
                        for ui in u.instances:
                            if all(p in ui.slots for p in parts):
                                ui.slots[comp] = "|".join(ui.slots[p] for p in parts)
                                ui.slot_nodes[comp] = ui.slot_nodes[parts[0]]
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
        for et in self.entity_types.values():
            for t in et.units:
                for sid in list(et.attr_slots[t]):
                    if sid in et.key_slot[t].split("|"):
                        continue
                    vals = set(self.units[t].slots[sid].values)
                    best = None
                    for tid2, ks in keys_of.items():
                        if tid2 == et.tid or not ks:
                            continue
                        ov = len(vals & ks) / len(vals)
                        if ov >= 0.5 and (best is None or ov > best[0]):
                            best = (ov, tid2)
                    if best:
                        et.ref_slots[(t, sid)] = best[1]
                        et.attr_slots[t].discard(sid)
                        et.evidence.append(f"slot {sid} of {t[:30]} references T{best[1]} ({best[0]:.2f})")
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

    def _parent_key(self, ui: UnitInstance) -> str | None:
        if ui.parent_root is None:
            return None
        pt = self.template(ui.sig, ui.parent_root)
        pu = self.units.get(pt)
        if pu is None or not pu.key_slot:
            return None
        for x in pu.instances:
            if x.sig == ui.sig and x.root == ui.parent_root:
                return x.slots.get(pu.key_slot)
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
        return len(pa & pb) / min(len(pa), len(pb)) >= 0.8  # one is the other plus optional parts

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
