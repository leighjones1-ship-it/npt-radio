#!/usr/bin/env python3
"""Build a local-area traffic JSON feed from official Traffic Wales RSS."""
import datetime as dt
import email.utils
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

FEEDS = [
    'https://traffic.wales/feeds/incidents-events/rss.xml',
    'https://traffic.wales/feeds/roadworks/rss.xml',
]
# Restrict to roads and places in/near Neath Port Talbot. M4 items must
# mention a nearby junction or locality, not just any M4 location.
LOCAL = re.compile(r'port talbot|neath|briton ferry|baglan|aberavon|margam|afan|pontrhydyfen|pontardawe|cymmer|cwmavon|taibach|abercregan|skewen|llansamlet|a\s?48|a465|a4107|a4241|a4063|a483|a4070|j(?:unction)?\s*(?:3[89]|4[0-3])\b', re.I)
M4 = re.compile(r'\bm4\b', re.I)
JUNCTION = re.compile(r'\b(?:j(?:unction)?\s*(?:3[89]|4[0-3]))\b', re.I)

def get_text(node, tag):
    child = node.find(tag)
    return ''.join(child.itertext()).strip() if child is not None else ''

def main():
    found=[]; failures=[]; seen=set()
    for url in FEEDS:
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'NPT-Radio-Traffic/1.0 (community information)'})
            with urllib.request.urlopen(req,timeout=25) as response: raw=response.read(3_000_000)
            root=ET.fromstring(raw)
            for item in root.findall('.//item'):
                title=get_text(item,'title'); description=re.sub(r'<[^>]*>',' ',get_text(item,'description'))
                description=re.sub(r'\s+',' ',description).strip()[:500]
                content=title+' '+description
                if not LOCAL.search(content) and not (M4.search(content) and JUNCTION.search(content)):
                    continue
                link=get_text(item,'link')
                if not link.startswith('https://traffic.wales/'):
                    link='https://traffic.wales/road-traffic-alerts'
                key=(title.casefold(),link)
                if key in seen:continue
                seen.add(key)
                found.append({'title':title[:250], 'description':description, 'url':link})
        except Exception as exc:
            failures.append(f'{url}: {exc}')
    if failures:
        # Don't overwrite the last valid feed with incomplete data.
        raise RuntimeError('Unable to refresh all official RSS feeds: '+'; '.join(failures))
    output={'updated_at':dt.datetime.now(dt.timezone.utc).isoformat(), 'source':'Traffic Wales', 'items':found[:30]}
    Path('traffic-feed.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Wrote',len(output['items']),'local traffic notices')

if __name__=='__main__': main()
