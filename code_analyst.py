from typing import Dict
import argparse
import os
from pathlib import Path
import json
import requests  # Import requests for the client call
from openrouter_client import HybridClient, ChatResponse # Assuming HybridClient is aliased as OpenRouterClient
from main import fatigue # Access to fatigue manager for model selection

# Initialize the HybridClient
# The HybridClient will automatically pick up OPENROUTER_API_KEY from environment variables
client = HybridClient()

def analyze_code(file_path: Path, verbose: bool = False) -> Dict:
    """
    Analyzes a single Python code file for improvements using an LLM.

    Args:
        file_path: The path to the code file to analyze.
        verbose: If True, prints additional debugging information.

    Returns:
        A dictionary containing the analysis report.
    """
    if not file_path.is_file():
        return {"error": f"File not found: {file_path}"}

    try:
        code_content = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return {"error": f"Could not read file {file_path}. Is it a text file?"}

    # Get the current model from the fatigue manager
    current_model = fatigue.get_model()
    
    # Construct the prompt for code analysis
    prompt_messages = [
        {"role": "system", "content": "You are an expert Code Analyst AI. Your task is to review Python code for quality, best practices, potential bugs, performance issues, security risks, and adherence to common Python conventions (like PEP 8). Provide clear, actionable suggestions and where appropriate, code examples for fixes. Format your response as a structured Markdown report."},
        {"role": "user", "content": f"Please analyze the following Python code for improvements. Focus on all aspects of code quality, performance, security, and best practices. Provide specific recommendations and code examples where possible. Also, mention the model you used for this analysis.\n\nFile: {file_path}\n\n```python\n{code_content}\n```"}
    ]

    if verbose:
        print(f"Analyzing file: {file_path}")
        print(f"Using model: {current_model}")
        print(f"Prompt length approx: {sum(len(msg['content']) for msg in prompt_messages)} characters")

    try:
        # Use the client to chat with the LLM
        # The client automatically handles fatigue-based model switching as per HybridClient logic
        chat_session = client.start_chat()
        response_text = chat_session.send_message(prompt_messages[1]['content']) # Sending the user message part
        
        # NOTE: The _chat_openrouter method in HybridClient already handles logging token usage and cost
        # So we don't need to explicitly do it here, but we can retrieve it if the client were to expose it.
        # For now, just rely on the ledger.log for overall cost tracking.

        return {
            "file": str(file_path),
            "model_used": current_model,
            "analysis_report": response_text
        }
    except Exception as e:
        return {"error": f"Error during AI analysis: {e}"}


def main():
    parser = argparse.ArgumentParser(description="Crow's Code Analyst Service.")
    parser.add_argument("file_path", type=str, help="Path to the Python file or directory to analyze.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output.")
    args = parser.parse_args()

    target_path = Path(args.file_path)

    if target_path.is_dir():
        # Future: Implement directory scanning
        print(f"Directory analysis for '{target_path}' is not yet implemented. Please provide a single file.")
        # For now, we'll just implement single file analysis
        results = {}
        for file in target_path.rglob("*.py"):
            print(f"Analyzing {file}...")
            analysis_result = analyze_code(file, args.verbose)
            results[str(file)] = analysis_result
            # Stop after first file for MVP
            break

    elif target_path.is_file():
        results = analyze_code(target_path, args.verbose)
    else:
        results = {"error": f"Invalid path: {target_path}. Must be a file or directory."}
    
    print("\n--- Code Analysis Result ---")
    if isinstance(results, dict) and "analysis_report" in results:
        print(f"File: {results.get('file')}")
        print(f"Model Used: {results.get('model_used')}")
        print("\n" + results['analysis_report'])
    elif isinstance(results, dict) and "error" in results:
        print(f"Error: {results['error']}")
    else:
        # If it was a directory analysis (future) results could be a dict of dicts
        json.dump(results, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
