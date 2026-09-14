"""V4: infer the observation model and the relational world model together.

V2 took the problem in stages -- UI structure, then entities and keys, then semantics. The
V3 benchmark falsified that (docs/v3_result.md, docs/v3_diagnosis.md): on six independently
written applications the compiler was usually wrong about what the entities were at all, and
every number downstream followed from that.

So V4 infers a relational model and its mapping to what is rendered at the same time,
treating identity, attachment, visibility and persistence as hypotheses that predictive
counterexamples refine.
"""
