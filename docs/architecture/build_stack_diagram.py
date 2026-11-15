"""Build the editable diagrams.net file and its SVG from shared geometry."""
from pathlib import Path
import json
import html
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
W, H = 2400, 1720
C = {'app':'#2563eb', 'metrics':'#0f766e', 'logs':'#b7791f',
     'alerts':'#c24145', 'future':'#8056b3', 'access':'#64748b'}
boxes, edges, labels = [], [], []

def box(id, x, y, w, h, title, lines=(), *, parent='1', fill='#ffffff',
        stroke='#94a3b8', group=False, dashed=False, size=21):
    boxes.append(dict(id=id,x=x,y=y,w=w,h=h,title=title,lines=list(lines),
                      parent=parent,fill=fill,stroke=stroke,group=group,
                      dashed=dashed,size=size))

def label(x,y,lines, *, color='#475569', size=18, anchor='middle', bg=True):
    labels.append(dict(x=x,y=y,lines=list(lines),color=color,size=size,anchor=anchor,bg=bg))

def edge(id, source,target,points,kind, text=(),at=None,both=False):
    edges.append(dict(id=id,source=source,target=target,points=points,
                      color=C[kind],dashed=kind=='future',both=both))
    if text: label(*at,text,color=C[kind],size=17)

box('browser',50,160,260,170,'FELHASZNÁLÓ',['Böngésző','Az alkalmazás felülete'],fill='#f8fafc',stroke='#64748b')
box('vercel',370,130,480,240,'VERCEL · frontend',group=True,fill='#f1f5f9',stroke='#64748b')
box('spa',395,205,430,130,'React webalkalmazás',['www.matchwise.tech','Böngészős integráció: külön teszt*'],parent='vercel',stroke='#64748b')
box('render',960,130,540,240,'RENDER · backend',group=True,fill='#eff6ff',stroke=C['app'])
box('backend',985,205,240,130,'Node.js + Express',['REST API + auth','Pino HTTP-naplózás'],parent='render',stroke=C['app'],size=20)
box('renderlogs',1260,205,215,130,'Render Logs API',['Alkalmazásnaplók','Pino JSON'],parent='render',stroke=C['logs'],size=20)
box('supabase',1620,130,470,240,'SUPABASE · kezelt adatbázis',group=True,fill='#ecfdf5',stroke=C['metrics'])
box('db',1645,205,220,130,'Auth + PostgreSQL',['PostgREST Data API','SQL-migrációk'],parent='supabase',stroke=C['metrics'],size=20)
box('metricsapi',1880,205,185,130,'Metrics API',['DB + host metrikák','HTTPS'],parent='supabase',stroke=C['metrics'],size=20)
box('ai',2140,130,240,240,'CLOUDFLARE AI',['Workers AI · gpt-oss-20b','CV → profil · feature branch','Élesítés nem igazolt'],fill='#faf5ff',stroke=C['future'],dashed=True,size=19)

box('cloudinary',2140,450,240,160,'CLOUDINARY',['CV-fájltárolás','Backendforrásban szerepel'],fill='#eff6ff',stroke=C['app'],size=19)

box('oracle',50,520,2040,1030,'ORACLE CLOUD VM · Ubuntu · ARM64 · monitoring',group=True,fill='#f8fafc',stroke='#475569')
box('host',80,600,410,880,'VM / systemd / helyi fájlok',parent='oracle',group=True,fill='#f1f5f9',stroke='#94a3b8')
box('linux',110,650,350,140,'Linux host metrikák',['CPU · RAM · lemez','Hálózat · uptime · load'],parent='host',stroke=C['metrics'])
box('collector',110,900,350,140,'Python naplógyűjtő',['systemd timer · kb. percenként','Render API · szűrés · deduplikálás'],parent='host',stroke=C['logs'],size=20)
box('files',110,1170,350,140,'Helyi fájlok és állapot',['render-backend.jsonl','SQLite dedup + időkurzor'],parent='host',stroke=C['logs'])
box('private',110,1370,350,80,'Privát konfiguráció',['.env / kulcsok · Gitből kizárva'],parent='host',stroke='#94a3b8',size=19)

