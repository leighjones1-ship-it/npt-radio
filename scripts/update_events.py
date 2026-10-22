
#!/usr/bin/env python3
"""Collect upcoming events from explicitly approved public iCalendar feeds."""

import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "event-sources.json").read_text(encoding="utf-8"))

BLOCKED_PHRASES = (
    "members only",
    "members-only",
    "member only",
    "private event",
    "private meeting",
    "invitation only",
    "invite only",
    "invited guests",
    "staff only",
    "closed meeting",
    "not open to the public",
    "postponed",
    "cancelled",
    "canceled",
)


def unfold(text):
    return re.sub(r"\r?\n[ \t]", "", text)


def unescape(value):
    return (
        value.replace("\\n", " ")
        .replace("\\N", " ")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )


def parse_date(value):
    match = re.match(r"^(\d{8})(?:T(\d{4,6}))?", value)
    if not match:
        return None, None

    digits = match.group(1)
    date = f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    clock = match.group(2)
    time = f"{clock[:2]}:{clock[2:4]}" if clock else ""
    return date, time


def public_event(fields):
    status = fields.get("STATUS", "").strip().upper()
    classification = fields.get("CLASS", "").strip().upper()

    if status in ("CANCELLED", "TENTATIVE"):
        return False

    if classification in ("PRIVATE", "CONFIDENTIAL"):
        return False

    if fields.get("TRANSP", "").strip().upper() == "TRANSPARENT":
        # Transparency is a calendar availability setting,
        # not a reliable public/private indicator.
        pass

    text = " ".join(
        fields.get(name, "")
        for name in ("SUMMARY", "DESCRIPTION", "LOCATION")
    ).casefold()

    return not any(phrase in text for phrase in BLOCKED_PHRASES)


def parse_ics(raw, source_url):
    events = []
    today = datetime.now(timezone.utc).date()
    horizon = today + timedelta(days=180)

    for chunk in unfold(raw).split("BEGIN:VEVENT")[1:]:
        chunk = chunk.split("END:VEVENT", 1)[0]
        fields = {}

        for line in chunk.splitlines():
            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            name = key.split(";", 1)[0].upper()
            fields[name] = unescape(value.strip())

        if not public_event(fields):
            continue

        date, time = parse_date(fields.get("DTSTART", ""))
        if not date:
            continue

        try:
            day = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            continue

        # Require a current or upcoming start date.
        if not today <= day <= horizon:
            continue

        title = fields.get("SUMMARY", "").strip()
        if not title:
            continue

        link = fields.get("URL", "").strip() or source_url
        if urlsplit(link).scheme not in ("https", "http"):
            link = source_url

        events.append({
            "title": title[:180],
            "date": date,
            "time": time,
            "location": fields.get("LOCATION", "")[:180],
            "url": link,
        })

    return events


all_events = []
failures = []
sources = CONFIG.get("ical_urls", [])

for url in sources:
    parts = urlsplit(url)

    if parts.scheme != "https" or not parts.hostname:
        failures.append("Skipped non-HTTPS source")
        continue

    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "NPT-Radio-Community-Events/1.0"},
        )

        with urllib.request.urlopen(request, timeout=18) as response:
            raw = response.read(2_000_001)

        if len(raw) > 2_000_000:
            raise ValueError("Calendar too large")

        text = raw.decode("utf-8-sig", errors="replace")

        if "BEGIN:VCALENDAR" not in text:
            raise ValueError("Source did not return an iCalendar feed")

        all_events.extend(parse_ics(text, url))

    except Exception as exc:
        failures.append(f"{parts.hostname}: {exc}")

seen = set()
unique = []

for event in sorted(
    all_events,
    key=lambda item: (item["date"], item["time"], item["title"]),
):
    key = (
        event["date"],
        event["title"].casefold(),
        event["location"].casefold(),
    )

    if key not in seen:
        seen.add(key)
        unique.append(event)

if failures:
    print("\n".join(failures), file=sys.stderr)

# Preserve the previous feed if every configured source fails.
if sources and len(failures) == len(sources):
    sys.exit(1)

output = {
    "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    "events": unique[:150],
}

(ROOT / "events-feed.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

print(f"Published {len(unique[:150])} events")
