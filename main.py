#!/usr/bin/env python3
"""
Crow - A minimal AI agent
Powered by Gemini
"""

import os
import re
import sys
import json
import select
import subprocess
import threading
from queue import Queue, Empty
from datetime import datetime
import google.generativeai as genai
from google.generativeai.types import content_types
from pathlib import Path
from dotenv import load_dotenv

# Load .env from Crow root
load_dotenv(Path(__file__).parent / '.env')

# Setup
WORKSPACE = Path(__file__).parent
LOGS_DIR = WORKSPACE / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Log file for this session
LOG_FILE = LOGS_DIR / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Heartbeat file for stall detection
HEARTBEAT_FILE = WORKSPACE / ".heartbeat"

# Conversation history files
HISTORY_FILE = WORKSPACE / "conversation.json"  # Compacted for loading
HISTORY_FULL_FILE = WORKSPACE / "conversation_full.json"  # Complete history for posterity

# Context budget (Gemini Flash has ~1M tokens ≈ 4M chars)
TOTAL_CONTEXT_CHARS = 4000000  # Total available
CONTEXT_UTILIZATION = 0.80     # Target utilization - compact when approaching this
COMPACTION_RATIO = 0.20        # Compact this % of oldest history when triggered

# ANSI colors
class C:
    CROW = '\033[95m'      # Magenta for Crow
    USER = '\033[96m'      # Cyan for User
    SYSTEM = '\033[90m'    # Gray for system info
    ACTION = '\033[93m'    # Yellow for actions
    ERROR = '\033[91m'     # Red for errors
    BOLD = '\033[1m'
    RESET = '\033[0m'

# Directories and patterns to skip when gathering repo
SKIP_DIRS = {'.git', '__pycache__', 'node_modules', 'logs', '.venv', 'venv', '.env', 'dist', 'build', 'backup'}
SKIP_EXTENSIONS = {'.pyc', '.pyo', '.so', '.dylib', '.dll', '.exe', '.bin', '.pkl', '.pickle', '.jpg', '.jpeg', '.png', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz'}

# Mode and message queue
MODE = "interactive"  # "interactive" or "autonomous"
user_message_queue = Queue()
input_thread = None
stop_input_thread = False
chat = None  # Global chat object for history access


def timestamp():
    """Return current timestamp string."""
    return datetime.now().strftime("%H:%M:%S")


def heartbeat():
    """Touch heartbeat file to signal we're alive."""
    HEARTBEAT_FILE.touch()


def input_listener():
    """Background thread to listen for user input without blocking."""
    global stop_input_thread
    while not stop_input_thread:
        try:
            # Use select for non-blocking check on stdin (Unix)
            if select.select([sys.stdin], [], [], 0.5)[0]:
                line = sys.stdin.readline().strip()
                if line:
                    ts = timestamp()
                    user_message_queue.put((ts, line))
                    log(f"{C.USER}[{ts}] You (queued): {line}{C.RESET}")
        except:
            pass


def get_queued_messages():
    """Collect all queued user messages."""
    messages = []
    while True:
        try:
            ts, msg = user_message_queue.get_nowait()
            messages.append(f"[{ts}] User: {msg}")
        except Empty:
            break
    return messages


def log(msg=""):
    """Print and log to file."""
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")


def save_history(chat):
    """Save conversation history to both full and working files."""
    history = []
    for content in chat.history:
        history.append({
            "role": content.role,
            "parts": [part.text for part in content.parts if hasattr(part, 'text')]
        })

    # Always save complete history for posterity
    with open(HISTORY_FULL_FILE, "w") as f:
        json.dump(history, f, indent=2)

    # Save working copy (will be compacted on load if needed)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def estimate_chars(history_data):
    """Estimate character count of history."""
    total = 0
    for item in history_data:
        for part in item.get("parts", []):
            total += len(part)
    return total


def summarize_messages(messages):
    """Use Gemini to summarize a chunk of conversation."""
    text = ""
    for msg in messages:
        role = msg["role"]
        parts = " ".join(msg.get("parts", []))
        text += f"{role}: {parts[:500]}...\n" if len(parts) > 500 else f"{role}: {parts}\n"

    prompt = f"""Summarize this conversation excerpt concisely, preserving key decisions, actions taken, and important context. Be brief but complete.

CONVERSATION:
{text}

SUMMARY:"""

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"[Summary failed: {e}] " + text[:1000]


def compact_history(history_data):
    """Compact oldest % of messages into summary when approaching context limit."""
    total_chars = estimate_chars(history_data)
    threshold = int(TOTAL_CONTEXT_CHARS * CONTEXT_UTILIZATION)

    if total_chars <= threshold:
        return history_data  # No compaction needed

    log(f"{C.SYSTEM}[Compacting history: {total_chars} chars, threshold {threshold}]{C.RESET}")

    # Calculate how many messages to compact (oldest COMPACTION_RATIO %)
    num_to_compact = max(1, int(len(history_data) * COMPACTION_RATIO))
    to_compact = history_data[:num_to_compact]
    to_keep = history_data[num_to_compact:]

    if not to_compact:
        return history_data

    # Summarize the oldest messages
    summary = summarize_messages(to_compact)

    # Create compacted history with summary prefix
    compacted = [{
        "role": "user",
        "parts": [f"[COMPACTED HISTORY - {num_to_compact} messages summarized]\n{summary}\n[END SUMMARY]"]
    }]
    compacted.extend(to_keep)

    log(f"{C.SYSTEM}[Compacted {num_to_compact} messages, now {estimate_chars(compacted)} chars]{C.RESET}")
    return compacted


def load_history():
    """Load and compact conversation history from file."""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE) as f:
            data = json.load(f)

        # Compact if needed
        data = compact_history(data)

        # Convert to Gemini content format
        history = []
        for item in data:
            history.append(content_types.to_content({
                "role": item["role"],
                "parts": item["parts"]
            }))
        return history
    except Exception as e:
        log(f"{C.ERROR}[Failed to load history: {e}]{C.RESET}")
        return []