box('docker',540,600,1500,880,'DOCKER COMPOSE · 6 alap + Caddy (public profil)',parent='oracle',group=True,fill='#ffffff',stroke='#64748b')
box('blackbox',590,650,370,140,'Blackbox Exporter',['HTTP-próbák és időmérés','Backend: 30 perc · frontend: 60 s'],parent='docker',fill='#f0fdfa',stroke=C['metrics'])
box('prometheus',1040,650,370,140,'Prometheus',['Metrikák gyűjtése + TSDB','Node / probe / Supabase'],parent='docker',fill='#f0fdfa',stroke=C['metrics'])
box('grafana',1570,650,410,140,'Grafana + Grafana Alerting',['Dashboardok · lekérdezések','12 riasztási szabály · Telegram'],parent='docker',fill='#fff7ed',stroke='#d97706')
box('node',590,900,370,140,'Node Exporter',['VM-erőforrások','Textfile collector: .prom / heartbeat'],parent='docker',fill='#f0fdfa',stroke=C['metrics'])
box('alloy',590,1170,370,140,'Grafana Alloy',['JSONL-fájl olvasása','Eredeti Render-időbélyeg'],parent='docker',fill='#fffbeb',stroke=C['logs'])
box('loki',1040,1170,370,140,'Loki',['Backend HTTP-naplók','LogQL · logokból számolt mutatók'],parent='docker',fill='#fffbeb',stroke=C['logs'])
box('caddy',1570,1010,410,140,'Caddy · HTTPS reverse proxy',['TCP 80/443 → helyi Grafana','TLS-tanúsítvány · secure cookie'],parent='docker',fill='#f8fafc',stroke=C['access'],size=20)
box('volumes',590,1390,1390,60,'Docker volume-ok: Prometheus TSDB · Grafana · Loki · Alloy · Caddy',parent='docker',fill='#f8fafc',stroke='#cbd5e1',size=19)

box('telegram',2140,650,240,240,'TELEGRAM',['Bot API → csapatcsoport','Riasztás / helyreállás','Értesítési útvonal beállítva'],fill='#fff1f2',stroke=C['alerts'],size=19)
box('operator',2140,1030,240,190,'CSAPATHOZZÁFÉRÉS',['HTTPS + Grafana login','Viewer · Unified Monitoring'],fill='#f8fafc',stroke=C['access'],size=19)
box('gitnote',2140,1320,240,200,'GITHUB',['Backend main → Render','Monitoring repo → VM','Konfiguráció','és dokumentáció'],fill='#f8fafc',stroke='#94a3b8',size=18)

edge('web','browser','spa',[(310,245),(395,245)],'app',['HTTPS'],(350,220),both=True)
edge('frontend-api','spa','backend',[(825,270),(985,270)],'future',['REST API','KÜLÖN TESZT*'],(905,235),both=True)
edge('stdout','backend','renderlogs',[(1225,285),(1260,285)],'logs')
edge('db-api','render','supabase',[(1500,325),(1620,325)],'app',['Auth + Data API','HTTPS'],(1560,285),both=True)
edge('ai-api','render','ai',[(1450,370),(1450,445),(2260,445),(2260,370)],'future',['AI API · feature branch, élesítés nem igazolt'],(1830,445),both=True)

edge('cv-storage','render','cloudinary',[(1500,350),(1580,350),(1580,480),(2140,480)],'app',['CV fájltárolás · backendforrás'],(1830,480),both=True)

edge('render-poll','renderlogs','collector',[(1360,335),(1360,485),(65,485),(65,950),(110,950)],'logs',
     ['Pino JSON · HTTPS · Render API lekérése kb. percenként'],(650,485))
edge('probe-front','blackbox','vercel',[(675,650),(675,370)],'metrics',['HTTP-próba / válasz · 60 s'],(675,410),both=True)
edge('probe-back','blackbox','render',[(880,650),(880,410),(1050,410),(1050,370)],'metrics',['HTTP-próba / válasz','30 perc'],(1020,440),both=True)
edge('supabase-metrics','metricsapi','prometheus',[(1970,335),(1970,400),(2100,400),(2100,560),(1350,560),(1350,650)],'metrics',
     ['Supabase-metrikák · HTTPS · Prometheus lekéri 60 s-onként'],(1725,560))

