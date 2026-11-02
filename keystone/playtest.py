"""Seeded bot playtesting: transcripts, diffing, policies and fairness checks.

This module is game-agnostic. A bot policy only sees the five-operation
game contract (``build_scene``, ``update``, ``snapshot``, ``actions``,
``status``) through :class:`ActionState` snapshots; it never imports a
game module and knows no genre rules.

Snapshot convention (opportunistic, no contract change): games that want
win/lose judgments include optional ``outcome`` (``ongoing``, ``win``
or ``lose``) and ``score`` (a number) keys in their ``snapshot()``
dict. Games that omit them get ``outcome: unknown`` coverage runs and
an ``unknown`` fairness verdict, never a false ``fair``.
"""

from __future__ import annotations

import random as _random
import time as _time
from collections.abc import Callable, Iterable, Mapping
from typing import Any, Protocol

from keystone.input import ActionState
from keystone.replay import FIXED_STEP, CommandLog, stable_hash

TRANSCRIPT_SCHEMA = 1
PLAYTEST_REPORT_SCHEMA = 1

OUTCOMES = ("ongoing", "win", "lose", "unknown")
TERMINAL_OUTCOMES = ("win", "lose")


def _canon_value(value: object) -> object:
    if isinstance(value, float):
        return round(value, 3)
    if isinstance(value, Mapping):
        return {str(key): _canon_value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_canon_value(item) for item in value]
    return value


