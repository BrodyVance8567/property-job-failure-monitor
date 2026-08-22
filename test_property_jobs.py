from datetime import date
import unittest

from property_jobs import (
    InspectionReminder,
    MaintenanceRequest,
    TenantDocument,
    needs_attention,
    run_property_job,
)


class PropertyJobDecisionTest(unittest.TestCase):
    def test_expired_tenant_document_marks_job_for_attention(self):
        request = MaintenanceRequest("MR-1", "Oak House", "Leaking tap", "low")
        document = TenantDocument("TEN-1", "lease", date(2026, 8, 9))
        reminder = InspectionReminder("Oak House", date(2026, 8, 20))

        self.assertTrue(needs_attention(request, document, reminder, date(2026, 8, 10)))
        self.assertEqual(
            run_property_job(request, document, reminder, today=date(2026, 8, 10)),
            "attention_required",
        )
