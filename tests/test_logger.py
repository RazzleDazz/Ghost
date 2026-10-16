import unittest
import os
import json
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import log_event, LOG_FILE

class TestLogger(unittest.TestCase):
    def test_log_creation(self):
        log_event("UNIT_TEST", {"test": "passed"})
        self.assertTrue(os.path.exists(LOG_FILE))
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)
        self.assertGreaterEqual(len(logs), 1)
        self.assertEqual(logs[-1]["event"], "UNIT_TEST")

if __name__ == "__main__":
    unittest.main()