def canon(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Project a snapshot to its canonical search form.

    Drops the volatile ``time`` key and rounds floats so that a
    visited-set over ``stable_hash(canon(snapshot))`` terminates for
    real-time games whose clocks strictly increase. Returns a plain
    JSON-safe dict.
    """
    if not isinstance(snapshot, Mapping):
        raise TypeError("snapshot must be a mapping")
    return {str(key): _canon_value(snapshot[key]) for key in sorted(snapshot, key=str) if str(key) != "time"}


def canon_hash(snapshot: Mapping[str, Any]) -> str:
    """Stable hash of the canonical snapshot projection."""
    return stable_hash(canon(snapshot))


def read_outcome(snapshot: Mapping[str, Any]) -> str:
    """Read the opportunistic outcome signal; ``unknown`` when absent."""
    outcome = snapshot.get("outcome", "unknown") if isinstance(snapshot, Mapping) else "unknown"
    return outcome if outcome in ("ongoing", "win", "lose") else "unknown"


def read_score(snapshot: Mapping[str, Any]) -> float | None:
    """Read the opportunistic numeric score signal, if present."""
    if not isinstance(snapshot, Mapping):
        return None
    score = snapshot.get("score")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return None
    return float(score)


class BotPolicy(Protocol):
    """One seeded decision step over the five-operation game contract."""

    name: str

    def reset(self, seed: int) -> None: ...
    def select(
        self,
        snapshot: dict[str, Any],
        actions_spec: dict[str, Any],
        rng: _random.Random,
    ) -> ActionState: ...


def to_command_log(transcript: Mapping[str, Any]) -> CommandLog:
    """Convert a transcript back to a replayable :class:`CommandLog`.

    The transcript envelope wraps the exact ``CommandLog`` shape, so a
    bot run replays through ``run_log`` and pins through ``--replay
    --expect-hash`` with no new machinery.
    """
    if not isinstance(transcript, Mapping):
        raise TypeError("transcript must be a mapping")
    envelope = transcript.get("command_log")
    if not isinstance(envelope, Mapping):
        raise TypeError("transcript holds no command_log envelope")
    return CommandLog.from_dict(
        {
            "seed": envelope.get("seed"),
            "step": envelope.get("step", FIXED_STEP),
            "frames": envelope.get("frames"),
        }
    )


def run_bot(
    factory: Callable[[], Any],
    policy: BotPolicy,
    frames: int = 120,
    seed: int = 0,
    step: float = FIXED_STEP,
    max_wall_seconds: float = 10.0,
    trace: bool = False,
) -> dict[str, Any]:
    """Play one seeded bot run headlessly and record the transcript.

    The policy's private RNG is ``random.Random(seed)`` and the global
    RNG is seeded from ``seed`` (the same semantics as ``run_log``) so
    that same seed plus same game means the same transcript. Exceeding
    ``max_wall_seconds`` or reaching a terminal ``outcome`` ends the
    run early with a reason instead of playing forever.
    """
    if not callable(factory):
        raise TypeError("factory must be callable")
    if frames < 0:
        raise ValueError("frames cannot be negative")
    if step <= 0.0:
        raise ValueError("step must be positive")
    if max_wall_seconds <= 0.0:
        raise ValueError("max_wall_seconds must be positive")
    reset = getattr(policy, "reset", None)
    select = getattr(policy, "select", None)
    if not callable(reset) or not callable(select):
        raise TypeError("policy must expose reset(seed) and select(snapshot, actions_spec, rng)")
    policy_name = getattr(policy, "name", None)
    if not isinstance(policy_name, str) or not policy_name.strip():
        raise ValueError("policy name must be a non-blank string")

    _random.seed(seed)
    rng = _random.Random(seed)
    policy.reset(seed)
    game = factory()
    build = getattr(game, "build_scene", None)
    update = getattr(game, "update", None)
    snapshot = getattr(game, "snapshot", None)
    actions_of = getattr(game, "actions", None)
    if not callable(build) or not callable(update) or not callable(snapshot) or not callable(actions_of):
        raise TypeError("replayed game must expose build_scene(), update(), snapshot() and actions()")
    build()

    try:
        spec = actions_of()
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"game actions() spec could not be read: {exc}") from exc
    if not isinstance(spec, Mapping):
        raise TypeError("game actions() spec must be a mapping")
    actions_spec = dict(spec)

    used: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    deadline = _time.monotonic() + max_wall_seconds
    outcome = "unknown"
    timed_out = False
    steps_used = 0
    for _ in range(frames):
        if _time.monotonic() >= deadline:
            timed_out = True
            break
        try:
            current = snapshot()
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError(f"game snapshot() failed: {exc}") from exc
        if not isinstance(current, Mapping):
            raise TypeError("game snapshot() must return a mapping")
        action = select(dict(current), dict(actions_spec), rng)
        if not isinstance(action, ActionState):
            raise TypeError("policy select() must return an ActionState")
        used.append(action.to_dict())
        update(step, action)
        steps_used += 1
        outcome = read_outcome(snapshot())
        if trace:
            final_of_frame = snapshot()
            if not isinstance(final_of_frame, Mapping):
                raise TypeError("game snapshot() must return a mapping")
            snapshots.append(dict(final_of_frame))
        if outcome in TERMINAL_OUTCOMES:
            break
    try:
        final = snapshot()
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"game snapshot() failed: {exc}") from exc
    if not isinstance(final, Mapping):
        raise TypeError("game snapshot() must return a mapping")
    final = dict(final)
    if timed_out and outcome not in TERMINAL_OUTCOMES:
        outcome = "timeout"
    transcript: dict[str, Any] = {
        "schema": TRANSCRIPT_SCHEMA,
        "game": getattr(game, "name", "game"),
        "seed": seed,
        "step": step,
        "frames": frames,
        "steps_used": steps_used,
        "timed_out": timed_out,
        "policy": {"name": policy_name, "seed": seed, "params": dict(getattr(policy, "params", {}))},
        "command_log": {"seed": seed, "step": step, "frames": used},
        "actions": used,
        "outcome": outcome,
        "final": final,
        "hash": stable_hash(final),
    }
    if trace:
        transcript["snapshots"] = snapshots
    return transcript


def diff_transcripts(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    """Compare two transcripts: hash fast-path, then first divergence.

    Both transcripts must use :data:`TRANSCRIPT_SCHEMA`. The fast path
    compares final hashes (the same comparison ``--expect-hash`` makes);
    when both transcripts carry traced snapshots, the slow path walks
    them frame by frame and reports the first divergent index.
    """
    for label, transcript in (("before", before), ("after", after)):
        if not isinstance(transcript, Mapping):
            raise TypeError(f"{label} transcript must be a mapping")
        if transcript.get("schema") != TRANSCRIPT_SCHEMA:
            raise ValueError(f"{label} transcript must use schema {TRANSCRIPT_SCHEMA}")
        if "final" not in transcript or "hash" not in transcript:
            raise ValueError(f"{label} transcript must hold 'final' and 'hash'")
    same_hash = before["hash"] == after["hash"]
    before_actions = before.get("actions", [])
    after_actions = after.get("actions", [])
    before_snaps = before.get("snapshots")
    after_snaps = after.get("snapshots")
    first_divergent: int | None = None
    if isinstance(before_snaps, list) and isinstance(after_snaps, list):
        for index, (first, second) in enumerate(zip(before_snaps, after_snaps)):
            if stable_hash(first) != stable_hash(second):
                first_divergent = index
                break
        if first_divergent is None and len(before_snaps) != len(after_snaps):
            first_divergent = min(len(before_snaps), len(after_snaps))
    elif before.get("final") is not None and after.get("final") is not None:
        if stable_hash(before["final"]) != stable_hash(after["final"]):
            first_divergent = min(len(before_actions), len(after_actions))
    return {
        "schema": TRANSCRIPT_SCHEMA,
        "same_hash": same_hash,
        "final_equal": before["final"] == after["final"],
        "first_divergent_frame": first_divergent,
        "frames": {"before": len(before_actions), "after": len(after_actions)},
        "policies": {"before": before.get("policy"), "after": after.get("policy")},
    }


def _validate_actions_spec(spec: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    axes = spec.get("axes", [])
    buttons = spec.get("buttons", [])
    if not isinstance(axes, list) or not all(isinstance(item, str) for item in axes):
        raise ValueError("game actions() spec 'axes' must be a list of strings")
    if not isinstance(buttons, list) or not all(isinstance(item, str) for item in buttons):
        raise ValueError("game actions() spec 'buttons' must be a list of strings")
    return list(axes), list(buttons)


_KNOWN_AXES = ("forward", "right", "up", "look_yaw", "look_pitch")


def _sample_action(rng: _random.Random, axes: Iterable[str], buttons: Iterable[str]) -> ActionState:
    axes = list(axes)
    buttons = list(buttons)
    payload: dict[str, Any] = {}
    for axis in axes:
        if axis in _KNOWN_AXES:
            payload[axis] = rng.uniform(-1.0, 1.0)
    pressed: list[str] = []
    if buttons and rng.random() < 0.25:
        pressed.append(rng.choice(list(buttons)))
    if pressed:
        payload["pressed"] = pressed
    return ActionState.from_dict(payload)


class RandomPolicy:
    """Uniform baseline: sample axes in [-1, 1], occasionally press a button."""

    name = "random"

    def __init__(self, press_chance: float = 0.25) -> None:
        if not 0.0 <= press_chance <= 1.0:
            raise ValueError("press_chance must be within [0, 1]")
        self.params = {"press_chance": press_chance}

    def reset(self, seed: int) -> None:
        return None

    def select(
        self,
        snapshot: dict[str, Any],
        actions_spec: dict[str, Any],
        rng: _random.Random,
    ) -> ActionState:
        axes, buttons = _validate_actions_spec(actions_spec)
        payload: dict[str, Any] = {}
        for axis in axes:
            if axis in _KNOWN_AXES:
                payload[axis] = rng.uniform(-1.0, 1.0)
        if buttons and rng.random() < float(self.params["press_chance"]):
            payload["pressed"] = [rng.choice(buttons)]
        return ActionState.from_dict(payload)


class GreedyPolicy:
    """Stateful bandit: repeat the last action while score improves, else resample.

    Deliberately lookahead-free: without a game clone API, one-step
    rollouts would cost prefix replays per candidate. The opportunistic
    scalar is ``snapshot["score"]`` when numeric; without it the policy
    reports itself as random-equivalent in the transcript params echo.
    """

    name = "greedy"

    def __init__(self) -> None:
        self.params: dict[str, Any] = {}
        self._last_action: ActionState | None = None
        self._last_score: float | None = None
        self._saw_score = False

    def reset(self, seed: int) -> None:
        self._last_action = None
        self._last_score = None
        self._saw_score = False

    def select(
        self,
        snapshot: dict[str, Any],
        actions_spec: dict[str, Any],
        rng: _random.Random,
    ) -> ActionState:
        axes, buttons = _validate_actions_spec(actions_spec)
        score = read_score(snapshot)
        if score is not None:
            self._saw_score = True
        if (
            self._last_action is not None
            and score is not None
            and self._last_score is not None
            and score >= self._last_score
        ):
            action = self._last_action
        else:
            action = _sample_action(rng, axes, buttons)
        self._last_action = action
        self._last_score = score
        self.params = {"score_guided": self._saw_score}
        return action


class ScriptedPolicy:
    """Replay an action list; hold the final action when the run is longer."""

    name = "scripted"

    def __init__(self, actions: Iterable[ActionState | Mapping[str, Any]]) -> None:
        script: list[ActionState] = []
        for item in list(actions):
            if isinstance(item, ActionState):
                script.append(item)
            elif isinstance(item, Mapping):
                script.append(ActionState.from_dict(dict(item)))
            else:
                raise TypeError("scripted actions must be ActionState or mappings")
        if not script:
            raise ValueError("scripted actions must contain at least one action")
        self.params = {"script_frames": len(script)}
        self._script = script
        self._cursor = 0

    def reset(self, seed: int) -> None:
        self._cursor = 0

    def select(
        self,
        snapshot: dict[str, Any],
        actions_spec: dict[str, Any],
        rng: _random.Random,
    ) -> ActionState:
        _validate_actions_spec(actions_spec)
        action = self._script[min(self._cursor, len(self._script) - 1)]
        self._cursor += 1
        return action


def make_report(
    transcript: Mapping[str, Any],
    fairness: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the frozen schema-1 playtest report shared with web adapters.

    A thin web adapter emits the identical report by wrapping a ``POST
    /api/simulate`` result (``final``, ``hash``, ``actions``) with the
    same ``policy``/``seed`` envelope; no browser driving is involved.
    """
    if not isinstance(transcript, Mapping):
        raise TypeError("transcript must be a mapping")
    if transcript.get("schema") != TRANSCRIPT_SCHEMA:
        raise ValueError(f"transcript must use schema {TRANSCRIPT_SCHEMA}")
    for key in ("game", "policy", "seed", "final", "hash"):
        if key not in transcript:
            raise ValueError(f"transcript must hold {key!r}")
    policy = transcript["policy"]
    if not isinstance(policy, Mapping) or "name" not in policy:
        raise ValueError("transcript policy must hold a name")
    snapshots = transcript.get("snapshots")
    if isinstance(snapshots, list):
        unique = {stable_hash(canon(item)) for item in snapshots if isinstance(item, Mapping)}
        coverage = {"states_visited": len(snapshots), "unique_hashes": len(unique)}
    else:
        coverage = {"states_visited": int(transcript.get("steps_used", 0)), "unique_hashes": None}
    verdict: dict[str, Any] = {"verdict": "unknown", "reasons": ["no_fairness_check"]}
    if fairness is not None:
        if not isinstance(fairness, Mapping) or fairness.get("verdict") not in ("fair", "unfair", "unknown"):
            raise ValueError("fairness must hold a verdict of fair, unfair or unknown")
        verdict = {"verdict": fairness["verdict"], "reasons": list(fairness.get("reasons", []))}
    return {
        "schema": PLAYTEST_REPORT_SCHEMA,
        "game": transcript["game"],
        "policy": {"name": policy["name"], "seed": policy.get("seed"), "params": dict(policy.get("params", {}))},
        "seed": transcript["seed"],
        "frames": transcript.get("frames"),
        "steps_used": transcript.get("steps_used"),
        "outcome": transcript.get("outcome", "unknown"),
        "final": transcript["final"],
        "hash": transcript["hash"],
        "transcript_hash": transcript["hash"],
        "coverage": coverage,
        "fairness": verdict,
        "web_compatible": True,
    }


def validate_fairness(
    factory: Callable[[], Any],
    reference_actions: Iterable[ActionState | Mapping[str, Any]] | None = None,
    frames: int = 120,
    seeds: Iterable[int] = (0, 1, 2),
    step: float = FIXED_STEP,
    max_states: int = 5000,
    max_wall_seconds: float = 10.0,
    time_limit_frames: int | None = None,
) -> dict[str, Any]:
    """Judge whether a configuration is winnable, with reasons.

    Rejection predicate — verdict ``unfair`` iff ANY holds:

    - ``spawn_terminal``: the initial snapshot is already terminal;
    - ``nondeterministic``: two same-seed runs diverge;
    - ``no_witnessed_win``: a reference solution was supplied and still
      never reaches ``outcome: win`` within budget;
    - ``budget_infeasible``: the shortest witnessed win path exceeds
      ``time_limit_frames``.

    Verdict ``fair`` requires a deterministic witnessed win within
    budget. Without an ``outcome`` signal the verdict is ``unknown``
    (``no_outcome_signal``); without a reference solution and without a
    rollout win it is ``unknown`` (``no_reference_solution``) rather
    than a false ``unfair``; exhausting ``max_states`` unique canonical
    hashes first is ``unknown`` (``state_space_exceeded_budget``).
    Sampling, not exhaustive game-tree search: maze-exact reachability
    for the proving stub lives fixture-side as ground truth.
    """
    if not callable(factory):
        raise TypeError("factory must be callable")
    if frames < 0:
        raise ValueError("frames cannot be negative")
    if step <= 0.0:
        raise ValueError("step must be positive")
    if max_states <= 0:
        raise ValueError("max_states must be positive")
    if max_wall_seconds <= 0.0:
        raise ValueError("max_wall_seconds must be positive")
    seeds = list(seeds)
    if not seeds:
        raise ValueError("seeds must contain at least one seed")
    if time_limit_frames is not None and time_limit_frames < 0:
        raise ValueError("time_limit_frames cannot be negative")

    probe = factory()
    for method in ("build_scene", "update", "snapshot", "actions"):
        if not callable(getattr(probe, method, None)):
            raise TypeError(f"game must expose {method}()")
    probe.build_scene()
    try:
        initial = probe.snapshot()
    except Exception as exc:  # noqa: BLE001 - failure-is-data, see run_bot
        return {"verdict": "unfair", "reasons": [f"crash: snapshot() failed: {exc}"]}
    if not isinstance(initial, Mapping):
        return {"verdict": "unfair", "reasons": ["crash: snapshot() must return a mapping"]}
    if read_outcome(initial) in TERMINAL_OUTCOMES:
        return {"verdict": "unfair", "reasons": [f"spawn_terminal:{read_outcome(initial)}"]}
    if "outcome" not in initial:
        return {"verdict": "unknown", "reasons": ["no_outcome_signal"]}

    try:
        first = run_bot(factory, RandomPolicy(), frames=frames, seed=seeds[0], step=step,
                        max_wall_seconds=max_wall_seconds, trace=False)
        second = run_bot(factory, RandomPolicy(), frames=frames, seed=seeds[0], step=step,
                         max_wall_seconds=max_wall_seconds, trace=False)
    except (ValueError, TypeError) as exc:
        return {"verdict": "unfair", "reasons": [f"crash: {exc}"]}
    if first["hash"] != second["hash"]:
        return {"verdict": "unfair", "reasons": ["nondeterministic"]}

    seen: set[str] = set()
    witnessed: list[tuple[str, int]] = []
    budget_exhausted = False

    def _absorb(transcript: Mapping[str, Any], label: str) -> None:
        nonlocal budget_exhausted
        for action in transcript.get("actions", []):
            seen.add(stable_hash(action))
            if len(seen) >= max_states:
                budget_exhausted = True
                return
        snapshots = transcript.get("snapshots")
        if isinstance(snapshots, list):
            for item in snapshots:
                if isinstance(item, Mapping):
                    seen.add(canon_hash(item))
                    if len(seen) >= max_states:
                        budget_exhausted = True
                        return
        else:
            seen.add(stable_hash(transcript.get("final")))
        if transcript.get("outcome") == "win":
            witnessed.append((label, int(transcript.get("steps_used", 0))))

    reference = list(reference_actions) if reference_actions is not None else None
    if reference is not None:
        if not reference:
            raise ValueError("reference_actions must not be empty")
        try:
            scripted = run_bot(factory, ScriptedPolicy(reference), frames=frames, seed=seeds[0],
                               step=step, max_wall_seconds=max_wall_seconds, trace=True)
        except (ValueError, TypeError) as exc:
            return {"verdict": "unfair", "reasons": [f"crash: {exc}"]}
        _absorb(scripted, "reference")
    for seed in seeds:
        try:
            rollout = run_bot(factory, RandomPolicy(), frames=frames, seed=seed, step=step,
                              max_wall_seconds=max_wall_seconds, trace=True)
        except (ValueError, TypeError) as exc:
            return {"verdict": "unfair", "reasons": [f"crash: {exc}"]}
        _absorb(rollout, f"random:{seed}")
        if witnessed:
            break

    if witnessed:
        label, won_in = witnessed[0]
        if time_limit_frames is not None and won_in > time_limit_frames:
            return {"verdict": "unfair",
                    "reasons": [f"budget_infeasible:witnessed_win_in_{won_in}_frames_exceeds_limit_{time_limit_frames}"]}
        return {"verdict": "fair", "reasons": [f"witnessed_win:{label}:{won_in}"]}
    if reference is not None:
        if time_limit_frames is not None and len(reference) > time_limit_frames:
            return {"verdict": "unfair",
                    "reasons": [f"budget_infeasible:reference_needs_{len(reference)}_frames_exceeds_limit_{time_limit_frames}"]}
        return {"verdict": "unfair", "reasons": ["no_witnessed_win"]}
    if budget_exhausted:
        return {"verdict": "unknown", "reasons": ["state_space_exceeded_budget"]}
    return {"verdict": "unknown", "reasons": ["no_reference_solution"]}
