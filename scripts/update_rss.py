#!/usr/bin/env python3
"""Update NPT Radio local news and verified public RSS events."""

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "rss-sources.json").read_text(encoding="utf-8"))

PLACES = (
    "neath", "port talbot", "aberavon", "aberafan",
    "margam", "briton ferry", "baglan", "afan",
    "pontardawe", "clydach", "skewen", "resolven",
    "neath port talbot", "sandfields", "cymmer",
    "glynneath", "bryn", "taibach", "cimla",
)

BLOCKED = (
    "members only", "members-only", "invitation only",
    "invite only", "private event", "staff only",
    "cancelled", "canceled", "postponed",
)

NS = "{https://npt-radio.example/ns/events/1}"


def clean(value):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", value or "")).strip()


def get_text(element, name):
    child = element.find(name)
    return clean(child.text) if child is not None else ""


def download(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise ValueError("Only HTTPS feed URLs are allowed")

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "NPT-Radio-RSS/1.0"}
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        content = response.read(2_000_001)

    if len(content) > 2_000_000:
        raise ValueError("RSS feed too large")

    root = ET.fromstring(content)
    if root.tag != "rss":
        raise ValueError("Expected an RSS 2.0 feed")

    return root.findall("./channel/item")


def safe_link(link):
    parts = urlsplit(link)
    return link if parts.scheme == "https" and parts.hostname else ""


def news_from_item(item, source):
    title = get_text(item, "title")
    description = get_text(item, "description")
    link = safe_link(get_text(item, "link"))

    if not title or not link:
        return None

    combined = (title + " " + description).casefold()
    if source.get("local_only", True):
        if not any(place in combined for place in PLACES):
            return None

    return {
        "title": title[:180],
        "description": description[:300],
        "url": link,
        "source": source.get("name", "Local news")[:80],
        "published": get_text(item, "pubDate"),
    }


def event_from_item(item, source):
    # Only accept feeds with an explicitly supplied event date
    # using the NPT Radio event namespace.
    title = get_text(item, "title")
    description = get_text(item, "description")
    link = safe_link(get_text(item, "link"))
    event_date = get_text(item, NS + "event_date")
    event_time = get_text(item, NS + "event_time")
    location = get_text(item, NS + "location")
    visibility = get_text(item, NS + "visibility").lower()
    status = get_text(item, NS + "status").lower()

    if not title or not link or visibility != "public":
        return None

    if status != "confirmed":
        return None

    combined = (title + " " + description).casefold()
    if any(term in combined for term in BLOCKED):
        return None

    try:
        day = date.fromisoformat(event_date)
    except ValueError:
        return None

    today = datetime.now(timezone.utc).date()
    if not today <= day <= today + timedelta(days=180):
        return None

    if event_time and not re.fullmatch(r"\d{2}:\d{2}", event_time):
        return None

    return {
        "title": title[:180],
        "date": event_date,
        "time": event_time,
        "location": location[:180],
        "url": link,
    }


def collect(sources, parser):
    results = []
    failures = []

    for source in sources:
        url = source.get("url", "")
        try:
            for item in download(url):
                result = parser(item, source)
                if result:
                    results.append(result)
        except Exception as exc:
            failures.append(f"{source.get('name', 'RSS source')}: {exc}")

    for failure in failures:
        print(failure, file=sys.stderr)

    if sources and len(failures) == len(sources):
        raise RuntimeError("All configured RSS sources failed")

    return results


def save(filename, events, limit):
    unique = []
    seen = set()

    for event in events:
        key = event["url"]
        if key not in seen:
            seen.add(key)
            unique.append(event)

    output = {
        "updated_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        ),
        "events": unique[:limit],
    }

    (ROOT / filename).write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"{filename}: {len(output['events'])} items")


news_sources = CONFIG.get("news_feeds", [])
event_sources = CONFIG.get("event_feeds", [])

news = collect(news_sources, news_from_item)
save("news-feed.json", news, 50)

# Event RSS requires a verified structured feed.
# Never interpret an article's publication date as an event date.
if event_sources:
    events = collect(event_sources, event_from_item)
    save("rss-events-feed.json", events, 100)
else:
    save("rss-events-feed.json", [], 100)
