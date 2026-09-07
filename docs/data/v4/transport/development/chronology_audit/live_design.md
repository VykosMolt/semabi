G3 live-normalization design audit. Read-only source review; no new experiment,
production edit, or test edit. The retained execution evidence remains
[results_before_g1.json](results_before_g1.json), described in [report.md](report.md):
the same numbered suffix page yields two objects after offline section
normalization and zero through the live raw-observation path. That witness is
independent of G1 graph ownership and survives the diagnostic G2 probe freeze.

The smallest defensible mechanism is a V4 observation adapter backed by a
normalizer fitted on the allowed **raw** corpus. It must return a consistent
canonical observation to semantic readers while leaving browser observations
and recorded primitive coordinates raw. Putting normalization only in
`ensure`, or replacing `Live.obs` with a canonical page, is insufficient.

The contract below is proposed implementation scope, not an implemented repair
or an execution claim. It preserves V2 modules and avoids any application,
fixture, or family-specific normalization rule.

**Source-backed boundary map**

| Entry or consumer | Current source | Required relationship |
| --- | --- | --- |
| Compilation and repeated promotion builds | `compile_v4.py:26–80,107–178` | Capture raw normalization evidence once; all builds for that fit use the same normalization rule and canonical evidence. |
| Search candidates | `v4/search.py:256–260,323–342,379–382` | A candidate owns its selected `H.G`; reader caches must follow that ownership or be independently constructed from an immutable profile. |
| Offline chronology | `v4/consequence.py:714–732` | Select the allowed raw prefix/frontier before fitting normalization; suffix interpretation cannot update the profile. |
| Direct live interpretation | `v2/abstractor.py:240–271,281–307,598–661,682–699` | `ensure`, `parsed`, `control_family`, and `complete_types` must agree on canonical observation and signature. Inherited `abstract` can reuse corrected `parsed`. |
| Tracking | `v2/abstractor.py:925–944,971–983`; `belief.py:147–153` | A V4 tracker adapter must canonicalize before the inherited observer hashes the page and checks completeness. |
| Grounding | `ground.py:142–182`; `induce.py:309–344` | Parsed ownership, control identities and tracked object roots must name the same canonical tree; returned primitive targets remain original indices. |
| Active form discovery | `active.py:280–335` | Tree walks must use the parsed canonical page, since their stopping root comes from parsed ownership. |
| Live probe paths bypassing A | `v4/probe.py:107–144,184–189`; `run_v4_probe.py:62–75,154–156` | These currently add raw pages directly to G and parse H. They need the same read boundary and the selected graph, with statistics frozen during interpretation. |
| Scoped consequence checks | `v4/consequence.py:823–885,965–1017,1147–1194` | Pre/post trees, bridges, correspondence and verdict dereferences must use one coordinate system per check. Original field nodes retain raw indices. |
| Outcome structural helpers | `v4/outcome.py:759–835,1263–1279` | `A.parsed(obs)` and `_lists_with(obs, target)` must see the same tree. |
| Model-version support diagnostics | `v4/prequential.py:79–99` | A synthetic section root is not a raw node coordinate; cross-model support needs its raw-span provenance. |

`run_v4_transfer._evidence` passes `compiled.log` to the behavioral objective
(`run_v4_transfer.py:31–47`). `objective.evaluate` and `Inducer` then operate on
that log and dispatch through A's tracker/parser. They do not need a second
normalization algorithm. `source_candidates._source_candidates` instead calls
`build_hypotheses` and then reuses the same log directly
(`v4/source_candidates.py:92–105,123–134`); changing the builder to normalize a
hidden copy without updating this caller would mismatch its step signatures.
The older `prospective` routines compile a prefix but score text from the raw
full log (`v4/prospective.py:330–337,382–404`); their text-only checks should not
be silently converted into a different instrument.

**Concrete ownership and data flow**