edge('hostmetrics','linux','node',[(460,720),(510,720),(510,935),(590,935)],'metrics',['Host metrikák'],(510,825))
edge('heartbeat','collector','node',[(460,995),(590,995)],'metrics',['.prom','heartbeat'],(525,1000))
edge('collector-output','collector','files',[(285,1040),(285,1170)],'logs',['JSONL + dedup','és időkurzor'],(285,1105))
edge('file-alloy','files','alloy',[(460,1240),(590,1240)],'logs',['JSONL','fájlolvasás'],(525,1240))
edge('alloy-loki','alloy','loki',[(960,1240),(1040,1240)],'logs',['push'],(1000,1210))
edge('node-prom','node','prometheus',[(960,970),(1190,970),(1190,790)],'metrics',['VM + heartbeat metrikák · 60 s'],(1190,910))
edge('probe-prom','blackbox','prometheus',[(960,720),(1040,720)],'metrics',['Próba-','metrikák'],(1000,720))
edge('prom-grafana','prometheus','grafana',[(1410,720),(1570,720)],'metrics',['PromQL','metrikák'],(1490,720),both=True)
edge('loki-grafana','loki','grafana',[(1410,1240),(1470,1240),(1470,850),(1775,850),(1775,790)],'logs',['LogQL · naplók és HTTP-statisztikák'],(1700,850),both=True)
edge('alerts','grafana','telegram',[(1980,720),(2100,720),(2100,770),(2140,770)],'alerts',['Riasztások','Bot API'],(2070,685))
edge('access','operator','caddy',[(2140,1125),(2070,1125),(2070,1080),(1980,1080)],'access',['HTTPS'],(2060,1045),both=True)
edge('caddy-grafana','caddy','grafana',[(1940,1010),(1940,790)],'access',['127.0.0.1:3000'],(1855,950),both=True)
edge('backend-deploy','gitnote','render',[(2380,1400),(2390,1400),(2390,105),(1230,105),(1230,130)],'access',['Backend main → Render deploy'],(1740,105))
edge('monitoring-pull','gitnote','host',[(2140,1460),(2110,1460),(2110,1540),(350,1540),(350,1480)],'access',['Monitoring repo → git pull / konfiguráció'],(1320,1540))

label(900,1515,['Belső monitoringvégpontok: loopback · Grafana: Caddy HTTPS · Üzemeltetés: SSH'],size=18,anchor='start',bg=False)
label(50,43,['MATCHWISE · TELJES STACK ÉS ADATÁRAMLÁS'],size=32,color='#0f172a',anchor='start',bg=False)
label(50,84,['Dokumentált állapot: 2026. november 16. · Üzemeltetői visszajelzés és verziózott konfiguráció alapján.'],size=19,anchor='start',bg=False)

for x,kind,name in [(70,'app','Alkalmazás / API'),(500,'metrics','Metrikák / HTTP-próbák'),(1040,'logs','Naplók'),(1390,'alerts','Riasztások'),(1790,'future','Tervezett kapcsolat')]:
    edges.append(dict(id='legend-'+kind,source=None,target=None,points=[(x,1610),(x+70,1610)],color=C[kind],dashed=kind=='future',both=False))
    label(x+85,1616,[name],size=19,anchor='start',bg=False)
label(50,1660,['* A frontend HTTP-elérése nem böngészős integrációs teszt. A backend auth API külön tesztelve működött.'],size=18,anchor='start',bg=False)
label(50,1690,['Telegram: csapatcsoport. AI: Cloudflare feature branch; éles állapot külön ellenőrizendő. A GitHub a verziókövetési és telepítési forrás.'],size=18,anchor='start',bg=False)

def e(s): return html.escape(str(s),quote=True)

