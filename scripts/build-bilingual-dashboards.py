#!/usr/bin/env python3
"""Create localized dashboard pairs without changing measurement expressions."""
import argparse
import copy
import json
from pathlib import Path
import re

T={
 'Nincs adat':'No data','ELÉRHETŐ':'UP','NEM ELÉRHETŐ':'DOWN',
 'Adatbázis':'Database','Memória':'Memory','Gyökérlemez':'Root filesystem',
 'Kérések':'Requests','Metódus':'Method','Útvonal':'Route','Időminták':'Timing samples',
 'Minden kérés':'All requests','Health nélkül':'Exclude health checks','Mind':'All',
 'Adatbáziscél':'Supabase target','Kérésazonosító · csak naplók':'Request ID · logs only',
 'Forgalom':'Traffic','Útvonal tartalmazza':'Route contains','HTTP-státusz · csak naplók':'HTTP status · logs only',
 'Minden kérés : ^$, Health nélkül : (/api/health|/health)':'All requests : ^$, Exclude health checks : (/api/health|/health)',
 'Mind : .*, 4xx : 4[0-9][0-9], 5xx : 5[0-9][0-9], 401 : 401, 404 : 404, 403 : 403, 429 : 429':'All : .*, 4xx : 4[0-9][0-9], 5xx : 5[0-9][0-9], 401 : 401, 404 : 404, 403 : 403, 429 : 429',
 'Olvasás':'Read','Írás':'Write','Bejövő':'Received','Kimenő':'Transmitted',
 'Terhelés · 1 perc':'Load · 1 minute','Terhelés · 5 perc':'Load · 5 minutes','Terhelés · 15 perc':'Load · 15 minutes',
 'Lezárt / s':'Committed / s','Visszagörgetett / s':'Rolled back / s','Puffertalálatok':'Buffer cache hits',
 'Ideiglenes írás / s':'Temporary writes / s','Várakozó kérések':'Waiting requests',
 'PostgreSQL deadlock / perc':'PostgreSQL deadlocks / min','PostgREST pool-időtúllépés / perc':'PostgREST pool timeouts / min',
 '{{device}} · Olvasás / s':'{{device}} · Read / s','{{device}} · Írás / s':'{{device}} · Write / s',
 '{{device}} · Olvasás':'{{device}} · Read','{{device}} · Írás':'{{device}} · Write',
 'Utolsó sikeres futás kora':'Age since last success','Utolsó sikeres gyűjtés kora':'Age since last successful collection',
 '0 = rendben / 1 = hiba':'0 = OK / 1 = error','Kérés / perc':'Requests / min','4xx / perc':'4xx / min','5xx / perc':'5xx / min',
 'suffix:kérés/perc':'suffix:requests/min','suffix:hiba/perc':'suffix:errors/min',
 'suffix:válasz/5perc':'suffix:responses/5min','suffix:tranzakció/s':'suffix:transactions/s',
 'suffix:esemény/perc':'suffix:events/min','suffix:válasz/perc':'suffix:responses/min',
 'suffix:kérés':'suffix:requests','suffix:csomag/perc':'suffix:batches/min',
 'suffix:megfigyelés/perc':'suffix:observations/min',
 'Backend · HTTP-próba':'Backend · HTTP probe','Frontend · HTTP-próba':'Frontend · HTTP probe',
 'Backend · CPU (%)':'Backend · CPU (%)','Adatbázis · CPU (%)':'Database · CPU (%)',
 'Backend · Memória (%)':'Backend · Memory (%)','Adatbázis · Memória (%)':'Database · Memory (%)','Oracle · Memória (%)':'Oracle · Memory (%)',
 'Frontend · API-indítás / perc':'Frontend · API starts/min','Frontend · HTTP-válasz / perc':'Frontend · HTTP responses/min',
 'Backend · Naplózott API / perc':'Backend · Logged API requests/min',
 'Frontend · Fejlécekig átlag':'Frontend · Mean to response headers','Frontend · Fejlécekig P95 (becsült)':'Frontend · P95 to response headers (estimated)',
 'Backend · Feldolgozás P95':'Backend · Processing P95','Backend · API / perc':'Backend · API requests/min',
 'Adatbázis · Tranzakció / s':'Database · Transactions/s','PostgREST · Várakozó kérések':'PostgREST · Waiting requests',
 'Backend API-kérés / perc':'Backend API requests/min','Adatbázis-tranzakció / s':'Database transactions/s',
 'Backend feldolgozás P95 (ms)':'Backend processing P95 (ms)','PostgREST várakozó kérések':'PostgREST waiting requests',
 'HTTP-válasz':'HTTP response','Hálózati hiba':'Network error','Megszakítva':'Aborted',
 'Sikertelen küldési kísérletek':'Failed delivery attempts','Elveszett csomagok':'Dropped batches','Elveszett megfigyelések':'Dropped observations',
 'Duplikált':'Duplicate','Elutasított':'Rejected','Fogadó által korlátozott':'Receiver rate-limited',
 'Összevont részletes megfigyelések':'Observations with folded dimensions','HTTP-hibák aránya':'HTTP error rate',
 'Jelenlegi 5 perces átlag':'Current 5-minute average','Korábbi 30 perces átlag (5 perc eltolás)':'Previous 30-minute average (offset 5m)',
 'Szolgáltatások összehasonlítása':'Service Comparison','Üzemeltetési áttekintés':'Unified Monitoring',
 'Frontend megnyitása':'Open frontend','1 perc':'1 minute','5 perc':'5 minutes','15 perc':'15 minutes','Esemény / perc':'Events / min',
}

