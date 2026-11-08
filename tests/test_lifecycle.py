"""Tests for deterministic component start/update/stop lifecycle hooks."""

import unittest
from dataclasses import dataclass

from keystone.lifecycle import (
    LIFECYCLE_HOOKS,
    ComponentRuntime,
    LifecycleContext,
    lifecycle_hooks,
)
from keystone.scene import Node, Scene

EVENTS: list[str] = []
CONTEXTS: list[LifecycleContext] = []


@dataclass
class Alpha:
    label: str = ""
    ticks: int = 0
    started: int = 0
    stopped: int = 0

    def start(self, context: LifecycleContext) -> None:
        self.started += 1
        CONTEXTS.append(context)
        EVENTS.append(
            f"{self.label}:start:{context.frame}:{context.dt}:{context.node.id}"
        )

    def update(self, context: LifecycleContext) -> None:
        self.ticks += 1
        CONTEXTS.append(context)
        EVENTS.append(
            f"{self.label}:update:{context.frame}:{context.dt}:{context.node.id}"
        )

    def stop(self, context: LifecycleContext) -> None:
        self.stopped += 1
        CONTEXTS.append(context)
        EVENTS.append(
            f"{self.label}:stop:{context.frame}:{context.dt}:{context.node.id}"
        )


@dataclass
class Beta(Alpha):
    pass


@dataclass
class Plain:
    value: int = 0


class LifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        EVENTS.clear()
        CONTEXTS.clear()

    def _scene(self) -> Scene:
        scene = Scene()
        first = scene.add(Node("first", id="first"))
        first.add_component(Alpha("a"))
        first.add_component(Beta("b"))
        second = scene.add(Node("second", id="second"))
        second.add_component(Alpha("c"))
        return scene

    def test_start_update_stop_order_context_and_counts(self):
        scene = self._scene()
        runtime = ComponentRuntime(scene)
        self.assertEqual(runtime.start(), 3)
        self.assertEqual(
            runtime.describe(),
            {
                "active": True,
                "frame": 0,
                "started": 3,
                "hooks": list(LIFECYCLE_HOOKS),
            },
        )
        self.assertEqual(runtime.update(0.25), 3)
        self.assertEqual(runtime.update(0.25), 3)
        self.assertEqual(runtime.describe()["frame"], 2)
        self.assertEqual(runtime.stop(), 3)
        self.assertEqual(
            EVENTS,
            [
                "a:start:0:0.0:first",
                "b:start:0:0.0:first",
                "c:start:0:0.0:second",
                "a:update:1:0.25:first",
                "b:update:1:0.25:first",
                "c:update:1:0.25:second",
                "a:update:2:0.25:first",
                "b:update:2:0.25:first",
                "c:update:2:0.25:second",
                "c:stop:2:0.0:second",
                "b:stop:2:0.0:first",
                "a:stop:2:0.0:first",
            ],
        )
        self.assertTrue(all(context.scene is scene for context in CONTEXTS))
        self.assertEqual(
            runtime.describe(),
            {"active": False, "frame": 2, "started": 0, "hooks": []},
        )

    def test_components_added_after_start_begin_on_the_next_tick(self):
        scene = Scene()
        first = scene.add(Node("first", id="first"))
        first.add_component(Alpha("a"))
        runtime = ComponentRuntime(scene)
        self.assertEqual(runtime.start(), 1)
        second = scene.add(Node("second", id="second"))
        second.add_component(Beta("b"))
        self.assertEqual(runtime.update(0.1), 2)
        self.assertEqual(runtime.describe()["started"], 2)
        self.assertEqual(
            EVENTS,
            [
                "a:start:0:0.0:first",
                "a:update:1:0.1:first",
                "b:start:1:0.0:second",
                "b:update:1:0.1:second",
            ],
        )
        self.assertEqual(runtime.stop(), 2)

    def test_failed_start_stops_components_it_already_started(self):
        class Boom:
            ticks = 0

            def start(self, context):
                raise RuntimeError("boom")

            def update(self, context):
                Boom.ticks += 1

            def stop(self, context):
                raise AssertionError("an unstarted component must not be stopped")

        scene = Scene()
        first = scene.add(Node("first", id="first"))
        alpha = Alpha("a")
        first.add_component(alpha)
        second = scene.add(Node("second", id="second"))
        second.add_component(Boom())

        runtime = ComponentRuntime(scene)
        with self.assertRaises(RuntimeError):
            runtime.start()

        self.assertEqual(alpha.started, 1)
        self.assertEqual(
            alpha.stopped,
            1,
            "a component whose start() succeeded must receive stop() when a later start() fails",
        )
        self.assertFalse(runtime.running)
        self.assertEqual(
            runtime.describe(),
            {"active": False, "frame": 0, "started": 0, "hooks": []},
        )
        self.assertEqual(Boom.ticks, 0, "a failed start must not tick any component")
        self.assertEqual(EVENTS, ["a:start:0:0.0:first", "a:stop:0:0.0:first"])

    def test_components_without_hooks_are_ignored(self):
        scene = Scene()
        node = scene.add(Node("plain", id="plain"))
        node.add_component(Plain(3))
        runtime = ComponentRuntime(scene)
        self.assertEqual(runtime.start(), 0)
        self.assertEqual(runtime.update(0.1), 0)
        self.assertEqual(runtime.stop(), 0)

    def test_lifecycle_hooks_reports_available_methods(self):
        self.assertEqual(lifecycle_hooks(Alpha), LIFECYCLE_HOOKS)
        self.assertEqual(lifecycle_hooks(Alpha("a")), LIFECYCLE_HOOKS)
        self.assertEqual(lifecycle_hooks(Plain), ())

    def test_runtime_state_and_dt_validation(self):
        runtime = ComponentRuntime(Scene())
        with self.assertRaises(ValueError):
            runtime.update(0.1)
        runtime.start()
        with self.assertRaises(ValueError):
            runtime.start()
        for value in (True, "0.1", None):
            with self.assertRaises(TypeError):
                runtime.update(value)  # type: ignore[arg-type]
        for value in (-0.1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                runtime.update(value)
        runtime.stop()
        with self.assertRaises(ValueError):
            runtime.stop()


if __name__ == "__main__":
    unittest.main()
