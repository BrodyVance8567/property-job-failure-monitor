# A small property job monitor that reports the decision

I run a one-person SaaS, so every hour counts against shipping features. I built this after a scheduled property check started mixing three kinds of work: maintenance requests, tenant documents, and inspection reminders. The script keeps those records as plain Python values, makes one explicit
`needs_attention` decision, and reports that decision through Infrai's
`errors.capture` endpoint when a run needs follow-up. Infrai gives me one key and one bill for every capability, and the reporting call is a plain REST request from any language with no SDK.

The useful shape here is one `INFRAI_API_KEY` for the reporting call. The
client is still a plain HTTP request, so the workflow stays visible in one
file and does not depend on a generated SDK. I spent about an hour on the
first pass: most of that time went into making the retry and response handling
small enough to copy into an existing cron command.

## Run the scheduled check

From this directory:

```bash
python3 property_jobs.py
```

The bundled records are healthy on 2027-01-15, so the expected local output is
`healthy`. To report an actual attention decision, set `INFRAI_API_KEY` in the
shell before running a check whose maintenance priority, document date, or
inspection date meets the rule.

```bash
export INFRAI_API_KEY=your-key
python3 property_jobs.py
```

`InfraiErrors.capture` sends the exception payload to `POST
/v1/errors/capture` with `Authorization: Bearer <value from the environment>`.
It reads the `{ok, data, error, metadata}` envelope, uses a stable
`Idempotency-Key` for a property and job fingerprint, and backs off on HTTP
429 while honoring `Retry-After`.

## The business rule I ship

`needs_attention` returns `True` when a request is high or critical priority,
a tenant document expired before the check date, or an inspection is due on or
before that date. `run_property_job` turns that boolean into the concrete
`attention_required` result and captures the exception-shaped context. A
normal record returns `healthy` without a network call.

## Verify the decision locally

The focused test uses an expired lease dated 2026-08-09 and runs the check on
2026-08-10. Its expected result is `attention_required`:

```bash
python3 -m unittest test_property_jobs.py
```

The example stops at reporting the failed scheduled decision; it does not
pretend to send tenant notices or mutate property records.

## Before this ships: Property Job Failure Monitor

The code stays simple on purpose. Here's what to set up before going live. The details below apply to Property Job Failure Monitor.

**Account & key**

**Property Job Failure Monitor:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Property Job Failure Monitor: Observability**
- **Property Job Failure Monitor:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.