UNIFIED_TITLES={
 1:'MatchWise · Operations overview',2:'01 · Availability and data freshness',3:'Oracle · Metrics scrape',
 4:'Backend · HTTP probe',5:'Frontend · HTTP probe',6:'Backend logs · Age since successful collection',
 7:'Oracle · CPU (%)',8:'Oracle · Memory (%)',9:'Oracle · Root filesystem (%)',10:'Backend · HTTP 5xx · Selected period',
 11:'04 · Oracle · Resource details',12:'Oracle · Uptime',13:'Oracle · Available memory',14:'Oracle · Available disk space',15:'Oracle · System load · 1 minute',
 16:'Oracle · CPU (%)',17:'Oracle · Memory (%)',18:'Oracle · Root filesystem (%)',19:'Oracle · Disk throughput',20:'Oracle · Network throughput',21:'Oracle · System load · 1 / 5 / 15 minutes',
 22:'06 · Backend · HTTP probe details',23:'Backend · Latest HTTP status code',24:'Backend · Latest HTTP probe duration',25:'Backend · Probe success rate · Selected period',26:'Backend · HTTP probe duration',27:'Backend · HTTP probe results',
 28:'07 · Frontend · HTTP probe details',29:'Frontend · Latest HTTP status code',30:'Frontend · Latest HTTP probe duration',31:'Frontend · Probe success rate · Selected period',32:'Frontend · HTTP probe duration',33:'Frontend · HTTP probe results',
 34:'02 · Application traffic and HTTP probes',35:'HTTP requests · Selected period',36:'HTTP 4xx · Selected period',37:'HTTP 5xx · Selected period',38:'HTTP error rate · 4xx and 5xx',39:'Backend · Requests/min · 5-minute average',40:'Backend · HTTP errors/min',41:'Backend · Processing time P50 / P95 · 15 minutes',42:'Backend · HTTP status codes · Rolling 5 minutes',43:'Backend · Most frequently logged routes',
 44:'10 · Log collection · Freshness and errors',45:'Log collector · Age since successful run',46:'Textfile collector · Scrape errors',47:'Backend · HTTP logs',48:'Backend · HTTP error logs · 4xx / 5xx',49:'11 · Diagnostics · Filtered backend logs',50:'Applications and filters',
 51:'Backend · HTTP probe age',52:'Frontend · HTTP probe age',53:'Backend · Probe samples · Selected period',54:'Frontend · Probe samples · Selected period',55:'Backend · Exporter scrape',56:'Frontend · Exporter scrape',57:'Backend · Latest HTTP probe time',58:'Frontend · Latest HTTP probe time',59:'Backend · Timing samples · Last 15 minutes',60:'Backend · HTTP 401 · Selected period',61:'Backend · HTTP 404 · Selected period',62:'Backend · Health requests · Selected period',63:'Log collector · HTTP events · Selected period',64:'Loki · Latest HTTP event · Last hour',65:'Log collection · Interpretation',66:'Backend · Endpoint summary',67:'Log collector · Age since successful run',68:'09 · Authentication · Selected period',69:'Successful logins · 200',70:'Rejected logins · 401',71:'Invalid login data · 400',72:'Login service errors · 5xx',73:'Successful logouts · 204',74:'Successful registrations · 201',
 75:'Database · Metrics scrape',76:'Database · PostgreSQL reachability',77:'Database · Connection slots used (%)',78:'Database · Data filesystem used (%)',79:'Database · CPU (%)',80:'Database · Memory (%)',81:'Database · Open connections',82:'Database · Database size',83:'Database · CPU and memory (%)',84:'Database · Filesystem utilization',85:'Database · Connections by role',86:'Database · Committed and rolled-back transactions',87:'Database · PostgreSQL buffer cache hit ratio',88:'Database · Temporary-file writes',89:'PostgREST · Waiting requests',90:'Database · Deadlocks and pool timeouts/min',91:'Database · Disk throughput',92:'Database · Average disk operation time',93:'03 · Database · Capacity',94:'05 · Database · Operational details',95:'08 · Application · Status codes and endpoints',96:'HTTP probe duration · Frontend and backend',
}
COMPARISON_TITLES={
 1:'MatchWise · Service Comparison',6:'Backend · HTTP probe',7:'Database · PostgreSQL reachability',8:'Frontend · HTTP probe',9:'Oracle · Metrics scrape',10:'Backend · CPU (%)',11:'Database · CPU (%)',13:'Oracle · CPU (%)',14:'Backend · Memory (%)',15:'Database · Memory (%)',17:'Oracle · Memory (%)',18:'Backend · Resource sample age',19:'Database · Metrics scrape',20:'Frontend · HTTP probe age',21:'Oracle · Textfile scrape errors',23:'Backend · All non-health requests/min',24:'Backend · HTTP 4xx and 5xx/min',25:'Backend · Processing time P50 / P95 · 15 minutes',26:'Backend · Age since successful log collection',28:'Security signals · Interpretation',29:'401 · Unauthenticated · 5 minutes',30:'403 · Access denied · 5 minutes',31:'404 · Not found · 5 minutes',32:'429 · Rate limited · 5 minutes',33:'Backend · HTTP status codes/min',34:'Backend · Current and previous traffic',38:'Telemetry · Oracle receiver',39:'Browser batches · Age since last arrival',40:'Browser batches · Total accepted',41:'API traffic · Frontend and backend',42:'Latency · Browser and backend',43:'Two axes · Interpretation',44:'API traffic ↔ Database transactions · Two axes',45:'Backend CPU ↔ Database transactions · Two axes',46:'Backend P95 ↔ PostgREST queue · Two axes',47:'Backend logs · Age since successful collection',48:'01 · API traffic and latency — comparable units',49:'02 · Backend, database and resources — shared timeline',50:'Backend · API traffic',51:'Database · Committed transactions',52:'PostgREST · Waiting requests',53:'CPU · Own service capacity (%)',54:'Memory · Own service capacity (%)',55:'Backend · Processing time P95',56:'03 · Resources and collection · Details',57:'04 · HTTP errors and security signals',59:'05 · Advanced comparison · Two separate axes',61:'06 · Frontend details · Routes, errors and delivery',62:'Frontend details · Interpreting the data',63:'API starts · By route group',64:'P95 to response headers · By route group (estimated)',65:'Outcomes · HTTP response, network error, abort',66:'HTTP responses · By status code',67:'HTTP error rate · 4xx and 5xx',68:'HTTP errors · By route group',69:'API starts · By HTTP method',70:'Longest time to response headers · Since receiver restart',71:'In-flight requests · Last reporting page',72:'Batch delay · Includes clock skew',73:'Aggregation window · Last batch',74:'Receiver · Extended metrics version',75:'Successful deliveries · Last page report',76:'Failed delivery attempts · Last page report',77:'Dropped batches · Last page report',78:'Dropped observations · Last page report',79:'Delivery issues · Largest reported page counters',80:'Batches reporting delivery issues/min',81:'Receiver quality · Duplicate, rejected and rate-limited batches',82:'Detailed dimensions · Observations folded at the limit',83:'API starts · Since receiver restart',84:'Results · Since receiver restart',85:'Mean time to response headers · By route group',86:'Results · By method and outcome',
}

