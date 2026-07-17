import json
import os
import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException

from routers.commercial import (
    AccessPayload,
    LeadPayload,
    commercial_config,
    create_access,
    create_lead,
    verify_access_token,
)
from routers.players import _deepseek_review, player_review


FALLBACK_REVIEW = {
    "headline": "Fallback review",
    "score": 60,
    "summary": "Deterministic review",
    "sections": [
        {
            "title": "Priority",
            "finding": "Finding",
            "evidence": "Evidence",
            "action": "Action",
        }
    ],
    "weekly_plan": [
        {
            "day": "Day 1",
            "focus": "Focus",
            "task": "Task",
            "metric": "Metric",
        }
    ],
    "priority_matches": [],
    "model_note": "Deterministic fallback",
}


class CommercialReviewTests(unittest.TestCase):
    def test_commercial_config_reports_only_configured_capabilities(self):
        env = {
            "DOTASENSE_CHECKOUT_REVIEW_URL": "https://checkout.example/review",
            "DOTASENSE_PRO_ACCESS_CODE": "test-code",
        }
        with patch.dict(os.environ, env, clear=True):
            config = commercial_config()

        plans = {plan["key"]: plan for plan in config["plans"]}
        self.assertTrue(plans["review"]["checkout_configured"])
        self.assertFalse(plans["founder"]["checkout_configured"])
        self.assertTrue(config["access_code_configured"])
        self.assertFalse(config["webhook_configured"])

    def test_access_code_issues_account_bound_token(self):
        env = {
            "DOTASENSE_PRO_ACCESS_CODE": "test-code",
            "DOTASENSE_ACCESS_SECRET": "test-secret",
        }
        with patch.dict(os.environ, env, clear=True):
            issued = create_access(AccessPayload(code="test-code", account_id=42, plan="review"))
            verified = verify_access_token(issued["access_token"], account_id=42)
            wrong_account = verify_access_token(issued["access_token"], account_id=43)

        self.assertTrue(issued["ok"])
        self.assertEqual(issued["plan"], "review")
        self.assertEqual(verified["account_id"], 42)
        self.assertIsNone(wrong_account)

    def test_access_code_rejects_invalid_value(self):
        with patch.dict(os.environ, {"DOTASENSE_PRO_ACCESS_CODE": "expected"}, clear=True):
            with self.assertRaises(HTTPException) as raised:
                create_access(AccessPayload(code="wrong"))

        self.assertEqual(raised.exception.status_code, 401)

    @patch("routers.commercial._send_webhook", return_value=False)
    @patch("routers.commercial._append_lead")
    def test_lead_uses_manual_contact_without_checkout(self, append_lead, _send_webhook):
        with patch.dict(os.environ, {}, clear=True):
            result = create_lead(LeadPayload(contact="test@example.com", plan="review"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["next_step"], "manual_contact")
        self.assertEqual(result["checkout_url"], "")
        append_lead.assert_called_once()

    def test_paid_review_rejects_missing_access_token(self):
        with patch.dict(os.environ, {"DOTASENSE_ACCESS_SECRET": "test-secret"}, clear=True):
            with self.assertRaises(HTTPException) as raised:
                player_review(account_id=42, request_payload={}, authorization=None)

        self.assertEqual(raised.exception.status_code, 402)

    @patch("routers.players._fallback_review", return_value=FALLBACK_REVIEW)
    @patch("routers.players._player_dashboard_payload", return_value={"warnings": []})
    def test_paid_review_falls_back_when_deepseek_is_not_configured(self, _payload, _fallback):
        env = {
            "DOTASENSE_PRO_ACCESS_CODE": "test-code",
            "DOTASENSE_ACCESS_SECRET": "test-secret",
        }
        with patch.dict(os.environ, env, clear=True):
            issued = create_access(AccessPayload(code="test-code", account_id=42, plan="review"))
            result = player_review(
                account_id=42,
                request_payload={"access_token": issued["access_token"]},
                authorization=None,
            )

        self.assertFalse(result["locked"])
        self.assertEqual(result["source"], "deterministic_fallback")
        self.assertEqual(result["review"], FALLBACK_REVIEW)
        self.assertIn("DEEPSEEK_API_KEY is not configured", result["warnings"])

    @patch("routers.players.requests.post")
    def test_deepseek_response_is_normalized(self, post):
        response = Mock(status_code=200)
        response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "headline": "AI review",
                                "score": 75,
                                "summary": "Evidence-based summary",
                                "sections": FALLBACK_REVIEW["sections"],
                                "weekly_plan": FALLBACK_REVIEW["weekly_plan"],
                                "priority_matches": [],
                            }
                        )
                    }
                }
            ]
        }
        post.return_value = response

        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}, clear=True):
            generated, warning = _deepseek_review({}, FALLBACK_REVIEW)

        self.assertIsNone(warning)
        self.assertEqual(generated["headline"], "AI review")
        self.assertEqual(generated["score"], 75)
        call = post.call_args
        self.assertEqual(call.args[0], "https://api.deepseek.com/chat/completions")
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(call.kwargs["json"]["response_format"], {"type": "json_object"})


if __name__ == "__main__":
    unittest.main()
