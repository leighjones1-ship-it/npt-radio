#!/usr/bin/env python3
"""Fetch explicitly configured public iCalendar feeds and publish upcoming events."""
import json, re, sys, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
config=json.loads((ROOT/'event-sources.json').read_text())

def unfold(text):
    return re.sub(r'\r?\n[ \t]', '', text)

def unescape(value):
    return value.replace('\\n',' ').replace('\\,',',').replace('\\;',';').replace('\\\\','\\')

def parse_date(value):
    match=re.match(r'^(\d{8})(?:T(\d{4,6}))?',value)
    if not match:return None,None
    d=match.group(1); date=f'{d[:4]}-{d[4:6]}-{d[6:]}'
    clock=match.group(2); time=f'{clock[:2]}:{clock[2:4]}' if clock else ''
    return date,time

def parse_ics(raw,url):
    events=[]; now=datetime.now(timezone.utc).date(); end=now+timedelta(days=180)
    for chunk in unfold(raw).split('BEGIN:VEVENT')[1:]:
        chunk=chunk.split('END:VEVENT',1)[0]; fields={}
        for line in chunk.splitlines():
            if ':' not in line:continue
            key,value=line.split(':',1); fields[key.split(';',1)[0].upper()]=unescape(value.strip())
        date,time=parse_date(fields.get('DTSTART',''))
        if not date:continue
        try:day=datetime.strptime(date,'%Y-%m-%d').date()
        except ValueError:continue
        if not now<=day<=end or fields.get('STATUS','').upper()=='CANCELLED':continue
        title=fields.get('SUMMARY','').strip()
        if not title:continue
        link=fields.get('URL','').strip() or url
        if urlsplit(link).scheme not in ('https','http'):link=url
        events.append({'title':title[:180],'date':date,'time':time,'location':fields.get('LOCATION','')[:180],'url':link})
    return events

all_events=[]; failures=[]
for url in config.get('ical_urls',[]):
    parts=urlsplit(url)
    if parts.scheme!='https' or not parts.hostname:
        failures.append('Skipped non-HTTPS source');continue
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'NPT-Radio-Community-Events/1.0'})
        with urllib.request.urlopen(req,timeout=18) as response:
            raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError('Calendar too large')
        all_events.extend(parse_ics(raw.decode('utf-8-sig',errors='replace'),url))
    except Exception as exc:failures.append(f'{parts.hostname}: {exc}')
seen=set(); unique=[]
for event in sorted(all_events,key=lambda x:(x['date'],x['time'],x['title'])):
    key=(event['date'],event['title'].casefold(),event['location'].casefold())
    if key not in seen:seen.add(key);unique.append(event)
if failures:print('\n'.join(failures),file=sys.stderr)
# Don't overwrite a working feed with empty data if all configured sources failed.
if config.get('ical_urls') and len(failures)==len(config['ical_urls']):sys.exit(1)
(ROOT/'events-feed.json').write_text(json.dumps({'updated_at':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),'events':unique[:150]},ensure_ascii=False,indent=2)+'\n')
print(f'Published {len(unique)} events')
