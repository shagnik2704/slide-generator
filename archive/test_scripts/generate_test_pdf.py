"""
Generate PDF from test_fewshot_output.json
"""
import json
from models.state import AgentState
from nodes.pdf_node import generate_script_pdf, generate_images, convert_to_latex, compile_pdf

# Load the test script
with open('test_fewshot_output.json', 'r') as f:
    script_data = json.load(f)

print("=" * 60)
print("GENERATING PDF FROM TEST SCRIPT")
print("=" * 60)

# Create initial state
state = {'json_script': script_data}

# Step 1: Generate script PDF for review
print("\n1. Generating script PDF...")
result = generate_script_pdf(AgentState(**state))
state.update(result)
print(f"   ✓ Script PDF: {state.get('script_pdf_path', 'N/A')}")

# Step 2: Generate images
print("\n2. Generating images...")
result = generate_images(AgentState(**state))
state.update(result)
image_paths = state.get('image_paths', {})
print(f"   ✓ Generated {len(image_paths)} images")

# Step 3: Convert to LaTeX
print("\n3. Converting to LaTeX...")
result = convert_to_latex(AgentState(**state))
state.update(result)
print(f"   ✓ LaTeX file: {state.get('latex_path', 'N/A')}")

# Step 4: Compile PDF
print("\n4. Compiling final PDF...")
result = compile_pdf(AgentState(**state))
state.update(result)
pdf_path = state.get('pdf_path')

print("\n" + "=" * 60)
print("✓ PDF GENERATION COMPLETE")
print("=" * 60)
print(f"\nFinal PDF: {pdf_path}")
print(f"Script PDF: {state.get('script_pdf_path', 'N/A')}")