def gather_repo_contents():
    """Gather all text files in the repo, skipping obvious non-essentials."""
    contents = []

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

            contents.append(file_content)
        except (UnicodeDecodeError, PermissionError):
            continue  # Skip binary or unreadable files

    return contents


def execute_internal_query(question):
    """Send question + entire repo to Gemini Flash for comprehensive answer."""
    repo_contents = gather_repo_contents()
    repo_text = "\n".join(repo_contents)

    prompt = f"""You are an internal knowledge system. Answer the following question as COMPREHENSIVELY as possible based on the repository contents below.

If you want specific files to be included verbatim in the response context, mark them with [INCLUDE: path/to/file] and they will be appended.

QUESTION: {question}

REPOSITORY CONTENTS:
{repo_text}"""

    try:
        response = model.generate_content(prompt)
        answer = response.text

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
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not set")
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
        ts = timestamp()
        log(f"\n{C.CROW}[{ts}] {C.BOLD}🐦‍⬛ Crow:{C.RESET} {C.CROW}{content}{C.RESET}\n")

        if MODE == "interactive":
            user_input = input(f"{C.USER}{C.BOLD}You:{C.RESET} {C.USER}")
            print(C.RESET, end='')  # Reset color after input
            ts_response = timestamp()
            log(f"[{ts_response}] [User responded: {user_input}]")
            return f"[{ts_response}] User response: {user_input}"
        else:
            # Autonomous mode - don't wait, just note the message was sent
            return f"[{ts}] Message delivered (autonomous mode - user may respond asynchronously)"

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

    elif action == "RESTART_SELF":
        log(f"\n{C.CROW}🐦‍⬛ Crow restarting...{C.RESET}")
        if chat:
            save_history(chat)  # Save before restart
        sys.exit(42)  # Special exit code tells runner to restart

    elif action == "DONE":
        return "SESSION_END"

    else:
        return f"Unknown action: {action}"

