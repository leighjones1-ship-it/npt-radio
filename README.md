# NPT Radio — Automatic Community Events Edition

The original blue-and-white website, logo, player and local editor are retained. The **Local Events** panel now reads `events-feed.json`, showing only upcoming entries, dates, venues and links. It never invents event listings. If the feed is empty or unavailable, the website shows a clear message and the manually entered station notices.

## Connect event sources (required)

Open `event-sources.json` and add **direct public HTTPS iCalendar (.ics) feed URLs** supplied by local organisers, venues, or authorised calendar providers. For example:

```json
{"ical_urls":["https://YOUR-ORGANISER.example/events.ics"]}
```

This URL is **only an example** and will not work. No unverified council or venue feeds are preconfigured. Seek permission when required. The collector currently supports standard individual VEVENT entries; recurring RRULE expansion is not supported, so use a feed that lists occurrences explicitly. It does not scrape web pages or Eventbrite listings.

## Refresh and publish

On your computer with Python 3, run `python scripts/update_events.py` from the site folder. Upload the resulting `events-feed.json` with your site. To automate every six hours, publish the whole project in a GitHub repository, enable GitHub Actions, and allow the workflow to commit changes. Deploy that repository using GitHub Pages, Netlify or another static host that republishes updated files. GitHub Actions schedules can be delayed and some repository settings may prevent write access; adjust permissions if necessary.

**Important:** Without real feed URLs and a deployed refresh workflow, automatic collection is **not active**. The sample `events-feed.json` is deliberately empty. Check organisers' dates and cancellations. The built-in editor still saves locally, not to a shared server. The radio player still needs a real HTTPS stream URL.

## Preview

Run `python -m http.server 8000` in this folder and open `http://localhost:8000`. The PWA requires HTTPS when published. Existing branding assets are included.
