# Free DNA v6 Dota expert review record

## Decision

The Free DNA v6 Dota-domain review is complete and approved.

- Review date: 2026-08-23
- Reviewer role: external expert Dota player
- Attestation source: project owner confirmation in the implementation task
- Private packet version: `v6-private-review-packet-1.0.0`
- Sampling seed: `6000`
- Reviewed claims: 50
- Accurate and useful: 50
- Supported but misleading: 0
- Unsupported: 0
- Unsure: 0
- Supported-and-believable precision: 100%
- Required precision: at least 90%
- Dota reviewer gate: pass

The project owner confirmed that the Dota expert received the complete review
material and agreed with every presented claim. The reviewer's identity was not
provided for storage in the repository. The stable reviewer reference carried
in aggregate release evidence is this record.

## What the reviewer was asked

Each sampled claim was shown with its plain-language Dota interpretation,
observed signals, confidence, interval, sample size, limitations, and allowed
interpretation. The reviewer chose one verdict:

- **Accurate and useful:** the evidence supports the claim and the wording is
  fair Dota language.
- **Supported but misleading:** the pattern exists, but the wording encourages
  an inference that is too strong or wrong.
- **Unsupported:** the shown signals do not justify the claim.
- **Unsure:** the reviewer cannot make a confident decision.

The 50-item sample contained these questions:

| Claim family | Items | Dota review question |
| --- | ---: | --- |
| Hero pool shape | 21 | Does the wording fairly describe the relationship between hero variety and the different functional jobs covered? |
| Transfer beyond familiar heroes | 4 | Does the claim fairly describe what changes on stretch heroes compared with familiar heroes? |
| Next match after a loss | 13 | Is the claim a fair description of the player's next-match pattern after losses, without implying that the loss caused it? |
| Combat expression | 12 | Does the wording fairly combine participation and death exposure without judging whether deaths were good, bad, avoidable, or caused by positioning? |

Session-drift wording used the same review framework but was not selected in
this deterministic 50-item sample. Its standing question is whether a claim
fairly describes early-versus-late changes within completed play sessions,
without confusing that with early versus late game time inside one match.

## Decisions captured

1. All 50 sampled claims are recorded as `supported=true` and
   `believable=true`.
2. The Dota reviewer approval is recorded as `true`.
3. No claim copy, formula, interval, threshold, or holdout result was changed as
   a consequence of the review.
4. Statistical review and data-basis approval remain separate roles. They are
   not inferred from Dota expertise and remain unapproved until qualified
   reviewers supply their own references.
5. The private item-level packet remains under `.local/calibration/review/`.
   Only aggregate counts, precision, approval state, and reviewer references
   may enter release evidence.

## Remaining questions before release

- Does an independent statistical reviewer approve the split, practical
  margins, empirical coverage and FDR interpretation, and sealed-holdout
  protocol?
- Does the data-basis approver confirm corpus provenance, public or consented
  use, retention, and privacy controls?
- Does the production image pass the container smoke with the exact candidate
  artifact bytes?
- Has an operator explicitly authorized a rollout stage while keeping the
  repository default `FREE_DNA_V6_ENABLED=false`?

Until those questions are answered, the candidate remains
`external-review-required` and must not be promoted or deployed. This does not
undo the completed Dota review; it keeps the independent release gates
distinct.

## Evidence handling

The completed private packet is ingested with:

```bash
uv run python scripts/evaluate_v6_calibration.py ingest-review \
  --input .local/calibration/review/reviewer-packet-6.0.0-completed.json \
  --output .local/calibration/review/review-evidence-6.0.0.json
```

The aggregate evaluation must show `50/50`, precision `1.0`, and a passing
`dota_reviewer_precision` gate. Promotion remains fail-closed while either of
the other external approvals is false or absent.

Audit checksums after ingestion:

| Artifact | SHA-256 |
| --- | --- |
| Private source packet | `8eeb990932ca79dad419897b347c22906381c8080ded41895ba106ce6108450f` |
| Completed private packet | `b1b8dc6e3eb6dc4c4446e0d590d238dfe454ab9184f1ee91ffa5af16acaf397d` |
| Aggregate review evidence | `de18df9b6af020c5fb7023d649f2df2de0a638577eb5e59d7f5e846b6e92c79b` |
| Manifest external-review checksum | `ac34e36ca3a1906688935010ad074f1df940be6f23d7fef8f09d5a27af4d9dca` |
| Aggregate calibration evaluation | `829fd6479b3d9405adc6a7bff9afd02674e845233184aacea6fc4a8dd514d4fb` |
| Release manifest | `515a95ab514034c37e2acb3eb031b2d3d421abcee5bfcb9061d7e13956e58cce` |