UNIFIED_DESCRIPTIONS={
 4:'Latest HTTP probe within a three-minute window, shown only while the current exporter scrape succeeds. Probes run every minute. Failed HTTP probe: red; missing or uncollectable observation: no data. This is not a continuous availability SLA.',
 51:'Age of the latest actual HTTP probe sample within a three-minute window. This is not browser traffic or telemetry batch age.',
 6:'Seconds since the last successful log collector run. This is not the age of the last business request.',
 23:'Latest HTTP probe observation within three minutes, shown only while its exporter is reachable. Probe duration includes DNS, connection and network time; it is not backend application processing time.',
 25:'Percentage of successful stored HTTP probe samples in the selected period. Read alongside sample counts; this is not continuous uptime or a contractual SLA. No percentage is calculated without samples.',
 39:'Logged backend HTTP requests as a five-minute average expressed per minute. Traffic and route filters apply. The comparison dashboard instead filters specifically for API route groups.',
 41:'Logged application processing time P50 and P95 over a rolling 15-minute window. These are neither HTTP probe durations nor full browser response times.',
 96:'HTTP probes initiated from the same Oracle machine, on a shared seconds scale. Includes DNS, connection and network time; these are not browser API timings or backend application processing times.',
 86:'Committed and rolled-back PostgreSQL transactions per second, averaged over five minutes. Includes internal services and other clients; this is not an HTTP request count.',
 89:'Requests waiting for a connection in the PostgREST pool only. This is not all PostgreSQL waiting, locking or backend traffic.',
 90:'Five-minute event rates expressed per minute. PostgreSQL deadlocks and PostgREST pool timeouts are separate series. Rollbacks or correlated activity alone do not prove an attack.',
}
for a,b in [(5,4),(52,51),(67,6),(45,6),(24,23),(29,23),(30,23),(31,25)]: UNIFIED_DESCRIPTIONS[a]=UNIFIED_DESCRIPTIONS[b]

