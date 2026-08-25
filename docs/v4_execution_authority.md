# V4 execution authority: threat model, architecture, and claim boundary

This document states exactly what the V4 evidence chain establishes about the *code that
actually ran*, and exactly what it does not. It is bounded on purpose. It is not a
general Python sandbox, not a reproducible-build framework, and not a supply-chain
attestation standard.

The mechanism is `scripts/v4_authority.py`. Everything below describes that file and the
two checks it wires into `semabi/compiler/v4/manifests.py`.

## The property being established

> Every SemABI/project-local module that actually executed during an authoritative V4
> run resolved inside the intended candidate checkout, corresponded byte-for-byte to a
> tracked file of that checkout, and was executed from those exact authenticated bytes.

Two directions are required, and the second is the one the campaign kept losing:

* **predicted ⊆ authenticated** — everything the manifests hash exists and matches. The
  manifest closure hashes already did this.
* **executed ⊆ authenticated** — everything project-local that actually ran was
  authenticated. This is what the runtime execution attestation establishes, and it is
  the direction a static scanner cannot establish.

## Why the previous mechanism failed

`manifests._module_path` predicted which file a module name would resolve to. It
resolved `X.py` before `X/__init__.py`; CPython's `FileFinder` resolves a directory
package first, and an extension module before either. An untracked
`semabi/compiler/v4/transfer/__init__.py` therefore executed while the closure
authenticated `semabi/compiler/v4/transfer.py`, with every hash, the bytecode-cache
check, the cache-cold recipe, V2 custody and the full suite green. Reproduced again in
this session before the repair:

    executed module file        : <root>/semabi/compiler/v4/transfer/__init__.py
    closure names transfer.py   : True
    vet_clinic/harbour/blend_book -> STRICT VALIDATION PASSED (undetected)

The witness was package-versus-module ordering. The defect was the abstraction: **an
integrity layer must not predict Python's import resolution.** Correcting the order
would have fixed the witness and preserved the defect, so the order was not the repair.

## The repair, in one sentence

Control the import environment, let CPython resolve project modules inside it,
authenticate the origin CPython actually selected, execute those exact bytes from
memory, and prove afterwards that nothing else project-local ran.

## Declared threat model

The attacker can write arbitrary files inside the checkout: untracked files, modified
tracked files, directories, symlinks, `__pycache__` entries, `.pyc` files, extension
module files. The attacker can also rely on whatever the developer's environment already
contains, including an editable installation of this project.

### Defended

