import unittest
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.net_checker import check_loopback

class TestNetChecker(unittest.TestCase):
    def test_net_checker_runs(self):
        try:
            check_loopback()
            success = True
        except Exception:
            success = False
        self.assertTrue(success)

if __name__ == "__main__":
    unittest.main()
