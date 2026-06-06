import unittest

from utils import validate_trip_request


class TripValidationTests(unittest.TestCase):
    def test_valid_singapore_prompt_is_accepted(self) -> None:
        request = (
            "Plan a 4-day Singapore trip from Mumbai for two people. "
            "Mid-budget. Avoid red-eye flights. Prefer food, city views, and cultural sites. "
            "Keep hotel budget under ₹45,000."
        )

        result = validate_trip_request(request)

        self.assertTrue(result["valid"])
        self.assertEqual(result["requirements"]["origin"], "Mumbai")
        self.assertEqual(result["requirements"]["destination"], "Singapore")
        self.assertEqual(result["requirements"]["duration_days"], 4)
        self.assertEqual(result["requirements"]["traveller_count"], 2)
        self.assertEqual(result["requirements"]["hotel_budget_inr"], 45000)
        self.assertTrue(result["requirements"]["avoid_red_eye"])
        self.assertIn("food", result["requirements"]["preferences"])
        self.assertIn("views", result["requirements"]["preferences"])
        self.assertIn("culture", result["requirements"]["preferences"])

    def test_alternative_phraseology_is_still_valid(self) -> None:
        result = validate_trip_request(
            "Plan a 4 days Singapore trip from Mumbai for two travellers. "
            "Avoid redeye flights. Prefer food, city views, and cultural sites. "
            "Keep hotel budget below 45000."
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["requirements"]["duration_days"], 4)
        self.assertEqual(result["requirements"]["traveller_count"], 2)
        self.assertEqual(result["requirements"]["hotel_budget_inr"], 45000)

    def test_invalid_prompt_is_rejected(self) -> None:
        result = validate_trip_request("Plan a 3-day Dubai trip from Delhi for one person.")

        self.assertFalse(result["valid"])
        self.assertTrue(result["errors"])


if __name__ == "__main__":
    unittest.main()
