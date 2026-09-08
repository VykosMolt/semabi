# Independent source review of W2 revision 2

The read-only reviewer `/root/sidecar_review` accepts the revision's exclusion of
competing attribute emitters, exact promoted-span comparison and unsupported
checked-state channels. No native execution occurred.

One material reference gap remains. `V2Abstractor._resolve_slot` can expand the
selected span or resolve another span from the same node. A unique source slot
does not identify the span that supplied the emitted reference. The compared
span could change while the reference is supplied by an unchanged fallback.

Root adopts the reviewer's bounded alternative: revision 3 adds widget evidence
only for emitted attributes, excluding reference slots from this added channel.
Reference-contributor provenance remains a separate follow-up. A negative test
must retain a changing span with an unchanged reference resolved from another
span. This closes the identified path by scope; it does not claim reference
support has been implemented or measured.
