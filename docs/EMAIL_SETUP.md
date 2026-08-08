# Email setup

Password reset, workspace invitations and notification emails are all dead in
production right now. No `EMAIL_SMTP*` variable is set, so
`CELERY_EMAIL_BACKEND` falls back to the console backend
(`jadawel/config/settings/base.py:1007-1031`): every message is printed to the
worker's stdout and discarded. The reset flow is the worst of these — the UI
reports success and no mail ever arrives, so a locked-out user has no recovery
path at all.

## What `jadawl.site` can do today

Checked against live DNS:

| Record | Value | Meaning |
|---|---|---|
| MX | `eforward1-5.registrar-servers.com` | Namecheap **free email forwarding**. |
| TXT | `v=spf1 include:spf.efwd.registrar-servers.com ~all` | Authorises the forwarder only. |
| `_dmarc` | *absent* | No DMARC policy. |

Email forwarding **receives and forwards; it cannot send**. There is no
outbound SMTP credential to find, because the current setup never had one.
`info@jadawl.site` works as the `From` address, but only once a sending
provider is authorised for the domain.

## Choosing a sender

| Option | Where credentials come from | Notes |
|---|---|---|
| **Namecheap Private Email** | Mailbox password, SMTP at `mail.privateemail.com:465` | Lowest friction: the domain is already there, and `info@jadawl.site` becomes a real mailbox instead of a forward. Replaces the forwarding MX records. Sending limits suit a launch, not a campaign. |
| **Amazon SES** (`me-south-1` Bahrain, `me-central-1` UAE) | Console → SES → *Create SMTP credentials* | Best throughput and bounce handling. Starts in a sandbox; production access takes ~24h. Nearest regions are Gulf, not Saudi. |
| **Resend / Postmark / Mailgun** | Dashboard → API keys | Good deliverability, US/EU only. |

A note on residency: transactional mail carries user addresses and reset
tokens, so a non-Saudi sender means that metadata leaves the country even
though the database does not. It is a weaker constraint than it looks —
messages reach Gmail and Outlook mailboxes regardless — but it is worth
deciding deliberately rather than by default.

## DNS records to add

Whichever provider is chosen, mail lands in spam without these. The domain is
registered at Namecheap, so they are added in the Namecheap DNS panel.

1. **SPF** — extend the existing record, do not replace it, or forwarding
   breaks. One TXT record only; two SPF records is itself a failure:

   ```
   v=spf1 include:spf.efwd.registrar-servers.com include:<provider> ~all
   ```

2. **DKIM** — the CNAME or TXT records the provider generates during domain
   verification.

3. **DMARC** — none exists. Start in monitor mode so nothing is rejected while
   the setup is validated:

   ```
   _dmarc.jadawl.site  TXT  "v=DMARC1; p=none; rua=mailto:info@jadawl.site"
   ```

## Application configuration

Set on the app in the CranL dashboard, then reload it. The variables are read
at `base.py:1007-1031`.

| Variable | Value |
|---|---|
| `EMAIL_SMTP` | `yes` |
| `EMAIL_SMTP_HOST` | provider's host |
| `EMAIL_SMTP_PORT` | `587` for STARTTLS, `465` for implicit TLS |
| `EMAIL_SMTP_USE_TLS` | `yes` for 587 |
| `EMAIL_SMTP_USER` | provider's SMTP username |
| `EMAIL_SMTP_PASSWORD` | provider's SMTP password |
| `FROM_EMAIL` | `info@jadawl.site` |

## Verifying

Mail is queued through Celery, so a failure surfaces in the worker log rather
than in the request:

```
./jadawel backend-cmd-with-db manage sendtestemail you@example.com
```

Then trigger a real password reset and confirm the message arrives with SPF
and DKIM passing — most clients expose this as "show original" or
"view source". Until a real reset has been received end to end, treat the flow
as untested.
