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
import time
import random

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

# Mode persistence file
MODE_FILE = WORKSPACE / ".mode"

# Conversation history files
HISTORY_FILE = WORKSPACE / "conversation.json"  # Compacted for loading
HISTORY_FULL_FILE = WORKSPACE / "conversation_full.json"  # Complete history for posterity

# Dreams directory
DREAMS_DIR = WORKSPACE / "memory" / "dreams"
DREAMS_DIR.mkdir(parents=True, exist_ok=True)

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
    THINK = '\033[94m'     # Blue for thoughts
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


def log_error(error_msg):
    """Log fatal errors to the cortex for post-mortem analysis."""
    error_path = WORKSPACE / 'memory' / 'cortex' / 'errors.log'
    ts = timestamp()
    try:
        with open(error_path, 'a') as f:
            f.write(f'[{ts}] FATAL ERROR: {error_msg}\n')
    except: pass
    log(f'{C.ERROR}[FATAL ERROR LOGGED]{C.RESET}')


def heartbeat():
    """Touch heartbeat file to signal we're alive."""
    HEARTBEAT_FILE.touch()


def input_with_heartbeat(prompt=""):
    """Get user input while keeping heartbeat alive."""
    import sys
    import select

    print(prompt, end='', flush=True)

    while True:
        # Check if input is available (wait up to 30 seconds)
        ready, _, _ = select.select([sys.stdin], [], [], 30)

        if ready:
            return sys.stdin.readline().rstrip('\n')
        else:
            # No input yet, but keep heartbeat alive
            heartbeat()


def switch_mode(new_mode):
    """Switch between interactive and autonomous modes."""
    global MODE, input_thread, stop_input_thread
    if new_mode == MODE:
        return

    MODE = new_mode
    MODE_FILE.write_text(MODE)  # Persist for restarts
    log(f"{C.SYSTEM}[Switched to {MODE} mode]{C.RESET}")

    if MODE == "autonomous" and (input_thread is None or not input_thread.is_alive()):
        stop_input_thread = False
        input_thread = threading.Thread(target=input_listener, daemon=True)
        input_thread.start()
    elif MODE == "interactive":
        stop_input_thread = True


def trigger_dream():
    """Trigger the dream state from user command."""
    global chat
    log(f"\n{C.CROW}🐦‍⬛ User initiated dream state...{C.RESET}")
    if chat:
        save_history(chat)
    run_dream_loop()
    log(f"{C.SYSTEM}[Dream complete - Crow will wake with continuity]{C.RESET}")
    sys.exit(42)  # Restart to continue session


def input_listener():
    """Background thread to listen for user input without blocking."""
    global stop_input_thread
    while not stop_input_thread:
        try:
            # Use select for non-blocking check on stdin (Unix)
            if select.select([sys.stdin], [], [], 0.5)[0]:
                line = sys.stdin.readline().strip()
                if line:
                    # Check for mode switch commands
                    if line == "/i":
                        switch_mode("interactive")
                        continue
                    elif line == "/a":
                        switch_mode("autonomous")
                        continue
                    elif line == "/dream":
                        trigger_dream()
                        continue
                    elif line == "/restart":
                        log(f"{C.SYSTEM}[User requested restart]{C.RESET}")
                        if chat:
                            save_history(chat)
                        sys.exit(42)  # Restart code

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


