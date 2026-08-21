"""Phase-1 exploration: novelty-weighted random primitives with reload/reset.

No semantics assumed. Affordances are enumerated from the observation; typed
strings are fresh unique tokens so that they can later anchor object identity.
"""
from __future__ import annotations

import random
import string
from collections import Counter

from semabi.compiler.browser import Browser, Primitive
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.observation import Observation


def fresh_token(rng: random.Random, existing: set[str]) -> str:
    while True:
        t = "".join(rng.choice(string.ascii_lowercase) for _ in range(2)) + "".join(rng.choice(string.digits) for _ in range(2))
        if t not in existing:
            return t


def affordance_key(obs: Observation, p: Primitive) -> tuple:
    if p.target is None:
        return (p.kind, p.text if p.kind == "press" else None)
    n = obs.node(p.target)
    return (p.kind, n.role, n.name or n.placeholder or "", p.text if p.kind == "select" else None)


def enumerate_affordances(obs: Observation, rng: random.Random, typed: set[str]) -> list[Primitive]:
    out = []
    for n in obs.interactive():
        if n.role in ("button", "link", "checkbox", "radio"):
            out.append(Primitive("click", n.i))
        elif n.role == "textbox":
            out.append(Primitive("type", n.i, fresh_token(rng, typed | obs.texts())))
        elif n.role == "combobox":
            for o in n.options or []:
                if o != n.value:
                    out.append(Primitive("select", n.i, o))
    out.append(Primitive("press", text="Enter"))
    return out


class Explorer:
    def __init__(self, browser: Browser, log: EvidenceLog, seed: int = 0, reload_prob: float = 0.08):
        self.b = browser
        self.log = log
        self.rng = random.Random(seed)
        self.reload_prob = reload_prob
        self.counts: Counter = Counter()
        self.last_typed_target: int | None = None

    def step(self, obs: Observation, episode: int, p: Primitive) -> Observation:
        res = self.b.act(p)
        after = self.b.observe()
        self.log.add_step(episode, p, res.ok, res.error, obs, after)
        self.counts[affordance_key(obs, p)] += 1
        # remember where we typed so that the next choice can favour nearby buttons
        self.last_typed_target = p.target if p.kind == "type" else None
        return after

    def choose(self, obs: Observation) -> Primitive:
        affs = enumerate_affordances(obs, self.rng, set(self.log.typed_tokens))
        # novelty weight: 1/(1+count)^2, typing slightly favoured so that buttons
        # near textboxes get meaningful input, pressing Enter rarely
        weights = []
        for p in affs:
            k = affordance_key(obs, p)
            w = 1.0 / (1 + self.counts[k]) ** 2
            if p.kind == "press":
                w *= 0.15
            if p.kind == "type":
                w *= 1.5
            if self.last_typed_target is not None and p.kind == "click" and p.target is not None:
                # form-completion prior: buttons sharing an ancestor within 2 levels of the textbox
                ta = obs.ancestors(self.last_typed_target)[:2]
                if set(obs.ancestors(p.target)[:2]) & set(ta):
                    w *= 6.0
            weights.append(w)
        return self.rng.choices(affs, weights)[0]

    def run(self, n_episodes: int, steps_per_episode: int, seed_base: int = 0) -> None:
        if self.b._last_obs is None:
            self.b.goto()
            self.b.observe()
        obs = self.b._last_obs
        for ep in range(n_episodes):
            # the reset itself is evidence (episode lineage): logged as a step
            obs = self.step(obs, self.b.episode + 1, Primitive("reset", text=str(seed_base + ep)))
            episode = self.b.episode
            for i in range(steps_per_episode):
                if i > 0 and self.rng.random() < self.reload_prob:
                    obs = self.step(obs, episode, Primitive("reload"))
                    continue
                obs = self.step(obs, episode, self.choose(obs))
            obs = self.step(obs, episode, Primitive("reload"))
