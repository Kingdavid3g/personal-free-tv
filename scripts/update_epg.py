#!/usr/bin/env python3
"""Build a provider-matched XMLTV guide without inventing programmes."""
import concurrent.futures as futures
import copy, datetime as dt, gzip, hashlib, json, re, subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
NOW = dt.datetime.now(dt.timezone.utc)
GUIDE_URL = 'https://raw.githubusercontent.com/Kingdavid3g/personal-free-tv/main/epg.xml'
SOURCES = {
 'Pluto TV':'https://i.mjh.nz/PlutoTV/us.xml.gz',
 'Samsung TV Plus':'https://i.mjh.nz/SamsungTVPlus/us.xml.gz',
 'Plex TV':'https://i.mjh.nz/Plex/us.xml.gz',
 'Tubi':'https://raw.githubusercontent.com/BuddyChewChew/tubi-scraper/refs/heads/main/tubi_epg.xml',
 'Roku Channel':'https://i.mjh.nz/Roku/all.xml.gz',
 'DistroTV':'https://epgshare01.online/epgshare01/epg_ripper_DISTROTV1.xml.gz',
}
def fetch(url):
 p=subprocess.run(['curl','--fail','--silent','--show-error','--location','--retry','2','--max-time','45',url],capture_output=True,check=True)
 b=p.stdout
 return gzip.decompress(b) if b[:2]==b'\x1f\x8b' else b

def norm(s):
 s=re.sub(r'\((?:\d+p|\d+i)\)|\[[^]]*\]','',s)
 return re.sub(r'[^a-z0-9]','',s.lower().replace('&','and'))

def entries(text):
 result=[];meta=None;extra=[]
 for line in text.splitlines():
  if line.startswith('#EXTINF:'):meta=line;extra=[]
  elif meta and line.startswith('#'):extra.append(line)
  elif meta and line.startswith(('http://','https://')):
   attrs=dict(re.findall(r'([\w-]+)="([^"]*)"',meta))
   result.append(dict(meta=meta,name=meta.split(',',1)[1],url=line,extra=extra,attrs=attrs,service=attrs.get('group-title','')));meta=None
 return result

def stamp(s):
 try:return dt.datetime.strptime(s,'%Y%m%d%H%M%S %z')
 except (ValueError,TypeError):return None

def load_source(pair):
 name,url=pair
 try:return name,ET.fromstring(fetch(url)),None
 except Exception as e:return name,None,str(e)

def xumo():
 mapping=ET.fromstring(fetch('https://raw.githubusercontent.com/iptv-org/epg/master/sites/xumo.tv/xumo.tv.channels.xml'))
 r=ET.Element('tv'); offsets=set()
 for c in mapping.findall('channel'):
  offset,cid=c.get('site_id').split('#');offsets.add(int(offset))
  out=ET.SubElement(r,'channel',id=cid,original_id=c.get('xmltv_id',''));ET.SubElement(out,'display-name').text=c.text
 tasks=[(d,b,o) for d in [NOW.date(),NOW.date()+dt.timedelta(days=1)] for b in range(4) for o in sorted(offsets)]
 def grab(t):
  d,b,o=t
  url=f'https://valencia-app-mds.xumo.com/v2/epg/10006/{d:%Y%m%d}/{b}.json?f=asset.title&f=asset.descriptions&limit=50&offset={o}'
  try:return json.loads(fetch(url))
  except Exception:return {}
 with futures.ThreadPoolExecutor(max_workers=6) as pool:
  for data in pool.map(grab,tasks):
   for c in data.get('channels',[]):
    for p in c.get('schedule',[]):
     a=data.get('assets',{}).get(p.get('assetId'),{})
     if not a.get('title'):continue
     try:
      start=dt.datetime.fromisoformat(p['start']).strftime('%Y%m%d%H%M%S %z');stop=dt.datetime.fromisoformat(p['end']).strftime('%Y%m%d%H%M%S %z')
     except (ValueError,KeyError):continue
     out=ET.SubElement(r,'programme',channel=str(c['channelId']),start=start,stop=stop)
     ET.SubElement(out,'title').text=a['title']
     if a.get('episodeTitle'):ET.SubElement(out,'sub-title').text=a['episodeTitle']
     desc=a.get('descriptions') or {};desc=desc.get('medium') or desc.get('small') or desc.get('tiny')
     if desc:ET.SubElement(out,'desc').text=desc
 return r

