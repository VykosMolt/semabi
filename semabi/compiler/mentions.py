"""V1 front end, part 1: units, slots and mentions (deterministic, global).

A *unit* is a repeated structural element (a row, a card, a list item) identified
by its role and anchor (role path from the document root); a *slot* is a
structural position inside a unit or at top level that carries text / widget
state. The catalog summarises units, slots and the values seen at them, plus
observation profiles (which units and static texts co-occur), for the schema
proposer; the grounder uses the same ids to map observations onto entities.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from semabi.compiler.observation import Observation
from semabi.compiler.parse import LEAF_ROLES, WIDGETS, Parser, leaf_label, leaf_value

LIST_CONTAINERS = {"list", "rowgroup", "table"}


@dataclass
class Slot:
    sid: str
    unit: str | None
    rolepath: str
    role: str
    values: Counter = field(default_factory=Counter)
    n: int = 0

    def summary(self, k: int = 10) -> str:
        vals = ", ".join(repr(v) for v, _ in self.values.most_common(k))
        more = f" (+{len(self.values) - k} more)" if len(self.values) > k else ""
        return f"{self.sid} [{self.role} @ {self.rolepath}]: {vals}{more}"


@dataclass
class Unit:
    uid: str
    role: str
    anchor: str
    view: str = "main"
    n_instances: int = 0
    n_obs: int = 0
    slots: dict[str, Slot] = field(default_factory=dict)


@dataclass
class Mention:
    node: int
    unit: str | None
    unit_root: int | None
    unit_index: int
    sid: str
    value: Any
    label: str


@dataclass
class ParsedMentions:
    mentions: list[Mention]
    unit_roots: dict[int, tuple[str, int]]  # root node -> (uid, ordinal)
    profile: tuple  # (units present, static slot ids present)


def rolepath_indexed(obs: Observation, i: int, stop: int) -> str:
    parts = []
    cur = i
    while cur != stop and cur >= 0:
        n = obs.node(cur)
        p = n.parent
        k = 0
        if p >= 0:
            for c in obs.children(p):
                if c == cur:
                    break
                if obs.node(c).role == n.role:
                    k += 1
        parts.append(f"{n.role}#{k}")
        cur = p
    return "/".join(reversed(parts))


def anchor_of(obs: Observation, i: int) -> str:
    return "/".join(obs.node(a).role for a in reversed(obs.ancestors(i))) + "/" + obs.node(i).role


class Catalog:
    """View context: the agent tracks which *view control* (a static button whose
    click deterministically changes the observation profile) it clicked last;
    after a reload/reset the view is recovered by matching the profile."""

    def __init__(self):
        self.parser = Parser()
        self.units: dict[str, Unit] = {}
        self.statics: dict[str, Slot] = {}
        self._unit_by_key: dict[tuple[str, str, str], str] = {}
        self._slot_count = 0
        self.profiles: Counter = Counter()
        self.controls: Counter = Counter()
        self._cache: dict[tuple[str, str], ParsedMentions] = {}
        self.view_controls: dict[str, str] = {}  # static button label -> view name (or family name)
        self.families: dict[str, list[str]] = {}  # family view name -> control labels seen
        self.label_of_step: dict[int, str | None] = {}  # step -> control label active (family views)
        self.view_profiles: dict[str, Counter] = defaultdict(Counter)  # view -> raw profiles seen
        self.view_of_step: dict[int, str] = {}  # step index -> view after the step
        self.initial_view = "main"

    def _new_slot(self, unit: str | None, rolepath: str, role: str) -> Slot:
        s = Slot(f"S{self._slot_count}", unit, rolepath, role)
        self._slot_count += 1
        return s

    def fit_log(self, log) -> None:
        """Fit from an evidence log: detect view controls from the action history,
        then index every observation under its view context."""
        observations = [log.obs(s.after) for s in log.steps]
        if log.steps:
            observations.append(log.obs(log.steps[0].before))
        self.parser.fit(observations, log.typed_tokens)
        self._detect_view_controls(log)
        # pass 1: profiles per view, using only clicks (reloads keep the unknown 'main')
        view = self.initial_view
        for s in log.steps:
            if s.action.kind in ("reload", "reset"):
                view = self.initial_view
            else:
                view = self._next_view(view, s, log)
            self.view_profiles[view][self.raw_profile(log.obs(s.after))] += 1
        # the initial view after a reload is whichever named view has the same profile
        named = {v: p for v, p in self.view_profiles.items() if v != self.initial_view}
        for prof, _ in self.view_profiles[self.initial_view].most_common(3):
            for v, profs in named.items():
                if any(pp[0] == prof[0] for pp in profs):
                    self.initial_view = v
                    break
            if self.initial_view != "main":
                break
        self.view_profiles.pop("main", None)
        self.initial_label = None
        if self.initial_view in self.families:
            # which tab is active after a reload? the first label (leftmost) by convention of the app; unknown otherwise
            self.initial_label = self.families[self.initial_view][0]
        # pass 2: index
        view = self.initial_view
        label = None
        for s in log.steps:
            nv = self._next_view(view, s, log)
            if s.action.kind == "click" and s.action.target_desc and s.action.target_desc.get("name") in self.view_controls:
                label = s.action.target_desc["name"] if nv in self.families else None
            elif s.action.kind in ("reload", "reset"):
                label = self.initial_label if nv in self.families else None
            view = nv
            self.view_of_step[s.step] = view
            self.label_of_step[s.step] = label
            self.index(log.obs(s.after), view)

    def raw_profile(self, obs: Observation) -> tuple:
        """View-independent profile: anchors of unit roots + static leaf labels outside units."""
        roots = self.unit_roots_raw(obs)
        anchors = set()
        for r in roots:
            anchors.add(anchor_of(obs, r))
        owner = set()
        for i, n in enumerate(obs.nodes):
            if i in roots or (n.parent >= 0 and n.parent in owner):
                owner.add(i)
        statics = set()
        for i, n in enumerate(obs.nodes):
            if i in owner:
                continue
            if n.role in LEAF_ROLES and leaf_label(n) and n.role != "textbox":
                statics.add((rolepath_indexed(obs, i, -1), leaf_label(n)))
        return (tuple(sorted(anchors)), tuple(sorted(statics)))

    def _detect_view_controls(self, log) -> None:
        """A static button is a view control if clicking it leads to a profile that is
        (mostly) the same regardless of where it was clicked from, and differs from the
        source profile in most cases."""
        outcomes: dict[str, list[tuple[tuple, tuple]]] = defaultdict(list)
        for s in log.steps:
            if s.action.kind != "click" or not s.action.target_desc:
                continue
            d = s.action.target_desc
            if d.get("role") != "button":
                continue
            before, after = log.obs(s.before), log.obs(s.after)
            # static = not inside a unit
            roots = self.unit_roots_raw(before)
            owner = set()
            for i, n in enumerate(before.nodes):
                if i in roots or (n.parent >= 0 and n.parent in owner):
                    owner.add(i)
            if s.action.target in owner:
                continue
            outcomes[d["name"]].append((self.raw_profile(before), self.raw_profile(after)))
        # position of each static button label (rolepath), to detect object-named tab families
        label_pos: dict[str, Counter] = defaultdict(Counter)
        for s in log.steps:
            if s.action.kind == "click" and s.action.target is not None and s.action.target_desc and s.action.target_desc.get("role") == "button":
                before = log.obs(s.before)
                label_pos[s.action.target_desc["name"]][rolepath_indexed(before, s.action.target, -1)] += 1
        for label, pairs in outcomes.items():
            if len(pairs) < 3:
                continue
            sources = set(b[0] for b, _ in pairs)
            if len(sources) < 2:
                continue  # a tab is reachable from several views; action buttons are not
            targets = Counter(a[0] for b, a in pairs)
            dom, dom_n = targets.most_common(1)[0]
            if dom_n < 0.7 * len(pairs):
                continue
            # clicking it from elsewhere must actually move to the dominant profile
            moved = [1 for b, a in pairs if b[0] != dom and a[0] == dom]
            stayed = [1 for b, a in pairs if b[0] == dom and a[0] == dom]
            if len(moved) + len(stayed) >= 0.7 * len(pairs) and len(moved) >= 1:
                self.view_controls[label] = label
        # families: several control labels at the same static position -> one parameterised view
        pos_labels: dict[str, set[str]] = defaultdict(set)
        for label, poss in label_pos.items():
            pos_labels[poss.most_common(1)[0][0]].add(label)
        fam_target: dict[str, tuple] = {}
        for pos, labels in pos_labels.items():
            if len(labels) >= 2 and any(l in self.view_controls for l in labels):
                fam = "tab@" + pos.rsplit("/", 1)[-1]
                # dominant target unit anchors of this family's controls
                tgt = Counter(a[0] for l in labels for _, a in outcomes.get(l, []))
                key = tgt.most_common(1)[0][0] if tgt else None
                # merge with an existing family leading to the same screen structure
                for f2, k2 in fam_target.items():
                    if key is not None and k2 == key:
                        fam = f2
                        break
                fam_target.setdefault(fam, key)
                for label in labels:
                    self.view_controls[label] = fam
                self.families[fam] = sorted(set(self.families.get(fam, [])) | labels)
        # views named by their control label

    def _next_view(self, view: str, s, log) -> str:
        if s.action.kind in ("reload", "reset"):
            return self.view_from_profile(log.obs(s.after))
        if s.action.kind == "click" and s.action.target_desc and s.action.target_desc.get("name") in self.view_controls:
            return self.view_controls[s.action.target_desc["name"]]
        return view

    def view_from_profile(self, obs: Observation) -> str:
        prof = self.raw_profile(obs)
        best, best_c = self.initial_view, 0
        for view, profs in self.view_profiles.items():
            c = profs.get(prof, 0)
            if c > best_c:
                best, best_c = view, c
        if best_c <= 0:
            # fall back on unit anchors only
            for view, profs in self.view_profiles.items():
                c = sum(n for p, n in profs.items() if p[0] == prof[0])
                if c > best_c:
                    best, best_c = view, c
        return best

    def unit_roots_raw(self, obs: Observation) -> dict[int, bool]:
        roots: dict[int, bool] = {}
        v0 = self.parser.detect_roots(obs)
        for p in range(len(obs.nodes)):
            pn = obs.node(p)
            kids = obs.children(p)
            if kids and pn.role in LIST_CONTAINERS:
                for c in kids:
                    if obs.node(c).role in ("row", "listitem", "cell", "group", "text"):
                        roots[c] = True
        for r in v0:
            if r not in roots and not any(a in roots for a in obs.ancestors(r)):
                roots[r] = True
        # same-role siblings of a unit instance are instances too (an expanded/selected variant)
        for r in list(roots):
            p = obs.node(r).parent
            if p < 0:
                continue
            for c in obs.children(p):
                if c not in roots and obs.node(c).role == obs.node(r).role and obs.children(c):
                    roots[c] = True
        return roots

    # ------------------------------------------------------------ unit roots
    def unit_roots(self, obs: Observation, view: str) -> dict[int, str]:
        return {r: self._unit_id(obs, r, view) for r in self.unit_roots_raw(obs)}

    def _unit_id(self, obs: Observation, r: int, view: str) -> str:
        key = (obs.node(r).role, anchor_of(obs, r), view)
        if key not in self._unit_by_key:
            uid = f"U{len(self.units)}"
            self._unit_by_key[key] = uid
            self.units[uid] = Unit(uid, key[0], key[1], view=view)
        return self._unit_by_key[key]

    # ------------------------------------------------------------ mentions
    def parse(self, obs: Observation, view: str) -> ParsedMentions:
        sig = (obs.structural_signature(), view)
        if sig in self._cache:
            return self._cache[sig]
        roots = self.unit_roots(obs, view)
        ordinal: Counter = Counter()
        unit_roots: dict[int, tuple[str, int]] = {}
        for r in sorted(roots):
            uid = roots[r]
            unit_roots[r] = (uid, ordinal[uid])
            ordinal[uid] += 1
        owner: dict[int, int] = {}
        for i, n in enumerate(obs.nodes):
            if i in roots:
                owner[i] = i
            elif n.parent >= 0 and n.parent in owner:
                owner[i] = owner[n.parent]
        mentions: list[Mention] = []
        static_sids = set()
        for i, n in enumerate(obs.nodes):
            is_leaf = n.role in LEAF_ROLES and (leaf_label(n) or n.role in WIDGETS)
            is_root_text = i in roots and n.name and n.role not in LEAF_ROLES
            if not (is_leaf or is_root_text):
                continue
            root = owner.get(i)
            if root is not None:
                uid, ordn = unit_roots[root]
                rp = rolepath_indexed(obs, i, root) if i != root else n.role + "@self"
                slots = self.units[uid].slots
                key = rp
            else:
                uid, ordn = None, -1
                rp = rolepath_indexed(obs, i, -1)
                slots = self.statics
                key = f"{view}:{rp}"
            if key not in slots:
                slots[key] = self._new_slot(uid, rp, n.role)
            slot = slots[key]
            value = n.name if n.role in ("button", "link") or is_root_text else leaf_value(n)
            mentions.append(Mention(i, uid, root, ordn, slot.sid, value, leaf_label(n) if is_leaf else n.name))
            if uid is None:
                static_sids.add(slot.sid)
        profile = (tuple(sorted(set(u for u, _ in unit_roots.values()))), tuple(sorted(static_sids)))
        pm = ParsedMentions(mentions, unit_roots, profile)
        self._cache[sig] = pm
        return pm

    def index(self, obs: Observation, view: str) -> ParsedMentions:
        pm = self.parse(obs, view)
        self.profiles[pm.profile] += 1
        seen = Counter(uid for uid, _ in pm.unit_roots.values())
        for uid, c in seen.items():
            self.units[uid].n_instances += c
            self.units[uid].n_obs += 1
        for m in pm.mentions:
            s = self.slot(m.sid)
            s.values[m.value] += 1
            s.n += 1
            if m.unit is None and s.role == "button":
                self.controls[m.value] += 1
        return pm

    def slot(self, sid: str) -> Slot:
        for s in self.statics.values():
            if s.sid == sid:
                return s
        for u in self.units.values():
            for s in u.slots.values():
                if s.sid == sid:
                    return s
        raise KeyError(sid)

    # ------------------------------------------------------------ report
    def describe(self, max_vals: int = 10) -> str:
        n_obs = sum(self.profiles.values())
        views = sorted(set([self.initial_view] + list(self.view_controls.values())))
        lines = [f"{n_obs} observations. View controls (static buttons that switch views): {sorted(self.view_controls)}",
                 f"Views: {views}. The view shown after a reload is '{self.initial_view}'."]
        for fam, labels in self.families.items():
            lines.append(f"View '{fam}' is a FAMILY: the same screen reached through differently labelled buttons at one position "
                         f"(labels seen: {labels}); the active label is available to the learner as context slot 'ctx_view:{fam}'.")
        for view in views:
            lines.append(f"== view '{view}'")
            lines.append("   static slots:")
            for key, s in self.statics.items():
                if key.startswith(view + ":"):
                    lines.append("      " + s.summary(max_vals) + f"   [present in {s.n} observations]")
            for u in self.units.values():
                if u.view != view:
                    continue
                lines.append(f"   unit {u.uid} ({u.role} at {u.anchor}): {u.n_instances} instances over {u.n_obs} observations")
                for s in u.slots.values():
                    lines.append("      " + s.summary(max_vals))
        return "\n".join(lines)