def parse_response(response):
    """Parse all actions from response - returns list of (action, content) tuples."""
    lines = response.strip().split('\n')
    valid_actions = ['THINK', 'TALK_TO_USER', 'RUN_COMMAND', 'INTERNAL_QUERY', 'RESTART_SELF', 'DONE']

    # Find all action lines and their indices
    action_indices = []
    for i, line in enumerate(lines):
        if line.strip() in valid_actions:
            action_indices.append((i, line.strip()))

    if not action_indices:
        return [(None, response)]

    # Extract content for each action
    actions = []
    for idx, (line_idx, action) in enumerate(action_indices):
        start = line_idx + 1
        end = action_indices[idx + 1][0] if idx + 1 < len(action_indices) else len(lines)
        content = '\n'.join(lines[start:end]).strip()
        actions.append((action, content))

    return actions

def run_session():
    """Run one session with Crow."""
    global MODE, input_thread, stop_input_thread, chat

    # Mode selection
    print(f"{C.CROW}{'=' * 50}")
    print(f"🐦‍⬛ Crow")
    print(f"{'=' * 50}{C.RESET}")
    print(f"\n{C.SYSTEM}Select mode:{C.RESET}")
    print(f"  {C.USER}[i]{C.RESET} Interactive - Crow waits for your responses")
    print(f"  {C.USER}[a]{C.RESET} Autonomous - Crow runs freely, you can send messages anytime")
    mode_choice = input(f"\n{C.USER}Mode (i/a): {C.RESET}").strip().lower()
    MODE = "autonomous" if mode_choice == "a" else "interactive"

    # Start input listener thread for autonomous mode
    if MODE == "autonomous":
        stop_input_thread = False
        input_thread = threading.Thread(target=input_listener, daemon=True)
        input_thread.start()
        log(f"{C.SYSTEM}[Autonomous mode - type messages anytime, they'll be queued]{C.RESET}")

    # Load conversation history for continuity
    history = load_history()
    chat = model.start_chat(history=history)

    log(f"\n{C.CROW}{'=' * 50}")
    log(f"🐦‍⬛ Crow Session Starting ({MODE} mode)")
    if history:
        log(f"[Restored {len(history)} messages from previous session]")
    log(f"{'=' * 50}{C.RESET}")

    # If continuing, just prompt to continue; if fresh, send seed prompt
    if history:
        response = chat.send_message("[Session resumed. Continue where you left off.]")
    else:
        response = chat.send_message(SEED_PROMPT)

    turn = 0
    while True:
        turn += 1
        heartbeat()  # Signal we're alive
        text = response.text
        ts = timestamp()
        log(f"\n{C.SYSTEM}[{ts}] --- Turn {turn} ---{C.RESET}")
        log(f"{C.SYSTEM}{text}{C.RESET}")

        actions = parse_response(text)

        # Check if no valid actions found
        if len(actions) == 1 and actions[0][0] is None:
            log(f"{C.ERROR}[No valid action found]{C.RESET}")
            response = chat.send_message("Please respond with a valid action.")
            continue

        # Execute all actions and collect results
        results = []
        session_done = False
        for action, content in actions:
            log(f"{C.ACTION}[{action}]{C.RESET}")
            log(f"{C.SYSTEM}{repr(content[:100])}...{C.RESET}" if len(content) > 100 else f"{C.SYSTEM}{repr(content)}{C.RESET}")

            if action == "DONE":
                log(f"\n{C.CROW}🐦‍⬛ Crow ended session{C.RESET}")
                session_done = True
                break

            result = execute_action(action, content)
            log(f"{C.SYSTEM}→ {result[:200]}...{C.RESET}" if len(result) > 200 else f"{C.SYSTEM}→ {result}{C.RESET}")
            results.append(f"[{action}]: {result}")

        if session_done:
            break

        # Check for queued user messages (autonomous mode)
        queued = get_queued_messages()
        if queued:
            results.append(f"[USER_MESSAGES_WHILE_WORKING]:\n" + "\n".join(queued))

        # Send combined results back
        combined_results = "\n\n".join(results)
        response = chat.send_message(f"[{timestamp()}] Results:\n{combined_results}")

        # Save history for continuity
        save_history(chat)

    # Cleanup
    stop_input_thread = True
    log(f"\n{C.CROW}{'=' * 50}")
    log(f"🐦‍⬛ Session Complete")
    log(f"{'=' * 50}{C.RESET}")

if __name__ == "__main__":
    run_session()
