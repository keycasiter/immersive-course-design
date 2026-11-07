#!/usr/bin/env python3
"""Check an HTML shell's semantics. Does not prove WebGL, layout or runtime interaction."""
import argparse
import re
from html.parser import HTMLParser
from pathlib import Path

class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.nodes=[]; self.stack=[]
    def handle_starttag(self,tag,attrs):
        n={'tag':tag,'attrs':dict(attrs),'text':'','inside_main':any(x['tag']=='main' or x['attrs'].get('role')=='main' for x in self.stack)}
        self.nodes.append(n)
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}: self.stack.append(n)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i]['tag']==tag: self.stack=self.stack[:i]; break
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs); self.handle_endtag(tag)
    def handle_data(self,data):
        for n in self.stack: n['text']+=data

def validate_html(source):
    page=Page(); page.feed(source); errors=[]; nodes=page.nodes
    main=[n for n in nodes if n['tag']=='main' or n['attrs'].get('role')=='main']
    if len(main)!=1: errors.append('use one semantic main experience region')
    if not any(n['tag']=='canvas' and n['inside_main'] for n in nodes): errors.append('main needs the real scene canvas; runtime-created canvas must be checked in rendered DOM')
    ids=[n['attrs']['id'] for n in nodes if n['attrs'].get('id')]
    if len(ids)!=len(set(ids)): errors.append('duplicate element IDs')
    by_id={n['attrs']['id']:n for n in nodes if n['attrs'].get('id')}
    def named(n):
        a=n['attrs']
        if a.get('aria-label','').strip(): return True
        refs=a.get('aria-labelledby','').split()
        if refs and all(x in by_id for x in refs) and any(by_id[x]['text'].strip() for x in refs): return True
        return bool(n['text'].strip())
    for n in nodes:
        if n['tag']=='button' or n['attrs'].get('role') in ('button','dialog') or n['tag']=='dialog':
            if not named(n): errors.append(n['tag']+' needs an accessible name')
        if n['tag']=='canvas' and not named(n): errors.append('canvas needs a name or useful fallback content')
    readable=[n for n in nodes if n['inside_main'] and n['tag'] in ('p','article','section','details') and n['text'].strip()]
    if not readable: errors.append('provide readable same-content orientation/support in main')
    if re.search(r'\{\{[^}]+\}\}',source): errors.append('unfilled placeholder')
    return errors

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('html',type=Path);a=p.parse_args()
    try: errors=validate_html(a.html.read_text())
    except (OSError,ValueError) as e: errors=[str(e)]
    for e in errors: print('ERROR: '+e)
    if not errors: print('VALID HTML semantics; rendered state, graphics and interaction require actual QA')
    return bool(errors)

if __name__=='__main__':raise SystemExit(main())