Add one small V4 module, proposed as `semabi/compiler/v4/normalization.py`, with
an explicit fitted profile, a per-reader runtime object, and a compiler evidence
view. The profile and reader have different lifetimes:

1. `SectionProfile.fit(raw_allowed)` constructs an `ObsGraph` from only the
   allowed raw observations, then sets `learning=False`. It retains a private
   snapshot of that raw graph, the allowed source signatures, and normalization
   policy identity. It receives no hypothesis, candidate reading, operator,
   outcome, or later observation. Its corpus statistics never change.
2. `SectionReader(profile)` owns a separate frozen probe and its runtime
   descriptors/mapping. It adds a new raw page only with learning disabled,
   invokes the existing section-candidate rule, and appends the same empty
   groups as `sections.normalise`. There is no new objecthood heuristic. A
   profile can be shared as immutable input; mutable reader/probe/cache state
   cannot be shared across fitted models or sibling search candidates.
3. A read result carries the current raw page, canonical page, both signatures,
   the raw node count, and a mapping from each synthetic root to its original
   span members. Its canonical page has its **own** recomputed structural
   signature. For every original index, role, name, value, checked state,
   options, placeholder, current flag and bbox remain exactly as supplied;
   only the derived copy's parent relation may change. The raw page is never
   mutated. A page needing no sections can retain the identity fast path.
4. The raw-signature map caches structural normalization decisions and the
   canonical signature, not an old live `Observation` as the universal answer.
   Structural signatures omit URL and bbox (`observation.py:80–83`). Applying
   a cached decision must retain the current snapshot's URL/bboxes. Known
   canonical input from the same profile is a no-op. Canonical input from a
   different profile must be projected back to its retained raw origin and
   reread; treating another model's invented groups as raw evidence is invalid.
5. `prepare_evidence(raw_log, profile)` creates a compiler-owned canonical view
   with copied step records and a raw-to-canonical signature map. It preserves
   raw evidence separately, typed-token/action metadata, and any already-owned
   retained probe metadata. It opens no path. Copying only the step list is
   insufficient: `EvidenceLog.through` shares its `Step` instances
   (`evidence.py:94–101`), so remapping shared steps can corrupt the raw or other
   view. Use a V4 view/factory with owned mutable containers and read-only append
   behavior; keep the shared EvidenceLog implementation unchanged.
6. `compile_v4` prepares one working view before any hypothesis/search/promotion
   work. `build_hypotheses` consumes that canonical view and attaches the fitted
   profile to its resulting G, so copies of H retain the correct profile.
   `V4Abstractor.__init__` creates its own reader from the selected `H.G` profile.
   `search._build` continues to use `Hx.G`, preserving G1. The preparation marker
   or explicit parameter must prevent later `build_hypotheses` calls from
   refitting normalization on already normalized observations.
7. Keep `build_hypotheses`' two-value return compatible. The existing in-place
   `_normalise_sections` helper may remain a facade for compiler-owned working
   logs, returning/storing the profile as well as remapping the log. Public
   compile/source-candidate/live-probe boundaries must first own their working
   copy. Direct builder/search callers must pass the same canonical work log
   to both; do not make the builder secretly canonicalize an inaccessible copy.
   In `run_v4_probe`, retain a separate raw log for browser evidence append.

The profile must preserve the **raw** statistics, not reconstruct them from
`A.G`. `ObsGraph` variation keys include role paths and indexed parent positions
(`v2/graph.py:343–412`); inserted groups change those coordinates even though
they carry no text. Freeze the normalizer before interpreting pages, regardless
of whether the semantic graph is still fitting. Rebuilding after a newly
completed transition creates a new profile/model; it does not thaw an old one.

`RetainedEvidenceLog.from_bytes` carries `probe_records` and disallows writes
(`v4/frozen_evidence.py:16–29,69–77`). The V4 abstractor avoids path reads only
when that attribute survives (`v4/abstractor.py:19–24`). A generic JSON round
trip or base `EvidenceLog.through` can drop it. V4 prepared views and their
slices must preserve metadata already belonging to that view and their
read-only behavior. This is metadata preservation, not a new rule granting a
prefix access to probe records that its evidence boundary excluded.

