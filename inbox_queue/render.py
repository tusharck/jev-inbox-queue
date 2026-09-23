"""Render the action queue as a single static HTML page (no server needed)."""

from html import escape

from .policy import PROMO_CUTOFF

# Urgency levels from the Score question, most urgent first: (level, key, label).
URGENCY = [(3, "today", "Today"), (2, "soon", "Next 1-2 days"), (1, "week", "This week or two"), (0, "later", "No rush")]
URGENCY_KEY = {level: key for level, key, _ in URGENCY}
WORKFLOWS = [
    ("engineering", "Engineering"),
    ("university_counselling", "University"),
    ("wedding_planning", "Wedding"),
    ("purchases", "Purchases"),
    ("other", "Other"),
]

CSS = """
:root { --bg:#f5f4f0; --card:#fff; --ink:#1c1c1a; --muted:#6d6b65; --line:#e2e0d9; --tag:#efede7;
  --accent:#2f5bd3; --accent-ink:#fff; --today:#c2410c; --soon:#b7791f; --week:#2f5bd3; --later:#8a8880; }
@media (prefers-color-scheme: dark) { :root { --bg:#141413; --card:#1e1e1c; --ink:#ecebe6; --muted:#9e9c95;
  --line:#34332f; --tag:#2a2926; --accent:#86a6ff; --accent-ink:#10131c; --today:#fb8c4f; --soon:#e9b44c;
  --week:#86a6ff; --later:#8f8d86; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 -apple-system, "Segoe UI", system-ui, sans-serif; }
main { max-width: 820px; margin: 0 auto; padding: 36px 16px 72px; }
h1 { font-size: 28px; letter-spacing: -.01em; margin: 0; }
.sub { color: var(--muted); margin: 4px 0 24px; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 26px; }
.stat { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
.stat b { display: block; font-size: 28px; line-height: 1.1; font-variant-numeric: tabular-nums; }
.stat span { font-size: 12.5px; color: var(--muted); }
.stat.hi b { color: var(--accent); }
@media (max-width: 620px) { .stats { grid-template-columns: repeat(2, 1fr); } }
.filters { display: flex; flex-direction: column; gap: 8px; margin-bottom: 8px; }
.row { display: flex; gap: 6px; flex-wrap: wrap; }
.chip { border: 1px solid var(--line); background: var(--card); color: var(--ink); border-radius: 99px;
  padding: 6px 12px; font: inherit; font-size: 13.5px; cursor: pointer; display: inline-flex; gap: 7px; align-items: center; }
.chip .n { color: var(--muted); font-variant-numeric: tabular-nums; }
.chip.on { background: var(--ink); border-color: var(--ink); color: var(--bg); }
.chip.on .n { color: inherit; opacity: .7; }
.chip.zero:not(.on) { opacity: .45; }
.chip.small { font-size: 12.5px; padding: 4px 10px; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--dot); }
h2 { font-size: 12.5px; text-transform: uppercase; letter-spacing: .07em; color: var(--muted); margin: 28px 0 10px; }
.card { background: var(--card); border: 1px solid var(--line); border-left: 4px solid var(--dot);
  border-radius: 10px; padding: 13px 16px; margin-bottom: 9px; }
.top { display: flex; gap: 10px; align-items: baseline; justify-content: space-between; flex-wrap: wrap; }
.title { font-weight: 650; font-size: 16px; }
.urg { font-size: 12px; font-weight: 650; color: var(--dot); white-space: nowrap; }
.subject { margin: 2px 0 8px; overflow-wrap: anywhere; }
.subject a { color: var(--accent); text-decoration: none; }
.meta { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; font-size: 12px; color: var(--muted); }
.tag { background: var(--tag); border-radius: 99px; padding: 1px 9px; }
.tag.wait { color: var(--today); }
details.why { margin-top: 9px; font-size: 13px; color: var(--muted); }
summary { cursor: pointer; }
table { border-collapse: collapse; margin-top: 6px; width: 100%; }
td { padding: 3px 8px 3px 0; vertical-align: top; border-top: 1px solid var(--line); }
td:first-child { white-space: nowrap; width: 1%; }
.none { color: var(--muted); font-style: italic; }
details.out { margin-top: 30px; }
details.out > summary { font-size: 12.5px; text-transform: uppercase; letter-spacing: .07em; color: var(--muted); }
details.out .card { opacity: .8; }
.u-today { --dot: var(--today); } .u-soon { --dot: var(--soon); } .u-week { --dot: var(--week); } .u-later { --dot: var(--later); }
footer { margin-top: 40px; font-size: 12.5px; color: var(--muted); }
"""