| # | Threat | How it is refused |
|---|---|---|
| 1 | Untracked project file or package shadow (`X/__init__.py` beside tracked `X.py`) | CPython selects it; the guard authenticates the *selected* origin and finds no tracked blob → `PROJECT_MODULE_NOT_IN_CANDIDATE_TREE` |
| 2 | Reverse shadow (untracked `X.py` beside tracked `X/__init__.py`) | CPython still selects the package; the tracked package authenticates and the untracked file never executes |
| 3 | Modified tracked file | executed bytes are compared with the checkout's blob content → `PROJECT_MODULE_BYTES_DIFFER_FROM_CANDIDATE_TREE` |
| 4 | Project extension module (`X.cpython-*.so`) | CPython selects `ExtensionFileLoader`; native code is not authenticable source → `DISALLOWED_PROJECT_LOADER` |
| 5 | Project `__pycache__` / stale / hash-based / timestamp `.pyc` | irrelevant: authenticated source bytes are compiled in memory and no project `.pyc` is ever opened |
| 6 | Sourceless project bytecode (`X.pyc` with no `X.py`) | CPython selects `SourcelessFileLoader` → `DISALLOWED_PROJECT_LOADER` |
| 7 | Editable-install contamination | `-S` means `site` never runs, so no `.pth` is read or executed; the guard owns `semabi` at `sys.meta_path[0]` and searches only the candidate root; a declared third-party directory containing a project top-level name is refused |
| 8 | Unexpected local `sys.path` entries | no project directory is ever placed on `sys.path`; any `sys.path` entry inside the checkout that is not a declared third-party directory → `PROJECT_PATH_ON_SYS_PATH` |
| 9 | Project imports resolving outside the candidate clone | the search path for project modules is the candidate root and package `__path__` entries, each required to be a non-symlinked directory inside the root |
| 10 | Unexpected project loaders | only `importlib.machinery.SourceFileLoader` may be selected; the executed loader is always the V4 verified loader |
| 11 | Local namespace-package portions | SemABI declares none; a namespace selection → `NAMESPACE_PACKAGE_PORTION` |
| 12 | Symlink substitution | `realpath(origin) != origin` → `SYMLINKED_PROJECT_ORIGIN`; the file is opened `O_NOFOLLOW`; tracked symlinks (mode `120000`) are never authenticable |
| 13 | Authoritative entrypoint code omitted from provenance | the two freeze scripts are executed from authenticated bytes under the same rules and appear in the attestation |
| 14 | Dynamic imports of local modules outside the authenticated set | `importlib.import_module` and `__import__` reach the same `sys.meta_path[0]` guard |
| 15 | A finder or path hook that supplies project code from elsewhere | the guard is `sys.meta_path[0]` and asserts it on every project import; resolution is performed by a private `FileFinder` and cross-checked against `PathFinder` → `RESOLUTION_DISAGREEMENT` |
| 16 | Anything project-local executing unauthenticated | the exit audit classifies every `sys.modules` entry and fails on any origin inside the checkout that is not authenticated → `UNAUTHORISED_MODULE_ORIGIN` |
| 17 | Code executing outside the declared manifest closure | the executed set must be a subset of the declared static closure the manifests hash → `EXECUTED_OUTSIDE_DECLARED_CLOSURE` |
| 18 | A second Python interpreter escaping the authority | no authoritative closure file starts a subprocess; a test pins this |

### Explicitly NOT defended

The trusted computing base is: the CPython binary and its standard library; the declared
third-party directory; Git; the exact candidate checkout; and `scripts/v4_authority.py`
itself. Out of scope, and never claimed:

* root or kernel compromise;
* a malicious CPython binary, standard library, linker or runtime;
* malicious content **inside** a declared third-party directory. Its contents are
  *trusted, not authenticated*. On this machine `.venv` happens to live inside the
  repository; it is refused if it holds any tracked path, but a writer who can modify an
  installed dependency has compromised the TCB by definition. Running from an
  environment outside the checkout removes even that adjacency;
* **the honesty of authenticated code.** The property is the *identity* of what executed,
  not the correctness of what it does. Code that is committed to the candidate can do
  anything the process can do, including reaching the authority object through the
  published `sys.modules` entry. That is by construction: the defence against dishonest
  committed code is reading the diff, which is what the adversarial review is for;
* the launcher authenticating itself. It checks its own bytes against the checkout, but
  a modified launcher could skip that check. **The launcher's identity comes from the
  checkout it is run from, not from itself** — which is why the authoritative gate is a
  fresh clone of the exact candidate commit;
* anything about *when* evidence was collected. Chronology remains
  `RETROACTIVE_SNAPSHOT_CHRONOLOGY_NOT_ESTABLISHED`.

No SLSA, provenance-standard, signature or PKI claim is made anywhere.

## Architecture

### 1. Startup

    .venv/bin/python -I -S -B scripts/v4_authority.py <command> ...

`-I`, `-S` and `-B` are **required**; the launcher refuses to run otherwise
(`NON_ISOLATED_STARTUP`). It does not re-exec itself into an isolated interpreter,
because the pre-exec process would already have run `site` and every `.pth`.

* `-I` (implies `-E`, `-s`, `-P`): no script directory on `sys.path`, no user site
  directory, no `PYTHON*` variables.