**Exact V4 reader adaptations**

In `v4/abstractor.py`, expose one `read_observation(obs)`/`canonical(obs)` hook
and use it in these bounded overrides:

- `ensure`: add only `(canonical_signature, canonical_observation)` to the
  semantic graph; preserve G1's `self.G is self.H.G`. Emissions and graph
  statistics retain their existing fit/freeze lifecycle. A raw hash must never
  identify a normalized node array.
- `parsed`: canonicalize, ensure that page, and call `_parse` with the canonical
  array. A canonical signature returned by `ensure` is not enough, because the
  inherited method passes its original argument to `_parse`
  (`v2/abstractor.py:267–270`). On a cache hit with new geometry/URL, return a
  shallow replacement of the cached `ParsedObs` with the current canonical
  `obs`; do not mutate a previously returned parse. Cache structure/slot results
  by canonical signature, with the observation payload belonging to the call.
- `control_family`: delegate the inherited implementation with canonical input.
  It passes that input to `controls.assign` and inspects node parents/paths
  (`v2/abstractor.py:286–305`; `v2/controls.py:212–239`).
- `complete_types`: delegate with canonical input and its matching parse; the
  inherited implementation directly recomputes the signature before
  `H.parse_units` (`v2/abstractor.py:689–691`).
- `make_tracker`: return a V4 tracker adapter whose `observe` canonicalizes once
  before delegating to `V2Tracker.observe`. The existing generic dispatch already
  calls this factory. This aligns the tracker signature, confirmation records,
  completeness, and `_rendered_under(raw.parsed, synthetic_root)`.

Inherited `abstract` can remain unchanged because it consumes `self.parsed` and
does not subsequently traverse its original observation argument. Inherited
`fit_view_controls` is safe only when its entire log is the canonical working
view. Its direct `H.parse_units(step.before)` calls cannot be repaired by an
`ensure` override. Preserve the retained/live probe branches already in the V4
adapter.

The constructor cannot recover the required raw corpus from an arbitrary
already-built normalized G. Compiler and builder construction paths must supply
profile provenance. Any legacy manually constructed `V4Abstractor(G,H)` lacking
that provenance must have an explicit compatibility policy; silently fitting a
new raw normalizer from G would violate the mechanism. The known V4 constructor
sites are the compiler, search builder, and tests that already call the V4
hypothesis builder.

**Grounding and the appended-parent limitation**

Leave `Browser._last_obs`, raw handle tables, `Live.obs`, `Live.refresh`, and
`Live.do` raw. The browser executes the current raw index and builds its target
description from that raw snapshot (`browser.py:245–264`). `Live.do` logs the raw
before/after pair before tracking (`ground.py:46–62`). Replacing those snapshots
globally would put synthetic nodes into the evidence/browser boundary.

With the V4 `parsed` and `control_family` overrides above,
`induce.control_keys`/`describe_target` and `Live.locate` already reach the same
canonical interpretation; they return an original leaf index. A local canonical
`(obs, po)` context in `Live.locate` is optional explicitness, not a reason to
copy or override all of Live. `SchemaGrounder` uses its own raw-signature maps
(`grounder.py:102–127`) and should remain untouched. The planner has no direct
coordinate adaptation to make (`planner.py:146–178`).

Active form discovery is different: it obtains an owner root from `po`, but
walks parents and subtrees in raw `live.obs` (`active.py:280–309`). A raw ancestry
chain cannot reach an appended synthetic owner. At this local semantic walk,
use `po.obs`; fields returned for execution remain original node indices. This
can be a narrow parsed-observation hook at the shared caller, with unchanged
V2 behavior, rather than an unrelated explorer rewrite.

