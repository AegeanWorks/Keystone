"""Tests for the deterministic SplitMix64 random stream."""

import json
import unittest

from keystone.plugin import describe_game
from keystone.rng import RandomStream, RandomStreamState
from keystone.samples import CubeDemo


class SplitMixVectorTest(unittest.TestCase):
    def test_seed_zero_matches_the_reference_vector(self):
        stream = RandomStream(0)
        self.assertEqual(
            [stream.next_u64() for _ in range(3)],
            [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4, 0x06C45D188009454F],
        )

    def test_seed_12345_matches_the_reference_vector(self):
        stream = RandomStream(12345)
        self.assertEqual(
            [stream.next_u64() for _ in range(3)],
            [0x22118258A9D111A0, 0x346EDCE5F713F8ED, 0x1E9A57BC80E6721D],
        )

    def test_equal_seeds_repeat_and_different_seeds_diverge(self):
        left = RandomStream(7)
        right = RandomStream(7)
        self.assertEqual([left.next_u64() for _ in range(3)], [right.next_u64() for _ in range(3)])
        self.assertNotEqual(RandomStream(7).next_u64(), RandomStream(8).next_u64())

    def test_negative_seeds_are_masked_not_rejected(self):
        self.assertEqual(RandomStream(-1).next_u64(), RandomStream((1 << 64) - 1).next_u64())


class RandomStreamTest(unittest.TestCase):
    def test_random_is_in_the_unit_interval(self):
        stream = RandomStream(3)
        for _ in range(200):
            value = stream.random()
            self.assertGreaterEqual(value, 0.0)
            self.assertLess(value, 1.0)

    def test_uniform_respects_bounds(self):
        stream = RandomStream(11)
        for _ in range(100):
            value = stream.uniform(5.0, 9.0)
            self.assertGreaterEqual(value, 5.0)
            self.assertLessEqual(value, 9.0)
        with self.assertRaises(ValueError):
            stream.uniform(9.0, 5.0)
        with self.assertRaises(ValueError):
            stream.uniform(0.0, float("nan"))
        with self.assertRaises(TypeError):
            stream.uniform("a", 2.0)  # type: ignore[arg-type]

    def test_randint_is_inclusive_and_integral(self):
        stream = RandomStream(5)
        for _ in range(200):
            value = stream.randint(3, 5)
            self.assertIn(value, (3, 4, 5))
        self.assertEqual(stream.randint(4, 4), 4)
        with self.assertRaises(ValueError):
            stream.randint(5, 3)
        with self.assertRaises(TypeError):
            stream.randint(True, 3)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            stream.randint(1.0, 3)  # type: ignore[arg-type]

    def test_choice_picks_a_member_deterministically(self):
        first = RandomStream(9)
        second = RandomStream(9)
        picks = [first.choice(("a", "b", "c")) for _ in range(20)]
        self.assertEqual(picks, [second.choice(("a", "b", "c")) for _ in range(20)])
        self.assertTrue(set(picks) <= {"a", "b", "c"})
        with self.assertRaises(ValueError):
            first.choice(())
        with self.assertRaises(TypeError):
            first.choice(item for item in "abc")  # type: ignore[arg-type]

    def test_shuffled_returns_a_permutation_without_touching_the_input(self):
        original = ["a", "b", "c", "d"]
        first = RandomStream(4).shuffled(original)
        second = RandomStream(4).shuffled(original)
        self.assertEqual(first, second)
        self.assertEqual(sorted(first), sorted(original))
        self.assertEqual(original, ["a", "b", "c", "d"])
        self.assertEqual(RandomStream(4).shuffled(()), ())

    def test_fork_is_deterministic_and_label_sensitive(self):
        parent = RandomStream(21)
        child_a = parent.fork("enemies")
        child_b = parent.fork("enemies")
        self.assertNotEqual(child_a.next_u64(), child_b.next_u64(), "fork consumes parent state")
        left = RandomStream(21)
        right = RandomStream(21)
        self.assertEqual(left.fork("enemies").next_u64(), right.fork("enemies").next_u64())
        self.assertNotEqual(RandomStream(21).fork("enemies").next_u64(), RandomStream(21).fork("props").next_u64())
        with self.assertRaises(ValueError):
            RandomStream(1).fork(" ")
        with self.assertRaises(TypeError):
            RandomStream(1).fork(3)  # type: ignore[arg-type]

    def test_snapshot_restores_the_exact_sequence(self):
        stream = RandomStream(33)
        for _ in range(5):
            stream.next_u64()
        snapshot = stream.snapshot()
        document = snapshot.to_dict()
        self.assertEqual(json.loads(json.dumps(document)), document)
        restored = RandomStream.from_snapshot(document)
        self.assertEqual([restored.next_u64() for _ in range(5)], [stream.next_u64() for _ in range(5)])

    def test_snapshot_validation(self):
        valid = RandomStream(5).snapshot().to_dict()
        with self.assertRaises(TypeError):
            RandomStream.from_snapshot(["not", "a", "mapping"])  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            RandomStream.from_snapshot(dict(valid, schema=2))
        with self.assertRaises(ValueError):
            RandomStream.from_snapshot(dict(valid, extra=1))
        with self.assertRaises(TypeError):
            RandomStream.from_snapshot(dict(valid, state="0"))
        with self.assertRaises(TypeError):
            RandomStream.from_snapshot(dict(valid, seed=1.5))

    def test_snapshot_is_immutable_and_typed(self):
        snapshot = RandomStream(5).snapshot()
        self.assertIsInstance(snapshot, RandomStreamState)
        with self.assertRaises(AttributeError):
            snapshot.state = 0  # type: ignore[misc]


class RandomStreamValidationTest(unittest.TestCase):
    def test_seed_must_be_an_integer(self):
        with self.assertRaises(TypeError):
            RandomStream(True)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            RandomStream(1.5)  # type: ignore[arg-type]

    def test_describe_advertises_deterministic_random(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["deterministic_random"])


if __name__ == "__main__":
    unittest.main()