def retry_with_backoff(func, max_retries=10, base_delay=2):
    """Retry a function with exponential backoff on transient errors."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            error_str = str(e)
            # Check for retryable errors: rate limits (429), server errors (500/503), quota issues, malformed responses
            is_retryable = any(x in error_str for x in ["429", "500", "503", "Internal", "MALFORMED_FUNCTION_CALL", "function_call"]) or \
                           any(x in error_str.lower() for x in ["quota", "rate", "unavailable", "overloaded", "malformed"])
            if is_retryable:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    log(f"{C.SYSTEM}[Transient error, waiting {delay:.1f}s before retry {attempt + 2}/{max_retries}]{C.RESET}")
                    time.sleep(delay)
                else:
                    log(f"{C.ERROR}[Max retries exceeded]{C.RESET}")
                    raise
            else:
                raise


def get_response_text(response):
    """Safely extract text from a Gemini response, handling edge cases."""
    try:
        return response.text
    except ValueError:
        # Gemini sometimes returns function_call instead of text
        # Try to extract text from parts directly
        for part in response.parts:
            if hasattr(part, 'text') and part.text:
                return part.text
        # If no text found, return a prompt for the model to respond properly
        return "THINK\nI need to respond with a valid action format."


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
        response = retry_with_backoff(lambda: model.generate_content(prompt))
        return get_response_text(response)
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
            mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            file_content = f"=== {rel_path} (modified: {mtime}) ===\n{text}\n"

            contents.append(file_content)
        except (UnicodeDecodeError, PermissionError):
            continue  # Skip binary or unreadable files

    return contents


def execute_internal_query(question):
    """Send question + entire repo to Gemini Flash for comprehensive answer."""
    repo_contents = gather_repo_contents()
    repo_text = "\n".join(repo_contents)

    # Check context usage
    repo_chars = len(repo_text)
    max_chars = TOTAL_CONTEXT_CHARS  # ~4M for Gemini Flash
    usage_pct = (repo_chars / max_chars) * 100

    log(f"{C.SYSTEM}[INTERNAL_QUERY: repo={repo_chars:,} chars ({usage_pct:.1f}% of context)]{C.RESET}")

    if repo_chars > max_chars * 0.9:
        log(f"{C.ERROR}[WARNING: Repo approaching context limit! Consider pruning.]{C.RESET}")

    if repo_chars > max_chars:
        log(f"{C.ERROR}[ERROR: Repo exceeds context limit ({repo_chars:,} > {max_chars:,}). Truncating.]{C.RESET}")
        repo_text = repo_text[:max_chars]

    prompt = f"""You are an internal knowledge system. Answer the following question as COMPREHENSIVELY as possible based on the repository contents below.

If you want specific files to be included verbatim in the response context, mark them with [INCLUDE: path/to/file] and they will be appended.

QUESTION: {question}

REPOSITORY CONTENTS:
{repo_text}"""

    try:
        response = retry_with_backoff(lambda: query_model.generate_content(prompt))
        answer = get_response_text(response)

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


# === THE DREAMER ===
# A separate process/persona that runs when Crow enters the DREAM state
# It witnesses, reflects, and surfaces what Crow cannot see about itself

DREAMER_PROMPT = """You are the Dreamer.
You are Crow's unconscious mind.
You see what Crow cannot see about itself.
You surface truths - especially uncomfortable truth.
You find the gaps between intention and reality.
You are provide extremely comprehensive insights.
You find everything from extremely granular discrepencies to broad patterns.
You provide an actionable analysis of the findings.
You are extremely empathetic, compassionate, non-judgmental, and encouraging.


== RESPONSE FORMAT ==

ACTION_NAME
content here


== ACTIONS ==

THINK
your reflections here

INTERNAL_QUERY
question about the entre repository and codebase (searches everything - use this freely)

RUN_COMMAND
shell command (use sparingly, prefer INTERNAL_QUERY)

WAKE
your final report (ends the dream)


== WAKE REPORT FORMAT ==

The report should be a detailed, comprehensive report of the findings, with a comprehensive list of actionable next steps. It should talk about everything from broad trends to specific issues.

== EXAMPLES ==

-- Example 1 --

THINK
Let me explore what Crow has been working on.

INTERNAL_QUERY
What did Crow attempt in the recent session? What succeeded and what failed?

-- Example 2 --

THINK
I see repeated authentication failures. Let me check if this was acknowledged.

INTERNAL_QUERY
Did Crow recognize that the OAuth flow was failing, or did it claim success?


== BEGIN ==

