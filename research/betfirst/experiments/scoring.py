"""Separate code acceptance from Agent session completion in benchmark results."""
from __future__ import annotations


def classify(
    *,
    task: dict,
    agent_exit: int | None,
    agent_timeout: bool,
    agent_subtype: str | None,
    test_exit: int | None,
    test_timeout: bool,
    oracle_exit: int | None,
    oracle_timeout: bool,
    test_integrity_passed: bool,
    workspace_changed: bool,
) -> dict:
    """Report independent outcomes and conservative, nonexclusive failure labels.

    code_accepted means the post-run tests and oracle passed and original
    tests stayed intact. It does NOT imply Agent ended cleanly (e.g., max turns).
    """
    code_failures = []
    if test_timeout:
        code_failures.append("visible_tests_timeout")
    elif test_exit != 0:
        code_failures.append("visible_tests_failed")
    if oracle_timeout:
        code_failures.append("oracle_timeout")
    elif oracle_exit not in (None, 0):
        code_failures.append("oracle_failed")
    if not test_integrity_passed:
        code_failures.append("tests_tampered")
    if task.get("no_change") and workspace_changed:
        code_failures.append("unexpected_change")

    session_failures = []
    if agent_timeout:
        session_failures.append("agent_timeout")
    elif agent_subtype == "error_max_turns":
        session_failures.append("agent_max_turns")
    elif agent_exit != 0 or (isinstance(agent_subtype, str) and agent_subtype.startswith("error_")):
        session_failures.append("agent_error")

    code_accepted = not code_failures
    session_success = not session_failures
    return {
        "code_accepted": code_accepted,
        "session_success": session_success,
        "passed": code_accepted and session_success,
        "failure_reasons": code_failures + session_failures,
    }
