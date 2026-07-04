import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from app.analyzer import DISCLAIMER, rule_based_analysis
from app.api import require_admin
from app.collector import event_payload, save_event_with_analysis
from app.config import Settings
from app.extract import clean_html, extract_tickers, match_themes
from app.storage import connect, init_db


class CoreTests(unittest.TestCase):
    def test_clean_html_and_tickers(self):
        text = clean_html("<html><script>x()</script><body>公司 600519 净利润增长 12.5%</body></html>")
        self.assertIn("600519", text)
        self.assertIn("净利润增长", text)
        self.assertEqual(extract_tickers(text), ["600519"])

    def test_theme_matching(self):
        themes = [{"name": "新能源", "keywords": ["储能", "光伏"]}]
        self.assertEqual(match_themes("公司储能业务增长", themes), ["新能源"])

    def test_rule_analysis_contains_required_fields(self):
        result = rule_based_analysis({"title": "年报业绩增长", "body": "净利润增长 20%，但提示监管风险。", "trust_level": "official"})
        data = result.as_dict()
        self.assertIn("importance_score", data)
        self.assertIn("risk_score", data)
        self.assertEqual(data["disclaimer"], DISCLAIMER)
        self.assertGreaterEqual(data["importance_score"], 0)
        self.assertLessEqual(data["importance_score"], 100)

    def test_save_event_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "test.db")
            init_db(conn)
            settings = Settings(Path(tmp) / "test.db", 180, "", "test-model", "test-agent", "", [])
            source = dict(conn.execute("SELECT * FROM sources WHERE id = 'pbc'").fetchone())
            event = event_payload(source, "央行政策新闻", "政策支持实体经济，提示风险。", source["url"])
            self.assertTrue(save_event_with_analysis(conn, event, settings))
            self.assertFalse(save_event_with_analysis(conn, event, settings))
            row = conn.execute("SELECT tickers, themes FROM events LIMIT 1").fetchone()
            json.loads(row["tickers"])
            json.loads(row["themes"])
            conn.close()

    def test_admin_token_required_when_configured(self):
        settings = Settings(Path("test.db"), 180, "", "test-model", "test-agent", "secret", [])
        with self.assertRaises(HTTPException) as context:
            require_admin("", settings)
        self.assertEqual(context.exception.status_code, 401)
        self.assertIsNone(require_admin("secret", settings))


if __name__ == "__main__":
    unittest.main()