COMPARISON_DESCRIPTIONS={
 6:'Latest HTTP probe within three minutes, shown only while the current exporter scrape succeeds. Failed HTTP probes are red; missing observations are unknown, not zero traffic.',
 38:'Whether Prometheus can scrape the receiver. This does not prove active browser reporting.',
 39:'Seconds since the last accepted batch, including empty manual tests. Accepted empty heartbeats refresh this age. With no open browser page, heartbeats may stop; an old batch alone does not prove a frontend outage.',
 47:'Age since the last successful log collector run, not since the last business request.',
 40:'Accepted, deduplicated batches since receiver startup, including empty manual test batches. Not API requests or users. Resets on receiver restart.',
 41:'Five-minute averages expressed as requests per minute, excluding health checks. Solid blue: starts; dashed blue: HTTP responses; orange: logged backend API requests. Same units, different coverage. Frontend freshness guards remain active.',
 42:'Different measurements for trend comparison: browser fetch time until response headers and logged backend processing time. Not full download time; subtracting them does not produce exact network latency. Frontend P95 is estimated from histogram buckets and requires HTTP outcomes with positive observation rates.',
 50:'Logged backend API requests per minute, averaged over five minutes. Excludes health checks; includes relative API routes and /api-prefixed routes. Missing logs are not replaced with zero.',
 51:'Committed PostgreSQL transactions per second, averaged over five minutes. Includes internal services and other clients; not backend request counts. Requires successful PostgreSQL connection and metrics scrape.',
 53:'Same percentage scale, different service capacities. Existing freshness guards remain active. Oracle/Supabase CPU: five-minute average; Render CPU: API sample.',
 54:'Same percentage scale; service capacities and memory definitions differ. Existing freshness guards remain active.',
 55:'P95 of logged backend API processing times in the last five minutes, in milliseconds. Excludes health checks. Does not include the full browser-to-backend network path.',
 52:'Requests currently waiting for the PostgREST connection pool. Not all database waiting. An observed zero is valid; missing observations are a separate state.',
 63:'Five-minute averages by auth, cv, jobs and other route groups. These are not user counts.',
 64:'Histogram-estimated browser time until HTTP response headers, not backend processing time.',
 65:'http: an HTTP response arrived, including error status codes; network_error: no HTTP response arrived; aborted: request was cancelled.',
 67:'Share of observed HTTP responses only. Excludes network errors and aborts. No ratio is shown without a positive response rate; no artificial 0% is displayed.',
 68:'4xx/5xx responses since the receiver extension was installed. Historical route-to-status relationships cannot be reconstructed from older metrics.',
 70:'Exact largest observed duration_max_ms by route since receiver restart. This is neither P95 nor a five-minute maximum. Restarts with the receiver.',
 71:'API requests still in flight on the last reporting page when its batch was created. Not total simultaneous requests across all browsers.',
 72:'Receiver arrival time minus the client-reported window end. May include retry delay and client clock skew; can be negative.',
 73:'Reported window end minus start. Background tabs, pending delivery and retries can affect the nominal 60-second interval.',
 74:'2 = receiver with extended metrics. The frontend batch schema is still version 1; no frontend deployment is required.',
 75:'Cumulative value since the last reporting page started, captured when the batch was created. Do not sum across batches or browsers. Does not yet include the delivery result of this batch.',
 79:'Largest cumulative per-page diagnostic values observed since receiver restart. Not global error totals or counts of new incidents.',
 80:'Rate of accepted unique batches reporting a positive issue counter. An older issue can appear in many subsequent batches; this is not the number of new failures.',
 81:'The Oracle receiver counters include production and test delivery. Duplicate batches do not increase business counters again.',
 82:'Detailed route/method/status/outcome combinations are capped at 4096. Additional dimensions fold into other/OTHER; overall traffic, HTTP status counts and timing histograms remain available. A missing series can mean no observation has exceeded the cap yet.',
 83:'Observed API starts by route group since receiver restart. Includes first observations even when traffic is low; resets on restart. Not session or user counts.',
 84:'Observed results by route group since the receiver extension, including network errors and aborts. Need not equal request starts.',
 85:'Mean time to response headers by route group, for requests receiving an HTTP response only.',
 86:'Detailed results by method and outcome. Above the dimension limit, methods fold into OTHER; overall result counts are retained.',
}
COMPARISON_DESCRIPTIONS[8]=COMPARISON_DESCRIPTIONS[6]
for i in (76,77,78): COMPARISON_DESCRIPTIONS[i]=COMPARISON_DESCRIPTIONS[75]

