# Email setup

Password reset, workspace invitations and notification emails are all dead in
production right now. No `EMAIL_SMTP*` variable is set, so
`CELERY_EMAIL_BACKEND` falls back to the console backend
(`jadawel/config/settings/base.py:1007-1031`): every message is printed to the
worker's stdout and discarded. The reset flow is the worst of these — the UI
reports success and no mail ever arrives, so a locked-out user has no recovery
path at all.

## What `jadawl.site` can do today

Checked against live DNS. The domain now runs **Zoho Mail** — it was on
Namecheap's free forwarding earlier, and that note is superseded:

| Record | Value | Meaning |
|---|---|---|
| NS | `dns1/dns2.registrar-servers.com` | DNS is still hosted at **Namecheap**, so records are added there. |
| MX | `mx.zoho.com`, `mx2`, `mx3` | Zoho Mail. `info@jadawl.site` is a real mailbox, not a forward. |
| TXT | `v=spf1 include:zohomail.com ~all` | Authorises Zoho only. |
| `zmail._domainkey` | `v=DKIM1; k=rsa; p=MIGf…` | Zoho DKIM is configured and signing. |
| `_dmarc` | *absent* | Still no DMARC policy. |

So inbound mail is healthy and already authenticated. Nothing here authorises
Resend yet.

### Resend status

The API key is live — a test send through `onboarding@resend.dev` was accepted
and returned a message id. The domain is not:

```
POST /emails  from: info@jadawl.site
→ 403 "The jadawl.site domain is not verified."
```

That is the whole of the remaining blocker. Until the records below exist and
Resend reports the domain verified, **every** send from `info@jadawl.site` is
rejected, which is why the application variables are not set yet.

## The sender: Resend, over SMTP

Resend is the chosen provider. It exposes both an HTTP API and an SMTP
endpoint, and **this deployment uses SMTP**. That is not a stylistic
preference — it is the only option that costs nothing to ship:

- The mail that matters is not sent by our code. Password resets, workspace
  invitations and notification digests are built and dispatched by Jadawel's
  own code paths through Django's email framework, queued onto Celery by
  `djcelery_email` (`base.py:1007`). Pointing those at Resend means giving
  Django an SMTP host. The Python SDK would instead require writing a custom
  `EmailBackend` and would leave every upstream call site untouched until it
  was wired in.
- **`pip install resend` costs a rebuild.** The root `Dockerfile` pulls a
  published image rather than building the monorepo, because the Nuxt build is
  OOM-killed on a 4 GB plan (`AGENTS.md`). A new backend dependency means
  republishing the all-in-one image and bumping `ARG JADAWEL_IMAGE`. SMTP
  needs no code, no dependency, and no rebuild — six environment variables and
  a reload.

So the snippet Resend hands out on signup — `resend.Emails.send({...})` with
`from: "onboarding@resend.dev"` — is a connectivity demo, not an integration.
Two things about it are worth keeping in mind anyway: `onboarding@resend.dev`
is a shared sandbox sender that can only deliver to the address that owns the
Resend account, and the API key it wants is the same string that becomes the
SMTP password below.

### SMTP endpoint

Per Resend's SMTP documentation:

| | |
|---|---|
| Host | `smtp.resend.com` |
| Ports | 25, 587, 2587 (STARTTLS) · 465, 2465 (implicit TLS) |
| Username | the literal string `resend` |
| Password | the API key, `re_…` |

Use **587 with STARTTLS**. Outbound 465 is blocked or throttled by more
networks than 587 is, and the setting pair below matches it.

### Region

Resend sends from one of four regions — `us-east-1` (North Virginia),
`eu-west-1` (Ireland), `sa-east-1` (São Paulo), `ap-northeast-1` (Tokyo).
There is no Middle East region, so **choose `eu-west-1`**: it is the closest of
the four to Saudi recipients.

