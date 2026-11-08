"""Tests for the shared typed-component JSON codec."""

import unittest
from dataclasses import dataclass

from keystone.component_codec import (
    component_from_dict,
    component_to_dict,
    json_safe,
    validate_component_types,
)


@dataclass(frozen=True)
class Health:
    value: int = 100


class ComponentCodecTest(unittest.TestCase):
    def test_dataclass_round_trip(self):
        encoded = component_to_dict(Health(7))
        self.assertEqual(encoded, {"type": "Health", "data": {"value": 7}})
        self.assertEqual(
            component_from_dict(encoded, {"Health": Health}), Health(7)
        )

    def test_primitive_round_trips(self):
        for value, name in (
            ("text", "str"),
            (5, "int"),
            (1.5, "float"),
            (True, "bool"),
            (None, "NoneType"),
            ([1, 2], "list"),
            ((1, 2), "tuple"),
            ({"a": 1}, "dict"),
        ):
            with self.subTest(value=value):
                encoded = component_to_dict(value)
                self.assertEqual(encoded["type"], name)
                decoded = component_from_dict(
                    encoded,
                    {
                        "str": str,
                        "int": int,
                        "float": float,
                        "bool": bool,
                        "NoneType": type(None),
                        "list": list,
                        "tuple": tuple,
                        "dict": dict,
                    },
                )
                self.assertEqual(decoded, value)
                self.assertIs(type(decoded), type(value))

    def test_from_dict_rejects_unknown_type_fields(self):
        document = {
            "type": "Health",
            "data": {"value": 3, "armour": 9},
        }
        with self.assertRaises(ValueError) as caught:
            component_from_dict(document, {"Health": Health})
        self.assertIn("armour", str(caught.exception))

    def test_from_dict_rejects_unknown_document_keys(self):
        document = {"type": "Health", "data": {"value": 3}, "notes": "typo"}
        with self.assertRaises(ValueError) as caught:
            component_from_dict(document, {"Health": Health})
        self.assertIn("notes", str(caught.exception))

    def test_from_dict_requires_type_and_data(self):
        for document in ({"data": 1}, {"type": "Health"}, [], "x"):
            with self.subTest(document=document), self.assertRaises(ValueError):
                component_from_dict(document, {"Health": Health})

    def test_from_dict_requires_a_type_map(self):
        with self.assertRaises(ValueError):
            component_from_dict({"type": "Health", "data": {}}, None)

    def test_from_dict_rejects_unknown_component_type(self):
        with self.assertRaises(ValueError):
            component_from_dict({"type": "Ghost", "data": {}}, {"Health": Health})

    def test_to_dict_rejects_an_unserializable_object(self):
        with self.assertRaises(TypeError):
            component_to_dict(object())

    def test_json_safe_rejects_non_finite_and_opaque_values(self):
        with self.assertRaises(ValueError):
            json_safe(float("nan"), "value")
        with self.assertRaises(ValueError):
            json_safe(float("inf"), "value")
        with self.assertRaises(ValueError):
            json_safe(object(), "value")
        self.assertEqual(json_safe({"a": [1, 2]}, "value"), {"a": [1, 2]})

    def test_validate_component_types_copies_and_rejects_bad_input(self):
        original = {"Health": Health}
        cleaned = validate_component_types(original)
        self.assertEqual(cleaned, original)
        self.assertIsNot(cleaned, original)
        self.assertIsNone(validate_component_types(None))
        with self.assertRaises(TypeError):
            validate_component_types(5)
        with self.assertRaises(ValueError):
            validate_component_types({"  ": Health})
        with self.assertRaises(TypeError):
            validate_component_types({"Health": "not a type"})


if __name__ == "__main__":
    unittest.main()
