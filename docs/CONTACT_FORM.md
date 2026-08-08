# Website contact form

The marketing site has two forms: *contact us* on the landing page and *report
a bug* on the releases page. Both now deliver to `info@jadawl.site` and show
the visitor a confirmation with a reference number.

## What was wrong

Both forms handed the visitor a `mailto:` link built from their own answers:

```js
window.location.href = `mailto:info@jadawl.site?subject=…&body=…`;
```

That does not send anything. It asks the browser to open a mail client, and
then relies on the visitor noticing the draft and pressing send themselves. On
a phone, or for anyone using webmail rather than a desktop client, nothing
happens at all — the click appears to do nothing and the message is lost.

The releases form was worse than the landing form: it showed
*"وصلنا بلاغك"* with a ticket number generated from `Date.now()` **before**
handing over the `mailto:`, so the visitor was told their report had been
received when nothing had left the browser and the number corresponded to
nothing.

## How it works now

`jadawl.site` is a static site with no server, so the browser posts to the
application instead:

```
POST https://app.jadawl.site/api/arabase/contact/
```

The endpoint validates the submission and sends it by email through the same
Resend SMTP path everything else uses (`docs/EMAIL_SETUP.md`). It answers with
a reference, which the browser shows to the visitor and which also appears in
the email subject — so quoting it back actually locates the message.

| Piece | Location |
|---|---|
| Endpoint, validation, throttle | `backend/src/arabase/api/contact.py` |
| Route | `backend/src/arabase/api/urls.py` |
| Browser side, both forms | `website/site-logic.js` |
| Tests | `backend/tests/arabase/test_contact.py` |

Cross-origin works because the site and the app are different hosts and
`CORS_ORIGIN_ALLOW_ALL` is true (`base.py:467`); a preflight to the app
returns `Access-Control-Allow-Origin: *` with `content-type` permitted.

### Request

`email`, `subject` and `message` are required; `name`, `source` and `details`
are optional. `details` is a flat string map — anything a form collects beyond
the named fields is forwarded as a labelled line, so a new field can be added
to the markup without touching the backend.

```json
{
  "name": "سارة",
  "email": "sara@example.com",
  "subject": "سؤال عن الأسعار",
  "message": "كم سعر الخطة السنوية؟",
  "source": "landing",
  "details": {"Severity": "blocking", "Version": "v0.9.4"}
}
```

Responses are `200 {"reference": "JD-A1B2C3"}`, `400` on validation, `429` when
rate limited, and `503` when the message could not be queued.

## Why it cannot be used to send mail as someone else

This is the only unauthenticated endpoint in the fork with a side effect, and
the side effect is *sending email*. Four things bound it:

- **`From` is always `FROM_EMAIL`.** The visitor's address goes in `Reply-To`,
  never in `From`. Sending as the visitor's domain would fail SPF and DKIM at
  Resend — those domains are not ours to sign for — and would turn the endpoint
  into a spoofing tool. Replying from the inbox still reaches them.
- **The recipient is not caller-controlled.** It comes from configuration, so
  the endpoint can only ever deliver to us. It is a contact form, not a relay.
- **Rate limited per IP**, 5/hour by default. The limit is set on the throttle
  class rather than in `DEFAULT_THROTTLE_RATES`, because the project only
  installs those when `JADAWEL_MAX_CONCURRENT_USER_REQUESTS` is set
  (`base.py:440-447`) and production does not set it. An endpoint that sends
  mail must not depend on a limit that may never be configured.
- **Honeypot.** A `company` field sits off-screen in the markup. A human never
  sees it; a form-filling bot usually does. When it arrives filled, the
  response is byte-for-byte a success and nothing is sent, so the bot gets no
  signal about which field gave it away.

Two smaller ones: newlines are collapsed out of the subject before it becomes
a mail header, which turns a header-injection attempt into ordinary text rather
than the `BadHeaderError` 500 Django would otherwise raise; and every field is
length-bounded, so a submission cannot be used to post megabytes.

The log line carries the reference and the source, deliberately **not** the
address or the message body — a public endpoint's logs should not accumulate
personal data.

### The limit of IP throttling

`get_ident` derives the client from `X-Forwarded-For`, which a determined
sender can rotate. The honeypot and the fixed recipient are what make that
uninteresting: the worst outcome is noise in one inbox, not mail sent to third
parties in our name. If noise does become a problem, the next step is a
captcha — the project already carries `JADAWEL_ENABLE_CAPTCHA` — rather than a
tighter IP limit.

## Configuration

Both are optional; the defaults are correct for this deployment.

| Variable | Default | Notes |
|---|---|---|
| `JADAWEL_CONTACT_FORM_EMAIL` | `FROM_EMAIL` | Comma-separated for several recipients. |
| `JADAWEL_CONTACT_FORM_RATE` | `5/hour` | DRF rate syntax, per IP. |

The default is deliberate: `FROM_EMAIL` is already `info@jadawl.site` and is
required for outbound mail to work at all, so the form reaches a human even on
a deployment that sets nothing.

## Deploying — order matters

**The backend change does not ship by pushing.** The root `Dockerfile` pulls a
published image rather than building the monorepo (`AGENTS.md`), so the
endpoint only exists once the image is republished:

1. Run the *Publish all-in-one image* workflow.
2. Bump `ARG JADAWEL_IMAGE` and redeploy the `jadawel` app.
3. Confirm the endpoint answers — a bare `POST` should give `400`, not `404`:

   ```
   curl -i -X POST https://app.jadawl.site/api/arabase/contact/ \
        -H 'Content-Type: application/json' -d '{}'
   ```

4. **Only then** deploy the `jadawl_website` app.

Deploying the website first would point both forms at a route that returns
`404`, and every visitor would see the failure message. That is worse than the
`mailto:` behaviour it replaces, so the order is not optional.

## Verifying

After both are deployed, submit the landing form and check three things: the
confirmation names a `JD-` reference, an email arrives at `info@jadawl.site`
with that reference in the subject, and **replying to it goes to the visitor**
rather than back to ourselves. The third is the one worth checking by hand,
because a broken `Reply-To` looks completely fine until someone tries to answer
a customer.