BODIES={
 ('unified',1):'**Availability → traffic → capacity.** Blue: frontend · Orange: backend · Green: database · Purple: Oracle.\n\nMissing data ≠ zero. Availability means an HTTP probe or a metrics connection; detailed sections can be expanded below.',
 ('unified',50):'[Open frontend](https://www.matchwise.tech/) · [Backend health](https://matchwise-backend-monitoring-test.onrender.com/api/health) · [Service Comparison](/d/matchwise-service-comparison/matchwise-szolgltatsok-sszehasonltsa)\n\n**Traffic** and **Route contains** filter application metrics; **HTTP status** and **Request ID** also apply to logs. Authentication counters are independent of these filters.',
 ('unified',65):'A successful log collector run means the Render API request completed successfully. A quiet application can have an old latest HTTP event; this alone is not a collection failure. Filters can also produce empty results. Error counters show zero only when matching HTTP traffic was observed; empty results do not prove an error-free system. P50/P95 curves use rolling 15-minute processing-time windows.',
 ('comparison',1):'**Status → traffic → load.** Blue: frontend · Orange: backend · Green: database · Purple: Oracle.\n\nShared timeline, clearly labelled units. Missing data ≠ zero. Detailed sections can be expanded below.',
 ('comparison',28):'**Last five minutes, excluding health checks.** HTTP 401/403/404/429 counts are investigation signals, not proof of an attack. Missing results do not mean zero events. No IP or account attribution is collected; a 429 panel does not prove that rate limiting is implemented.',
 ('comparison',43):'**Advanced view: two separate vertical axes.** Left and right axes use different units; curve heights cannot be compared directly. The separate main-view plots are easier to read. Database transactions are not backend requests; the queue covers only the PostgREST connection pool.',
 ('comparison',62):'**Real browser traffic; 60-second batches.** Rates use five-minute averages and may not yet include the first events of a new counter series. Cumulative counts below help when traffic is low.\n\n**Network error ≠ HTTP 4xx/5xx.** Aborted requests have no HTTP response, so failed outcomes are shown separately. Routes are groups (auth, cv, jobs…), not full URLs.\n\n**The last batch contains a snapshot from one reporting page**, not the sum of all open browsers. Delivery counters accumulate since that page started and are captured when its batch is created; they have no safe global sum. Observed maxima are measured since the Oracle receiver started. Issue-reporting batches can repeat an old issue rather than indicate a new failure.\n\n**Batch delay may include browser–Oracle clock skew**, so it can be negative and is not pure network latency. Missing data ≠ zero. Fresh snapshots disappear when the latest real batch is older than three minutes; cumulative counts and maxima require a successful receiver scrape.\n\nRoute-detail plots use consistent route-group colors across panels.',
}

