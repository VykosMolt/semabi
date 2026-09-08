# Two bounded corrections

The six files bound by `preparation_manifest_v1.json` remain unchanged.

`source_evidence_amendment_v2.json` adds the missing binding for
`semabi/compiler/v2/abstractor.py`, 52,053 bytes, SHA-256
`0d9b484e558df2844ce8c21dd5b15d16d894a823ae9cd7152a1421a351dd61d5`.
That file implements the inherited abstract-state view construction and
`_instance_widgets`. `V4Abstractor` subclasses it and delegates ordinary
`EvidenceLog` view-control fitting to V2. The original source-evidence field
attributed inherited view construction to the V4 subclass; this amendment
corrects that attribution without changing native code.

`control_v2.py` is the exact held `control_v1.py` plus one admission check:
the family recovered from all four radios must equal `radio:Select receiver`.
The existing parsed-family recovery, strict slot-value check, native collection
guard, copied-cache policy, owner admission, two arms, query collection and
equivalence checks are otherwise identical. The exact change is retained in
`control_v2_from_v1.patch`. No replacement family string is invented for the
intervention, and a guard veto remains a possible result.

The normal-fitting input audit and the proposed driver are preparation for a
separate root-reviewed execution. `read_outputs=True` permits normal fitting on
the disclosed observed training outputs. It does not authorize held-out outcome
scoring. Neither version of the control nor the proposed driver has been run.
