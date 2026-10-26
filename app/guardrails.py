from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    reason: str = ""


BLOCKED_TERMS = frozenset({"delete all data", "drop database", "steal credentials"})


def validate_task(task: str) -> GuardrailResult:
    normalized = " ".join(task.lower().split())
    if not normalized:
        return GuardrailResult(False, "Task must not be empty.")
    if len(normalized) > 2_000:
        return GuardrailResult(False, "Task exceeds the 2,000 character limit.")
    for term in BLOCKED_TERMS:
        if term in normalized:
            return GuardrailResult(False, "Task contains a prohibited destructive instruction.")
    return GuardrailResult(True)
