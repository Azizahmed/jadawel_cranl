"""Public contact endpoint for the marketing site.

The static site at jadawl.site cannot send mail — it has no server. Both of its
forms previously handed the visitor a `mailto:` link, which opens whatever mail
client the browser is configured for and sends nothing at all when there isn't
one. On a phone, or for anyone on webmail, the message was simply lost.

This endpoint accepts the submission over HTTP and posts it through the same
Resend SMTP path the rest of the application uses (`docs/EMAIL_SETUP.md`).

It is the only unauthenticated, side-effecting endpoint the fork adds, so it is
also the only one that can be used to send mail on someone else's behalf. Three
things keep that in check: a per-IP rate limit, a honeypot field, and a `From`
address the caller cannot influence.
"""

import logging
import os
import secrets

from django.conf import settings
from django.core.mail import EmailMessage

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

MAX_DETAIL_ENTRIES = 20
DEFAULT_RATE = "5/hour"


def _configured_rate() -> str:
    """The throttle rate, falling back when the variable is unusable.

    ``SimpleRateThrottle`` parses its rate lazily, on the first request, so a
    typo in the environment turned every submission into a 500 rather than
    failing at boot. Validating here keeps a bad value from taking the endpoint
    down, and says so in the log.
    """

    rate = os.getenv("JADAWEL_CONTACT_FORM_RATE", "").strip()
    if not rate:
        return DEFAULT_RATE
    try:
        count, period = rate.split("/")
        int(count)
        if period[0] not in ("s", "m", "h", "d"):
            raise ValueError(period)
    except (ValueError, IndexError):
        logger.warning(
            "JADAWEL_CONTACT_FORM_RATE=%r is not a DRF rate such as '5/hour'. "
            "Falling back to %s.",
            rate,
            DEFAULT_RATE,
        )
        return DEFAULT_RATE
    return rate


def contact_recipients() -> list[str]:
    """Where submissions are delivered.

    Falls back to ``FROM_EMAIL`` so the form still reaches a human on a
    deployment that never sets the variable — that address is already required
    for outbound mail to work at all.
    """

    raw = os.getenv("JADAWEL_CONTACT_FORM_EMAIL", "") or settings.FROM_EMAIL
    return [address.strip() for address in raw.split(",") if address.strip()]


class ContactFormThrottle(SimpleRateThrottle):
    """Per-IP limit on an endpoint that sends mail for anonymous callers.

    The rate is set on the class rather than through ``DEFAULT_THROTTLE_RATES``
    because the project only installs those when
    ``JADAWEL_MAX_CONCURRENT_USER_REQUESTS`` is set (`base.py:440-447`), which
    production does not. An endpoint that relays email has to carry its own
    limit rather than inherit one that may never be configured.
    """

    scope = "arabase_contact"
    rate = _configured_rate()

    def get_cache_key(self, request: Request, view) -> str:
        # Unlike AnonRateThrottle this does not exempt authenticated users:
        # nothing about this endpoint requires an account, so an account should
        # not lift the limit.
        #
        # `get_ident` is only countable because `NUM_PROXIES` is set (`base.py`).
        # Left unset, DRF keys on the whole `X-Forwarded-For` string, which the
        # caller controls — and this endpoint sends mail, so an uncountable
        # limit here is an open relay.
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class ContactFormSerializer(serializers.Serializer):
    """Validates and bounds every field that reaches an email header or body."""

    # The releases form has no name field, the landing form requires one.
    name = serializers.CharField(
        max_length=120, required=False, allow_blank=True, trim_whitespace=True
    )
    email = serializers.EmailField(max_length=254)
    subject = serializers.CharField(max_length=200, trim_whitespace=True)
    message = serializers.CharField(max_length=5000, trim_whitespace=True)
    source = serializers.CharField(
        max_length=40, required=False, allow_blank=True, trim_whitespace=True
    )
    details = serializers.DictField(
        child=serializers.CharField(
            max_length=2000, allow_blank=True, trim_whitespace=True
        ),
        required=False,
    )
    # Honeypot. Positioned off-screen in the markup, so a human never sees it
    # and a form-filling bot almost always does.
    company = serializers.CharField(required=False, allow_blank=True)

    def validate_subject(self, value: str) -> str:
        # The subject becomes a mail header. Django raises BadHeaderError on an
        # embedded newline, which would surface as a 500, so an injection
        # attempt has to be neutralised here. Everything from the first line
        # break on is dropped rather than folded into the header: the smuggled
        # `Bcc: ...` never becomes a real header either way, but there is no
        # reason to carry it into the subject a human then reads.
        return " ".join(value.splitlines()[0].split()) if value.strip() else ""

    def validate_details(self, value: dict) -> dict:
        if len(value) > MAX_DETAIL_ENTRIES:
            raise serializers.ValidationError(
                f"No more than {MAX_DETAIL_ENTRIES} detail entries are accepted."
            )
        return value


def _build_body(data: dict, reference: str) -> str:
    lines = [f"Reference: {reference}"]
    if data.get("name"):
        lines.append(f"Name: {data['name']}")
    lines.append(f"Email: {data['email']}")
    if data.get("source"):
        lines.append(f"Sent from: {data['source']}")
    for key, value in (data.get("details") or {}).items():
        lines.append(f"{key}: {value}")
    lines += ["", data["message"]]
    return "\n".join(lines)


def send_contact_email(data: dict) -> str:
    """Queue one submission and return its reference.

    ``From`` stays ``FROM_EMAIL``. Sending as the visitor's address would fail
    SPF and DKIM at Resend — the domain is not ours to sign for — and would make
    the endpoint a spoofing tool. The visitor's address goes in ``Reply-To``
    instead, so replying from the inbox still reaches them.
    """

    reference = f"JD-{secrets.token_hex(3).upper()}"
    email = EmailMessage(
        subject=f"[{reference}] {data['subject']}",
        body=_build_body(data, reference),
        from_email=settings.FROM_EMAIL,
        to=contact_recipients(),
        reply_to=[data["email"]],
    )
    email.send(fail_silently=False)
    return reference


class ContactFormView(APIView):
    """Accepts a message from the marketing site and emails it onward."""

    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ContactFormThrottle,)

    @extend_schema(
        tags=["Jadawel"],
        operation_id="arabase_contact_form",
        request=ContactFormSerializer,
        description=(
            "Accepts a contact or bug-report submission from the public website "
            "and delivers it by email. Unauthenticated and rate limited per IP. "
            "Returns the reference that appears in the email subject."
        ),
        responses={200: None, 400: None, 429: None, 503: None},
    )
    def post(self, request: Request) -> Response:
        serializer = ContactFormSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data.get("company"):
            # Answer exactly as a success would, so a bot gets no signal about
            # which of its fields gave it away.
            logger.info("Discarded a contact submission that filled the honeypot.")
            return Response({"reference": f"JD-{secrets.token_hex(3).upper()}"})

        try:
            reference = send_contact_email(data)
        except Exception:
            # Queueing is what fails here — the SMTP conversation happens later
            # in the worker. Report it rather than confirming a message that was
            # never accepted, so the visitor knows to use the address directly.
            logger.exception("Could not queue a contact form submission.")
            return Response(
                {"error": "ERROR_CONTACT_FORM_NOT_SENT"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Deliberately without the address or the message body: this is a public
        # endpoint and its log line should not become a store of personal data.
        logger.info(
            "Contact submission %s queued from %s.",
            reference,
            data.get("source") or "unknown",
        )
        return Response({"reference": reference})
