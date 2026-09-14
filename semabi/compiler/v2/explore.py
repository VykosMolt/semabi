"""Exploration with probes and surveys, not just random actions.

A passive trace cannot settle two things: whether a change is domain state or interface
state, and what a change did to the other views. Both need an intervention.

A persistence probe reloads the first time an action kind changes the page; if the page
differs from the last known one, something persisted. It then visits every navigation
control and compares each view with its last rendering. Each probed action kind ends up
DOMAIN, VIEW or UNDETERMINED in probes.jsonl.

A survey does the same visiting, occasionally, after other page-changing actions.

Navigation controls are the static buttons present in nearly every observation so far;
nothing else is assumed.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Callable, Any

from semabi.compiler.browser import Primitive
from semabi.compiler.explorer import Explorer, affordance_key
from semabi.compiler.observation import Observation
from semabi.compiler.parse import Parser


class SurveyExplorer(Explorer):
    def __init__(self, browser, log, seed: int = 0, survey_prob: float = 0.3):
        super().__init__(browser, log, seed=seed, reload_prob=0.0)
        self.survey_prob = survey_prob
        self.button_presence: Counter = Counter()
        self.n_obs = 0
        self.P = Parser()
        self.probed: dict[tuple, str] = {}
        self.probe_count: Counter = Counter()
        self.last_view_obs: dict[str, str] = {}  # nav name -> signature at the last visit (this episode)
        self.last_reload_obs: str | None = None
        self.default_skeleton: frozenset | None = None  # role-path set of the view a reload shows
        self.fresh = False  # every view's rendering is known since the last page-changing action
        self.pending: list[tuple] = []  # page-changing actions since the last probe (their effects are mixed in)
        self.post_reload_views: dict[str, str] = {}  # view renderings at the last post-reload survey
        self.probes_path = Path(log.dir) / "probes.jsonl"

    # ----------------------------------------------------------- navigation
    def _static_buttons(self, o: Observation):
        roots = self.P.detect_roots(o)
        inside = set()
        for i, n in enumerate(o.nodes):
            if i in roots or (n.parent >= 0 and n.parent in inside):
                inside.add(i)
        return [n for n in o.nodes if n.role == "button" and n.i not in inside]

    def note(self, o: Observation) -> None:
        self.n_obs += 1
        for n in self._static_buttons(o):
            self.button_presence[n.name] += 1

    def nav_names(self) -> list[str]:
        if self.n_obs < 5:
            return []
        return [name for name, c in self.button_presence.items() if c >= 0.9 * self.n_obs][:8]

    @staticmethod
    def skeleton(o: Observation) -> frozenset:
        paths = {}
        # walked, not taken in list order: `sections.normalise` appends its containers
        stack = [n.i for n in o.nodes if n.parent < 0]
        for r in stack:
            paths[r] = o.node(r).role
        while stack:
            x = stack.pop()
            for c in o.children(x):
                paths[c] = paths[x] + "/" + o.node(c).role
                stack.append(c)
        for n in o.nodes:
            paths.setdefault(n.i, n.role)
        return frozenset(paths.values())

    def track(self, obs: Observation) -> None:
        """Remember the rendering of the default view whenever we are looking at it."""
        if self.default_skeleton is not None and self.skeleton(obs) == self.default_skeleton:
            self.last_reload_obs = obs.structural_signature()

    def survey(self, obs: Observation, episode: int) -> tuple[Observation, list[str]]:
        changed = []
        for name in self.nav_names():
            t = next((n for n in self._static_buttons(obs) if n.name == name), None)
            if t is None:
                continue
            obs = self.step(obs, episode, Primitive("click", t.i))
            self.note(obs)
            self.track(obs)
            sig = obs.structural_signature()
            if name in self.last_view_obs and self.last_view_obs[name] != sig:
                changed.append(name)
            self.last_view_obs[name] = sig
        self.fresh = True
        return obs, changed

    # ----------------------------------------------------------- probe
    def probe(self, obs: Observation, episode: int, key: tuple, step_index: int) -> Observation:
        before_reload = self.last_reload_obs
        obs = self.step(obs, episode, Primitive("reload"))
        self.note(obs)
        sig = obs.structural_signature()
        persisted_default = None if before_reload is None else (sig != before_reload)
        self.last_reload_obs = sig
        if self.default_skeleton is None:
            self.default_skeleton = self.skeleton(obs)
        obs, _ = self.survey(obs, episode)
        # compare with the previous post-reload survey: selection state is reset by both reloads,
        # so differences are domain changes made by the actions in between
        changed_views = [n for n, sg in self.last_view_obs.items() if n in self.post_reload_views and self.post_reload_views[n] != sg]
        comparable = bool(self.post_reload_views)
        self.post_reload_views = dict(self.last_view_obs)
        mixed = [k for k in self.pending if self.probed.get(k) != "VIEW"]
        self.pending = []
        if not comparable:
            status = "UNDETERMINED"
        elif mixed:
            status = "UNDETERMINED" if (persisted_default or changed_views) else "VIEW"
        elif persisted_default or changed_views:
            status = "DOMAIN"
        else:
            status = "VIEW"
        # a key is DOMAIN once any attempt persisted (a first attempt may have been refused)
        self.probe_count[key] += 1
        if self.probed.get(key) != "DOMAIN":
            self.probed[key] = status
        with self.probes_path.open("a") as f:
            f.write(json.dumps({"step": step_index, "key": list(key), "status": status, "mixed": [list(k) for k in mixed],
                                "persisted_default": persisted_default, "changed_views": changed_views}) + "\n")
        return obs

    def want_probe(self, key: tuple) -> bool:
        """Probe a new action kind; re-probe VIEW/UNDETERMINED kinds up to three times (a
        first attempt may have been refused or mixed with other actions)."""
        st = self.probed.get(key)
        return st is None or (st != "DOMAIN" and self.probe_count[key] < 3)

    def controlled_persistence_probe(self, obs: Observation, episode: int, primitive: Primitive,
                                     component_id: str, identity: dict[str, Any],
                                     value_of: Callable[[Observation, dict[str, Any]], Any],
                                     predictions: dict[str, Any]) -> tuple[Observation, dict[str, Any]]:
        """Execute one hypothesis-targeted action -> reload -> survey intervention.

        `identity` and `value_of` are compiler-side mention descriptors.  They contain
        only rendered structure/values; no evaluator annotation is available here.
        """
        before_sig = obs.structural_signature()
        before_value = value_of(obs, identity)
        action_step = len(self.log.steps)
        after = self.step(obs, episode, primitive)
        self.note(after)
        self.track(after)
        after_sig = after.structural_signature()
        after_value = value_of(after, identity)

        reloaded = self.step(after, episode, Primitive("reload"))
        self.note(reloaded)
        reload_sig = reloaded.structural_signature()
        reload_value = value_of(reloaded, identity)
        baseline_views = dict(self.post_reload_views or self.last_view_obs)
        self.last_reload_obs = reload_sig
        surveyed, _ = self.survey(reloaded, episode)
        changed_views = sorted(name for name, sig in self.last_view_obs.items()
                               if name in baseline_views and baseline_views[name] != sig)
        self.post_reload_views = dict(self.last_view_obs)

        chosen = primitive.text if primitive.kind in ("select", "type") else after_value
        persisted = chosen is not None and reload_value == chosen and before_value != chosen
        if persisted:
            status = "DOMAIN"
        elif reload_value == before_value and not changed_views:
            status = "VIEW"
        else:
            status = "UNDETERMINED"
        key = affordance_key(obs, primitive)
        record = {
            "step": action_step,
            "key": list(key),
            "status": status,
            "controlled": True,
            "component_id": component_id,
            "identity": identity,
            "predictions": predictions,
            "before_sig": before_sig,
            "after_sig": after_sig,
            "reload_sig": reload_sig,
            "before_value": before_value,
            "after_value": after_value,
            "reload_value": reload_value,
            "chosen_value": chosen,
            "same_mention_value_persisted": persisted,
            "changed_views": changed_views,
            "mixed": [],
        }
        with self.probes_path.open("a") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
        with (Path(self.log.dir) / "interventions_v2.jsonl").open("a") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
        self.probed[key] = status
        self.probe_count[key] += 1
        return surveyed, record

    def run(self, n_episodes: int, steps_per_episode: int, seed_base: int = 0) -> None:
        obs = self.b.observe()
        self.note(obs)
        for ep in range(n_episodes):
            obs = self.step(obs, self.b.episode + 1, Primitive("reset", text=str(seed_base + ep)))
            episode = self.b.episode
            self.note(obs)
            self.last_view_obs = {}
            self.pending = []
            self.last_reload_obs = obs.structural_signature()
            if self.default_skeleton is None:
                self.default_skeleton = self.skeleton(obs)
            obs, _ = self.survey(obs, episode)  # known rendering of every view at the start
            self.post_reload_views = dict(self.last_view_obs)
            for i in range(steps_per_episode):
                p = self.choose(obs)
                key = affordance_key(obs, p)
                before = obs
                step_index = len(self.log.steps)
                obs = self.step(obs, episode, p)
                self.note(obs)
                self.track(obs)
                if obs.structural_signature() == before.structural_signature():
                    continue
                self.fresh = False
                nav = (p.kind == "click" and p.target is not None and before.node(p.target).name in self.nav_names())
                if nav:
                    self.last_view_obs[before.node(p.target).name] = obs.structural_signature()
                elif p.kind in ("click", "select", "press") and self.want_probe(key):
                    obs = self.probe(obs, episode, key, step_index)
                else:
                    if p.kind in ("click", "select", "press"):
                        self.pending.append(key)
                    if p.kind in ("click", "select", "press") and self.rng.random() < self.survey_prob:
                        obs, _ = self.survey(obs, episode)
            obs = self.step(obs, episode, Primitive("reload"))
