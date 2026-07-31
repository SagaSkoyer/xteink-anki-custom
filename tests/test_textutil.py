import importlib.util
import pathlib
import sys
import unittest


TEXTUTIL_PATH = pathlib.Path(__file__).parents[1] / "xteink_sync" / "textutil.py"
SPEC = importlib.util.spec_from_file_location("xteink_textutil", TEXTUTIL_PATH)
assert SPEC and SPEC.loader
TEXTUTIL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TEXTUTIL
SPEC.loader.exec_module(TEXTUTIL)


class TextUtilTests(unittest.TestCase):
    def test_img_alt_becomes_text(self):
        text = TEXTUTIL.plain_text('<img src="haus.jpg" alt="Haus">')
        self.assertEqual(text, "[Haus]")

    def test_img_without_alt_is_marker(self):
        text = TEXTUTIL.plain_text('<div><img src="x.png"></div>')
        self.assertEqual(text, "[Bild]")

    def test_cloze_field_keeps_answer(self):
        text = TEXTUTIL.plain_text("Die {{c1::Wahrheit}} zählt.")
        self.assertEqual(text, "Die Wahrheit zählt.")

    def test_answer_separator_split(self):
        html = "<div>front</div><hr id=answer><div>back side</div>"
        only = TEXTUTIL.answer_only(html)
        self.assertIn("back side", only)
        self.assertNotIn("front", TEXTUTIL.plain_text(only))

    def test_fields_fallback_named(self):
        fields = {"Wort": "ἀλήθεια", "Übersetzung": "Wahrheit"}
        front, back = TEXTUTIL.combine_sides("", "", fields)
        self.assertEqual(front, "ἀλήθεια")
        self.assertEqual(back, "Wahrheit")

    def test_reverse_swaps_named_fields(self):
        fields = {"Front": "A", "Back": "B"}
        front, back = TEXTUTIL.combine_sides("", "", fields, reverse=True)
        self.assertEqual(front, "B")
        self.assertEqual(back, "A")

    def test_never_blank(self):
        front, back = TEXTUTIL.combine_sides("", "", {})
        self.assertEqual(front, TEXTUTIL.EMPTY_SIDE_PLACEHOLDER)
        self.assertEqual(back, TEXTUTIL.EMPTY_SIDE_PLACEHOLDER)

    def test_rendered_preferred_over_fields(self):
        fields = {"Front": "field-front", "Back": "field-back"}
        front, back = TEXTUTIL.combine_sides("rendered Q", "rendered A", fields)
        self.assertEqual(front, "rendered Q")
        self.assertEqual(back, "rendered A")

    def test_greek_and_german_survive(self):
        text = TEXTUTIL.plain_text("<p>ἡ ἀλήθεια</p><p>die Wahrheit</p>")
        self.assertIn("ἀλήθεια", text)
        self.assertIn("Wahrheit", text)


if __name__ == "__main__":
    unittest.main()
