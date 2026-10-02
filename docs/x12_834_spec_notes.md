# X12 834 Segment Spec Notes (real, sourced)

Extracted from the real DC HBX Benefit Enrollment (834) Companion Guide,
v1.0.3 (see `data/bronze/SOURCE.md` for the full citation and honest
disclosure of how it was reached).

## Control segments

| Segment | Key elements used |
|---|---|
| ISA | ISA01 Auth Qualifier "00"; ISA05/07 ID Qualifier "30"; ISA06/08 Sender/Receiver Federal Tax ID; ISA09/10 date/time; ISA12 Version "00501"; ISA13 Control Number; ISA15 Usage "P"/"T" |
| GS | GS01 Functional ID "BE"; GS02/03 Sender/Receiver Code; GS06 Group Control Number; GS08 Version "005010X220A1" |
| ST | Starts the 834 transaction set |
| BGN | BGN08 Action Code "2" (Change/additions); BGN02 Transaction Set Control Number |
| SE / GE / IEA | Close transaction set / functional group / interchange |

## Member-level segments

| Segment | Key elements used |
|---|---|
| N1 (Loop 1000A/1000B/1000C) | Plan Sponsor / Payer-Carrier / TPA-Broker identification |
| INS | INS01 "Y" subscriber / "N" dependent; **INS03 Maintenance Type Code**: `021` = Addition, `024` = Cancellation or Termination; INS04 Maintenance Reason Code (`EC`, `28`, `03`, `59`); INS05 Benefit Status "A" |
| REF | REF01 Qualifier: `0F` subscriber number, `23` carrier-assigned member ID, `ZZ` carrier-assigned subscriber ID |
| DTP | DTP01 Qualifier: `303` Maintenance Effective, `348` Benefit Begin, `357` Eligibility End Date |
| HD | HD03 Insurance Line Code: `HLT` / `DEN` |

## What this project implements

`src/x12_834_generator.py` builds real ISA/GS/ST/BGN/N1/INS/REF/DTP/SE/GE/IEA
segments from the MongoDB `enrollment_events` collection, using the real
`021`/`024` maintenance-type codes for add/terminate events respectively.
Loop-2700/2750 reporting categories and COB loops (2320/2330) are
documented here as the real spec calls for them, but are out of scope for
this build (no reporting-category or COB data exists in the synthetic
member estate) -- see `docs/cost-tradeoffs.md`.