def walk(panels):
    for p in panels:
        yield p
        yield from walk(p.get('panels',[]))

def localized_url(value):
    for uid,new in [('matchwise-unified-overview','/d/matchwise-unified-overview-en/matchwise-unified-monitoring'),('matchwise-service-comparison','/d/matchwise-service-comparison-en/matchwise-service-comparison')]:
        value=re.sub(r'/d/'+re.escape(uid)+r'(?!-en)(?:/[^?\s)\]"\x27]*)?',lambda m:new,value)
    return value

def translate(value):
    if isinstance(value,str): return localized_url(T.get(value,value))
    if isinstance(value,list): return [translate(v) for v in value]
    if isinstance(value,dict):
        # Expressions are machine contracts; never translate or rewrite their contents.
        return {T.get(k,k):(v if k=='expr' else translate(v)) for k,v in value.items()}
    return value

def build(source,name):
    source=copy.deepcopy(source)
    en_titles=UNIFIED_TITLES if name=='unified' else COMPARISON_TITLES
    descriptions=UNIFIED_DESCRIPTIONS if name=='unified' else COMPARISON_DESCRIPTIONS
    panels={p['id']:p for p in walk(source['panels'])}
    assert set(panels)==set(en_titles),'Missing English panel title'
    # Translate literal UI strings, including transform/override names used by tables.
    for pid,p in panels.items():
        T[p['title']]=en_titles[pid]
        if pid in descriptions: T[p['description']]=descriptions[pid]
        if (name,pid) in BODIES: T[p['options']['content']]=BODIES[name,pid]
    english=translate(source)
    # Variable values and queries are data, even when a value happens to match a UI label.
    for original,localized in zip(source['templating']['list'],english['templating']['list']):
        for key in ('regex','datasource','definition'):
            if key in original: localized[key]=copy.deepcopy(original[key])
        if 'current' in original and 'value' in original['current']:
            localized['current']['value']=copy.deepcopy(original['current']['value'])
        for a,b in zip(original.get('options',[]),localized.get('options',[])):
            if 'value' in a: b['value']=copy.deepcopy(a['value'])
        if original['type'] in ('query','textbox'):
            localized['query']=copy.deepcopy(original['query'])
        if original['type']=='textbox': localized['current']=copy.deepcopy(original['current'])
    english['title']='MatchWise | Unified Monitoring' if name=='unified' else 'MatchWise · Service Comparison'
    english['uid']=source['uid']+'-en'
    english['tags']=[t for t in english.get('tags',[]) if t.lower() not in ('hu','magyar')]
    if not source['title'].endswith(' HU'):
        source['title']+=' HU'
        source['version']+=1
    english['version']=source['version']
    source.setdefault('links',[])
    english.setdefault('links',[])
    source['links']=[l for l in source['links'] if l.get('title')!='Angol változat']
    english['links']=[l for l in english['links'] if l.get('title') not in ('Angol változat','Hungarian version (HU)')]
    en_slug='matchwise-unified-monitoring' if name=='unified' else 'matchwise-service-comparison'
    hu_slug='matchwise-unified-monitoring' if name=='unified' else 'matchwise-szolgltatsok-sszehasonltsa'
    source['links'].insert(0,{'title':'Angol változat','url':f'/d/{english["uid"]}/{en_slug}?${{__url_time_range}}','type':'link','targetBlank':False})
    english['links'].insert(0,{'title':'Hungarian version (HU)','url':f'/d/{source["uid"]}/{hu_slug}?${{__url_time_range}}','type':'link','targetBlank':False})
    return source,english

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_directory',type=Path)
    parser.add_argument('output_directory',type=Path)
    args=parser.parse_args();args.output_directory.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for name,filename in [('unified','matchwise-unified-monitoring.json'),('comparison','matchwise-service-comparison.json')]:
        path=args.source_directory/filename
        if not path.exists(): path=args.source_directory/('source-'+name+'.json')
        source=json.loads(path.read_text(encoding='utf-8'))
        hu,en=build(source,name)
        for file,d in [(filename,hu),(filename.replace('.json','-en.json'),en)]:
            (args.output_directory/file).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
            manifest.append({'file':file,'uid':d['uid'],'title':d['title'],'language':'en' if file.endswith('-en.json') else 'hu','kind':name})
            print(d['title'],d['uid'])
    (args.output_directory/'dashboard-language-manifest.json').write_text(json.dumps({'dashboards':manifest},ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')

if __name__=='__main__': main()
