# Email setup

Outbound email is **configured and live**: Resend over SMTP, sending as
`info@jadawl.site`. Before this, no `EMAIL_SMTP*` variable was set, so
`CELERY_EMAIL_BACKEND` fell back to the console backend
(`jadawel/config/settings/base.py:1007-1031`) and every password reset,
workspace invitation and notification was printed to the worker's stdout and
discarded — the UI reported success and no mail ever arrived, leaving a
locked-out user with no recovery path.

## Two providers, two jobs

The domain runs **Zoho Mail for receiving** and **Resend for sending**. That
split is deliberate, not an accident of history, and the two do not conflict:
Zoho owns the apex records, Resend owns a `send.` subdomain.

Live DNS, verified:

| Record | Value | Owner |
|---|---|---|
| NS | `dns1/dns2.registrar-servers.com` | Namecheap hosts DNS, so records are added there. |
| MX (apex) | `mx.zoho.com`, `mx2`, `mx3` | Zoho. `info@jadawl.site` is a real mailbox. |
| TXT (apex) | `v=spf1 include:zohomail.com ~all` | Zoho. |
| `zmail._domainkey` | `v=DKIM1; k=rsa; p=MIGf…` | Zoho DKIM, signing. |
| MX `send` | `feedback-smtp.eu-west-1.amazonses.com` | Resend return-path. |
| TXT `send` | `v=spf1 include:amazonses.com ~all` | Resend SPF. |
| `resend._domainkey` | `p=MIGf…` | Resend DKIM, signing. |
| `_dmarc` | `v=DMARC1; p=none;` | Monitor mode. |

Two SPF records on two different names is correct and is *not* the "two SPF
records" failure — that only applies to two records on the *same* name. The two
DKIM selectors, `zmail` and `resend`, are likewise distinct.

DMARC alignment holds for Resend because the return-path `send.jadawl.site` is
a subdomain of the From domain, which satisfies relaxed alignment.

### Why not send through Zoho

The Zoho plan is paid, so its SMTP (`smtp.zoho.com:587`) *is* available and
would work. Resend is still the better choice for this traffic:

- **Zoho throttles.** Its SMTP limits are sized for human correspondence, and a
  burst of invitations or a notification digest can trip them. Resend is built
  for transactional volume.
- **Reputation isolation.** A bounce storm from application mail would damage
  the same reputation `info@jadawl.site` relies on to reach customers. Separate
  senders keep that blast radius contained.
- **Observability.** Resend logs every message with its delivery status, which
  is where a failed reset gets diagnosed. Zoho's sent folder is not that.

Keeping Zoho as the inbox also means replies to application mail land
somewhere a human reads.

### Verification evidence

Confirmed end to end, not assumed:

| Check | Result |
|---|---|
| Resend API, from `onboarding@resend.dev` | accepted, id `99a91025…` |
| Resend API, from `info@jadawl.site` | accepted, id `ad49f336…` — domain verified |
| `smtp.resend.com:587`, STARTTLS, user `resend` | **`250` accepted** |
| App reachable after reload | `GET /api/settings/` → `200` |

The SMTP check is the one that matters: it exercises the exact host, port,
username, key and TLS mode the backend is now configured with.

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

DMARC is separate, and now exists at the apex as `v=DMARC1; p=none;` — monitor
mode, so nothing is rejected. It has **no `rua=`**, which means no aggregate
reports are being delivered anywhere and the monitoring period is collecting
nothing. Worth adding before any move to `p=quarantine`:

| Type | Host | Value |
|---|---|---|
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:info@jadawl.site` |

Alignment still works under this layout: DKIM signs with `d=jadawl.site`, and
the Return-Path `send.jadawl.site` is a subdomain of the From domain, which
satisfies DMARC's relaxed alignment.

## Application configuration

These are **set on the `jadawel` app and live**. The variables are read at
`base.py:1007-1031`; `FROM_EMAIL` at `base.py:854`.

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

Set `FROM_EMAIL` only after the domain verifies. Against an unverified domain
Resend rejects every send, which is louder than the console backend but no less
broken.

## Verifying

Mail is queued through Celery, so a failure surfaces in the worker log rather
than in the request — a green response in the UI proves nothing. There are
three tests, in increasing order of what they prove.

**1. The transport.** Bypasses the app entirely and checks the credentials:

```
curl --ssl-reqd --url 'smtp://smtp.resend.com:587' \
     --user 'resend:re_…' \
     --mail-from 'info@jadawl.site' --mail-rcpt 'you@example.com' \
     --upload-file mail.txt
```

A `250` means host, port, username, key and STARTTLS are all correct.

**2. The app's own sender.** `/api/_health/email/` (`EmailTesterView`) forces
the message through `CELERY_EMAIL_BACKEND` synchronously so the error comes
back in the response instead of vanishing into a worker log
(`core/health/handler.py:94-104`). Staff authentication required. This is the
best single test, because it proves the container can reach Resend — something
no test run from a laptop can establish.

**3. A real password reset.** Note the trap: `send-reset-password-email`
returns **`204` whether or not the address exists**. The view swallows
`UserNotFound` deliberately, to stop the endpoint being used to enumerate
registered accounts (`api/user/views.py:395-415`). A 204 for an unregistered
address queues nothing at all, so testing with the wrong address proves
nothing. Use an address you know has an account, then confirm the message
arrives with SPF and DKIM passing — most clients expose this under "show
original" or "view source".

Resend's dashboard logs every attempt with its delivery status, and is the
fastest place to see a rejection. Until a real reset has been received end to
end, treat the flow as untested.
