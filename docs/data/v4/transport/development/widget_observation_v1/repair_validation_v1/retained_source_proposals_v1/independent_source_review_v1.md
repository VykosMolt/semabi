# W2 source review and retained corrections

Reviewer: `/root/baseline_verification/post_controls_review`. Root transcribed
the delivered findings and verdicts after read-only review. These are not
original execution-tool receipts. No native code, collection or tests ran in
this review.

Candidate source v1 was **REPAIR REQUIRED**: a universal physical DOM-owner
check excludes native inherited frame fields whose widget node remains a sibling
of their logical child owner. Candidate source v2 was **REPAIR REQUIRED**:
the replacement `not frame.slots` check observes final parser state and rejects
valid transfers followed by column or attachment materialization. Both rejected
source snapshots remain unchanged; neither is accepted retroactively.

Candidate source v3 is **ACCEPTED for the bounded source proposal**. The reviewer
authenticated the worktree and retained snapshot at SHA-256
`c63ff4e6408c08d976fdfb4a9153d67e6cb1935ca231ee51b32a861648d78fca`,
the v2-to-v3 patch at
`a7ae3a8ba580bef40f2ad942b26102d3201d7b2cdbd5c5eb639750342aae7df0`
and the full objective patch at
`6652862e6743209db2bb487e821ef2e39a8612b7cc3047731498f9d97f3db50e`.
The source diff passes the whitespace check.

The inherited branch requires an immediate raw parent frame, its sole nested
child to be the current owner, absence of the specific transient source value
`sid[1:] + '~'`, and retention of that source's exact node binding. Native frame
transfer alone clears values while retaining their bindings. Ordinary token
creation, later column fields and composite materialization add value/binding
pairs; attachments remove both at their source. The specific-source check thus
allows unrelated later frame fields without granting unsupported attached fields
the earlier owner's persistence.

The ordinary-path gates are unchanged: complete selected-key node/text witnesses
before canonicalization; unique raw witness and actual V2 owner/type/key;
positional, record, mention and context exclusions; exact child persistence and
active source binding; a unique actual attribute emitter across widget and
non-widget sources; reference exclusion; exact emitted owner value; and comparison
of the exact native span. V2's predicate still runs first. V2 scoring source,
`evaluate` and its verdict ordering are unchanged.

The reviewer also found the original stale-binding fixture patched public
`H.parse_units` while this channel uses `H._parse_units(raw_keys=True)`, after
normal abstractor outputs were cached. The versioned fixture must mutate only
the after-page raw result, preserve the owner's key, and remove only the field
value or only its node binding. A manual raw-boundary pre-exercise establishes
the intended mutation and unchanged cached delta. The unchanged objective may
make zero raw calls during scoring; shared verdict expectations must allow that.
Separate positive cases prevent an implementation from simply ignoring this
added observation channel. The original fixture remains retained as superseded
unexecuted evidence.

Execution and adoption remain pending. Runtime compatibility requires the exact
reviewed W3 raw-key parser API and its no-normal-cache-write behavior. Additional
raw parsing may increase search time. Step-level evidence pooling is explicitly
accepted by the contract and does not prove correspondence for every delta atom.