def main():
 lineup=entries((ROOT/'channels.m3u').read_text());guides={};errors={}
 with futures.ThreadPoolExecutor(max_workers=6) as pool:
  for name,r,error in pool.map(load_source,SOURCES.items()):
   if r is not None:guides[name]=r
   else:errors[name]=error
 try:guides['Xumo']=xumo()
 except Exception as e:errors['Xumo']=str(e)
 tubi_stream_ids=defaultdict(set)
 try:
  tubi_list=fetch('https://raw.githubusercontent.com/BuddyChewChew/tubi-scraper/refs/heads/main/tubi_playlist.m3u').decode()
  for entry in entries(tubi_list):
   for uuid in re.findall(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',entry['url']):
    tubi_stream_ids[uuid].add(entry['attrs'].get('tvg-id'))
 except Exception as e:errors['Tubi stream mapping']=str(e)
 indices={}
 for service,r in guides.items():
  cs={c.get('id'):c for c in r.findall('channel')};names=defaultdict(set);programs=defaultdict(list);original={}
  for cid,c in cs.items():
   for n in c.findall('display-name'):names[norm(n.text or '')].add(cid)
   if c.get('original_id'):original[c.get('original_id')]=cid
  for p in r.findall('programme'):
   st,en=stamp(p.get('start')),stamp(p.get('stop'))
   if st and en and st<en and en>NOW and st<NOW+dt.timedelta(days=7) and p.findtext('title'):programs[p.get('channel')].append(p)
  indices[service]=(cs,names,programs,original)
 out=ET.Element('tv',{'generator-info-name':'Personal Free TV EPG','date':NOW.strftime('%Y%m%d%H%M%S +0000')})
 lines=[f'#EXTM3U url-tvg="{GUIDE_URL}" x-tvg-url="{GUIDE_URL}"'];report=[]
 for e in lineup:
  uid='pftv.'+hashlib.sha256((e['service']+'|'+e['url']).encode()).hexdigest()[:20]
  cid=None;reason='No provider guide source';channel=None;ps=[]
  if e['service'] in indices:
   cs,names,programs,original=indices[e['service']];reason='No unambiguous provider channel match'
   m=re.search(r'plu-([a-f0-9]+)',e['url']) if e['service']=='Pluto TV' else None
   if m and m[1] in cs:cid=m[1]
   elif e['service']=='Tubi' and any(u in tubi_stream_ids for u in re.findall(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',e['url'])):
    candidates=set().union(*(tubi_stream_ids[u] for u in re.findall(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',e['url'])))
    if len(candidates)==1 and next(iter(candidates)) in cs:cid=next(iter(candidates))
   elif e['attrs'].get('tvg-id') in original:cid=original[e['attrs']['tvg-id']]
   else:
    candidates=names[norm(e['name'])]
    if len(candidates)==1:cid=next(iter(candidates))
   if cid:
    channel=cs[cid];ps=programs[cid];reason='Matched with upcoming programmes' if ps else 'Matched but no unexpired programmes'
  c=ET.SubElement(out,'channel',id=uid);ET.SubElement(c,'display-name').text=e['name']
  if channel is not None:
   for icon in channel.findall('icon'):c.append(copy.deepcopy(icon))
  seen=set()
  for p in sorted(ps,key=lambda p:p.get('start')):
   key=(p.get('start'),p.get('stop'),p.findtext('title'))
   if key in seen:continue
   seen.add(key);p=copy.deepcopy(p);p.set('channel',uid);out.append(p)
  meta=re.sub(r'tvg-id="[^"]*"',f'tvg-id="{uid}"',e['meta'])
  if 'tvg-id=' not in meta:meta=meta.replace('#EXTINF:-1',f'#EXTINF:-1 tvg-id="{uid}"',1)
  icon=channel.find('icon') if channel is not None else None
  if icon is not None and 'tvg-logo=' not in meta:
   logo=icon.get('src','').replace('"','%22');meta=meta.replace('#EXTINF:-1',f'#EXTINF:-1 tvg-logo="{logo}"',1)
  lines.extend([meta,*e['extra'],e['url']])
  report.append(dict(service=e['service'],name=e['name'],id=uid,source_id=cid,programmes=len(seen),status=reason))
 covered=sum(bool(r['programmes']) for r in report)
 if covered<max(1,len(lineup)//2):raise RuntimeError(f'Only {covered} channels have fresh schedules; refusing to replace guide')
 # XMLTV requires all channel declarations before programme elements.
 out[:]=out.findall('channel')+out.findall('programme')
 xml=ET.tostring(out,encoding='utf-8',xml_declaration=True)
 ET.fromstring(xml)
 (ROOT/'epg.xml').write_bytes(xml)
 (ROOT/'playlist.m3u').write_text('\n'.join(lines)+'\n')
 summary={'generated_at':NOW.isoformat(),'total_entries':len(lineup),'entries_with_upcoming_programmes':covered,'programmes':len(out.findall('programme')),'source_errors':errors,'sources':SOURCES,'channels':report}
 (ROOT/'coverage.json').write_text(json.dumps(summary,indent=2)+'\n')
 counts=Counter(r['service'] for r in report if r['programmes']);total=Counter(e['service'] for e in lineup)
 md='# Guide coverage\n\nGenerated '+NOW.isoformat()+f'\n\n{covered} of {len(lineup)} playlist entries have upcoming programmes. Coverage is not a guarantee of gap-free schedules or playback. Matching is provider-specific; no cross-service schedule substitutions or fabricated programmes.\n\n| Service | With schedules | Entries |\n|---|---:|---:|\n'
 md+=''.join(f'| {s} | {counts[s]} | {t} |\n' for s,t in total.items())
 md+='\n## Missing schedules\n\n'+''.join(f'- {r["service"]}: {r["name"]} — {r["status"]}\n' for r in report if not r['programmes'])
 (ROOT/'COVERAGE.md').write_text(md)
 print(json.dumps({k:v for k,v in summary.items() if k not in ['channels','sources']},indent=2))
if __name__=='__main__':main()
