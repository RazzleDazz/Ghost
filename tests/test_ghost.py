import unittest
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.monitor import scan_workspace

class TestGhostAgent(unittest.TestCase):
    def test_workspace_structure(self):
        self.assertTrue(os.path.exists("core/monitor.py"))
        self.assertTrue(os.path.exists("utils/mcp_stub.py"))
        self.assertTrue(os.path.exists("ghost.py"))

if __name__ == "__main__":
    unittest.main()
