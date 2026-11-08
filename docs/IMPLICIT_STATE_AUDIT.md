# Implicit state machines — verified audit

Audit date: 2026-11-08. Scope: `projects/keystone` (88 Python modules, 2 browser
modules). Every candidate was re-verified against the live source and, where
observable, by executing it. The two initial catalogs were treated as hypotheses,
not findings: eight of their claims did not survive verification and are recorded
below as rejected so the same false positives are not re-filed.

## Verified defects (fixed)

| ID | Machine | File | Defect | Evidence |
|---|---|---|---|---|
| V1 | Component lifecycle (`ComponentRuntime`) | `keystone/lifecycle.py` | `start()` sets `running = True`, then starts components one by one. If a later `start()` raised, the exception escaped with earlier components started, `running` still `True` and no `stop()` delivered — a half-started scene that could never be cleanly stopped. | Probe: `started=1 stopped=0 running=True` after a raised start. Fixed and pinned by `tests/test_lifecycle.py::test_failed_start_stops_components_it_already_started`. |
| V2 | Playtest outcome vocabulary | `keystone/playtest.py` | `OUTCOMES` declared four outcomes but the runner also emits `"timeout"`. `read_outcome` mapped any value outside `("ongoing","win","lose")` to `"unknown"`, so a transcript's own `timeout` was erased when read back. `OUTCOMES` had no call sites at all. | Probe: `read_outcome({"outcome": "timeout"}) -> "unknown"`. Fixed; pinned by `test_outcome_vocabulary_covers_what_the_runner_emits`, `test_read_outcome_round_trips_every_declared_outcome`, `test_timeout_is_reported_for_a_run_that_never_signals`. |
| V3 | Console play loop vs server play state | `keystone/web/static/app.js` | The client loop (`playLoopActive` + timer) was only ever stopped from its own error path. Nothing reconciled it with the authoritative `editor.play.active`, so a server-side end of play left the client posting `play_step` indefinitely. `playResume` also started the loop unconditionally instead of confirming the server state, unlike `playStart`. | `showEditor` had no `stopPlayLoop()`; verified by `scratch/check_console_loop.js` which fails on the pre-fix source and passes after. |
| V4 | Viewport cursor rule | `keystone/web/static/viewer.js` | One cursor rule existed in four copies with divergent conditions: `setViewMode` and `setProjectionPreset` checked `viewMode === "scene"`, while `setBoxSelect` and `updateGizmoHover` did not — so toggling box-select in Game view painted a crosshair over a game view. `setEditable(false)` cleared the cursor and re-enabling never restored it. | Four inline copies; now one `cursorFor(axis)` with 6 call sites and 0 inline copies (`scratch/verify_cursor.py`). |
| V5 | Prefab-edit mode | `keystone/web/server.py` | `_scene_before_prefab` was assigned in `_edit_prefab_locked` and never cleared, so after the first edit cycle it permanently shadowed `getattr(self.game, "scene")` in `_scene_locked()`. Behaviourally masked today by `_built`, which makes it a latent hazard rather than a live bug. | Field had 1 write and 0 clears; authored-scene survival probe passes before and after, so this is a safety fix, not a bug fix. Pinned by an assertion in `test_editor_prefab_edit_mode_round_trip`. |

## Rejected after verification (do not re-file)

| Claim | Why it was rejected |
|---|---|
| `play_step` advances while `play_paused` is true, so pause is unenforced | **By design.** The console Step button pauses first and then steps (`app.js` `playStep`), and single-stepping a paused session is the documented workflow. Gating `play_step` on pause would break Step. |
| A failed asset load never retries until the file changes | Retrying on every refresh would re-raise the same error for an unchanged file. Reporting `failed` again is correct; the probe's "unchanged" reading was my labelling error, not behaviour. Post-fix check confirms the failure is reported, not swallowed. |
| A looping blend state fires its clip events only once | Wrong. Measured 3 `step` fires across 3.33 loops of a 1 s clip, i.e. exactly once per loop. |
| A crossfade re-fires the destination clip's opening event | Wrong. Crossfade and direct `play()` both fire the `enter` event exactly once. |
| `--verify-determinism --trace` is silently accepted and ignored | Wrong. The CLI rejects it with exit 2. |
| `delete_scene` yields "dirty with nothing to revert to" and `revert_scene` then reverts a different scene | Not reproduced; `scene_dirty` is recomputed from the action table at the end of every action and `revert_scene` reports its own name. Recorded as unproven, not fixed. |
| `select_many` `replace([])` and `remove(all)` converge differently | Cosmetic internal divergence with an identical visible result; no user, developer or agent impact. Deliberately not changed. |
| `history.History` is dead code duplicating `EditorHistory` | True that it has no call sites, but removing a public exported class is a breaking API change beyond this task's scope. Filed as a follow-up. |

## Systemic finding

The recurring shape is **one fact stored in several primitives with no single
owner**: play state in five client flags plus the server document, the cursor
rule in four places, prefab-edit state across six fields, and the outcome
vocabulary declared in one tuple while the runner wrote a second set of literals.
The fixes above each give that fact one owner (a reconciler in `showEditor`, one
`cursorFor` rule, one cleared field, one derived vocabulary). The remaining
clusters noted by the catalogs (CLI flag table, renderer bloom resources, CLI
`--trace` pairing) are documented but were not changed because no defect in them
could be reproduced, and this task commits only evidence-backed fixes.
