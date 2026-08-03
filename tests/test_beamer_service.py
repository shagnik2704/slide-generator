import unittest

from src.services.beamer_service import (
    DEFAULT_THEME_COLOR,
    generate_beamer_template,
    normalize_theme_color,
)


def color_line(tex: str) -> str:
    return next(line for line in tex.splitlines() if "definecolor" in line)


class NormalizeThemeColorTests(unittest.TestCase):
    def test_accepts_hex_with_and_without_hash(self):
        self.assertEqual(normalize_theme_color("#1F4E79"), "1F4E79")
        self.assertEqual(normalize_theme_color("1f4e79"), "1F4E79")

    def test_expands_three_digit_shorthand(self):
        self.assertEqual(normalize_theme_color("#abc"), "AABBCC")

    def test_empty_falls_back_to_the_default(self):
        self.assertEqual(normalize_theme_color(None), DEFAULT_THEME_COLOR.lstrip("#"))
        self.assertEqual(normalize_theme_color(""), DEFAULT_THEME_COLOR.lstrip("#"))

    def test_rejects_anything_that_is_not_a_hex_colour(self):
        """The value is interpolated into a .tex the user then compiles, so a
        non-hex value must raise rather than be escaped through."""
        for value in (
            r"#708094}\input{/etc/passwd",
            r"red}\immediate\write18{rm -rf ~}",
            "#12345",
            "rebeccapurple",
            "#GGGGGG",
            123,
            [],
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_theme_color(value)


class BeamerThemeColorTests(unittest.TestCase):
    def test_default_keeps_the_historic_slate(self):
        self.assertIn("{HTML}{708094}", color_line(generate_beamer_template()))

    def test_custom_colour_reaches_the_document(self):
        tex = generate_beamer_template(theme_color="#8C2F39")

        self.assertIn("{HTML}{8C2F39}", color_line(tex))
        self.assertIn(r"\setbeamercolor{structure}{fg=themecolor}", tex)
        self.assertIn(r"\setbeamercolor{alerted text}{fg=themecolor}", tex)

    def test_bad_colour_raises_before_producing_a_document(self):
        with self.assertRaises(ValueError):
            generate_beamer_template(theme_color="blue}\\input{x")


if __name__ == "__main__":
    unittest.main()