* `-S`: `site` never runs, so **no `.pth` file is read and no `.pth` import line
  executes**. This is what neutralises the editable installation, whose entire mechanism
  is one `.pth` import line. `-S` is not `-I`; both are needed.
* `-B` and `sys.dont_write_bytecode` are hygiene only. `-B` stops Python *writing*
  `.pyc`; it says nothing about *reading* one, and is never treated as the bytecode
  boundary here. The boundary is that project bytecode is never opened at all.

The interpreter's own `sys.path` (three stdlib entries) is kept. Declared third-party
directories are **appended as ordinary paths**; because `site` never ran, their `.pth`
files are inert, and each one's presence is recorded in the environment record.

### 2. Candidate identity and authenticated content

The candidate root is derived from the launcher's own resolved path, never from the
working directory or a flag. Content authority comes from Git:

* `git ls-files --stage -z` gives every tracked path with its blob id and mode. A
  tracked `*.py` path whose mode is not `100644`/`100755` is refused.
* `git cat-file --batch` reads the **exact stored bytes** of each tracked `*.py` blob.

Executed bytes are then compared with those stored bytes **directly**. The Git object id
is used only as a lookup key and never as a security hash, so SHA-1 collision resistance
is not load-bearing anywhere in this mechanism.

Membership is against the **index**, which equals `HEAD` in any clean checkout. The
environment record states `index_matches_head` for every run. Artifact regeneration
necessarily happens with new code staged and not yet committed; the fresh-clone
verification of the candidate commit is where `index_matches_head` is `true`.

### 3. Resolution

For a project name the guard:

1. asserts it is still `sys.meta_path[0]`;
2. builds the search path — the candidate root for `semabi`, otherwise the importing
   package's `__path__`, every entry required to be non-symlinked and inside the root;
3. asks **CPython's own `importlib.machinery.FileFinder`**, constructed with CPython's
   own loader table (extensions, source, bytecode — the exact triple
   `importlib._bootstrap_external._get_supported_file_loaders()` returns; a test pins the
   equality). Package-before-module and extension-before-source ordering are therefore
   CPython's, not ours;
4. cross-checks the selection against `importlib.machinery.PathFinder` over the same
   path and refuses on any disagreement, which is what an injected path hook or a stale
   importer cache would produce.

No part of the authority reimplements the search.

### 4. Authenticate, then execute those bytes

The selected `ModuleSpec` is inspected — `spec.loader` type, `spec.origin`,
`spec.submodule_search_locations` — never `__file__` alone. Then, once:

    open(origin, O_RDONLY|O_NOFOLLOW) -> fstat (regular file) -> read all bytes -> close
    compare bytes with the authenticated candidate content
    compile(bytes) and exec into the module namespace

The path is never reopened. The V4 verified loader has no `get_data` that reads from
disk, no bytecode cache path, and refuses any read it is asked to perform. There is no
window between hashing a pathname and letting `SourceFileLoader` reopen it.

Package semantics are preserved: `__init__.py` origins are packages, their
`submodule_search_locations` is the package directory, so relative imports, `__path__`
walking and dynamic `importlib.import_module` all behave normally and all re-enter the
guard.

### 5. Exit audit

Every `sys.modules` entry is classified: authenticated project module (and its
`__loader__` must be the verified loader), builtin/frozen, interpreter stdlib directory,
or declared third-party directory. **Anything else fails the run**, including any origin
inside the checkout that was not authenticated. `__main__` is the launcher, checked
separately against the checkout.

### 6. Attestation

Two records are produced:

* `docs/data/v4/attestations/*.execution.json` — schema
  `semabi.v4.execution-attestation.v1`. Deliberately **byte-reproducible**: policy,
  runtime, entrypoint, every executed project module (name, repo-relative path, sha256,
  size, package flag, search locations, resolver, loader, executed-from-memory),
  `project_execution_sha256`, the declared-closure comparison, the third-party top-level
  names that executed, and the artifact it accompanies with its sha256. It contains no
  absolute path and no commit id, so it reproduces identically from any checkout of the
  same code.
