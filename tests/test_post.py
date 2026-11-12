"""Tests for the deterministic post color-grade (in-shader exposure + vignette)."""

import unittest

from keystone.analysis import analyze_frame, compare_reports
from keystone.gpu.post import POST_EXPOSURE, POST_VIGNETTE, grade_color, vignette_factor
from keystone.plugin import describe_game
from keystone.samples import CubeDemo
from keystone.scene import PostSettings, Scene
from keystone.scene_snapshot import scene_from_dict, scene_to_dict


class PostMathTest(unittest.TestCase):
    def test_constants_are_fixed(self):
        self.assertAlmostEqual(POST_EXPOSURE, 1.12)
        self.assertAlmostEqual(POST_VIGNETTE, 0.28)

    def test_vignette_center_is_one_and_corners_dim(self):
        self.assertAlmostEqual(vignette_factor(0.5, 0.5), 1.0)
        corner = vignette_factor(0.0, 0.0)
        self.assertLess(corner, 1.0)
        self.assertGreaterEqual(corner, 0.0)
        self.assertAlmostEqual(corner, 1.0 - POST_VIGNETTE)

    def test_grade_applies_exposure_then_vignette(self):
        center = grade_color((0.5, 0.5, 0.5), 0.5, 0.5)
        self.assertAlmostEqual(center[0], min(1.0, 0.5 * POST_EXPOSURE), places=6)
        corner = grade_color((0.5, 0.5, 0.5), 0.0, 0.0)
        self.assertLess(corner[0], center[0])
        clamped = grade_color((1.0, 1.0, 1.0), 0.5, 0.5)
        self.assertLessEqual(clamped[0], 1.0)


class PostContractsTest(unittest.TestCase):
    def test_post_settings_default_enabled(self):
        scene = Scene()
        self.assertTrue(scene.post.enabled)
        scene.post = PostSettings(enabled=False)
        self.assertFalse(scene.post.enabled)

    def test_describe_reports_post(self):
        self.assertTrue(describe_game(CubeDemo())["capabilities"]["post"])

    def test_report_includes_post_metadata_and_hash(self):
        scene = CubeDemo().build_scene()
        report = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        self.assertEqual(report["schema"], 11)
        self.assertEqual(report["scene"]["post"], {"enabled": True})
        scene.post = PostSettings(enabled=False)
        off = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        self.assertEqual(off["scene"]["post"], {"enabled": False})
        self.assertNotEqual(report["hash"], off["hash"])

    def test_compare_reports_diffs_post(self):
        scene = CubeDemo().build_scene()
        pixels = bytes((0, 0, 0, 255)) * 4
        on = analyze_frame(scene, pixels, 2, 2)
        scene.post = PostSettings(enabled=False)
        off = analyze_frame(scene, pixels, 2, 2)
        diff = compare_reports(on, off)
        self.assertFalse(diff["same_report"])
        self.assertFalse(diff["same_post"])
        self.assertEqual(diff["post"], {"before": {"enabled": True}, "after": {"enabled": False}})
        same = compare_reports(on, analyze_frame(CubeDemo().build_scene(), pixels, 2, 2))
        self.assertTrue(same["same_post"])
        self.assertEqual(diff["schema"], 11)

    def test_compare_accepts_legacy_without_post(self):
        scene = CubeDemo().build_scene()
        report = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        legacy = dict(report)
        legacy["schema"] = 7
        legacy["scene"] = dict(report["scene"])
        legacy["scene"].pop("post", None)
        diff = compare_reports(legacy, report)
        self.assertTrue(diff["same_post"])
        self.assertEqual(diff["schema"], 11)

    def test_snapshot_round_trips_post_flag(self):
        scene = CubeDemo().build_scene()
        scene.post = PostSettings(enabled=False)
        restored = scene_from_dict(scene_to_dict(scene))
        self.assertFalse(restored.post.enabled)
        legacy = scene_to_dict(CubeDemo().build_scene())
        legacy["environment"].pop("post", None)
        self.assertTrue(scene_from_dict(legacy).post.enabled)
        with self.assertRaises(TypeError):
            bad = scene_to_dict(scene)
            bad["environment"]["post"] = "on"
            scene_from_dict(bad)

    def test_scene_document_and_inspector_expose_post(self):
        from keystone.web.scene import scene_document

        document = scene_document(CubeDemo().build_scene())
        self.assertEqual(
            document["post"],
            {
                "enabled": True,
                "tone": "none",
                "exposure": 1.12,
                "vignette": 0.28,
                "anti_alias": "none",
            },
        )


