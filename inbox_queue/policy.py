"""Turn Jev's answers into queue decisions.

Jev supplies judgments; this file is the policy. Changing a threshold
here never needs new API calls, because the answers are cached.
"""

from .questions import NEXT_STEP_TITLES, URGENCY_LABELS

SKIP_KINDS = {"acknowledgement", "promotional"}
PROMO_CUTOFF = 0.5  # is_promotional at or above (more likely yes than no): filtered out
DEFAULT_HIGH = 0.6  # at or above: goes in the queue
DEFAULT_LOW = 0.3  # between LOW and HIGH: "check these" section


def decide(answers: dict, high: float = DEFAULT_HIGH, low: float = DEFAULT_LOW) -> tuple[str, str]:
    """Return (bucket, reason). Bucket is "queue", "check" or "skip"."""
    action, waiting, kind = answers["needs_action"], answers["waiting_on_me"], answers["kind"]

    # Marketing often literally asks for something ("leave a review", "register now"),
    # which raises needs_action. The dedicated promotional Noul overrules it.
    promo = answers["is_promotional"]
    if promo >= PROMO_CUTOFF:
        return "skip", f"Promotional ({promo:.0%}), even though it may ask for something ({action:.0%})"
    if action >= high:
        return "queue", f"Needs action ({action:.0%})"
    if waiting >= high:
        return "queue", f"Someone is waiting on you ({waiting:.0%})"
    if action >= low:
        # Unsure about action: let a confident message-kind answer break the tie.
        if kind["choice"] in SKIP_KINDS and kind["confidence"] >= 0.8:
            return "skip", f"Unsure about action ({action:.0%}), but clearly {kind['choice']} ({kind['confidence']:.0%})"
        return "check", f"Not sure it needs action ({action:.0%})"
    return "skip", f"Only {action:.0%} chance it needs action"


def build_queue(threads: list[dict], all_answers: dict[str, dict], high=DEFAULT_HIGH, low=DEFAULT_LOW) -> dict:
    """Group threads into queue / check / skip, most urgent first."""
    buckets = {"queue": [], "check": [], "skip": []}
    for thread in threads:
        answers = all_answers[thread["id"]]
        bucket, reason = decide(answers, high, low)
        urgency = answers["urgency"]["score"]
        waiting = answers["waiting_on_me"] >= 0.5
        buckets[bucket].append(
            {
                "thread": thread,
                "answers": answers,
                "reason": reason,
                "title": NEXT_STEP_TITLES[answers["next_step"]["choice"]],
                "urgency_level": min(round(urgency), len(URGENCY_LABELS) - 1),
                "urgency_label": URGENCY_LABELS[min(round(urgency), len(URGENCY_LABELS) - 1)],
                "waiting": waiting,
                "priority": urgency + (0.75 if waiting else 0),
            }
        )
    for items in buckets.values():
        items.sort(key=lambda item: item["priority"], reverse=True)
    return buckets
