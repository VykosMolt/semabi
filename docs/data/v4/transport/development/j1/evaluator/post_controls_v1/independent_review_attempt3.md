# Independent held-source review, attempt 3

Reviewer: `/root/baseline_verification/post_controls_review`, independent
`sol_reviewer`. This is the implementation owner's retained transcription of the
bounded final assessment delivered through collaboration.

## Findings

None in the bounded correction.

## Contract assessment

The two prior defects are repaired:

- `same_typed` now compares dictionary keys and values independently of insertion
  order while retaining strict type distinctions.
- Parsed observations require `nodes` to be a list, and semantic fields use strict
  typed comparison. Tuple substitutions for `nodes` or `options` become
  `UNAVAILABLE` through the production `assess` boundary.

The four new assertions exercise reordered detached copies, typed key aliases,
and both container substitutions. Protocol and `source_manifest_v2.json`
accurately bind the revised behavior.

Verified held hashes:

- `controls.py`: `3f2fd82d6b682d9c64e8fb76f3f90f95e5a4a572d291084ba2a7f68175b69c31`
- `checks.py`: `5fe2734c83fd31b6813c24d5ebeb7d7be2cfd72e4996bd4f0b65c59c4f836b07`
- `protocol.md`: `1783c42be59b6c124609dd3f182dce73996fdc243f9e92fd015885f505ddeeb9`
- `source_manifest_v2.json`: `d89de95be0bd809a726ba2149da3fad1a2a96ade6bdb11d5b6992a692547122a`

Independent reruns reproduced:

- 82/82 PASS: `2af902a9325a4b03f8be7aae77bc6ed74f0b5e65256b64f984aa1673a4e0fa25`
- Immutable 19/19 PASS: `105403597aa8f4e45282ac9b0a2aae870dd073dd0157ea91ed7d3df20266bafd`

## Evidence gaps

No actual J1 first-pass manifest, run payload, forecast, checkpoint, job, or
production output was inspected. V2 production execution therefore remains
unestablished.

## Residual risks

The previously documented page-local correspondence heuristics, non-atomic
hash/read window, narrow role-declaration validation, and absence of paired
invariance remain. None is expanded by this correction.

## Verdict

**ACCEPT WITH RESIDUAL RISK**