This is a deliberate exception to the residency rule. The database stays in
Riyadh; transactional mail does not, because no provider with usable
deliverability sends from inside the Kingdom. What leaves the country is
recipient addresses and reset tokens in transit, not table data — and those
messages end up in Gmail and Outlook mailboxes regardless of who relays them.
Worth recording as a decision rather than letting it happen by default.

## DNS records to add

Added in the Namecheap DNS panel, from the values on the domain's **Records**
tab in the Resend dashboard. Copy them from there rather than from here — the
DKIM key and the regional hostnames are unique per domain.

The important structural point: Resend verifies a **`send.` subdomain**, and
its Return-Path defaults to `send.jadawl.site`. Its SPF and MX records
therefore go on `send`, not on the root. **Zoho's root MX and its
`include:zohomail.com` SPF are left completely alone** — no merging, no risk to
inbound mail, and no second SPF record on the apex. The two providers coexist:
Zoho receives, Resend sends. `zmail._domainkey` and `resend._domainkey` are
different selectors and do not collide either.

Namecheap's Host field takes the label only, without the domain suffix:

| Type | Host | Value |
|---|---|---|
| MX | `send` | `feedback-smtp.eu-west-1.amazonses.com`, priority `10` |
| TXT | `send` | `v=spf1 include:amazonses.com ~all` |
| TXT | `resend._domainkey` | the `p=…` key Resend generates |

DMARC is separate, and none exists today. Add it at the apex once Resend
verifies, in monitor mode so nothing is rejected while the setup is validated:

| Type | Host | Value |
|---|---|---|
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:info@jadawl.site` |

Alignment still works under this layout: DKIM signs with `d=jadawl.site`, and
the Return-Path `send.jadawl.site` is a subdomain of the From domain, which
satisfies DMARC's relaxed alignment.

## Application configuration

Set on the app in the CranL dashboard, then reload it. The variables are read
at `base.py:1007-1031`; `FROM_EMAIL` at `base.py:854`.

| Variable | Value |
|---|---|
| `EMAIL_SMTP` | `yes` |
| `EMAIL_SMTP_HOST` | `smtp.resend.com` |
| `EMAIL_SMTP_PORT` | `587` |
| `EMAIL_SMTP_USE_TLS` | `yes` |
| `EMAIL_SMTP_USER` | `resend` |
| `EMAIL_SMTP_PASSWORD` | the `re_…` API key |
| `FROM_EMAIL` | `info@jadawl.site` |

Three traps in that block:

- `EMAIL_SMTP_USE_SSL` must stay **unset**. `base.py:1022-1026` raises
  `ImproperlyConfigured` if both TLS and SSL are set, and the app will not
  boot. Set SSL only if you switch to port 465, and unset TLS at the same time.
- Every one of these is read with `bool(os.getenv(...))`, so *any* non-empty
  string is true — `EMAIL_SMTP_USE_TLS=false` enables TLS. To disable one,
  remove it; do not set it to `false`.
- `EMAIL_SMTP_PASSWORD` is a live credential. It belongs in the CranL
  dashboard only, never in a compose file or in the repository.

Set them together, in one edit. A partial configuration is worse than none:
the moment `EMAIL_SMTP` is non-empty the backend flips from console to SMTP
(`base.py:1009`), so an incomplete block turns silently-discarded mail into
authentication failures in the Celery worker.

Until the domain is verified, `FROM_EMAIL` must remain a Resend-owned address
or every send is rejected. Verify the domain first, then set `FROM_EMAIL`.

## Verifying

Mail is queued through Celery, so a failure surfaces in the worker log rather
than in the request — a green response in the UI proves nothing:

```
./jadawel backend-cmd-with-db manage sendtestemail you@example.com
```

Then trigger a real password reset and confirm the message arrives with SPF
and DKIM passing — most clients expose this as "show original" or
"view source". Resend's own dashboard logs every attempt with its delivery
status, which is the fastest place to see a rejection. Until a real reset has
been received end to end, treat the flow as untested.
