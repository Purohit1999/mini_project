import unittest

from main import DEFAULT_REQUEST, resolve_request_text


class CliDefaultRequestTests(unittest.TestCase):
    def test_empty_request_falls_back_to_default_prompt(self) -> None:
        self.assertEqual(resolve_request_text(""), DEFAULT_REQUEST)

    def test_whitespace_request_falls_back_to_default_prompt(self) -> None:
        self.assertEqual(resolve_request_text("   \n  "), DEFAULT_REQUEST)


if __name__ == "__main__":
    unittest.main()