* the **environment record** (`semabi.v4.execution-environment.v1`), printed to stdout
  and retained in the verification artifact, holding what cannot be reproducible:
  candidate commit, candidate root, `sys.executable`, `sys.prefix`, `sys.base_prefix`,
  interpreter flags, initial and final `sys.path`, `sys.meta_path`, `sys.path_hooks`,
  declared third-party directories with their inert `.pth` files, module-origin counts,
  and the subprocess policy. It is labelled `"reproducible": false`.

The split is deliberate and is stated here so it cannot be mistaken for hiding the
commit: putting the commit inside the retained attestation would make the attestation
differ between the run that generated it and any later verification of the commit that
contains it.

### 7. Binding the report to the authority

`semabi/run_v4_transfer.py` records `authority.execution_authority` in every report:

* `V4_IMPORT_AUTHORITY_ACTIVE` with the `project_execution_sha256`, or
* `NOT_ESTABLISHED_NO_V4_IMPORT_AUTHORITY` for any ordinary run.

The launcher then refuses to finish if the report does not claim the authority, or if
the report's execution digest differs from the final attestation's — which is what a
module imported after the report was written would produce. A retained report therefore
cannot be reproduced byte-for-byte except under the launcher.

## Static closure versus runtime execution set

Both are kept, with honest roles.

* The **declared static closure** (`manifests.local_import_closure`, built by scanning
  literal imports with `manifests._module_path`) is a *declaration*. It is what the
  manifests hash. It is **not** a proof of completeness, because Python's dynamic
  behaviour is not decidable by scanning, and it is **not** the authority for what
  executes.
* The **runtime execution set** is the guarantee.

The invariant enforced is `executed ⊆ declared`: nothing may execute that the manifests
did not hash. The converse is *not* an error — the attestation records
`declared_but_not_executed` for every declared file a given run did not import, because
the scanner legitimately over-approximates.

`_module_path` keeps its discovery role and additionally refuses names it cannot
describe: a directory package beside a same-named module file, or any extension-module
file for the name, now raise `ManifestError` instead of silently choosing one. That is a
secondary consistency check on the declaration, not the execution authority.

## The evaluator boundary

The compiler/evaluator separation is not enforced by the import authority directly; it is
enforced by the declared closure. `manifests._module_path` refuses `semabi.hidden`,
`semabi.env`, `semabi.eval` and `semabi.baselines` outright, so no declared closure can
contain them, and `executed ⊆ declared` means an authoritative run that imported one --
statically or dynamically -- fails with `EXECUTED_OUTSIDE_DECLARED_CLOSURE`. The static
scan in `tests/test_boundary.py` remains the primary gate.

## Subprocesses

No file in the SOURCE-generation, chain-construction or replay closures references
`subprocess`, `os.system`, `os.exec*`, `os.spawn*`, `multiprocessing`, `runpy` or
`popen`; `tests/test_v4_execution_authority.py` pins that as an invariant. The only
subprocess anywhere in the authoritative path is the launcher's own read-only `git`
queries, run with a minimal environment and system/global Git configuration disabled.
There is no second Python interpreter outside the execution authority.

## Reproduction

    ROOT=$(pwd)
    PY=$ROOT/.venv/bin/python

    # every authoritative command
    $PY -I -S -B scripts/v4_authority.py --attestation <att> <command> ...

For the exact commands that regenerate the manifests and the three reports, see
`docs/v4_handoff.md`. Running any of them without `-I -S -B` is refused.

## What this does not establish

* It says nothing about the *scientific* result, which is unchanged and negative.
* It does not establish prospective chronology, unique transported selection,
  representation transportability, or fresh generalization; all remain
  `NOT_ESTABLISHED`.
* It does not establish that a declared third-party dependency is honest.
* "Fresh clone" alone is never used as shorthand for independent execution. Independence
  is claimed only where the attestation shows every executed project module bound to the
  clone.
