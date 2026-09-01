import unittest
from datetime import date

from services.subscription_service import (
    SubscriptionService,
    calculate_subscription_expiry,
    get_subscription_status,
)


class SubscriptionServiceTests(unittest.TestCase):
    def test_registration_adds_exactly_one_year(self):
        self.assertEqual(calculate_subscription_expiry(date(2026, 9, 1)), date(2027, 9, 1))

    def test_leap_year_addition_uses_calendar_safe_date(self):
        self.assertEqual(calculate_subscription_expiry(date(2024, 2, 29)), date(2025, 2, 28))

    def test_status_is_active_when_more_than_two_days_remain(self):
        today = date(2026, 9, 1)
        expiry = date(2026, 9, 10)
        self.assertEqual(get_subscription_status(today, expiry), 'Active')

    def test_status_is_expiring_soon_within_two_days(self):
        today = date(2026, 9, 8)
        expiry = date(2026, 9, 10)
        self.assertEqual(get_subscription_status(today, expiry), 'Expiring Soon')

    def test_status_is_expired_after_due_date(self):
        today = date(2026, 9, 12)
        expiry = date(2026, 9, 10)
        self.assertEqual(get_subscription_status(today, expiry), 'Expired')

    def test_reminder_window_includes_final_two_days_before_expiry(self):
        reminder_dates = SubscriptionService.get_reminder_dates_for_window(date(2026, 9, 8), date(2026, 9, 10))
        self.assertEqual(reminder_dates, [date(2026, 9, 8), date(2026, 9, 9), date(2026, 9, 10)])

    def test_add_calendar_year_from_existing_expiry_handles_leap_year(self):
        self.assertEqual(SubscriptionService.add_calendar_years(date(2024, 2, 29), 1), date(2025, 2, 28))

    def test_add_calendar_months_clamps_to_last_valid_day(self):
        self.assertEqual(SubscriptionService.add_calendar_months(date(2024, 1, 31), 1), date(2024, 2, 29))

    def test_no_expiry_is_safe_for_quick_action_base_date(self):
        self.assertEqual(SubscriptionService.get_valid_quick_action_base(date(2025, 5, 1), None), date(2026, 5, 1))
        self.assertIsNone(SubscriptionService.get_valid_quick_action_base(None, None))
        self.assertEqual(SubscriptionService.get_valid_quick_action_base(date(2025, 5, 1), date(2026, 5, 1)), date(2026, 5, 1))


if __name__ == '__main__':
    unittest.main()