There is an independent pre-existing parser limitation that a stronger
operational G3 gate must address. `_parse` assigns descendant owners in one
flat pass over `obs.nodes`, relying on the parent already being in `owner_of`
(`v2/abstractor.py:509–517`). Appended section parents arrive after their
children. Those controls can therefore become static even when section objects
exist. Updating `node_instance` afterward is insufficient: the same pass already
allocated static/per-instance slots and leaf ordinals (`518–542`).

The two-object-versus-zero parity repair does not, by itself, prove that an
owner-specific button can be grounded. Freeze these as separate acceptance
claims. If G3 includes contained-control execution, make a V4-only adaptation of
that ownership pass: compute nearest instance ownership by ancestry or a
separate parent-first traversal, then allocate leaf slots in the existing
original-node order. V2 has no narrow hook there; an explicit V4 copy of `_parse`
with this one ownership change is more defensible than a subclass trick that
changes how the node array iterates. Do not reorder `Observation.nodes` while
retaining `Node.i`: `Observation.node(i)` is `self.nodes[i]`. Existing unit
instances are already built by DFS (`v2/hypotheses.py:158–178`). This ownership
adaptation is required for that stronger gate, not optional cleanup and not a
demonstrated new execution failure from this read-only audit.

Keep canonical pages out of the existing raw display path as well:
`Observation.render` assumes each parent's depth was assigned earlier in list
order (`observation.py:105–106`). A canonical debug renderer would need its own
tree traversal; reindexing the nodes to make that renderer work would break the
more important action-coordinate contract. Such display work is optional.

**Offline chronology and coordinate-consuming checks**

`consequence.fit` should select `raw_full.through(cut)` or
`raw_full.before_action(cut)` first and fit one profile on exactly that raw view.
For `TRANSDUCTIVE` only, its explicitly wider source corpus remains allowed.
Prepare the canonical full log with a scratch reader from that profile, then
derive its canonical prefix/frontier and pass the same profile provenance into
`compile_v4`. V4 slicing must retain that provenance; `compile_v4` must not
refit normalization from canonical pages. The A-owned reader starts from the
allowed raw profile, not a probe whose retained pages already include the
whole suffix. The scratch full-log reader may see suffix structure only with
learning disabled and is not the semantic learner.

Keep `Fit.log` as the canonical derived log, as the current scorer already
expects, and retain raw origin/mapping separately. This avoids silently changing
the established scorer's tree choice while repairing live parity. Scoring
functions must take both pre and post from that same profile's canonical view:

- `slot_nodes` uses `A.ensure` and `A.H.parse_units`, with synthetic object roots
  as bridge keys but original text/input nodes as the usual bridge values
  (`consequence.py:313–336`). `_under_one_binding` then dereferences the bridge
  value in `pre` and the match result in `post` (`990–1012`). Canonical A parsing
  paired with raw pre/post here would be invalid even though many indices fit.
- `correspondence` traverses ancestors/children all the way from the root
  (`correspondence.py:264–308`). Never normalize one half of a transition, use
  profiles from different cuts, or normalize only the predicted node.
- Preserve actual original field values and the selected mask field (`name`,
  `value`, or `checked`); these are selected by `outcome_field` and compared by
  `leaf_value`. A test must establish raw/canonical equality at every original
  feature index. No learned attribute may replace the observed field value.
- Synthetic roots have no raw node counterpart. The existence fallback can use
  `subject.node` when no raw key-node bridge exists (`consequence.py:1166–1183`).
  It must be dereferenced only in its canonical tree and identified as a
  derived span in provenance. Do not label such an index as an original raw
  observation node or silently clamp it to a raw node. Adding a new raw-span
  existence verdict or changing this fallback to UNKNOWN would change the
  instrument and should be a separately frozen decision, not hidden in G3.
