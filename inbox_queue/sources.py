"""Where threads come from: the labelled demo inbox, or a real mailbox over IMAP.

Every source returns a list of threads shaped like:
    {"id": str, "state": {...sent to Jev...}, "label": {...} | None, "link": str | None}
"""

import email
import html
import imaplib
import json
import os
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from email.policy import default as default_policy
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path

DEMO_PATH = Path(__file__).resolve().parent.parent / "data" / "demo_inbox.json"
MAX_CHARS_PER_MESSAGE = 2000


def load_demo() -> list[dict]:
    data = json.loads(DEMO_PATH.read_text())
    return [
        {
            "id": t["id"],
            "state": {
                "today": data["today"],
                "me": data["me"],
                "thread": {"subject": t["subject"], "messages": t["messages"]},
            },
            "label": t["label"],
            "link": None,
        }
        for t in data["threads"]
    ]


# --- IMAP ------------------------------------------------------------------


def _strip_html(text: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", text)
    return html.unescape(re.sub(r"<[^>]+>", " ", text))


def _body_text(msg) -> str:
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    try:
        text = part.get_content()
    except (LookupError, UnicodeDecodeError):
        return ""
    if part.get_content_type() == "text/html":
        text = _strip_html(text)
    # Drop quoted history; earlier messages are already in the thread.
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(">"))
    text = re.split(r"\nOn [^\n]{0,200}wrote:\s*\n", text)[0]
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text).strip()
    return text[:MAX_CHARS_PER_MESSAGE]


KEYCHAIN_SERVICE = "jev-inbox-queue"


def get_password(user: str) -> str:
    """Prefer the macOS Keychain (or the OS equivalent); fall back to .env."""
    import keyring

    password = keyring.get_password(KEYCHAIN_SERVICE, user) or os.environ.get("IMAP_PASSWORD")
    if not password:
        raise SystemExit("No mail password found. Run: uv run python -m inbox_queue save-password")
    return password


def save_password() -> None:
    """Store the mail app password in the OS keychain via a hidden prompt."""
    import getpass

    import keyring

    user = os.environ.get("IMAP_USER") or input("Email address: ").strip()
    password = getpass.getpass(f"App password for {user} (hidden): ").replace(" ", "")
    keyring.set_password(KEYCHAIN_SERVICE, user, password)
    print(f"Saved to your keychain as '{KEYCHAIN_SERVICE}' / {user}. You can remove IMAP_PASSWORD from .env.")


def _all_mail_box(conn) -> str | None:
    """Find Gmail's "All Mail" folder (its name is localised, its flag is not)."""
    _, boxes = conn.list()
    for raw in boxes or []:
        line = raw.decode(errors="replace")
        if "\\All" in line:
            return line.rsplit(' "/" ', 1)[-1]
    return None


def load_imap(days: int = 7, limit: int = 40) -> list[dict]:
    """Read recent threads from the mailbox configured in .env (read-only)."""
    host = os.environ.get("IMAP_HOST", "imap.gmail.com")
    user = os.environ["IMAP_USER"]
    password = get_password(user)
    me = {"name": os.environ.get("MY_NAME", user), "email": user}

    conn = imaplib.IMAP4_SSL(host)
    conn.login(user, password)
    all_mail = _all_mail_box(conn)
    gmail = all_mail is not None
    # All Mail includes your sent replies, so Jev can see what you already answered.
    conn.select(all_mail or "INBOX", readonly=True)

    since = (date.today() - timedelta(days=days)).strftime("%d-%b-%Y")
    _, data = conn.uid("search", None, f"SINCE {since}")
    uids = data[0].split()[-limit * 4 :]  # newest messages; enough to fill `limit` threads

    threads: dict[str, list] = defaultdict(list)
    subjects: dict[str, str] = {}
    fetch = "(X-GM-THRID BODY.PEEK[])" if gmail else "(BODY.PEEK[])"
    for uid in uids:
        _, parts = conn.uid("fetch", uid, fetch)
        if not parts or not isinstance(parts[0], tuple):
            continue
        meta, raw = parts[0][0].decode(errors="replace"), parts[0][1]
        match = re.search(r"X-GM-THRID (\d+)", meta)
        thread_id = match.group(1) if match else uid.decode()

        msg = email.message_from_bytes(raw, policy=default_policy)
        try:
            sent = parsedate_to_datetime(msg["Date"])
        except (TypeError, ValueError):
            sent = datetime.now()
        name, address = parseaddr(str(msg["From"] or ""))
        subjects.setdefault(thread_id, str(msg["Subject"] or "(no subject)"))
        threads[thread_id].append(
            {
                "sort": sent.timestamp(),
                "from": f"{name} <{address}>" if name else address,
                "date": sent.strftime("%Y-%m-%d %H:%M"),
                "text": _body_text(msg),
            }
        )
    conn.logout()

    newest_first = sorted(threads.items(), key=lambda kv: max(m["sort"] for m in kv[1]), reverse=True)
    today = date.today().strftime("%Y-%m-%d (%A)")
    result = []
    for thread_id, messages in newest_first[:limit]:
        messages.sort(key=lambda m: m["sort"])
        for m in messages:
            del m["sort"]
        result.append(
            {
                "id": thread_id,
                "state": {"today": today, "me": me, "thread": {"subject": subjects[thread_id], "messages": messages}},
                "label": None,
                "link": f"https://mail.google.com/mail/u/{user}/#all/{int(thread_id):x}" if gmail else None,
            }
        )
    return result