def svg_text(x,y,lines,size,color='#0f172a',anchor='middle',bold=False):
    out=[f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{700 if bold else 400}">']
    for i,line in enumerate(lines):
        out.append(f'<tspan x="{x}" dy="{0 if i==0 else size*1.4}">{e(line)}</tspan>')
    return ''.join(out)+'</text>'

svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', '<rect width="100%" height="100%" fill="white"/>','<defs>']
for color in set(C.values()):
    key=color[1:]
    svg.append(f'<marker id="arrow-{key}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M 1 1 L 9 5 L 1 9 z" fill="{color}"/></marker>')
svg.append('</defs>')
for b in boxes:
    if not b['group']: continue
    x,y,w,h=b['x'],b['y'],b['w'],b['h']
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{b["fill"]}" stroke="{b["stroke"]}" stroke-width="2"/>')
    svg.append(svg_text(x+20,y+34,[b['title']],21,b['stroke'],'start',True))
for a in edges:
    points=' '.join(f'{x},{y}' for x,y in a['points'])
    svg.append(f'<polyline points="{points}" fill="none" stroke="white" stroke-width="8" stroke-linejoin="round"/>')
    attrs=f'stroke="{a["color"]}" stroke-width="2.5" stroke-linejoin="round" marker-end="url(#arrow-{a["color"][1:]})"'
    if a['both']: attrs+=f' marker-start="url(#arrow-{a["color"][1:]})"'
    if a['dashed']: attrs+=' stroke-dasharray="9 6"'
    svg.append(f'<polyline points="{points}" fill="none" {attrs}/>')
for b in boxes:
    if b['group']: continue
    x,y,w,h=b['x'],b['y'],b['w'],b['h']
    dash='stroke-dasharray="9 6"' if b['dashed'] else ''
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{b["fill"]}" stroke="{b["stroke"]}" stroke-width="2" {dash}/>')
    titley=y+(h-((b['size']+12)+len(b['lines'])*26))/2+b['size']
    svg.append(svg_text(x+w/2,titley,[b['title']],b['size'],bold=True))
    if b['lines']: svg.append(svg_text(x+w/2,titley+34,b['lines'],17.5,'#475569'))
for l in labels:
    x,y,size=l['x'],l['y'],l['size']
    if l['bg']:
        width=max(len(s) for s in l['lines'])*size*.52+14
        left=x-width/2 if l['anchor']=='middle' else x-5
        svg.append(f'<rect x="{left}" y="{y-size}" width="{width}" height="{size*1.4*len(l["lines"])+5}" rx="4" fill="white" fill-opacity="0.97"/>')
    svg.append(svg_text(x,y,l['lines'],size,l['color'],l['anchor']))
svg.append('</svg>')
(ROOT/'matchwise-stack.svg').write_text('\n'.join(svg),encoding='utf-8')

mxfile=ET.Element('mxfile',host='app.diagrams.net',agent='Codex',version='26.0.0')
diagram=ET.SubElement(mxfile,'diagram',id='matchwise-stack',name='Teljes stack')
model=ET.SubElement(diagram,'mxGraphModel',dx=str(W),dy=str(H),grid='1',gridSize='10',guides='1',tooltips='1',connect='1',arrows='1',fold='1',page='1',pageScale='1',pageWidth=str(W),pageHeight=str(H),math='0',shadow='0')
r=ET.SubElement(model,'root');ET.SubElement(r,'mxCell',id='0');ET.SubElement(r,'mxCell',id='1',parent='0')
byid={b['id']:b for b in boxes}
for b in boxes:
    value=f'<div style="font-size:{b["size"]}px;font-weight:bold;">'+e(b['title'])+'</div>'
    if b['lines']: value+='<div style="font-size:17.5px;line-height:1.4;margin-top:12px;">'+'<br>'.join(e(s) for s in b['lines'])+'</div>'
    style=f'rounded=1;whiteSpace=wrap;html=1;fillColor={b["fill"]};strokeColor={b["stroke"]};strokeWidth=2;fontFamily=Arial;fontSize=18;fontColor=#0f172a;spacing=10;'
    if b['group']: value='<b>'+e(b['title'])+'</b>';style+='fontSize=21;verticalAlign=top;align=left;container=1;collapsible=0;spacingTop=12;'
    if b['dashed']: style+='dashed=1;dashPattern=9 6;'
    cell=ET.SubElement(r,'mxCell',id=b['id'],value=value,style=style,vertex='1',parent=b['parent'])
    p=byid.get(b['parent']);x=b['x']-(p['x'] if p else 0);y=b['y']-(p['y'] if p else 0)
    ET.SubElement(cell,'mxGeometry',x=str(x),y=str(y),width=str(b['w']),height=str(b['h']),attrib={'as':'geometry'})
for a in edges:
    style=f'edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor={a["color"]};strokeWidth=2.5;endArrow=block;endFill=1;jettySize=auto;jumpStyle=arc;jumpSize=8;'
    if a['both']: style+='startArrow=block;startFill=1;'
    if a['dashed']: style+='dashed=1;dashPattern=9 6;'
    kw=dict(id=a['id'],style=style,edge='1',parent='1')
    for which,point in [('source',a['points'][0]),('target',a['points'][-1])]:
        if a[which]:
            b=byid[a[which]];kw[which]=a[which]
            prop='exit' if which=='source' else 'entry'
            style+=f'{prop}X={(point[0]-b["x"])/b["w"]};{prop}Y={(point[1]-b["y"])/b["h"]};{prop}Dx=0;{prop}Dy=0;{prop}Perimeter=0;'
    kw['style']=style;cell=ET.SubElement(r,'mxCell',**kw);g=ET.SubElement(cell,'mxGeometry',relative='1',attrib={'as':'geometry'})
    for prop,point in [('sourcePoint',a['points'][0]),('targetPoint',a['points'][-1])]: ET.SubElement(g,'mxPoint',x=str(point[0]),y=str(point[1]),attrib={'as':prop})
    if len(a['points'])>2:
        arr=ET.SubElement(g,'Array',attrib={'as':'points'})
        for x,y in a['points'][1:-1]: ET.SubElement(arr,'mxPoint',x=str(x),y=str(y))
for i,l in enumerate(labels):
    size=l['size'];width=max(len(s) for s in l['lines'])*size*.57+20;height=size*1.4*len(l['lines'])+10
    left=l['x']-width/2 if l['anchor']=='middle' else l['x']
    style=f'text;html=1;strokeColor=none;fillColor={"#ffffff" if l["bg"] else "none"};align={"center" if l["anchor"]=="middle" else "left"};verticalAlign=middle;whiteSpace=wrap;rounded=1;fontFamily=Arial;fontSize={size};fontColor={l["color"]};'
    cell=ET.SubElement(r,'mxCell',id=f'label-{i}',value='<br>'.join(e(s) for s in l['lines']),style=style,vertex='1',parent='1')
    ET.SubElement(cell,'mxGeometry',x=str(left),y=str(l['y']-size-2),width=str(width),height=str(height),attrib={'as':'geometry'})
ET.indent(mxfile)
(ROOT/'matchwise-stack.drawio').write_text(ET.tostring(mxfile,encoding='unicode'),encoding='utf-8')
(ROOT/'diagram-layout.json').write_text(json.dumps(dict(width=W,height=H,boxes=boxes,edges=edges,labels=labels),ensure_ascii=False,indent=2),encoding='utf-8')

# Structural checks cover editability, containment, references and orthogonal paths.
ids=[c.attrib['id'] for c in r.findall('mxCell')]
assert len(ids)==len(set(ids))
for b in boxes:
    if b['parent'] in byid:
        p=byid[b['parent']]
        assert p['x']<=b['x'] and p['y']<=b['y'] and b['x']+b['w']<=p['x']+p['w'] and b['y']+b['h']<=p['y']+p['h'],b['id']
for a in edges:
    for x,y in zip(a['points'],a['points'][1:]): assert x[0]==y[0] or x[1]==y[1],a['id']
ET.parse(ROOT/'matchwise-stack.drawio');ET.parse(ROOT/'matchwise-stack.svg')
print(f'Built draw.io + SVG: {len(boxes)} boxes, {sum(not a["id"].startswith("legend-") for a in edges)} connections. Structural checks passed.')
