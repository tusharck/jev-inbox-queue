"""Send each thread to Jev and cache the answers on disk.

The cache means re-running the queue or the evaluation with different
thresholds costs nothing: only new or changed threads call the API.
"""

import asyncio
import hashlib
import json
import time
from pathlib import Path

from typesafe_sdk import AsyncTypeSafeClient

from .questions import QUESTIONS

CACHE_DIR = Path(".cache/jev")
CONCURRENCY = 5


def _cache_path(state: dict) -> Path:
    questions = {name: q.model_dump(mode="json") for name, q in QUESTIONS.items()}
    payload = json.dumps({"state": state, "questions": questions}, sort_keys=True)
    return CACHE_DIR / f"{hashlib.sha256(payload.encode()).hexdigest()[:24]}.json"


def _to_dict(response) -> dict:
    """Keep only what the app needs, as plain JSON."""
    nouls, choices, scores = response.nouls, response.choices, response.scores

    def choice(name):
        c = choices[name]
        return {"choice": c.choice, "confidence": c.confidence, "probabilities": dict(c.probabilities)}

    urgency = scores["urgency"]
    return {
        "needs_action": nouls["needs_action"].noul,
        "waiting_on_me": nouls["waiting_on_me"].noul,
        "is_promotional": nouls["is_promotional"].noul,
        "kind": choice("kind"),
        "workflow": choice("workflow"),
        "next_step": choice("next_step"),
        "urgency": {
            "score": urgency.score,
            "confidence": urgency.confidence,
            "probabilities": {str(k): v for k, v in urgency.probabilities.items()},
        },
        "model": response.model,
        "usage": {
            "input_tokens": response.usage.input_tokens if response.usage else None,
            "output_tokens": response.usage.output_tokens if response.usage else None,
        },
    }


async def _classify_all(threads: list[dict], fresh: bool) -> tuple[dict[str, dict], dict]:
    results: dict[str, dict] = {}
    todo = []
    for thread in threads:
        path = _cache_path(thread["state"])
        if path.exists() and not fresh:
            results[thread["id"]] = json.loads(path.read_text())
        else:
            todo.append((thread, path))

    started = time.perf_counter()
    if todo:
        print(f"Asking Jev about {len(todo)} thread(s) ({len(results)} cached)...")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        limit = asyncio.Semaphore(CONCURRENCY)
        async with AsyncTypeSafeClient() as client:

            async def one(thread, path):
                async with limit:
                    response = await client.system_one(state=thread["state"], questions=QUESTIONS)
                answers = _to_dict(response)
                path.write_text(json.dumps(answers, indent=2))
                results[thread["id"]] = answers

            await asyncio.gather(*(one(t, p) for t, p in todo))
    stats = {"sorted": len(todo), "cached": len(threads) - len(todo), "seconds": time.perf_counter() - started}
    return results, stats


def classify_all(threads: list[dict], fresh: bool = False) -> tuple[dict[str, dict], dict]:
    """Return Jev's answers keyed by thread id, plus timing for the threads sent to Jev.

    fresh=True ignores the cache and asks Jev about every thread again.
    """
    return asyncio.run(_classify_all(threads, fresh))
