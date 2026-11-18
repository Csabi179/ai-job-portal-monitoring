import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("demo", Path(__file__).with_name("service-comparison-alert-test.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Tests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "grafana/provisioning/alerting/service-comparison-alerts.json"
        if not path.exists():
            path = Path(__file__).with_name("service-comparison-alerts-source.json")
        self.source = json.loads(path.read_text(encoding="utf-8"))

    def test_originals_and_expression_graph_unchanged(self):
        before = copy.deepcopy(self.source)
        result, start, end = m.build(self.source, 1000)
        self.assertEqual(self.source, before)
        self.assertEqual((start, end), (1120, 1840))
        originals = {r["uid"]: r for g in self.source["groups"] for r in g["rules"]}
        for rule in result["groups"][0]["rules"]:
            original = next(r for r in originals.values() if m.IDS[r["uid"]] == rule["uid"])
            self.assertEqual(rule["for"], original["for"])
            self.assertTrue(rule["title"].startswith("TEST | "))
            self.assertEqual(rule["labels"]["category"], "security_test")
            expected = [q for q in original["data"] if q["datasourceUid"] == "__expr__"]
            actual = [q for q in rule["data"] if q["datasourceUid"] == "__expr__"]
            self.assertEqual(actual, expected)
            self.assertNotIn("__dashboardUid__", rule["annotations"])

    def test_cleanup_can_only_delete_test_rules(self):
        ids = {r["uid"] for r in m.cleanup()["deleteRules"]}
        self.assertEqual(ids, set(m.IDS.values()))
        self.assertFalse(ids.intersection(m.IDS))
        self.assertNotIn("groups", m.cleanup())

    def test_missing_source_rejected_and_atomic_output(self):
        with self.assertRaises(ValueError):
            m.build({"groups": []}, 1000)
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            path = Path(directory) / "test.json"
            m.write_json(path, {"old": True})
            m.write_json(path, m.cleanup())
            self.assertEqual(json.loads(path.read_text()), m.cleanup())
            self.assertEqual(list(Path(directory).iterdir()), [path])

if __name__ == "__main__":
    unittest.main()
