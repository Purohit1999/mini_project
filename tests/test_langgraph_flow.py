import os
import unittest

from langgraph_flow import run_langgraph_pipeline
from main import DEFAULT_REQUEST


class LangGraphFlowTests(unittest.TestCase):
    def test_langgraph_offline_pipeline_returns_final_output(self) -> None:
        result = run_langgraph_pipeline(DEFAULT_REQUEST, demo_mode="offline")

        self.assertEqual(result["status"], "complete")
        self.assertIn("final_output", result)
        self.assertIn("final_itinerary", result["final_output"])
        self.assertTrue(result.get("markdown_path"))

    def test_langgraph_pipeline_rejects_invalid_requests(self) -> None:
        result = run_langgraph_pipeline("Plan a 3-day Dubai trip from Delhi for one person.", demo_mode="offline")

        self.assertEqual(result["status"], "error")
        self.assertTrue(result["validation_errors"])


if __name__ == "__main__":
    unittest.main()
