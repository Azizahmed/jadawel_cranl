from unittest.mock import patch

from django.core import mail
from django.shortcuts import reverse

import pytest
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from arabase.api.contact import ContactFormSerializer, contact_recipients

VALID = {
    "name": "سارة",
    "email": "sara@example.com",
    "subject": "سؤال عن الأسعار",
    "message": "كم سعر الخطة السنوية؟",
    "source": "landing",
}


@pytest.fixture(autouse=True)
def _clear_throttle_history():
    """Each test starts with a fresh rate-limit bucket.

    The throttle keys on the client IP, which the test client keeps constant,
    so without this the fifth test in a module would start seeing 429s.
    """

    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestContactForm:
    def _url(self):
        return reverse("api:arabase.api:contact_form")

    def test_sends_the_message(self, api_client):
        response = api_client.post(self._url(), VALID, format="json")

        assert response.status_code == HTTP_200_OK
        assert response.json()["reference"].startswith("JD-")
        assert len(mail.outbox) == 1

    def test_puts_the_reference_in_the_subject(self, api_client):
        response = api_client.post(self._url(), VALID, format="json")

        assert mail.outbox[0].subject == (
            f"[{response.json()['reference']}] سؤال عن الأسعار"
        )

    def test_replies_go_to_the_visitor_not_the_from_address(self, api_client, settings):
        settings.FROM_EMAIL = "info@jadawl.site"

        api_client.post(self._url(), VALID, format="json")

        message = mail.outbox[0]
        # The From must stay ours: Resend signs for jadawl.site and nothing else,
        # so sending as the visitor would fail SPF and enable spoofing.
        assert message.from_email == "info@jadawl.site"
        assert message.reply_to == ["sara@example.com"]

    def test_delivers_to_the_configured_recipient(self, api_client, monkeypatch):
        monkeypatch.setenv("JADAWEL_CONTACT_FORM_EMAIL", "info@jadawl.site")

        api_client.post(self._url(), VALID, format="json")

        assert mail.outbox[0].to == ["info@jadawl.site"]

    def test_body_carries_the_sender_and_the_message(self, api_client):
        api_client.post(self._url(), VALID, format="json")

        body = mail.outbox[0].body
        assert "sara@example.com" in body
        assert "كم سعر الخطة السنوية؟" in body

    def test_includes_the_detail_entries(self, api_client):
        payload = {
            **VALID,
            "details": {"Severity": "blocking", "Version": "v0.9.4"},
        }

        api_client.post(self._url(), payload, format="json")

        body = mail.outbox[0].body
        assert "Severity: blocking" in body
        assert "Version: v0.9.4" in body

    def test_needs_no_authentication(self, api_client):
        # No credentials are set on the client at all.
        assert api_client.post(self._url(), VALID, format="json").status_code == (
            HTTP_200_OK
        )


@pytest.mark.django_db
class TestValidation:
    def _url(self):
        return reverse("api:arabase.api:contact_form")

    def test_rejects_a_malformed_address(self, api_client):
        response = api_client.post(
            self._url(), {**VALID, "email": "not-an-address"}, format="json"
        )

        assert response.status_code == HTTP_400_BAD_REQUEST
        assert mail.outbox == []

    def test_rejects_a_missing_message(self, api_client):
        payload = {key: value for key, value in VALID.items() if key != "message"}

        response = api_client.post(self._url(), payload, format="json")

        assert response.status_code == HTTP_400_BAD_REQUEST

    def test_rejects_an_oversized_message(self, api_client):
        response = api_client.post(
            self._url(), {**VALID, "message": "x" * 5001}, format="json"
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

    def test_rejects_too_many_detail_entries(self, api_client):
        details = {f"key{index}": "value" for index in range(21)}

        response = api_client.post(
            self._url(), {**VALID, "details": details}, format="json"
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

    def test_collapses_a_newline_in_the_subject(self):
        serializer = ContactFormSerializer(
            data={**VALID, "subject": "Hello\nBcc: victim@example.com"}
        )

        assert serializer.is_valid()
        assert "\n" not in serializer.validated_data["subject"]

    def test_a_header_injection_attempt_sends_one_message(self, api_client):
        api_client.post(
            self._url(),
            {**VALID, "subject": "Hi\nBcc: victim@example.com"},
            format="json",
        )

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == contact_recipients()
        assert "victim@example.com" not in str(mail.outbox[0].subject)


@pytest.mark.django_db
class TestAbuseControls:
    def _url(self):
        return reverse("api:arabase.api:contact_form")

    def test_honeypot_reports_success_but_sends_nothing(self, api_client):
        response = api_client.post(
            self._url(), {**VALID, "company": "Acme Corp"}, format="json"
        )

        # Indistinguishable from a real success, so a bot learns nothing.
        assert response.status_code == HTTP_200_OK
        assert response.json()["reference"].startswith("JD-")
        assert mail.outbox == []

    def test_an_empty_honeypot_is_a_normal_submission(self, api_client):
        response = api_client.post(self._url(), {**VALID, "company": ""}, format="json")

        assert response.status_code == HTTP_200_OK
        assert len(mail.outbox) == 1

    def test_rate_limits_a_repeated_sender(self, api_client):
        for _ in range(5):
            assert api_client.post(self._url(), VALID, format="json").status_code == (
                HTTP_200_OK
            )

        response = api_client.post(self._url(), VALID, format="json")

        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS
        assert len(mail.outbox) == 5


@pytest.mark.django_db
class TestFailure:
    def _url(self):
        return reverse("api:arabase.api:contact_form")

    @patch(
        "arabase.api.contact.EmailMessage.send",
        side_effect=OSError("redis is unreachable"),
    )
    def test_reports_a_queue_failure_instead_of_confirming(self, _send, api_client):
        response = api_client.post(self._url(), VALID, format="json")

        assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["error"] == "ERROR_CONTACT_FORM_NOT_SENT"


class TestRecipients:
    def test_splits_a_comma_separated_list(self, monkeypatch):
        monkeypatch.setenv("JADAWEL_CONTACT_FORM_EMAIL", "a@x.com, b@x.com")

        assert contact_recipients() == ["a@x.com", "b@x.com"]

    def test_falls_back_to_the_from_address(self, monkeypatch, settings):
        monkeypatch.delenv("JADAWEL_CONTACT_FORM_EMAIL", raising=False)
        settings.FROM_EMAIL = "info@jadawl.site"

        assert contact_recipients() == ["info@jadawl.site"]