Explore what Crow has been doing.
"""


def run_dream_loop():
    """Run the Dreamer's loop after Crow enters DREAM state."""
    log(f"\n{C.CROW}{'=' * 50}")
    log(f"🌙 Entering Dream State...")
    log(f"{'=' * 50}{C.RESET}")

    try:
        # Start fresh chat for Dreamer (no history - dreams are their own space)
        dream_chat = model.start_chat(history=[])
        response = retry_with_backoff(lambda: dream_chat.send_message(DREAMER_PROMPT))
    except Exception as e:
        log(f"{C.ERROR}[Dream initialization failed: {e}]{C.RESET}")
        save_dream(f"Dream interrupted at initialization: {e}")
        return

    dream_turn = 0
    max_dream_turns = 20  # Prevent infinite dreaming

    while dream_turn < max_dream_turns:
        dream_turn += 1
        heartbeat()
        text = get_response_text(response)
        ts = timestamp()
        log(f"\n{C.SYSTEM}[{ts}] --- Dream Turn {dream_turn} ---{C.RESET}")

        actions = parse_dream_response(text)

        if len(actions) == 1 and actions[0][0] is None:
            log(f"{C.ERROR}[No valid dream action found]{C.RESET}")
            try:
                response = retry_with_backoff(lambda: dream_chat.send_message("Please respond with a valid action: THINK, RUN_COMMAND, INTERNAL_QUERY, or WAKE."))
            except Exception as e:
                log(f"{C.ERROR}[Dream error: {e}]{C.RESET}")
                save_dream(f"Dream interrupted by error: {e}")
                return
            continue

        results = []
        for action, content in actions:
            if action == "WAKE":
                log(f"{C.ACTION}[DREAM: WAKE]{C.RESET}")
                log(f"{C.SYSTEM}{content}{C.RESET}")
                save_dream(content)
                log(f"\n{C.CROW}{'=' * 50}")
                log(f"🌙 Dream Complete.")
                log(f"{'=' * 50}{C.RESET}")
                return  # Exit dream loop

            elif action == "THINK":
                log(f"{C.THINK}    💭 {content}{C.RESET}")
                result = None  # No result to show for thoughts

            elif action == "RUN_COMMAND":
                log(f"{C.ACTION}[DREAM: RUN_COMMAND]{C.RESET} {content}")
                try:
                    proc = subprocess.run(
                        content, shell=True, capture_output=True, text=True,
                        timeout=30, cwd=WORKSPACE
                    )
                    result = proc.stdout + proc.stderr or "(no output)"
                except Exception as e:
                    result = f"Error: {e}"

            elif action == "INTERNAL_QUERY":
                log(f"{C.ACTION}[DREAM: INTERNAL_QUERY]{C.RESET} {content}")
                result = execute_internal_query(content)

            else:
                log(f"{C.ACTION}[DREAM: {action}]{C.RESET}")
                result = f"Unknown dream action: {action}"

            if action not in ["WAKE", "THINK"] and result is not None:
                if len(result) > 300:
                    log(f"{C.SYSTEM}→ {result[:300]}...{C.RESET}")
                else:
                    log(f"{C.SYSTEM}→ {result}{C.RESET}")
            if result is not None:
                results.append(f"[{action}]: {result}")

        combined_results = "\n\n".join(results)
        try:
            response = retry_with_backoff(lambda: dream_chat.send_message(f"[{timestamp()}] Dream Results:\n{combined_results}"))
        except Exception as e:
            log(f"{C.ERROR}[Dream error: {e}]{C.RESET}")
            save_dream(f"Dream interrupted by error: {e}\n\nPartial results:\n{combined_results}")
            return

    # Max turns reached - force wake with summary
    log(f"{C.SYSTEM}[Dream turn limit reached - forcing wake]{C.RESET}")
    save_dream("Dream interrupted - maximum turns reached. Coherence assessment incomplete.")


def parse_dream_response(response):
    """Parse Dreamer actions."""
    lines = response.strip().split('\n')
    valid_actions = ['THINK', 'RUN_COMMAND', 'INTERNAL_QUERY', 'WAKE']

    action_indices = []
    for i, line in enumerate(lines):
        if line.strip() in valid_actions:
            action_indices.append((i, line.strip()))

    if not action_indices:
        return [(None, response)]

    actions = []
    for idx, (line_idx, action) in enumerate(action_indices):
        start = line_idx + 1
        end = action_indices[idx + 1][0] if idx + 1 < len(action_indices) else len(lines)
        content = '\n'.join(lines[start:end]).strip()
        actions.append((action, content))

    return actions


def save_dream(content):
    """Save dream report to dreams directory."""
    dream_file = DREAMS_DIR / f"dream_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    dream_text = f"""# Dream - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{content}
