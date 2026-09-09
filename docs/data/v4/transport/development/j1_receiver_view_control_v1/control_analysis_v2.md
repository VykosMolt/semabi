# Receiver-view control: actual result

The single frozen run supports the checked-owner projection for this admitted
naming boundary. It does not establish ordinary learned JOIN or transport.

The unchanged wrapper finished on 2026-09-09 at 15:54:08 UTC with child return
code zero and confirmed termination. Root reaped exec session 75861 (completion
chunk `f4b932`, exit zero), then preserved all 19 raw files before interpreting
the query payloads. The [raw manifest](raw_preservation_v2.json) has SHA-256
`e64545340227afae62ef6bd38898fcd299a1b4566c673fb19367418c4fb11a2a`.
The execution receipt reports one fit, one completed control, verified
postflight, and no findings. Root and a separate read-only reviewer inspected
the actual result and owner mapping.

| Observation / training step | Checked raw container owner | A denotation | B denotation |
| --- | --- | --- | --- |
| `06f4a3dad59b9656` / 0 | none | empty | empty |
| `3821550301c5b69f` / 36 | T1 / Qir | empty | T1 / Qir |
| `de1da1d18aed05e3` / 75 | T1 / Tav | empty | T1 / Tav |
| `5c64d2b807fd478e` / 101 | T1 / Yuk | empty | T1 / Yuk |
| `b85b3b735272a749` / 153 | T1 / Nes | empty | T1 / Nes |

Raw radio nodes 30/36/42/48 map to parsed instances 4/5/6/7, container roots
27/33/39/45, and the corresponding native owners Qir/Tav/Nes/Yuk. Raw and
normalized signatures agree. A proposes no selection query; B proposes exactly
the existing `radio:Select receiver` family query. All five A/B guard maps agree,
with no family veto. Non-view state is equal across arms, and the only B view
delta is the checked owner's key under that family. Before, after, and final
captures agree; identity tokens are stable and typed-copy errors are empty.

Decision: implement a general checked-owner projection in the ordinary V4
observation path, using only already established owners and observed checked
state. Keep conservative behavior for missing/ambiguous owners, positional or
provisional identities, colliding families, and ambiguous key matches. Follow
with focused unit and ordinary-path integration checks.

The four query-learning bindings were supplied from the checked raw owner.
Those bindings and B's encoded value share a derivation, so agreement is not
independent proof of owner correctness. This retrospective five-state control
supplies no patch object, patch identity, endpoint reference, action binding,
existential witness, production grounding, or prospective transport result.
The separate reviewer accepted the bounded result with these residual limits.