- `outcome.structural_roles` and `structural_selects` should canonicalize at
  entry, or use `po.obs` for `_lists_with`; both currently combine a parse with
  tree walks on their argument. Text-only live-region extraction can continue
  using original values: inserted groups have no text/status channel. Preserve
  missing channel versus empty channel (`emission.py:102–115`).

This recommendation preserves the current scoped instrument's use of derived
section trees. It does not prove the stronger claim that section decisions
themselves are outcome-masked: `sections.candidates` uses the current page's
fillings before correspondence masks the predicted field. That source-level
distinction predates G3. Do not relabel G3 as a repair of that separate
measurement question, nor silently switch all correspondence to raw trees to
avoid discussing it.

`probe.locate` and `renders_family` must acquire a canonical read result through
the profile associated with the selected H/G, then add/read only that canonical
signature. They currently mutate G directly and can learn from newly visited
pages because no freeze is performed there. Interpreting one fitted reading
must not extend its statistics; collecting an observation into the separate
raw log and recompiling is the learning path. Probe outputs should distinguish
the canonical signature used for hypothesis parsing from the raw signature of
the executable snapshot. This avoids redefining the existing raw acquisition
record merely to make parsing work.

**Cache and diagnostic constraints**

No new global raw-signature cache is acceptable: identical raw pages can receive
different section decisions under different allowed prefixes. Keep all runtime
maps under their reader/profile identity. Search copies must not share mutable
normalization probes or canonical log objects. `_KEYS_BEFORE` in outcome is
already keyed by `id(log)` although its content depends on A
(`outcome.py:1436–1464`); sharing one prepared log across fitted readings would
create a direct model-order hazard. A fresh view per Fit avoids introducing that
sharing. Moving that legacy cache into Fit, or solving its independent id-reuse
problem, is separate cleanup.

Correspondence's descriptor cache uses `(id(obs), node)` without retaining the
observation (`correspondence.py:139–150`). Canonical pages used by a scorer must
remain alive and unchanged for the cache's lifetime. Do not generate and discard
temporary canonical pages on each node query while retaining that cache. A
prepared scoring log naturally provides that lifetime.

For prequential representation comparisons, extend the V4 fingerprint with the
normalization profile identity; its current types/slots/control-only digest
omits the normalization semantics (`prequential.py:58–76`). `type_support`
currently records `(sig, o.node)` as raw support. When `o.node` is synthetic,
use its stable raw-span origin, not the appended integer, to compare two models
over the same raw page. These changes are required if G3 is used to make those
diagnostic claims; they are not prerequisites for a narrow in-memory parsing
parity test. No model serialization or pinned-family policy redesign is needed
for the current in-memory live path.

**Meaningful acceptance cases to freeze before implementation**

1. Reuse the preserved numbered witness: the same prefix-only pinned reading
   reads exactly objects `3` and `4` from both live raw Q and the prepared
   offline Q. Their type/key/attribute/reference results, control identities,
   and completeness agree. Also cover a page for which no section qualifies.
2. Preserve G2's five-node future-only counterexample: varying only the future
   outcome never changes the allowed prefix/frontier canonical representation
   under either chronological regime. All-evidence normalization remains equal
   to the existing helper for that bounded corpus.
3. Assert `canonical.structural_signature()` equals every canonical graph/log
   key; raw hashes are unchanged and never label the longer array. Every copied
   step reference resolves. Raw, sibling, and supplied retained step objects
   remain unchanged by canonical remapping.
4. Preserve all original node indices and fields, including `None`, empty
   strings, `False`, empty/nonempty options, placeholder/current and bbox. Missing
   attributes and unseen fields must retain existing unknown/partial-state
   behavior; no new field/type or completeness claim is learned from the suffix.
5. Read two unseen pages in both orders and repeat them. Compare canonical
   structure, parsed objects, controls and tracker results. Verify no growth of
   either normalizer or semantic learned statistics: templates and variation
   counts, vocabulary/header statistics/value paths, emission vocabulary,
   type/slot inventories and learned control families. Per-page descriptors and
   parse caches may grow.
