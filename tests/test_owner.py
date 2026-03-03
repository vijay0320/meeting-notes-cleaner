"""
Unit tests for owner detection.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app_v2 import detect_owner

class TestOwnerDetection:
    def test_dash_pattern(self):
        assert detect_owner("troy - blocked on API spec") == "Troy"

    def test_colon_pattern(self):
        assert detect_owner("john: finished auth module") == "John"

    def test_assigned_to(self):
        assert detect_owner("assigned to sara for review") == "Sara"

    def test_will_pattern(self):
        assert detect_owner("John will fix the bug") == "John"

    def test_team_token_devops(self):
        assert detect_owner("devops investigating pipeline") == "Devops"

    def test_team_token_marketing(self):
        assert detect_owner("marketing to finalize assets") == "Marketing"

    def test_acronym_cto(self):
        assert detect_owner("cto flagged this as critical") == "CTO"

    def test_acronym_qa(self):
        assert detect_owner("qa team regression tests failing") == "QA Team"

    def test_unassigned(self):
        assert detect_owner("pipeline broke last night") is None

    def test_unassigned_generic(self):
        assert detect_owner("budget approval needed before EOD") is None

    def test_two_word_name(self):
        result = detect_owner("product team to schedule interviews")
        assert result is not None