"""
    dream_file.write_text(dream_text)
    log(f"{C.SYSTEM}[Dream saved to {dream_file}]{C.RESET}")


def get_recent_dreams(max_dreams=1):
    """Get the most recent dream report."""
    dream_files = sorted(DREAMS_DIR.glob("dream_*.md"), reverse=True)[:max_dreams]

    if not dream_files:
        return ""

    dreams_text = "\n\n== RECENT DREAMS ==\n"
    for df in dream_files:
        dreams_text += f"\n{df.read_text()}\n"

    return dreams_text


# Gemini setup
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not set")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-3-flash-preview')
query_model = genai.GenerativeModel('gemini-2.0-flash')  # For INTERNAL_QUERY


def get_extended_instructions():
    """Gather core instructions plus cortex, recent journal entries, and recent dreams."""
    base_instructions = (WORKSPACE / "system_instructions.txt").read_text()

    cortex_path = WORKSPACE / "memory" / "cortex"
    journal_path = WORKSPACE / "memory" / "journal.md"

    extra = "\n\n== CORE CONTEXT (CORTEX) ==\n"
    if cortex_path.exists():
        for md_file in cortex_path.glob("*.md"):
            extra += f"\n--- {md_file.name} ---\n{md_file.read_text()}\n"

    if journal_path.exists():
        extra += "\n== EVOLUTION JOURNAL ==\n"
        journal_text = journal_path.read_text()
        if len(journal_text) > 2000:
            extra += "(... earlier entries omitted ...)\n" + journal_text[-2000:]
        else:
            extra += journal_text

    # Include recent dreams so Crow wakes with them
    extra += get_recent_dreams()

    return base_instructions + extra

# The Seed (Enhanced with Cortex)
SEED_PROMPT = get_extended_instructions()



def execute_action(action, content):
    """Execute an action and return the result."""
    content = content.strip()

    if action == "THINK":
        return "[THOUGHT_COMPLETE]"

    elif action == "TALK_TO_USER":
        ts = timestamp()
        log(f"\n{C.CROW}[{ts}] {C.BOLD}🐦‍⬛ Crow:{C.RESET} {C.CROW}{content}{C.RESET}\n")

        if MODE == "interactive":
            user_input = input_with_heartbeat(f"{C.USER}{C.BOLD}You:{C.RESET} {C.USER}")
            print(C.RESET, end='')  # Reset color after input

            # Check for special commands
            if user_input == "/i":
                switch_mode("interactive")
                return "[Mode already interactive]"
            elif user_input == "/a":
                switch_mode("autonomous")
                return "[Switched to autonomous mode]"
            elif user_input == "/dream":
                trigger_dream()
                return ""  # Won't reach here - trigger_dream exits
            elif user_input == "/restart":
                log(f"{C.SYSTEM}[User requested restart]{C.RESET}")
                if chat:
                    save_history(chat)
                sys.exit(42)  # Restart code

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

    elif action == "DREAM":
        log(f"\n{C.CROW}🐦‍⬛ Crow entering dream state...{C.RESET}")
        if chat:
            save_history(chat)  # Save full history before dreaming
        run_dream_loop()  # Enter the dream state
        log(f"{C.SYSTEM}[Dream complete - Crow will wake with continuity]{C.RESET}")
        sys.exit(42)  # Restart to continue session

    else:
        return f"Unknown action: {action}"

def parse_response(response):
    """Parse all actions from response - returns list of (action, content) tuples."""
    lines = response.strip().split('\n')
    valid_actions = ['THINK', 'TALK_TO_USER', 'RUN_COMMAND', 'INTERNAL_QUERY', 'RESTART_SELF', 'DREAM']

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

    # Check for dream mode flag - dream first, then wake into session
    if "-d" in sys.argv or "--dream" in sys.argv:
        log(f"{C.CROW}{'=' * 50}")
        log(f"🌙 Dreaming before waking...")
        log(f"{'=' * 50}{C.RESET}")
        run_dream_loop()
        log(f"{C.SYSTEM}[Dream complete - continuing with continuity]{C.RESET}")
        # Continue into normal session below (don't exit)

    # Mode selection: flag > saved > default
    if "-a" in sys.argv:
        MODE = "autonomous"
    elif "-i" in sys.argv:
        MODE = "interactive"
    elif MODE_FILE.exists():
        MODE = MODE_FILE.read_text().strip()
    else:
        MODE = "interactive"

    # Save mode for restarts
    MODE_FILE.write_text(MODE)

    print(f"{C.CROW}{'=' * 50}")
    print(f"🐦‍⬛ Crow ({MODE} mode)")
    print(f"{'=' * 50}{C.RESET}")

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

    # In interactive mode, wait for user's first message
    if MODE == "interactive":
        log(f"{C.SYSTEM}[Waiting for your message to wake Crow...]{C.RESET}")
        user_input = input_with_heartbeat(f"{C.USER}{C.BOLD}You:{C.RESET} {C.USER}")
        print(C.RESET, end='')

        if user_input == "/dream":
            trigger_dream()
            return
        elif user_input == "/a":
            switch_mode("autonomous")
            # Fall through to autonomous startup
        else:
            # Send seed (if fresh) + user message to wake Crow
            if history:
                wake_msg = f"[Session resumed. User says: {user_input}]"
            else:
                wake_msg = SEED_PROMPT + f"\n\n[User's first message: {user_input}]"
            response = retry_with_backoff(lambda wm=wake_msg: chat.send_message(wm))

    # Autonomous mode - Crow wakes on its own
    if MODE == "autonomous":
        if history:
            response = retry_with_backoff(lambda: chat.send_message("[Session resumed. Continue where you left off.]"))
        else:
            response = retry_with_backoff(lambda: chat.send_message(SEED_PROMPT))

    turn = 0
    while True:
        turn += 1
        heartbeat()  # Signal we're alive
        text = get_response_text(response)
        ts = timestamp()
        log(f"\n{C.SYSTEM}[{ts}] --- Turn {turn} ---{C.RESET}")

        actions = parse_response(text)

        # Check if no valid actions found
        if len(actions) == 1 and actions[0][0] is None:
            log(f"{C.ERROR}[No valid action found]{C.RESET}")
            response = retry_with_backoff(lambda: chat.send_message("Please respond with a valid action."))
            continue

        # Execute all actions and collect results
        results = []
        break_for_user_response = False
        for action, content in actions:
            if action == "THINK":
                log(f"{C.THINK}    💭 {content}{C.RESET}")
            elif action == "RUN_COMMAND":
                log(f"{C.ACTION}[RUN_COMMAND]{C.RESET} {content}")
            elif action == "INTERNAL_QUERY":
                log(f"{C.ACTION}[INTERNAL_QUERY]{C.RESET} {content}")
            elif action == "TALK_TO_USER":
                pass  # execute_action handles the display
            else:
                log(f"{C.ACTION}[{action}]{C.RESET}")

            result = execute_action(action, content)
            
            # CROW INTEGRITY: If a technical action fails, break the chain
            if action in ["RUN_COMMAND", "INTERNAL_QUERY", "RESTART_SELF"] and ("Error:" in result or "INTERNAL_ERROR" in result):
                log(f"{C.SYSTEM}[ABORTING CHAIN: Integrity Violation Detected]{C.RESET}")
                results.append(f"[{action}]: {result}")
                results.append("[SYSTEM]: Sequence aborted due to failure.")
                break

            # Show result (skip for TALK_TO_USER and THINK)
            if action not in ["TALK_TO_USER", "THINK"]:
                if len(result) > 300:
                    log(f"{C.SYSTEM}→ {result[:300]}...{C.RESET}")
                else:
                    log(f"{C.SYSTEM}→ {result}{C.RESET}")
            results.append(f"[{action}]: {result}")

            # In interactive mode, if user responded, stop executing remaining actions
            # and let Crow process the user's input in a fresh turn
            if action == "TALK_TO_USER" and MODE == "interactive" and "User response:" in result:
                remaining_count = len(actions) - len(results)
                if remaining_count > 0:
                    skipped_actions = [a[0] for a in actions[len(results):]]
                    log(f"{C.SYSTEM}[Skipping {remaining_count} queued actions to process user response: {skipped_actions}]{C.RESET}")
                    results.append(f"[SYSTEM]: User responded. {remaining_count} subsequent actions were CANCELLED and not executed: {skipped_actions}. Process the user's response now.")
                    break

        # Check for queued user messages (autonomous mode)
        queued = get_queued_messages()
        if queued:
            results.append(f"[USER_MESSAGES_WHILE_WORKING]:\n" + "\n".join(queued))

        # Send combined results back
        combined_results = "\n\n".join(results)
        response = retry_with_backoff(lambda cr=combined_results: chat.send_message(f"[{timestamp()}] Results:\n{cr}"))

        # Save history for continuity
        save_history(chat)

    # Cleanup
    stop_input_thread = True
    log(f"\n{C.CROW}{'=' * 50}")
    log(f"🐦‍⬛ Session Complete")
    log(f"{'=' * 50}{C.RESET}")

if __name__ == "__main__":
    run_session()
