"""Measure the queue against the labelled demo inbox.

The two numbers that matter:
  missed     - actionable threads that did not reach the queue or "check these"
  irrelevant - threads that were surfaced but need no action
"""

from .policy import DEFAULT_HIGH, DEFAULT_LOW, build_queue


def _surfaced_ids(buckets: dict) -> set[str]:
    return {i["thread"]["id"] for b in ("queue", "check") for i in buckets[b]}


def evaluate(threads: list[dict], answers: dict[str, dict], high=DEFAULT_HIGH, low=DEFAULT_LOW) -> None:
    by_id = {t["id"]: t for t in threads}
    actionable = {t["id"] for t in threads if t["label"]["actionable"]}
    buckets = build_queue(threads, answers, high, low)
    surfaced = _surfaced_ids(buckets)
    missed = sorted(actionable - surfaced)
    irrelevant = sorted(surfaced - actionable)

    def subject(tid):
        return by_id[tid]["state"]["thread"]["subject"]

    print(f"\nPolicy: queue if needs_action >= {high}, 'check' if >= {low}")
    print(f"  {len(threads)} threads, {len(actionable)} actionable")
    print(f"  queue={len(buckets['queue'])}  check={len(buckets['check'])}  kept out={len(buckets['skip'])}")
    print(f"  Missed actionable: {len(missed)}/{len(actionable)}")
    for tid in missed:
        print(f"    - {tid}: {subject(tid)}  (needs_action={answers[tid]['needs_action']:.2f})")
    print(f"  Irrelevant surfaced: {len(irrelevant)}/{len(surfaced)}")
    for tid in irrelevant:
        print(f"    - {tid}: {subject(tid)}  (needs_action={answers[tid]['needs_action']:.2f})")

    print("\nHow often each answer matches the label:")
    for name in ("kind", "workflow", "next_step"):
        # next_step only matters for threads that reach the queue.
        scope = [t for t in threads if t["id"] in actionable] if name == "next_step" else threads
        right = [t for t in scope if answers[t["id"]][name]["choice"] == t["label"][name]]
        note = "  (actionable threads only)" if name == "next_step" else ""
        print(f"  {name:<14} {len(right)}/{len(scope)}{note}")
        for t in scope:
            got = answers[t["id"]][name]["choice"]
            if got != t["label"][name]:
                print(f"      {t['id']}: expected {t['label'][name]}, Jev said {got}")
    right = [t for t in threads if (answers[t["id"]]["waiting_on_me"] >= 0.5) == t["label"]["waiting_on_me"]]
    print(f"  {'waiting_on_me':<14} {len(right)}/{len(threads)}  (at 0.5)")
    promo_label = {t["id"]: t["label"]["kind"] == "promotional" for t in threads}
    right = [tid for tid, is_promo in promo_label.items() if (answers[tid]["is_promotional"] >= 0.5) == is_promo]
    print(f"  {'is_promotional':<14} {len(right)}/{len(threads)}  (at 0.5)")
    for tid, is_promo in promo_label.items():
        if (answers[tid]["is_promotional"] >= 0.5) != is_promo:
            print(f"      {tid}: expected {is_promo}, Jev said {answers[tid]['is_promotional']:.2f}")

    print("\nThreshold sweep (single cut-off on needs_action, no 'check' section):")
    print("  threshold  missed  irrelevant")
    for step in range(1, 10):
        cut = step / 10
        shown = {tid for tid, a in answers.items() if tid in by_id and a["needs_action"] >= cut}
        print(f"  {cut:>9.1f}  {len(actionable - shown):>6}  {len(shown - actionable):>10}")

    total_in = sum(a["usage"]["input_tokens"] or 0 for a in answers.values())
    total_out = sum(a["usage"]["output_tokens"] or 0 for a in answers.values())
    print(f"\nTokens across all threads: {total_in} in, {total_out} out")
