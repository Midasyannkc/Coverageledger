# Incident Reports

## Incident 1: naive retry-on-timeout sends a termination twice

**JD language this answers directly:** "maintain a transmission ledger and
acknowledgment reconciliation, and guarantee a termination is sent exactly
once."

**Scenario.** `src/transmit_834.py`'s first transmitter
(`transmit_naive`) generates a real X12 834 termination segment, writes it
to the SFTP-equivalent outbox, and logs each termination in a MongoDB
`transmission_ledger` collection. A simulated SFTP timeout can occur
*after* the ledger write already landed (a real, common failure mode: the
side effect succeeds, the acknowledgment doesn't come back). The caller's
retry logic re-invokes the transmitter from the top.

**Detection.** A test drove exactly this sequence: first call raises
`TimeoutError` after writing the ledger, then a retry call runs to
completion.

```
tests/test_transmit_834.py::test_naive_transmitter_resends_termination_after_timeout_retry PASSED
  ledger_after_timeout == n_term        # first ("failed") call still wrote the ledger
  ledger_after_retry == n_term * 2      # BUG: every termination logged twice on retry
```

**Fix.** `transmit()` creates a unique index on the natural key
`(member_id, event_type, effective_date)` and checks the ledger for
already-sent terminations before generating the file, so a retry after a
successful-but-unacknowledged send finds nothing new to send.

```
tests/test_transmit_834.py::test_fixed_transmitter_sends_each_termination_exactly_once PASSED
  first call  -> sends n_term terminations
  retry call  -> sends 0 (no-op)
  ledger count == n_term, exactly once regardless of retries
```

**Business impact if unfixed:** a carrier receiving a duplicate 834
termination transaction for the same member on the same effective date can
either reject the whole file (blocking every OTHER member's real
transaction in the same batch) or, worse, silently process it as a
re-termination with no practical effect -- masking the fact that the
transmission layer is not actually idempotent, which would eventually
surface as a real compliance/audit finding.

**Git history:**
```
bc50295 Transmit 834 terminations via naive retry-on-timeout; reproduced duplicate termination logging after retry (test confirms bug)
b17620f Fix: idempotent transmit() with unique natural-key index on transmission_ledger; retry after success is a no-op, termination sent exactly once; 2/2 tests passing
```

---

## Incident 2: a legacy loader's identifier mismatch silently zeroes a client's census

**JD language this answers directly:** "normalize across the many
identifier systems healthcare data lives in (EIN, employer/group codes,
member and client reference IDs) so joins stay correct across systems."

**Scenario.** One client's `enrollment_events` were populated by a legacy
loader that wrote the client's EIN into the `group_code` field instead of
the client's real `group_code` (see `src/seed_mongo.py`,
`BUGGY_CLIENT_GROUP_CODE`). A naive report join
(`src/reconcile_pmpm.py::pmpm_naive`) matches `enrollment_events.group_code`
straight against `clients.group_code`.

**Detection.**
```
tests/test_reconcile_pmpm.py::test_naive_pmpm_silently_zeroes_out_the_misidentified_client PASSED
  buggy["enrolled"] == 0       # census silently reports zero enrolled members
  buggy["paid"] > 0            # ...for a client with real claims paid
  buggy["pmpm"] is not None    # claims-derived PMPM looks FINE -- masking the real problem
```
The PMPM dollar figure is computed independently from claims (member-months),
so it looked healthy even while the client's census was silently wrong --
exactly the kind of number that "ties out" on one report while being wrong
on another, which is what a reconciliation mindset is for.

**Fix.** `pmpm()` resolves `enrollment_events` to each client by matching
on EITHER `group_code` OR `ein`, built from an explicit identifier map
read off the `clients` collection, rather than assuming the foreign key is
always the same field.

```
tests/test_reconcile_pmpm.py::test_fixed_pmpm_resolves_the_misidentified_client PASSED
  buggy_fixed["enrolled"] > 0
  buggy_fixed["pmpm"] is not None
  every other client's figures unchanged by the fix
```

**Business impact if unfixed:** a client-facing census report
(explicitly named in the JD's "census, and regulatory outputs" bullet)
would show zero enrolled members for a paying client with real utilization
-- the kind of error that erodes client trust fast and is exactly what
this role exists to catch before it reaches a client or broker.

**Git history:**
```
4d5303d Compute PMPM rollups; naive group_code join silently zeroes enrolled count for the client whose legacy enrollment loader wrote EIN instead of group_code (reproduced, test confirms)
88681f2 Fix: resolve enrollment_events by group_code OR ein before joining; misidentified client's PMPM now resolves correctly, other clients unchanged; 8/8 tests passing
```
