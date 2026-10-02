"""
Governed semantic layer: field definitions, business rules, and join keys
for the collections in the MongoDB document estate -- the JD's explicit
"stand up and version the governed semantic layer ... so model and report
inputs can't silently drift" requirement.

This is read by both the PMPM reconciliation report and the RAG grounding
index (src/rag_index.py), so a renamed or redefined field is a one-place
change rather than a silent drift between what a report says and what an
LLM-grounded answer says.
"""
SEMANTIC_LAYER = {
    "version": "1.0.0",
    "entities": {
        "clients": {
            "primary_key": "group_code",
            "fields": {
                "group_code": "Canonical TPA-assigned employer group identifier. The ONLY correct join key from enrollment_events/claims back to clients.",
                "ein": "Employer's federal tax ID. NOT a reliable join key on its own -- see known data-quality note below.",
                "funding_type": "Either 'self-funded' or 'level-funded'; controls which reserve/stop-loss rules apply downstream.",
            },
        },
        "members": {
            "primary_key": "member_id",
            "fields": {
                "member_id": "Canonical member identifier, unique per person.",
                "subscriber_id": "member_id of the subscriber this member is enrolled under (equals member_id for subscribers themselves).",
                "relationship_code": "'subscriber' or 'dependent'. Maps to X12 834 INS01 (Y/N) -- see docs/x12_834_spec_notes.md.",
            },
        },
        "enrollment_events": {
            "primary_key": ["member_id", "event_type", "effective_date"],
            "fields": {
                "event_type": "'add' or 'terminate'. Maps to X12 834 INS03 maintenance type codes 021/024.",
                "effective_date": "Date the add/termination takes effect. Maps to X12 834 DTP01=303.",
            },
            "known_data_quality_notes": [
                "One legacy-loaded client's events are keyed by `ein` instead of `group_code` in this field "
                "(see docs/incidents.md, Incident 2). Always resolve via {group_code: {$in: [group_code, ein]}}, "
                "never a bare group_code equality match."
            ],
        },
        "claims": {
            "primary_key": None,
            "fields": {
                "allowed_amount": "Plan-allowed charge before member cost-share, USD.",
                "paid_amount": "Amount actually paid by the plan, USD. Used as the numerator for PMPM.",
                "service_month": "Calendar month the claim's service occurred in, truncated to the 1st.",
            },
        },
        "transmission_ledger": {
            "primary_key": ["member_id", "event_type", "effective_date"],
            "business_rule": "A termination must be logged here EXACTLY ONCE per (member_id, effective_date) "
            "-- see docs/incidents.md, Incident 1. Enforced by a unique index, not just application logic.",
        },
    },
    "business_rules": {
        "pmpm": "paid_amount summed per group_code, divided by COUNT(enrollment_events WHERE event_type='add' "
        "AND group_code normalized via clients.ein fallback). See src/reconcile_pmpm.py.",
    },
}
