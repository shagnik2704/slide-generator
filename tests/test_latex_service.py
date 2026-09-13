import unittest

from src.services.latex_service import escape_latex, generate_bullets


class LatexServiceEscapeTests(unittest.TestCase):
    def test_escapes_ampersand(self):
        self.assertEqual(escape_latex("C++ & Python"), r"C++ \& Python")

    def test_escapes_percentage(self):
        self.assertEqual(escape_latex("100% complete"), r"100\% complete")

    def test_escapes_dollar_sign(self):
        self.assertEqual(escape_latex("Cost is $50"), r"Cost is \$50")

    def test_escapes_hash_and_underscore(self):
        self.assertEqual(escape_latex("#include <stdio.h> in file_name.c"), r"\#include <stdio.h> in file\_name.c")

    def test_escapes_curly_braces(self):
        self.assertEqual(escape_latex("{block}"), r"\{block\}")

    def test_escapes_tilde_and_caret(self):
        escaped = escape_latex("~home and 2^3")
        self.assertIn(r"\textasciitilde{}", escaped)
        self.assertIn(r"\textasciicircum{}", escaped)

    def test_escapes_backslash(self):
        escaped = escape_latex(r"C:\Users\Name")
        self.assertIn(r"\textbackslash{}", escaped)

    def test_handles_non_string_gracefully(self):
        self.assertEqual(escape_latex(12345), "12345")
        self.assertEqual(escape_latex(None), "None")

    def test_converts_markdown_bold_to_latex_textbf(self):
        text = "This is **very important** text"
        self.assertEqual(escape_latex(text), r"This is \textbf{very important} text")

    def test_converts_markdown_bold_with_escaped_characters(self):
        text = "Learn **C++ & Python** today"
        self.assertEqual(escape_latex(text), r"Learn \textbf{C++ \& Python} today")


class LatexServiceBulletTests(unittest.TestCase):
    def test_generates_empty_string_for_empty_list(self):
        self.assertEqual(generate_bullets([]), "")
        self.assertEqual(generate_bullets(None), "")

    def test_generates_itemize_block_with_escaped_items(self):
        items = ["First item & details", "100% working", "**Bold** topic"]
        latex = generate_bullets(items)
        self.assertTrue(latex.startswith(r"\begin{itemize}"))
        self.assertTrue(latex.endswith(r"\end{itemize}"))
        self.assertIn(r"\item First item \& details", latex)
        self.assertIn(r"\item 100\% working", latex)
        self.assertIn(r"\item \textbf{Bold} topic", latex)


if __name__ == "__main__":
    unittest.main()
