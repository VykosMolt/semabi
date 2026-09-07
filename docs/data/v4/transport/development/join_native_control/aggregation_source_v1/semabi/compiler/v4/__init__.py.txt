"""V4: joint inference of the observation model and the relational world model.

V2 factored the problem as UI structure -> point-estimate entities and keys -> semantics.
gauntlet-v3 falsified that factorization (docs/v3_result.md, docs/v3_diagnosis.md): on six
independently authored applications the compiler was usually wrong about what the entities
were at all, and every downstream number followed from that.

The V4 thesis: jointly infer a behaviourally sufficient relational world model and its
observation mapping from black-box interaction, treating entity identity, attachment,
visibility and persistence as hypotheses refined by predictive counterexamples.
"""
