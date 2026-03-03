"""
Unit tests for the priority engine (flag_priority function).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app_v2 import flag_priority

class TestHighPriority:
    def test_asap(self):
        assert flag_priority("needs to be done asap") == "high"

    def test_urgent(self):
        assert flag_priority("this is urgent") == "high"

    def test_critical(self):
        assert flag_priority("critical issue found") == "high"

    def test_blocker(self):
        assert flag_priority("this is a blocker") == "high"

    def test_eod(self):
        assert flag_priority("submit before EOD") == "high"

    def test_escalate(self):
        assert flag_priority("escalate to management") == "high"

    def test_broke(self):
        assert flag_priority("pipeline broke last night") == "high"

    def test_overdue(self):
        assert flag_priority("report is overdue") == "high"

    def test_at_risk(self):
        assert flag_priority("sprint is at risk") == "high"

    def test_expires(self):
        assert flag_priority("certificate expires in 3 days") == "high"

    def test_case_insensitive(self):
        assert flag_priority("needs it ASAP") == "high"
        assert flag_priority("CRITICAL blocker") == "high"

class TestMediumPriority:
    def test_need(self):
        assert flag_priority("need to review the code") == "medium"

    def test_review(self):
        assert flag_priority("review the pull request") == "medium"

    def test_schedule(self):
        assert flag_priority("schedule a meeting") == "medium"

    def test_pending(self):
        assert flag_priority("approval is pending") == "medium"

    def test_waiting(self):
        assert flag_priority("waiting for design team") == "medium"

    def test_sign_off(self):
        assert flag_priority("needs sign off from product") == "medium"

    def test_investigate(self):
        assert flag_priority("investigate slow queries") == "medium"

    def test_will(self):
        assert flag_priority("john will fix the bug") == "medium"

class TestLowPriority:
    def test_completed(self):
        assert flag_priority("john finished the auth module") == "low"

    def test_fyi(self):
        assert flag_priority("team offsite is next friday") == "low"

    def test_moved(self):
        assert flag_priority("retrospective moved to friday") == "low"

    def test_shared(self):
        assert flag_priority("docs uploaded to confluence") == "low"

    def test_empty_ish(self):
        assert flag_priority("standup at 10am") == "low"
