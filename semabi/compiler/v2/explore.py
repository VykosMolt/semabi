"""V2 exploration: random actions interleaved with *surveys* and *reload probes*.

Passive traces leave two questions open that no amount of inference settles:
(1) what a change did to the representations in the other views (needed for
cross-view identity: the floor-plan slot that appears when a catalogue row's
location changes) and (2) whether a change is domain state or interface state
(a selection, a dialog, a feedback line). Both are answered by interventions:

  survey : after an action that changed the page, visit every navigation control
           once (so that every representation is observed within a step or two of
           the change), then continue from wherever that leaves us;
  reload : after an action that changed the page, reload once in a while: what
           survives is domain state, what does not is interface state.

Navigation controls are static buttons (outside every repeated unit) that are
present in nearly every observation so far; no other knowledge is assumed.
"""
from __future__ import annotations

import random
from collections import Counter

from semabi.compiler.browser import Primitive
from semabi.compiler.explorer import Explorer, view_sweep
from semabi.compiler.observation import Observation
from semabi.compiler.parse import Parser


class SurveyExplorer(Explorer):
    def __init__(self, browser, log, seed: int = 0, survey_prob: float = 0.6, reload_prob: float = 0.25):
        super().__init__(browser, log, seed=seed, reload_prob=0.0)
        self.survey_prob = survey_prob
        self.probe_reload_prob = reload_prob
        self.button_presence: Counter = Counter()
        self.n_obs = 0
        self.P = Parser()

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

    def survey(self, obs: Observation, episode: int) -> Observation:
        for name in self.nav_names():
            t = next((n for n in self._static_buttons(obs) if n.name == name), None)
            if t is None:
                continue
            obs = self.step(obs, episode, Primitive("click", t.i))
            self.note(obs)
        return obs

    def run(self, n_episodes: int, steps_per_episode: int, seed_base: int = 0) -> None:
        obs = self.b.observe()
        self.note(obs)
        for ep in range(n_episodes):
            obs = self.step(obs, self.b.episode + 1, Primitive("reset", text=str(seed_base + ep)))
            episode = self.b.episode
            self.note(obs)
            for i in range(steps_per_episode):
                before = obs
                p = self.choose(obs)
                obs = self.step(obs, episode, p)
                self.note(obs)
                if obs.structural_signature() == before.structural_signature():
                    continue
                if p.kind in ("click", "select", "press") and self.rng.random() < self.survey_prob:
                    obs = self.survey(obs, episode)
                if self.rng.random() < self.probe_reload_prob:
                    obs = self.step(obs, episode, Primitive("reload"))
                    self.note(obs)
            obs = self.step(obs, episode, Primitive("reload"))
