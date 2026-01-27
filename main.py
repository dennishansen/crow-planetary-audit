#!/usr/bin/env python3
"""
Crow - A minimal AI agent
Powered by Gemini
"""

import os
import re
import subprocess
from datetime import datetime
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv

# Load .env from Albatross root
load_dotenv(Path(__file__).parent / '.env')

# Setup
WORKSPACE = Path(__file__).parent
LOGS_DIR = WORKSPACE / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Log file for this session
LOG_FILE = LOGS_DIR / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Context budget (roughly 50k tokens ~ 200k chars)
MAX_REPO_CHARS = 200000
MAX_RESPONSE_CHARS = 50000

# Directories and patterns to skip when gathering repo
SKIP_DIRS = {'.git', '__pycache__', 'node_modules', 'logs', '.venv', 'venv', '.env', 'dist', 'build'}
SKIP_EXTENSIONS = {'.pyc', '.pyo', '.so', '.dylib', '.dll', '.exe', '.bin', '.pkl', '.pickle', '.jpg', '.jpeg', '.png', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz'}

def log(msg=""):
    """Print and log to file."""
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")


def gather_repo_contents():
    """Gather all text files in the repo, skipping obvious non-essentials."""
    contents = []
    total_chars = 0

    for path in WORKSPACE.rglob('*'):
        if not path.is_file():
            continue

        # Skip if in excluded directory
        if any(skip in path.parts for skip in SKIP_DIRS):
            continue

        # Skip binary extensions
        if path.suffix.lower() in SKIP_EXTENSIONS:
            continue

        # Try to read as text
        try:
            text = path.read_text(encoding='utf-8')
            rel_path = path.relative_to(WORKSPACE)
            file_content = f"=== {rel_path} ===\n{text}\n"

            if total_chars + len(file_content) > MAX_REPO_CHARS:
                return contents, True  # True = truncated

            contents.append(file_content)
            total_chars += len(file_content)
        except (UnicodeDecodeError, PermissionError):
            continue  # Skip binary or unreadable files

    return contents, False


def execute_internal_query(question):
    """Send question + entire repo to Gemini Flash for comprehensive answer."""
    repo_contents, truncated = gather_repo_contents()

    if truncated:
        log("[INTERNAL_QUERY] WARNING: Repo too large, some files truncated")

    repo_text = "\n".join(repo_contents)

    prompt = f"""You are an internal knowledge system. Answer the following question as COMPREHENSIVELY as possible based on the repository contents below.

If you want specific files to be included verbatim in the response context, mark them with [INCLUDE: path/to/file] and they will be appended.

QUESTION: {question}

REPOSITORY CONTENTS:
{repo_text}"""

    try:
        response = model.generate_content(prompt)
        answer = response.text

        if len(answer) > MAX_RESPONSE_CHARS:
            log("[INTERNAL_QUERY] WARNING: Response too large, truncating")
            answer = answer[:MAX_RESPONSE_CHARS] + "\n[TRUNCATED]"

        # Parse [INCLUDE: filepath] markers and append those files
        includes = re.findall(r'\[INCLUDE:\s*([^\]]+)\]', answer)

        if includes:
            answer += "\n\n=== INCLUDED FILES ==="
            for filepath in includes:
                filepath = filepath.strip()
                full_path = WORKSPACE / filepath
                if full_path.exists() and full_path.is_file():
                    try:
                        answer += f"\n\n=== {filepath} ===\n{full_path.read_text()}"
                    except:
                        answer += f"\n\n=== {filepath} ===\n[Could not read file]"

        return answer
    except Exception as e:
        return f"Error in internal query: {e}"


# Gemini setup
# Get API key - check multiple env var names
api_key = None
for key_name in ["GEMINI_API_KEY", "GEMENI_API_KEY", "GOOGLE_API_KEY"]:
    val = os.environ.get(key_name)
    if val and len(val) > 0:
        api_key = val
        break
if not api_key:
    raise ValueError("No Gemini API key found! Set GEMINI_API_KEY environment variable.")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-3-flash-preview')

# The Seed
SEED_PROMPT = (Path(__file__).parent / "system_instructions.txt").read_text()


def execute_action(action, content):
    """Execute an action and return the result."""
    content = content.strip()

    if action == "THINK":
        return "[THOUGHT_COMPLETE]"

    elif action == "TALK_TO_USER":
        log(f"\n🐦‍⬛ Crow: {content}\n")
        return "[Message sent]"

    elif action == "RUN_COMMAND":
        try:
            result = subprocess.run(
                content, shell=True, capture_output=True, text=True,
                timeout=30, cwd=WORKSPACE
            )
            output = result.stdout + result.stderr
            return output or "(no output)"
        except Exception as e:
            return f"Error: {e}"

    elif action == "INTERNAL_QUERY":
        return execute_internal_query(content)

    elif action == "DONE":
        return "SESSION_END"

    else:
        return f"Unknown action: {action}"

def parse_response(response):
    """Parse all actions from response - returns list of (action, content) tuples."""
    lines = response.strip().split('\n')

    valid_actions = ['THINK', 'TALK_TO_USER', 'RUN_COMMAND', 'INTERNAL_QUERY', 'DONE']

    # Find all action lines and their indices
    action_indices = []
    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # Check for exact match (e.g., "WEB_SEARCH")
        if line_stripped in valid_actions:
            action_indices.append((i, line_stripped))
            continue

        # Check for "ACTION_NAME: ACTION" or "ACTION:" format
        for valid in valid_actions:
            if line_stripped == f"ACTION_NAME: {valid}" or line_stripped == f"{valid}:":
                action_indices.append((i, valid))
                break

    if not action_indices:
        return [(None, response)]

    # Extract content for each action (content goes until the next action or end)
    actions = []
    for idx, (line_idx, action) in enumerate(action_indices):
        # Content starts after the action line
        start = line_idx + 1
        # Content ends at the next action line, or end of response
        if idx + 1 < len(action_indices):
            end = action_indices[idx + 1][0]
        else:
            end = len(lines)
        content = '\n'.join(lines[start:end]).strip()
        actions.append((action, content))

    return actions

def run_session():
    """Run one session with Crow."""
    chat = model.start_chat(history=[])

    log("=" * 50)
    log("🐦‍⬛ Crow Session Starting")
    log("=" * 50)

    response = chat.send_message(SEED_PROMPT)
    
    max_turns = 50
    for turn in range(max_turns):
        text = response.text
        log(f"\n--- Turn {turn + 1} ---")
        log(text)
        
        actions = parse_response(text)
        
        # Check if no valid actions found
        if len(actions) == 1 and actions[0][0] is None:
            log("[PARSED] No valid action found")
            response = chat.send_message("Please respond with a valid action.")
            continue
        
        # Execute all actions and collect results
        results = []
        session_done = False
        for action, content in actions:
            log(f"[PARSED] Action: {action}")
            log(f"[PARSED] Content: {repr(content[:100])}..." if len(content) > 100 else f"[PARSED] Content: {repr(content)}")
            
            if action == "DONE":
                log("\n🐦‍⬛ Crow ended session")
                session_done = True
                break

            result = execute_action(action, content)
            log(f"[{action}] -> {result[:200]}..." if len(result) > 200 else f"[{action}] -> {result}")
            results.append(f"[{action}]: {result}")
        
        if session_done:
            break
        
        # Send combined results back
        combined_results = "\n\n".join(results)
        response = chat.send_message(f"Results:\n{combined_results}")
    
    log("\n" + "=" * 50)
    log("🐦‍⬛ Session Complete")
    log("=" * 50)

if __name__ == "__main__":
    run_session()
