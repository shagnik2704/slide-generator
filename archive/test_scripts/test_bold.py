"""
Test script to verify bold markdown conversion is working.
"""
from latex_templates import escape_latex

test_cases = [
    "This is **bold text** in a sentence.",
    "Multiple **bold** words **here** and **there**.",
    "**Start bold** and end normal.",
    "Normal start and **end bold**",
    "Text with special chars: **A&B**, **C%D**, **E$F**",
    "No bold here.",
    "Nested special: **Text with {braces} and $dollar$**"
]

print("=" * 60)
print("BOLD MARKDOWN TO LATEX CONVERSION TEST")
print("=" * 60)

for i, test in enumerate(test_cases, 1):
    result = escape_latex(test)
    print(f"\n{i}. INPUT:  {test}")
    print(f"   OUTPUT: {result}")
    
    # Check if conversion worked
    has_markdown_bold = "**" in result
    has_latex_bold = "\\textbf{" in result
    
    if "**" in test:
        if has_markdown_bold:
            print(f"   ❌ FAILED: Still has ** **")
        elif has_latex_bold:
            print(f"   ✅ PASSED: Converted to \\textbf{{}}")
        else:
            print(f"   ⚠️  WARNING: No bold found in output")
    else:
        if has_latex_bold:
            print(f"   ⚠️  WARNING: Added bold where none existed")
        else:
            print(f"   ✅ PASSED: No bold conversion needed")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
