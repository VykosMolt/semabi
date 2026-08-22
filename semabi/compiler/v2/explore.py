"""V2 exploration: random actions with *persistence probes* and *surveys*.

Passive traces leave two questions open that no amount of inference settles:
(1) whether a change is domain state or interface state (a selection, a dialog, a
feedback line) and (2) what a change did to the representations in the other
views (needed for cross-view identity). Both are answered by interventions:

  persistence probe : the first time an action kind (role + label) changes the page,
                      reload; if the page after the reload differs from the last known
                      page of that view, something persisted (domain state); then
                      survey every navigation control and compare each view with its
                      last known rendering. Every probed action kind gets a label-free
                      status DOMAIN / VIEW / UNDETERMINED, recorded in probes.jsonl.
  survey            : after other page-changing actions, with some probability, visit
                      every navigation control once (precise co-change evidence).

Navigation controls are static buttons (outside every repeated unit) present in
nearly every observation so far; nothing else is assumed.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

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
        self.last_view_obs: dict[str, str] = {}  # nav name -> signature at the last visit (this episode)
        self.last_reload_obs: str | None = None
        self.default_skeleton: frozenset | None = None  # role-path set of the view a reload shows
        self.fresh = False  # every view's rendering is known since the last page-changing action
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
        for n in o.nodes:
            paths[n.i] = n.role if n.parent < 0 else paths[n.parent] + "/" + n.role
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
        obs, changed_views = self.survey(obs, episode)
        if persisted_default or changed_views:
            status = "DOMAIN"
        elif persisted_default is False and self.last_view_obs:
            status = "VIEW"
        else:
            status = "UNDETERMINED"
        self.probed[key] = status
        with self.probes_path.open("a") as f:
            f.write(json.dumps({"step": step_index, "key": list(key), "status": status,
                                "persisted_default": persisted_default, "changed_views": changed_views}) + "\n")
        return obs

    def probed_ok(self, key: tuple) -> bool:
        return all(self.probed.get(k) is None for k in (key,))

    def run(self, n_episodes: int, steps_per_episode: int, seed_base: int = 0) -> None:
        obs = self.b.observe()
        self.note(obs)
        for ep in range(n_episodes):
            obs = self.step(obs, self.b.episode + 1, Primitive("reset", text=str(seed_base + ep)))
            episode = self.b.episode
            self.note(obs)
            self.last_view_obs = {}
            self.last_reload_obs = obs.structural_signature()
            if self.default_skeleton is None:
                self.default_skeleton = self.skeleton(obs)
            obs, _ = self.survey(obs, episode)  # known rendering of every view at the start
            for i in range(steps_per_episode):
                p = self.choose(obs)
                key = affordance_key(obs, p)
                if key not in self.probed and not self.fresh and p.kind in ("click", "select", "press"):
                    obs, _ = self.survey(obs, episode)  # a probe needs every view's rendering to be current
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
                elif p.kind in ("click", "select", "press") and key not in self.probed and self.probed_ok(key):
                    obs = self.probe(obs, episode, key, step_index)
                elif p.kind in ("click", "select", "press") and self.rng.random() < self.survey_prob:
                    obs, _ = self.survey(obs, episode)
            obs = self.step(obs, episode, Primitive("reload"))
