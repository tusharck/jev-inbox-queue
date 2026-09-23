"""The seven questions Jev answers about every email thread.

All seven are sent in one request and answered in parallel. Question names
(the dict keys) are only for our code; Jev never sees them, so every
instruction spells out its full meaning.

State sent with each request looks like:
    {"today": "...", "me": {"name", "email"},
     "thread": {"subject": "...", "messages": [{"from", "date", "text"}, ...]}}
"""

from typesafe_sdk import Choice, Noul, Score

QUESTIONS = {
    # --- Noul: probability that something is true -------------------------
    "needs_action": Noul(
        instructions=(
            "Does `me` still need to do something because of this email thread? "
            "Judge from the latest messages in `thread.messages`: has anything been "
            "asked of `me` (reply, send a document, pay, schedule, decide, or do a task) "
            "that `me` has not already done in a later message?"
        ),
        criteria={
            "true": "There is an open request or required step for `me`, from a person or from an organisation.",
            "false": (
                "Nothing is pending for `me`: the thread is information, a confirmation, "
                "marketing, a thank-you, or `me` already handled the request."
            ),
        },
    ),
    "waiting_on_me": Noul(
        instructions=(
            "Is a specific human being waiting on `me`, unable to continue or left "
            "without an answer until `me` replies or acts?"
        ),
        criteria={
            "true": "A real person (colleague, vendor, counsellor, friend, case worker) asked `me` directly and is expecting something back.",
            "false": "Nobody is waiting: the message is automated, broadcast to many people, or the next move belongs to someone else.",
        },
    ),
    "is_promotional": Noul(
        instructions=(
            "Is this email thread promotional or bulk content that `me` can safely ignore, "
            "even if it asks `me` to do something?"
        ),
        criteria={
            "true": (
                "Marketing, sales and offers, newsletters, digests, event or webinar invitations sent "
                "to many people, and requests to leave a review or rating."
            ),
            "false": (
                "Written to `me` personally, or about `me`'s own account, order, application, case or "
                "payment, even if it comes from a company or an automated system."
            ),
        },
    ),
    # --- Choice: exactly one of a defined set ------------------------------
    "kind": Choice(
        instructions="What kind of message is the latest message in `thread.messages`?",
        criteria={
            "new_request": "Asks `me` for something that has not been asked before in this thread.",
            "follow_up": "A reminder or nudge about something asked of `me` earlier that is still not done.",
            "acknowledgement": "Confirms that something was received, completed or approved; asks for nothing new.",
            "information": "Shares news, an update or a notification without asking `me` for anything.",
            "promotional": "Marketing, newsletters, digests, offers or review requests.",
        },
    ),
    "workflow": Choice(
        instructions="Which part of `me`'s life does this email thread belong to?",
        criteria={
            "engineering": "`me`'s software engineering job: code reviews, incidents, teammates, dev tools.",
            "university_counselling": "Graduate school applications, admissions offices, counsellor sessions, recommendations.",
            "wedding_planning": "`me`'s upcoming wedding: vendors, venue, guests, invitations, partner planning.",
            "purchases": "Online orders, deliveries, returns, refunds, subscriptions, shipping claims.",
            "other": "Anything else: personal life, home, bank, health, friends, general office notices.",
        },
    ),
    "next_step": Choice(
        instructions="What is the single most useful next step for `me` on this email thread?",
        criteria={
            "reply": "Write back with an answer, confirmation or decision.",
            "send_document": "Send or upload a requested document, file or list.",
            "pay": "Make or fix a payment.",
            "schedule": "Pick a time or book a meeting.",
            "review_or_decide": "Review something someone prepared, or choose between options.",
            "complete_task": "Do a task outside email (fix, grant access, drop off, prepare something).",
            "none": "No step is needed.",
        },
    ),
    # --- Score: a position on an ordered scale -----------------------------
    "urgency": Score(
        instructions=(
            "How soon does `me` need to deal with this email thread, given `today` "
            "and any deadlines or waiting people mentioned?"
        ),
        criteria=[
            "No time pressure: nothing to do, or no deadline in the next two weeks.",
            "Should be handled within the next week or two.",
            "Should be handled within a day or two: a deadline this week or someone waiting soon.",
            "Must be handled today: deadline today or overdue, an active incident, or someone blocked right now.",
        ],
    ),
}

# Code turns the chosen next step into a queue title (select, don't generate).
NEXT_STEP_TITLES = {
    "reply": "Reply",
    "send_document": "Submit requested document",
    "pay": "Make payment",
    "schedule": "Pick a time",
    "review_or_decide": "Review and decide",
    "complete_task": "Complete task",
    "none": "Take a look",
}

URGENCY_LABELS = ["No rush", "This week or two", "Next 1-2 days", "Today"]
