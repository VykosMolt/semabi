"""REJECTED, kept: drafted when five Book pilot states of the berth holdout went
unestablished under the ordered vocabulary, on the hypothesis that the greedy
generalisation of a pair seed missed a three-occasion rule.  The exact triple
enumeration (vs_exact.py, p28_vs_exact_{ref,pil}.json) agrees with the greedy answer at
every one of 607 held-out states, so the hypothesis is refuted and this was never applied."""
"""Apply after battery #5: the corroborated rule class seeds from pure triples, exactly."""
import pathlib
p = pathlib.Path("/home/moloch/semabi/semabi/compiler/v4/outcome.py"); s = p.read_text()
old = """        here = self._mask(literals)
        out: dict[str, Vouch] = {}
        for event, idxs in self.by_event.items():
            other = [j for j in range(len(self.events)) if self.events[j] != event]
            keep = self._keep(event)
            best, mark = None, None
            for a in range(len(idxs)):
                ma = here & self.masks[idxs[a]] & keep
                for b in range(a + 1, len(idxs)):
                    cond = ma & self.masks[idxs[b]]
                    if any(cond & self.masks[j] == cond for j in other):
                        continue      # the condition reaches an occasion of another event
                    cond = self._generalise(cond, other)
                    covers = sum(1 for i in idxs if cond & self.masks[i] == cond)
                    # Which pure condition to vouch by, where several are pure.  By default the
                    # widest, which is what the greedy learner also prefers.  Under `simplest`,
                    # the one with fewest literals -- guards are short, so Occam should pick the
                    # application's own condition over a coincidence.  **It does not.**  The
                    # shortest separating condition in this language is an object's key, so the
                    # preference selects memorisation; asking cellar for it returned `id = B1`.
                    # Measured on every application and it changes nothing else, so: off, kept
                    # for what it revealed.  See `docs/v4_admissibility.md`.
                    if corroborated and simplest and covers <= 2:
                        # Only corroborated candidates may compete, or preferring a short
                        # condition could discard an event whose *longer* condition was
                        # admissible -- refusing more, which would look like an improvement
                        # and would not be one.
                        continue
                    score = ((-_bits(cond), covers) if simplest else (covers,))
                    if best is None or score > mark:
                        best, mark = Vouch(event, (idxs[a], idxs[b]),
                                           self._condition(cond), covers), score
                    if not corroborated:
                        break
                if best is not None and not simplest and (not corroborated or best.covers > 2):
                    break
            if best is not None and (not corroborated or best.covers > 2):
"""
new = """        here = self._mask(literals)
        out: dict[str, Vouch] = {}
        for event, idxs in self.by_event.items():
            other = [j for j in range(len(self.events)) if self.events[j] != event]
            best, mark = None, None
            for witnesses, cond in self._seeds(idxs, here & self._keep(event), other,
                                               corroborated=corroborated, simplest=simplest):
                cond = self._generalise(cond, other)
                covers = sum(1 for i in idxs if cond & self.masks[i] == cond)
                # Which pure condition to vouch by, where several are pure.  By default the
                # widest, which is what the greedy learner also prefers.  Under `simplest`,
                # the one with fewest literals -- guards are short, so Occam should pick the
                # application's own condition over a coincidence.  **It does not.**  The
                # shortest separating condition in this language is an object's key, so the
                # preference selects memorisation; asking cellar for it returned `id = B1`.
                # Measured on every application and it changes nothing else, so: off, kept
                # for what it revealed.  See `docs/v4_admissibility.md`.
                if corroborated and simplest and covers <= 2:
                    # Only corroborated candidates may compete, or preferring a short
                    # condition could discard an event whose *longer* condition was
                    # admissible -- refusing more, which would look like an improvement
                    # and would not be one.
                    continue
                score = ((-_bits(cond), covers) if simplest else (covers,))
                if best is None or score > mark:
                    best, mark = Vouch(event, witnesses, self._condition(cond), covers), score
                if not simplest and (not corroborated or best.covers > 2):
                    break
            if best is not None and (not corroborated or best.covers > 2):
"""
assert s.count(old) == 1; s = s.replace(old, new)
anchor = "    # ------------------------------------------------------------ the decision-list class\n"
helper = '''    def _seeds(self, idxs: list[int], here: int, other: list[int], *,
               corroborated: bool, simplest: bool):
        """Witness sets of one event whose shared conjunction with the query is pure.

        Pairs decide the uncorroborated question exactly.  The corroborated one was seeded
        from a pure pair and completed by greedy generalisation, which finds a third
        occasion only if the drop order happens to widen past the witnesses: a richer query
        enlarges the pair's conjunction, the same order can settle on a cover of two, and
        the class then says nothing where a three-occasion rule exists (the pilot bookings
        of harbour's berth holdout, once the ordered vocabulary reached the query).  A pure
        conjunction covering three occasions exists iff some triple's shared conjunction
        with the query is pure, and a triple is pure only if each of its pairs is, so the
        pure pairs are found first and the triples grown from them."""
        triples = corroborated and not simplest
        pure: dict[int, set[int]] = {}
        for a in range(len(idxs)):
            ma = here & self.masks[idxs[a]]
            for b in range(a + 1, len(idxs)):
                cond = ma & self.masks[idxs[b]]
                if any(cond & self.masks[j] == cond for j in other):
                    continue
                if triples:
                    pure.setdefault(a, set()).add(b)
                    continue
                yield (idxs[a], idxs[b]), cond
                if not corroborated:
                    break      # one pair per first witness, as the pair search always did
        for a in sorted(pure):
            for b in sorted(pure[a]):
                for c in sorted(pure[a] & pure.get(b, set())):
                    cond = here & self.masks[idxs[a]] & self.masks[idxs[b]] & self.masks[idxs[c]]
                    if not any(cond & self.masks[j] == cond for j in other):
                        yield (idxs[a], idxs[b], idxs[c]), cond

'''
assert s.count(anchor) == 1; s = s.replace(anchor, helper + anchor)
p.write_text(s); print("applied")
