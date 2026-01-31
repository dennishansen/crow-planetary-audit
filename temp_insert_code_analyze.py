import re
import sys # ADDED THIS IMPORT
from pathlib import Path

main_py_path = Path("main.py")
main_content = main_py_path.read_text()
main_lines = main_content.splitlines(keepends=True)

# 1. Insert CODE_ANALYZE action into the action enum
# Find the line that starts with 'ACTIONS =' (more robust regex)
actions_start_line_index = -1
for i, line in enumerate(main_lines):
    if re.match(r"^\s*ACTIONS\s*=", line): # Use regex to find ACTIONS = potentially with whitespace
        actions_start_line_index = i
        break

if actions_start_line_index != -1:
    # Check if a line 'CODE_ANALYZE' already exists immediately after the ACTIONS = block
    inserted = False
    for i in range(actions_start_line_index + 1, len(main_lines)):
        if main_lines[i].strip() == "CODE_ANALYZE":
            print("CODE_ANALYZE already in ACTIONS enum. Skipping insertion.")
            inserted = True
            break
    if not inserted:
        main_lines.insert(actions_start_line_index + 1, "CODE_ANALYZE\nmessage to display\n")
        print("Inserted CODE_ANALYZE into ACTIONS enum.")
else:
    print("Could not find 'ACTIONS =' in main.py. Aborting enum modification.")
    sys.exit(1)


# 2. Insert action handler into execute_action
action_handler_insertion_point_index = -1
for i, line in enumerate(main_lines):
    if line.strip() == 'elif action == "INTERNAL_QUERY":':
        action_handler_insertion_point_index = i
        break

if action_handler_insertion_point_index != -1:
    # Build the action handler string to check against
    code_analyze_handler = '    elif action == "CODE_ANALYZE":'
    # Check if the CODE_ANALYZE handler is already there (looking ahead a few lines)
    inserted = False
    for i in range(action_handler_insertion_point_index + 1, min(len(main_lines), action_handler_insertion_point_index + 5)):
        if main_lines[i].strip().startswith(code_analyze_handler):
            print("CODE_ANALYZE action handler already exists. Skipping insertion.")
            inserted = True
            break
    if not inserted:
        new_handler_lines = [
            '    elif action == "CODE_ANALYZE":\n',
            '        log(f"{C.ACTION}[CODE_ANALYZE]{C.RESET} {content}")\n',
            '        result = execute_code_analyze(Path(content))\n',
        ]
        main_lines[action_handler_insertion_point_index+1:action_handler_insertion_point_index+1] = new_handler_lines
        print("Inserted CODE_ANALYZE action handler.")
else:
    print("Could not find 'elif action == \"INTERNAL_QUERY\":' for handler insertion. Aborting handler modification.")
    sys.exit(1)


# 3. Add execute_code_analyze function
code_analyze_func_lines = """
def execute_code_analyze(file_path: Path):
    \"\"\"Analyzes a single Python code file for improvements using an LLM.\"\"\"
    if not file_path.is_file():
        return f"File not found: {file_path}"

    try:
        code_content = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return f"Could not read file {file_path}. Is it a text file?"

    current_model_name = fatigue.get_model() # Get current model from fatigue manager
    
    prompt_messages = [
        {\"role\": \"system\", \"content\": \"You are an expert Code Analyst AI. Your task is to review Python code for quality, best practices, potential bugs, performance issues, security risks, and adherence to common Python conventions (like PEP 8). Provide clear, actionable suggestions and where appropriate, code examples for fixes. Format your response as a structured Markdown report.\"},
        {\"role\": \"user\", \"content\": f\"Please analyze the following Python code for improvements. Focus on all aspects of code quality, performance, security, and best practices. Provide specific recommendations and code examples where possible. Also, mention the model you used for this analysis.\\n\\nFile: {file_path}\\n\\n```python\\n{code_content}\\n```\"}
    ]

    log(f"{C.SYSTEM}[CODE_ANALYZE] Starting LLM analysis of {file_path} using {current_model_name}...")

    try:
        # Use the global `model` object from main.py's context
        response = retry_with_backoff(lambda: model.generate_content(prompt_messages[1]['content'], model=current_model_name))
        response_text = get_response_text(response)

        # Ensure response_text is a clean string before writing
        clean_response_text = str(response_text).strip() # Convert to string and strip whitespace
        # Optional: further sanitize if special characters are problematic, e.g., using encode/decode
        # clean_response_text = clean_response_text.encode('utf-8', 'ignore').decode('utf-8')


        log(f"{C.SYSTEM}[CODE_ANALYZE Debug] Cleaned response_text len: {len(clean_response_text)}")
        log(f"{C.SYSTEM}[CODE_ANALYZE Debug] Cleaned response_text snippet: {clean_response_text[:200]}")

        report_output_dir = WORKSPACE / "memory" / "cortex"
        report_output_dir.mkdir(parents=True, exist_ok=True)
        report_filename = f"analysis_report_{file_path.name}.md"
        report_output_path = report_output_dir / report_filename

        try:
            report_output_path.write_text(clean_response_text)
            log(f"{C.SYSTEM}[CODE_ANALYZE] Analysis report saved to: {report_output_path.resolve()}") # Use .resolve() for absolute path
            return f"Analysis complete. Report saved to: {report_output_path.resolve()}"
        except Exception as write_e:
            log(f"{C.ERROR}[CODE_ANALYZE] Error writing report to {report_output_path.resolve()}: {write_e}")
            return f"Error writing analysis report: {write_e}"

    except Exception as e:
        log(f"{C.ERROR}[CODE_ANALYZE] Error during AI analysis of {file_path}: {e}")
        return f"Error during AI analysis: {e}"
""" .splitlines(keepends=True) # Split into lines immediately


function_insertion_point_index = -1
for i, line in enumerate(main_lines):
    if line.strip().startswith("def execute_internal_query(question):"):
        function_insertion_point_index = i
        break

if function_insertion_point_index != -1:
    # Check if the function is already there
    function_exists = False
    for i in range(function_insertion_point_index - len(code_analyze_func_lines) - 5, function_insertion_point_index): # Check a window above
        if i >= 0 and "def execute_code_analyze(file_path: Path):" in main_lines[i]:
            function_exists = True
            print("execute_code_analyze function already exists. Skipping insertion.")
            break
    if not function_exists:
        main_lines[function_insertion_point_index:function_insertion_point_index] = code_analyze_func_lines
        print("Inserted execute_code_analyze function.")
else:
    print("Could not find 'def execute_internal_query(question):' for function insertion. Aborting function modification.")
    sys.exit(1)


# Rewrite the entire main.py file
main_py_path.write_text("".join(main_lines))
print("main.py modified successfully for CODE_ANALYZE.")

