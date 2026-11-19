#!/usr/bin/env python3
"""Check separate HU/English identities and identical measurement semantics."""
import argparse
import importlib.util
import json
from pathlib import Path
import re

def load_module(root):
    spec=importlib.util.spec_from_file_location('audit',root/'check-dashboard-final-audit.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def walk(panels):
    for p in panels:
        yield p
        yield from walk(p.get('panels',[]))

def ui_strings(value):
    if isinstance(value,str): yield value
    elif isinstance(value,list):
        for v in value: yield from ui_strings(v)
    elif isinstance(value,dict):
        for k,v in value.items():
            if k!='expr': yield from ui_strings(v)

def validate(root):
    audit=load_module(root)
    manifest=json.loads((root/'dashboard-language-manifest.json').read_text(encoding='utf-8'))['dashboards']
    assert len(manifest)==4 and len({d['uid'] for d in manifest})==4
    models={d['file']:json.loads((root/d['file']).read_text(encoding='utf-8')) for d in manifest}
    for item in manifest:
        d=models[item['file']]
        assert d['uid']==item['uid'] and d['title']==item['title'] and len(d['uid'])<=40
        assert d['title'].endswith(' HU')==(item['language']=='hu')
        audit.validate_layout(d['panels'])
    for kind,filename,en_title in [('unified','matchwise-unified-monitoring.json','MatchWise | Unified Monitoring'),('comparison','matchwise-service-comparison.json','MatchWise · Service Comparison')]:
        hu=models[filename];en=models[filename.replace('.json','-en.json')]
        assert en['title']==en_title and en['uid']==hu['uid']+'-en'
        h={p['id']:p for p in walk(hu['panels'])};e={p['id']:p for p in walk(en['panels'])}
        assert len(h)==len(list(walk(hu['panels']))) and len(e)==len(list(walk(en['panels'])))
        assert set(h)==set(e)
        assert hu['time']==en['time'] and hu['refresh']==en['refresh']=='1m'
        hv={v['name']:v for v in hu['templating']['list']};ev={v['name']:v for v in en['templating']['list']}
        assert set(hv)==set(ev)
        for key,v in hv.items():
            other=ev[key]
            for attr in ('type','datasource','regex','multi','includeAll'):
                assert v.get(attr)==other.get(attr)
            assert v.get('current',{}).get('value')==other.get('current',{}).get('value')
            assert [(o['value'],o.get('selected')) for o in v.get('options',[])]==[(o['value'],o.get('selected')) for o in other.get('options',[])]
            if v['type']=='query': assert v['query']==other['query'] and v['definition']==other['definition']
        for pid,p in h.items():
            q=e[pid]
            for key in ('type','gridPos','collapsed','datasource'):
                assert p.get(key)==q.get(key),(kind,pid,key)
            pt=p.get('targets',[]);qt=q.get('targets',[])
            assert len(pt)==len(qt)
            for a,b in zip(pt,qt):
                for key in ('refId','expr','datasource','instant','range','queryType','format'):
                    assert a.get(key)==b.get(key),(kind,pid,key)
                assert audit.expand(a['expr'],hu)==audit.expand(b['expr'],en),(kind,pid,'expanded query differs')
            f=p.get('fieldConfig',{}).get('defaults',{});g=q.get('fieldConfig',{}).get('defaults',{})
            for key in ('min','max','decimals','thresholds'): assert f.get(key)==g.get(key)
            if f.get('unit')!=g.get('unit'):
                assert f['unit'].startswith('suffix:') and g['unit'].startswith('suffix:')
        leftovers=[s for s in ui_strings(en) if re.search('[áéíóöőúüűÁÉÍÓÖŐÚÜŰ]',s)]
        assert not leftovers,('Untranslated UI',leftovers[:2])
        assert any('/d/'+en['uid']+'/' in l.get('url','') for l in hu['links'])
        assert any('/d/'+hu['uid']+'/' in l.get('url','') for l in en['links'])
        # Every English panel/text data link stays in English; only the explicit switch leads to HU.
        for s in ui_strings(en['panels']):
            assert '/d/matchwise-unified-overview/' not in s and '/d/matchwise-service-comparison/' not in s
        if kind=='unified':
            assert e[66]['options']['sortBy'][0]['displayName']=='Requests'
            assert e[66]['transformations'][-1]['options']['renameByName']=={'method':'Method','route':'Route'}
            assert any(o['matcher'].get('options')=='Route' for o in e[66]['fieldConfig']['overrides'])
        else:
            assert not ({58,60}&set(e)) and e[61]['collapsed']
        print(kind+': HU/English parity PASS; '+str(len(h))+' panels; expressions, expanded queries, defaults and layout agree.')
    print('PASS: four distinct dashboards; HU suffixes; English base names; localized UI and data links.')
    return models

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args();models=validate(args.directory)
    if args.live: return int(load_module(args.directory).query_all(models,True))
    return 0

if __name__=='__main__': raise SystemExit(main())
