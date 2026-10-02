# Real Data / Spec Source

## X12 EDI 834 (Benefit Enrollment and Maintenance) segment layout

Real, publicly published carrier enrollment companion guide:

**DC Health Benefit Exchange Authority — Benefit Enrollment (834) Companion
Guide, Version 1.0.3 (August 6, 2013)**
https://hbx.dc.gov/sites/default/files/dc/sites/Health%20Benefit%20Exchange%20Authority/publication/attachments/DCExchangeBenefitEnrollmentCompanionGuide_v103.pdf

This is a real, production companion guide published by a government health
insurance exchange, specifying exactly the kind of carrier-companion-guide-
driven 834 file this JD describes ("generate and transmit enrollment files
... driven by carrier companion guides"). The segment layout, qualifier
codes, and loop structure extracted from it (see
`docs/x12_834_spec_notes.md`) are the real schema anchor for
`src/x12_834_generator.py` -- not an invented or simplified format.

Specifically real and taken directly from this guide:
- ISA/GS/ST/BGN/N1/INS/REF/DTP/HD/SE/GE/IEA segment structure and element
  usage
- INS03 maintenance type codes: "021" (Addition), "024" (Cancellation or
  Termination)
- INS04 maintenance reason codes ("EC", "28", "03", "59")
- DTP qualifier codes ("303" Maintenance Effective, "348" Benefit Begin,
  "357" Eligibility End Date)
- Loop structure (1000A Plan Sponsor, 1000B Payer/Carrier, 1000C
  TPA/Broker, 2000 Member Detail, 2100A Member Name/Contact, 2700/2750
  Member Reporting Categories)

**Honest disclosure:** direct access to `hbx.dc.gov` was not re-verified
live from the build sandbox's egress-restricted environment (the same
restriction confirmed against `fema.gov` and `cms.gov` in earlier portfolio
projects); the segment layout above was extracted via a web-content fetch
tool rather than a direct `curl`/`wget` from this sandbox's shell. The
member-level enrollment data transmitted through this real format is
disclosed-synthetic (see `data/synthetic/GENERATION_NOTES.md`) -- no real
member PHI exists in or was used by this project.

## MongoDB

No real `mongod` server is reachable from this build sandbox (confirmed:
`apt-get` has no installable `mongodb-server` package on this Debian base,
and `fastdl.mongodb.org` is network-blocked, consistent with every other
third-party binary-download domain tested in this portfolio). `mongomock`
(a MongoDB-wire-API-compatible in-memory implementation, used via the real
`pymongo` client interface) stands in for the real server; every query in
this project is written and run against the real `pymongo` API, so it is
the same code that would run against production MongoDB. See
`docs/cost-tradeoffs.md`.
