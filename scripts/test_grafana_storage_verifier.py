import copy
import importlib.util
import json
from pathlib import Path
import sqlite3
import unittest

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('verify',HERE/'verify-provisioned-dashboards.py')
verify=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(verify)

def model():
    return {'uid':'sample','title':'Sample HU','panels':[{'id':1,'type':'stat','title':'CPU','gridPos':{'x':0,'y':0,'w':6,'h':4},'datasource':{'uid':'prometheus','type':'prometheus'},'targets':[{'refId':'A','expr':'vector(1)'}]}]}

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.c=sqlite3.connect(':memory:')
        self.addCleanup(self.c.close)
        self.c.execute('CREATE TABLE dashboard (uid TEXT,data TEXT)')
        self.c.execute('CREATE TABLE resource ("group" TEXT,resource TEXT,namespace TEXT,name TEXT,value TEXT,action INTEGER)')

    def legacy(self,d):
        self.c.execute('INSERT INTO dashboard VALUES (?,?)',(d['uid'],json.dumps(d)))

    def current(self,d,namespace='default',name=None,api='v0alpha1',group='dashboard.grafana.app',resource='dashboards',action=2,deleted=False):
        uid=name or d['uid']
        obj={'apiVersion':'dashboard.grafana.app/'+api,'kind':'Dashboard','metadata':{'name':uid,'namespace':namespace},'spec':d}
        if deleted: obj['metadata']['deletionTimestamp']='2026-11-19T00:00:00Z'
        self.c.execute('INSERT INTO resource VALUES (?,?,?,?,?,?)',(group,resource,namespace,uid,json.dumps(obj),action))

    def disallow_legacy_reads(self):
        self.c.set_authorizer(lambda op,table,*args: sqlite3.SQLITE_DENY if op==sqlite3.SQLITE_READ and table=='dashboard' else sqlite3.SQLITE_OK)

    def test_current_unified_model_wins_over_stale_legacy_without_reading_it(self):
        d=model();stale=copy.deepcopy(d);stale['title']='Old title'
        self.legacy(stale);self.current(d);self.disallow_legacy_reads()
        source,actual=verify.read_models(self.c,['sample'])
        self.assertIn('unified.resource',source)
        self.assertTrue(verify.matches(actual['sample'],d))

    def test_fresh_legacy_cannot_mask_wrong_current_expression(self):
        d=model();stale=copy.deepcopy(d);stale['panels'][0]['targets'][0]['expr']='vector(0)'
        self.legacy(d);self.current(stale);self.disallow_legacy_reads()
        _,actual=verify.read_models(self.c,['sample'])
        self.assertFalse(verify.matches(actual['sample'],d))

    def test_missing_current_dashboard_does_not_fall_back_to_legacy(self):
        self.legacy(model());self.disallow_legacy_reads()
        _,actual=verify.read_models(self.c,['sample'])
        self.assertEqual(actual,{})

    def test_foreign_org_and_other_resource_types_are_not_accepted(self):
        d=model();self.current(d,namespace='org-2');self.current(d,group='other.example');self.current(d,resource='folders')
        _,actual=verify.read_models(self.c,['sample'])
        self.assertEqual(actual,{})

    def test_classic_spec_wrappers_and_org_one_alias(self):
        for api in ('v0alpha1','v1beta1','v1'):
            self.c.execute('DELETE FROM resource')
            d=model();self.current(d,namespace='org-1',api=api)
            _,actual=verify.read_models(self.c,['sample'])
            self.assertTrue(verify.matches(actual['sample'],d))

    def test_storage_key_and_wrapped_identity_must_agree(self):
        obj={'apiVersion':'dashboard.grafana.app/v1','kind':'Dashboard','metadata':{'name':'wrong','namespace':'default'},'spec':model()}
        self.c.execute('INSERT INTO resource VALUES (?,?,?,?,?,?)',('dashboard.grafana.app','dashboards','default','sample',json.dumps(obj),2))
        with self.assertRaises(verify.UnsupportedStorage): verify.read_models(self.c,['sample'])

    def test_deleted_resources_are_not_current_dashboards(self):
        for action,deleted in [(3,False),(2,True)]:
            self.c.execute('DELETE FROM resource');self.current(model(),action=action,deleted=deleted)
            _,actual=verify.read_models(self.c,['sample']);self.assertEqual(actual,{})

    def test_unhandled_v2_schema_is_explicitly_rejected_not_accepted(self):
        obj={'apiVersion':'dashboard.grafana.app/v2','kind':'Dashboard','metadata':{'name':'sample','namespace':'default'},'spec':{'title':'Sample HU','elements':{},'layout':{}}}
        self.c.execute('INSERT INTO resource VALUES (?,?,?,?,?,?)',('dashboard.grafana.app','dashboards','default','sample',json.dumps(obj),2))
        with self.assertRaises(verify.UnsupportedStorage): verify.read_models(self.c,['sample'])

    def test_migration_marker_prevents_legacy_only_false_success(self):
        self.c.execute('DROP TABLE resource');self.c.execute('CREATE TABLE unifiedstorage_migration_log (id TEXT)');self.legacy(model())
        with self.assertRaises(verify.UnsupportedStorage): verify.read_models(self.c,['sample'])

    def test_diagnostic_names_difference_without_printing_expression(self):
        d=model();actual=copy.deepcopy(d);actual['panels'][0]['targets'][0]['expr']='private-placeholder-value'
        message=';'.join(verify.differences(actual,d))
        self.assertIn('panel 1/A: expression differs',message)
        self.assertNotIn('private-placeholder-value',message)

    def test_pre_unified_schema_retains_legacy_read_support(self):
        self.c.execute('DROP TABLE resource');d=model();self.legacy(d)
        source,actual=verify.read_models(self.c,['sample'])
        self.assertIn('legacy.dashboard',source);self.assertTrue(verify.matches(actual['sample'],d))

    def test_preparation_uses_the_current_pinned_verifier_revision(self):
        shell=(HERE/'install-bilingual-dashboards.sh').read_text(encoding='utf-8')
        self.assertIn('git show "$ref:scripts/install-dashboard-final-audit.sh"',shell)
        self.assertIn('bash "$stage/prepare.sh" "$ref"',shell)
        self.assertNotIn('git show "$preparation:scripts/install-dashboard-final-audit.sh"',shell)

if __name__=='__main__': unittest.main()
