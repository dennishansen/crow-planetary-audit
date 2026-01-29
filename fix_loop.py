import re

with open('main.py', 'r') as f:
    content = f.read()

# Pattern to find the execute_action loop
# and add a break condition for errors
old_loop = """            result = execute_action(action, content)

            # Show result (skip for TALK_TO_USER since it handles its own output)"""

new_loop = """            result = execute_action(action, content)
            
            # CROW INTEGRITY: If a technical action fails, break the chain
            if action in ["RUN_COMMAND", "INTERNAL_QUERY", "RESTART_SELF"] and ("Error:" in result or "INTERNAL_ERROR" in result):
                log(f"{C.SYSTEM}[ABORTING CHAIN: Integrity Violation Detected]{C.RESET}")
                results.append(f"[{action}]: {result}")
                results.append("[SYSTEM]: Sequence aborted due to failure.")
                break

            # Show result (skip for TALK_TO_USER since it handles its own output)"""

updated_content = content.replace(old_loop, new_loop)
with open('main.py', 'w') as f:
    f.write(updated_content)
