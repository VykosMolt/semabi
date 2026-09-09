# Bounded rendered-value candidate review

Decision: revise before adoption. The inline aggregation is useful, but paragraph text needs a local completeness condition before it can serve as a record witness.

Scope: read-only inspection of the isolated candidate and current matching code; synthetic HTML only. No application calls, reserved UI inspection, source edits, or completed-assessment re-diagnosis. No general presentation-transport claim.

Reviewed bytes:

- Main `semabi/compiler/browser_session.py`: `bd16840231dab7ed0e20783a56e304e78f33258d67e5f048ed4df03e95975cab`
- Candidate `/tmp/semabi_rendered_value_candidate/semabi/compiler/browser_session.py`: `d8518fa80537ff414a12c894d5367a6c2907abc73d9f5fd06bfe7c7cb703b799`
- Main `semabi/compiler/surface.py`: `c735c6f7cd243741cd92bb072f33cbc22b19543b0b073b5eb6288246d1adaf6c`
- Main `semabi/compiler/runtime.py`: `ba4d8eef0bab7fbd38982161319b1824063f540c3b3c62d427a1ec2274b85ba1`

Evidence from Chromium, using static `page.set_content`, all requests aborted, and the actual SURFACE_JS strings parsed from each reviewed file. `Surface` and `record_witness` came from main and are unchanged in the candidate. No app origin was accessed.

| Learned text slot | Current HTML inside article | Main accepts | Candidate accepts | Meaning |
| --- | --- | --- | --- | --- |
| `<p>Expected</p>` | `<p>Ex<strong>pect</strong>ed</p>` | false | true | Useful complete inline reconstruction |
| `<p>Expected</p>` | `<p>Expected<span style="display:block"> extra</span></p>` | true | true | Direct-text prefix can falsely retain the paragraph slot |
| `<p>Expected</p>` | `<p>Expected<span aria-hidden="true"> extra</span></p>` | true | true | Visible suffix is excluded from aggregation but ownText remains a prefix witness |
| `<p><span>Expected</span></p>` | `<p><span>Expected</span> extra</p>` | true | true | Successful aggregation still leaves a partial descendant eligible at the learned leaf slot |
| `<p><span>Expected</span></p>` | `<p><span>Expected</span><span style="display:block">extra</span></p>` | true | true | Removing only the paragraph fallback name would leave a descendant bypass |

Additional synthetic observations: the candidate's reconstructed `Expected` inside an article nested in a native form with textarea and Save remained excluded as a draft preview. A paragraph containing a link named `Expected` did not reuse the learned plain-paragraph text slot. An opacity-zero suffix did not appear in either snapshot's paragraph/descendant names in the tested simple case. The patch does not change editor exclusion or link-destination channels; this is not an audit of all preexisting descendant innerText fallbacks.

One recommended mechanism: carry paragraph-local text-witness eligibility as Surface metadata, leaving observation names available for ordinary UI inspection. For a noneditable P/PRE with a complete accepted aggregate, a node inside that paragraph may supply a text witness only when its full normalized name equals that complete paragraph value. When aggregation declines, exclude text witnesses from that whole paragraph subtree. Apply the same eligibility to anchor matching, record `texts`, and relative text slots. Keep link-destination matching independent. Include the metadata in settling signatures and trace serialization. This preserves the existing deepest-equal-node path rule for fully wrapped complete values, while preventing both direct and descendant prefixes from claiming completeness.

This is a local field-completeness rule, not a general DOM rewrite, semantic field discovery, or wrapper-invariant matching. P/PRE containing unsupported widgets or blocks remain conservatively unestablished. All other element handling and editor safety stay within the existing contract.

Execution receipts: initial sandbox launch produced no output and was interrupted with exit 130 (tool chunk `37ab65`); no completion was claimed for that attempt. Host synthetic probe `c534b2` exited 0 in 0.919541527 s, and the independently motivated wrapped-prefix probe `22adfd` exited 0 in 0.59175862 s. Both successful probes used a 30-second timeout, CPU 4, single-thread numerical-library environment settings, browser cleanup in finally, and aborted network requests. Hash inspection was tool chunk `c4fb15`.

Exposure disclosure: before learning the agent's current assignment, this reviewer messaged `widget_scoring_regressions` to ask whether candidate regressions were already running and included the generic declined-paragraph ownText prefix counterexample. The agent replied that it was the reserved ordinary-UI evaluator/task constructor and had not read the candidate or tests. The parent was informed immediately. No further repair details were sent to that evaluator. No assessment results, fixture values, or reserved UI details were exchanged. This is real repair-detail exposure; no claim of complete evaluator blinding is made.