6. Build sibling candidates and models from different prefixes; reading a new
   page in one must not change the other's graphs, profiles, maps, or answers.
   Feed already-canonical input from the same profile and verify no second set
   of groups. Exercise foreign-profile canonical provenance through the explicit
   raw-origin path, rather than silently accepting its invented groups as raw.
7. Two successive snapshots have the same structural signature but different
   URL/bboxes. The latest read exposes current metadata; earlier returned
   parses remain unchanged. This verifies metadata preservation, not a claim
   that the inspected live grounder currently clicks by bbox.
8. For the stronger ownership gate, put identically labelled buttons in two
   inferred sections. Each owner-specific locator must resolve its own original
   button index, neither button may become static, and primitives must target
   only original interactive nodes. This gate needs the separate V4 ownership
   pass adaptation identified above.
9. Track a synthetic root whose index exceeds the raw node count across reset,
   confirmation, a changed rendered value, and a complete-collection absence.
   Check canonical provenance and safe subtree traversal, while retaining
   partial-state unknowns outside a complete collection. Form discovery in one
   inferred section must exclude sibling-section fields.
10. Score a value and an existence claim with canonical pre/post pages from one
    profile. Verify original feature-node text/value/checked equality to raw,
    outcome masking at the correct field, preserved set-valued ambiguity, no
    mixed-array dereference, and explicit derived-span provenance when an
    existence fallback uses a synthetic root. Do not invent a new verdict to
    make the parity test pass.
11. Exercise both direct A readers and the A-bypassing probe functions. Browser
    snapshots, logged observations, action descriptions and raw reload/change
    signatures remain raw. Retained compilation preserves probe metadata and
    performs no path reopen. Existing V1/V2 tracker, parser and grounding tests
    retain their prior behavior; choose existing test files as the homes.

The primary G3 patch can remain in the new V4 normalization module,
`compile_v4.py`, `v4/abstractor.py`, and `v4/consequence.py`, with explicit profile
propagation through `v4/search.py`. Completing the bypass paths additionally
requires the bounded `v4/probe.py`/live-probe caller changes and local canonical
tree use in outcome/active helpers. Broad changes to ObsGraph, Observation,
EvidenceLog, Browser, planner, STRIPS induction, family selection, or the V2
abstractor are unnecessary. The stronger owner-grounding gate and prequential
diagnostic gate have their exact extra requirements above; they must not be
claimed merely because the two-object witness passes.

Source identity at this review includes G1 construction changes and the
unmodified pre-G2 helper. SHA-256:

| File | SHA-256 |
| --- | --- |
| `semabi/compiler/compile_v4.py` | `20f559193b1a5c18c9d6ad3236b6e35ae9047bebdf6f4154ef319fcc83a0e07b` |
| `semabi/compiler/v4/search.py` | `c87e3633207dfaa1483574cad2335b23222bec6fa51fe35526adf8dd9576f72c` |
| `semabi/compiler/v4/abstractor.py` | `4e772cf28d002461de3449e4a939ced2b39a672e629b916612c83bb6ad0625f1` |
| `semabi/compiler/v4/consequence.py` | `158551f35160a79d9c165c767486b63579564dccc3e99febf45d4d714ef0791b` |
| `semabi/compiler/v2/abstractor.py` | `0d9b484e558df2844ce8c21dd5b15d16d894a823ae9cd7152a1421a351dd61d5` |
| `semabi/compiler/v2/graph.py` | `f601fb6bd56d8728a01fdc404c6a0d80636cb2ccba98dab09cd26abf5c425b2a` |
| `semabi/compiler/v2/sections.py` | `4bd39bf7e067a94ec19f6ad6c23c098d13ac01efdabafe2f6e15eb213003ba02` |

These hashes identify source inspection only. G1 verification and the isolated
G2 repair remain separate from this document, and no frozen T1 artifact was
recomputed or altered.