JS = """
const state = { urgency: "all", workflow: "all" };
const cards = [...document.querySelectorAll(".filterable .card")];
const fits = (card, key, val) => val === "all" || card.dataset[key] === val;
function apply() {
  cards.forEach(c => { c.hidden = !(fits(c, "urgency", state.urgency) && fits(c, "workflow", state.workflow)); });
  document.querySelectorAll(".chip").forEach(chip => {
    const { key, val } = chip.dataset;
    const other = key === "urgency" ? "workflow" : "urgency";
    const n = cards.filter(c => fits(c, key, val) && fits(c, other, state[other])).length;
    chip.querySelector(".n").textContent = n;
    chip.classList.toggle("on", state[key] === val);
    chip.classList.toggle("zero", n === 0);
  });
  document.querySelectorAll(".filterable").forEach(section => {
    const shown = section.querySelectorAll(".card:not([hidden])").length;
    section.querySelector(".count").textContent = shown;
    section.querySelector(".none").hidden = shown > 0;
  });
}
document.addEventListener("click", e => {
  const chip = e.target.closest(".chip");
  if (chip) { state[chip.dataset.key] = chip.dataset.val; apply(); }
});
apply();
"""


def _pct(p: float) -> str:
    return f"{p:.0%}"


def _answers_table(a: dict) -> str:
    def choice_row(name):
        c = a[name]
        runner_up = sorted(c["probabilities"].items(), key=lambda kv: kv[1], reverse=True)[1:2]
        extra = f" &middot; next: {escape(runner_up[0][0])} {_pct(runner_up[0][1])}" if runner_up else ""
        return f"<tr><td>{name} <em>(Choice)</em></td><td>{escape(c['choice'])} &middot; confidence {_pct(c['confidence'])}{extra}</td></tr>"

    u = a["urgency"]
    return (
        "<table>"
        f"<tr><td>needs_action <em>(Noul)</em></td><td>{_pct(a['needs_action'])} chance yes</td></tr>"
        f"<tr><td>waiting_on_me <em>(Noul)</em></td><td>{_pct(a['waiting_on_me'])} chance yes</td></tr>"
        f"<tr><td>is_promotional <em>(Noul)</em></td><td>{_pct(a['is_promotional'])} chance yes</td></tr>"
        + choice_row("kind")
        + choice_row("workflow")
        + choice_row("next_step")
        + f"<tr><td>urgency <em>(Score)</em></td><td>{u['score']:.2f} of 3 &middot; confidence {_pct(u['confidence'])}</td></tr>"
        "</table>"
    )


def _card(item: dict) -> str:
    thread, a = item["thread"], item["answers"]
    t = thread["state"]["thread"]
    last = t["messages"][-1]
    subject = escape(t["subject"])
    if thread.get("link"):
        subject = f'<a href="{escape(thread["link"])}" target="_blank" rel="noopener">{subject}</a>'
    urgency = URGENCY_KEY[item["urgency_level"]]
    workflow = a["workflow"]["choice"]
    wait = '<span class="tag wait">someone is waiting</span>' if item["waiting"] else ""
    return f"""
<div class="card u-{urgency}" data-urgency="{urgency}" data-workflow="{escape(workflow)}">
  <div class="top"><span class="title">{escape(item['title'])}</span>
    <span class="urg">{escape(item['urgency_label'])}</span></div>
  <div class="subject">{subject}</div>
  <div class="meta"><span class="tag">{escape(workflow.replace('_', ' '))}</span>
    <span class="tag">{escape(a['kind']['choice'].replace('_', ' '))}</span>{wait}
    <span>from {escape(last['from'])}</span></div>
  <details class="why"><summary>Why? {escape(item['reason'])}</summary>{_answers_table(a)}</details>
</div>"""


