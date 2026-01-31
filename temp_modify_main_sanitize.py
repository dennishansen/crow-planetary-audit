import re
from pathlib import Path

main_py_path = Path("main.py")
main_content = main_py_path.read_text()

# Find the execute_code_analyze function and modify its content
# Specifically target the section where response_text is handled and written

# Pattern to find the existing logic we want to replace/modify
# This accounts for the debug prints I added previously
# I'll replace a larger block to ensure proper insertion
target_block_regex = re.compile(r"""
        log\(f"\{C\.SYSTEM\}\[CODE_ANALYZE Debug\] response_text type: \{type\(response_text\)\}, len: \{len\(response_text\)\ if isinstance\(response_text, str\)\ else \'N/A\'\}"\)
        log\(f"\{C\.SYSTEM\}\[CODE_ANALYZE Debug\] response_text snippet: \{response_text\[:200\]\ if isinstance\(response_text, str\)\ else \'N/A\'\}"\)

        report_output_dir = WORKSPACE / \"memory\" / \"cortex\"
        report_output_dir.mkdir\(parents=True, exist_ok=True\)
        report_filename = f\"analysis_report_{file_path.name}\.md\"
        report_output_path = report_output_dir / report_filename

        try:
            report_output_path.write_text\(response_text\)
            log\(f"\{C\.SYSTEM\}\[CODE_ANALYZE\] Analysis report saved to: \{report_output_path.resolve\(\)\}"\) # Use .resolve() for absolute path
            return f\"Analysis complete\. Report saved to: \{report_output_path.resolve\(\)}\"
        except Exception as write_e:
            log\(f"\{C\.ERROR\}\[CODE_ANALYZE\] Error writing report to \{report_output_path.resolve\(\)}\: \{write_e\}"\)
            return f\"Error writing analysis report: \{write_e\}\"
""", re.VERBOSE)

new_block_content = r"""
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
"""

main_content = re.sub(target_block_regex, new_block_content, main_content, flags=re.MULTILINE | re.VERBOSE)


main_py_path.write_text(main_content)
print("main.py updated with response_text sanitization and explicit path handling for debug.")