if __name__ == "__main__":
    unittest.main()

class PostToneTest(unittest.TestCase):
    def test_settings_validate_and_round_trip(self):
        self.assertEqual(PostSettings().tone, "none")
        scene = Scene()
        scene.post = PostSettings(tone="aces")
        restored = scene_from_dict(scene_to_dict(scene))
        self.assertEqual(restored.post.tone, "aces")
        legacy = scene_to_dict(Scene())
        legacy["environment"]["post"].pop("tone", None)
        self.assertEqual(scene_from_dict(legacy).post.tone, "none")
        with self.assertRaises(ValueError):
            PostSettings(tone="film")
        with self.assertRaises(ValueError):
            scene_from_dict({"schema": 1, "environment": {"post": {"enabled": True, "tone": "film"}}})

    def test_set_scene_accepts_and_rejects_a_tone(self):
        from keystone.web.editor import set_scene

        scene = CubeDemo().build_scene()
        set_scene(scene, {"environment": {"tone": "reinhard"}})
        self.assertEqual(scene.post.tone, "reinhard")
        with self.assertRaises(ValueError):
            set_scene(scene, {"environment": {"tone": "film"}})

    def test_describe_advertises_tonemapping(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["post_tonemap"])


class PostToneRenderTest(unittest.TestCase):
    def setUp(self):
        from keystone.gpu.context import GLContext
        from keystone.gpu.renderer import Renderer

        self.context = GLContext(64, 48, visible=False)
        self.addCleanup(self.context.close)
        self.renderer = Renderer(64, 48)
        self.addCleanup(self.renderer.release)

    def _scene(self, tone):
        from keystone.geometry import Material
        from keystone.math3d import Vec3
        from keystone.primitives import cube
        from keystone.scene import Node, Transform

        scene = Scene()
        scene.background = Vec3(0.02, 0.02, 0.03)
        scene.sky = scene.background
        scene.add(
            Node(
                "screen",
                transform=Transform(position=Vec3(0.0, 0.0, -3.0)),
                mesh=cube(2.0),
                material=Material(
                    color=Vec3(0.0, 0.0, 0.0),
                    specular=0.0,
                    metallic=0.0,
                    roughness=1.0,
                    emissive=Vec3(0.8, 0.8, 0.8),
                ),
            )
        )
        scene.post = PostSettings(tone=tone)
        return scene

    def _center(self):
        pixels = self.renderer.read_pixels()
        index = ((48 // 2) * 64 + 64 // 2) * 4
        return tuple(pixels[index : index + 4])

    def test_reinhard_and_aces_darken_a_bright_surface(self):
        self.renderer.render(self._scene("none"))
        none = self._center()[0]
        stats = self.renderer.last_stats
        self.assertEqual(stats["post_tone"], "none")
        self.renderer.render(self._scene("reinhard"))
        reinhard = self._center()[0]
        self.assertEqual(self.renderer.last_stats["post_tone"], "reinhard")
        self.renderer.render(self._scene("aces"))
        aces = self._center()[0]
        self.assertGreater(none, reinhard)
        self.assertNotEqual(aces, reinhard)
        self.assertLessEqual(aces, none)

    def test_disabled_post_ignores_the_tone(self):
        off = self._scene("none")
        off.post = PostSettings(enabled=False, tone="none")
        self.renderer.render(off)
        first = self._center()
        changed = self._scene("aces")
        changed.post = PostSettings(enabled=False, tone="aces")
        self.renderer.render(changed)
        self.assertEqual(first, self._center())

class PostExposureTest(unittest.TestCase):
    def test_defaults_match_the_grade_constants(self):
        settings = PostSettings()
        self.assertAlmostEqual(settings.exposure, POST_EXPOSURE)
        self.assertAlmostEqual(settings.vignette, POST_VIGNETTE)

    def test_settings_validate(self):
        self.assertEqual(PostSettings(exposure=0.0, vignette=0.0).exposure, 0.0)
        self.assertEqual(PostSettings(exposure=2.5, vignette=1.0).vignette, 1.0)
        for bad in (-0.1, float("nan"), float("inf")):
            with self.subTest(exposure=bad), self.assertRaises(ValueError):
                PostSettings(exposure=bad)
        for bad in (-0.1, 1.1, float("nan")):
            with self.subTest(vignette=bad), self.assertRaises(ValueError):
                PostSettings(vignette=bad)
        with self.assertRaises(TypeError):
            PostSettings(exposure=True)  # type: ignore[arg-type]

    def test_snapshot_round_trips_exposure_and_vignette(self):
        scene = Scene()
        scene.post = PostSettings(exposure=2.0, vignette=0.0)
        restored = scene_from_dict(scene_to_dict(scene))
        self.assertEqual(restored.post.exposure, 2.0)
        self.assertEqual(restored.post.vignette, 0.0)
        legacy = scene_to_dict(Scene())
        legacy["environment"]["post"].pop("exposure")
        legacy["environment"]["post"].pop("vignette")
        self.assertEqual(scene_from_dict(legacy).post.exposure, POST_EXPOSURE)

    def test_set_scene_accepts_and_rejects_grade_values(self):
        from keystone.web.editor import set_scene

        scene = CubeDemo().build_scene()
        set_scene(scene, {"environment": {"exposure": 1.5, "vignette": 0.1}})
        self.assertEqual(scene.post.exposure, 1.5)
        self.assertEqual(scene.post.vignette, 0.1)
        with self.assertRaises(ValueError):
            set_scene(scene, {"environment": {"exposure": -1.0}})
        with self.assertRaises(ValueError):
            set_scene(scene, {"environment": {"vignette": 2.0}})


class PostExposureRenderTest(unittest.TestCase):
    def setUp(self):
        from keystone.gpu.context import GLContext
        from keystone.gpu.renderer import Renderer

        self.context = GLContext(64, 48, visible=False)
        self.addCleanup(self.context.close)
        self.renderer = Renderer(64, 48)
        self.addCleanup(self.renderer.release)

    def _scene(self, exposure: float, vignette: float = 0.0) -> Scene:
        from keystone.geometry import Material
        from keystone.math3d import Vec3
        from keystone.primitives import cube
        from keystone.scene import Node, Transform

        scene = Scene()
        scene.background = Vec3(0.02, 0.02, 0.03)
        scene.sky = scene.background
        scene.add(
            Node(
                "screen",
                transform=Transform(position=Vec3(0.0, 0.0, -3.0)),
                mesh=cube(2.0),
                material=Material(
                    color=Vec3(0.30, 0.30, 0.30),
                    specular=0.0,
                    metallic=0.0,
                    roughness=1.0,
                ),
            )
        )
        scene.post = PostSettings(exposure=exposure, vignette=vignette)
        return scene

    def _center(self):
        pixels = self.renderer.read_pixels()
        index = ((48 // 2) * 64 + 64 // 2) * 4
        return tuple(pixels[index : index + 4])

    def _corner(self):
        pixels = self.renderer.read_pixels()
        return tuple(pixels[0:4])

    def test_exposure_brightens_and_reports(self):
        self.renderer.render(self._scene(1.0))
        base = self._center()[0]
        self.assertEqual(self.renderer.last_stats["post_exposure"], 1.0)
        self.renderer.render(self._scene(2.0))
        brighter = self._center()[0]
        self.assertGreater(brighter, base)
        self.assertEqual(self.renderer.last_stats["post_exposure"], 2.0)

    def test_vignette_darkens_the_corner(self):
        self.renderer.render(self._scene(1.0, vignette=0.0))
        clear = self._corner()
        self.renderer.render(self._scene(1.0, vignette=1.0))
        dark = self._corner()
        self.assertLess(dark[0], clear[0])
        self.assertEqual(self.renderer.last_stats["post_vignette"], 1.0)

class PostFxaaTest(unittest.TestCase):
    def test_settings_validate_and_round_trip(self):
        self.assertEqual(PostSettings().anti_alias, "none")
        scene = Scene()
        scene.post = PostSettings(anti_alias="fxaa")
        restored = scene_from_dict(scene_to_dict(scene))
        self.assertEqual(restored.post.anti_alias, "fxaa")
        legacy = scene_to_dict(Scene())
        legacy["environment"]["post"].pop("anti_alias")
        self.assertEqual(scene_from_dict(legacy).post.anti_alias, "none")
        with self.assertRaises(ValueError):
            PostSettings(anti_alias="smaa")
        with self.assertRaises(ValueError):
            scene_from_dict(
                {"schema": 1, "environment": {"post": {"enabled": True, "anti_alias": "smaa"}}}
            )

    def test_set_scene_accepts_and_rejects_anti_alias(self):
        from keystone.web.editor import set_scene

        scene = CubeDemo().build_scene()
        set_scene(scene, {"environment": {"anti_alias": "fxaa"}})
        self.assertEqual(scene.post.anti_alias, "fxaa")
        set_scene(scene, {"environment": {"anti_alias": "none"}})
        self.assertEqual(scene.post.anti_alias, "none")
        with self.assertRaises(ValueError):
            set_scene(scene, {"environment": {"anti_alias": "smaa"}})

    def test_describe_advertises_fxaa(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["post_fxaa"])


class PostFxaaRenderTest(unittest.TestCase):
    def setUp(self):
        from keystone.gpu.context import GLContext
        from keystone.gpu.renderer import Renderer

        self.context = GLContext(64, 48, visible=False)
        self.addCleanup(self.context.close)
        self.renderer = Renderer(64, 48)
        self.addCleanup(self.renderer.release)

    def _scene(self, anti_alias: str) -> Scene:
        from keystone.geometry import Material
        from keystone.math3d import Vec3
        from keystone.primitives import cube
        from keystone.scene import Node, Transform

        scene = Scene()
        scene.background = Vec3(0.02, 0.02, 0.03)
        scene.sky = scene.background
        scene.add(
            Node(
                "screen",
                transform=Transform(
                    position=Vec3(0.0, 0.0, -3.0),
                    rotation=__import__("keystone.math3d", fromlist=["Quat"]).Quat.from_axis_angle(
                        Vec3.UP, 0.3
                    ),
                ),
                mesh=cube(2.0),
                material=Material(color=Vec3(0.9, 0.2, 0.2), specular=0.0),
            )
        )
        scene.post = PostSettings(anti_alias=anti_alias)
        return scene

    def test_fxaa_changes_silhouette_pixels_and_reports(self):
        self.renderer.render(self._scene("none"))
        off = self.renderer.read_pixels()
        self.assertEqual(self.renderer.last_stats["post_aa"], "none")
        self.renderer.render(self._scene("fxaa"))
        on = self.renderer.read_pixels()
        self.assertEqual(self.renderer.last_stats["post_aa"], "fxaa")
        self.assertNotEqual(off, on)


    def test_bloom_and_fxaa_compose(self):
        self.renderer.render(self._scene("none"))
        off = self.renderer.read_pixels()
        self.assertEqual(self.renderer.last_stats["bloom_enabled"], 1)
        self.renderer.render(self._scene("fxaa"))
        on = self.renderer.read_pixels()
        self.assertEqual(self.renderer.last_stats["post_aa"], "fxaa")
        self.assertEqual(self.renderer.last_stats["bloom_enabled"], 1)
        self.assertNotEqual(off, on)

    def test_fxaa_leaves_a_uniform_frame_alone(self):
        from keystone.math3d import Vec3

        scene = Scene()
        scene.background = Vec3(0.1, 0.2, 0.3)
        scene.sky = scene.background
        scene.post = PostSettings(anti_alias="fxaa")
        self.renderer.render(scene)
        with_aa = self.renderer.read_pixels()
        scene.post = PostSettings(anti_alias="none")
        self.renderer.render(scene)
        self.assertEqual(with_aa, self.renderer.read_pixels())