def _section(title: str, items: list[dict], empty: str) -> str:
    cards = "".join(_card(i) for i in items)
    return (
        f'<section class="filterable"><h2>{title} (<span class="count">{len(items)}</span>)</h2>'
        f'{cards}<p class="none" hidden>{empty}</p></section>'
    )


def _chip(key: str, val: str, label: str, dot: str = "", small: bool = False) -> str:
    dot_html = f'<span class="dot u-{dot}"></span>' if dot else ""
    cls = "chip small" if small else "chip"
    return f'<button class="{cls}" data-key="{key}" data-val="{val}">{dot_html}{escape(label)} <span class="n"></span></button>'


def _duration(seconds: float) -> str:
    return f"{seconds:.1f}s" if seconds < 60 else f"{int(seconds // 60)}m {int(seconds % 60)}s"


def _timing_tile(run: dict | None) -> str:
    if not run or not run.get("sorted"):
        return '<div class="stat"><b>&ndash;</b><span>answers loaded from cache</span></div>'
    n, seconds = run["sorted"], run["seconds"]
    note = " &middot; now cached" if run.get("from_cache") else ""
    return (
        f'<div class="stat"><b>{_duration(seconds)}</b>'
        f"<span>to sort {n} emails &middot; {seconds / n:.2f}s each{note}</span></div>"
    )


def render(buckets: dict, source_name: str, run: dict | None = None) -> str:
    total = sum(len(v) for v in buckets.values())
    todo, check, skipped = buckets["queue"], buckets["check"], buckets["skip"]
    check_note = f" &middot; {len(check)} to check" if check else ""
    promos = sum(1 for i in skipped if i["answers"]["is_promotional"] >= PROMO_CUTOFF)

    urgency_chips = _chip("urgency", "all", "All") + "".join(_chip("urgency", key, label, dot=key) for _, key, label in URGENCY)
    workflow_chips = _chip("workflow", "all", "All workflows", small=True) + "".join(
        _chip("workflow", key, label, small=True) for key, label in WORKFLOWS
    )
    skipped_cards = "".join(_card(i) for i in skipped) or '<p class="none">Nothing was filtered out.</p>'

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Action Queue</title><style>{CSS}</style></head>
<body><main>
<h1>Action queue</h1>
<p class="sub">{escape(source_name)} &middot; sorted by Jev (TypeSafe System One)</p>

<div class="stats">
  <div class="stat"><b>{total}</b><span>emails sorted</span></div>
  {_timing_tile(run)}
  <div class="stat hi"><b>{len(todo)}</b><span>need you{check_note}</span></div>
  <div class="stat"><b>{len(skipped)}</b><span>filtered out &middot; {promos} promotional</span></div>
</div>

<div class="filters">
  <div class="row">{urgency_chips}</div>
  <div class="row">{workflow_chips}</div>
</div>

{_section("To do", todo, "Nothing here for this filter.")}
{_section("Check these", check, "Nothing uncertain for this filter.") if check else ""}

<details class="out"><summary>Filtered out ({len(skipped)})</summary>{skipped_cards}</details>

<footer>Each email gets seven questions in one request: three Nouls (needs action, someone waiting, promotional),
three Choices (message kind, workflow, next step) and one Score (urgency). Open "Why?" on any card to see the answers.</footer>
</main><script>{JS}</script></body></html>"""
