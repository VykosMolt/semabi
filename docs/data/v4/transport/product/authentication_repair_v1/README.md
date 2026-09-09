# Guarded password-form authentication

The first reserved Vikunja run stopped before learning because its visible login
form used an ordinary button rather than an HTML submit control. The original
[result](../reserved_assessment_v1/README.md) remains unchanged. Its setup views
showed one username, one password, a visibility toggle and a Login button. The
exact frozen onboarding DOM was not retained publicly, so matching those views
to that refusal is an inference supported by the unchanged selection code.

The general repair prefers one native submit and adds a narrow fallback for a
unique same-form button with the whole English label Login, Log in or Sign in.
Ambiguous, disabled, readonly, externally owned or unsupported controls stop
authentication. Before each credential action, the browser reads a settled
allowed-origin view, reselects the same contract and checks retained form, field
and button elements. Harmless node renumbering is allowed; replacement is not.
Attempt counts precede dispatch, errors omit credential values, and retained
handles are released. Public results disclose the selection basis.

Root and an independent reviewer inspected the implementation. The reviewer
found an outside-form native ownership counterexample; the selector now refuses
that unsupported arrangement. Independent plain-data probes covered ownership,
continuity, origin, settling and failure accounting. The implementation then
passed 403 focused tests, including one Chromium test containing six invented
login scenes. Test commands, source hashes and measurements are retained here.
This is not a full repository test run.

The new development onboarding on Vikunja authenticated through this fallback
and learned one task-creation operation through the ordinary HTTP entry point.
The authenticated flow used three credential actions. Saved-effect calls and
persisted reuse are separate development checks. No application-specific login
selector or mapping was supplied.

Fallback language support remains limited to the three disclosed English labels.
Checks precede dispatch rather than making DOM state and actions atomic.
CONNECTED means a settled same-origin view no longer exposes a password field;
it is not an independent proof of which account authenticated. MFA and SSO are
outside this adapter.
