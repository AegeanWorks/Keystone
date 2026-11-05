"""Unit tests for bounded undo/redo history."""

import unittest

from keystone.history import History


class HistoryTest(unittest.TestCase):
    def test_push_undo_redo_restores_values(self):
        history = History(capacity=4)
        history.push(1)
        history.push(2)
        history.push(3)
        self.assertTrue(history.can_undo)
        self.assertEqual(history.undo(), 2)
        self.assertEqual(history.undo(), 1)
        self.assertFalse(history.can_undo)
        self.assertEqual(history.redo(), 2)
        self.assertEqual(history.redo(), 3)
        self.assertFalse(history.redo_available)

    def test_new_push_clears_redo_branch(self):
        history = History()
        history.push("a")
        history.push("b")
        history.undo()
        history.push("c")
        self.assertFalse(history.can_redo)
        self.assertEqual(history.values(), ["a", "c"])

    def test_capacity_drops_oldest_entries(self):
        history = History(capacity=2)
        history.push(1)
        history.push(2)
        history.push(3)
        self.assertEqual(history.values(), [2, 3])
        self.assertEqual(history.undo(), 2)
        self.assertEqual(history.undo(), None)
        self.assertFalse(history.can_undo)

    def test_snapshots_are_deep_copied(self):
        payload = {"items": [1, 2]}
        history = History()
        history.push(payload)
        payload["items"].append(3)
        self.assertEqual(history.peek(), {"items": [1, 2]})
        restored = history.undo()
        self.assertIsNone(restored)
        history.push({"items": [4]})
        self.assertEqual(history.peek(), {"items": [4]})

    def test_clear_and_empty_behavior(self):
        history = History()
        self.assertIsNone(history.undo())
        self.assertIsNone(history.redo())
        history.push(1)
        history.clear()
        self.assertFalse(history.can_undo)
        self.assertFalse(history.can_redo)
        self.assertEqual(history.values(), [])

    def test_peek_returns_current_without_moving(self):
        history = History()
        history.push(1)
        history.push(2)
        self.assertEqual(history.peek(), 2)
        self.assertEqual(history.peek(), 2)

    def test_capacity_rejects_non_int(self):
        with self.assertRaises(TypeError):
            History(capacity=True)
        with self.assertRaises(TypeError):
            History(capacity=2.5)
        with self.assertRaises(TypeError):
            History(capacity="4")
        with self.assertRaises(ValueError):
            History(capacity=0)


if __name__ == "__main__":
    unittest.main()
