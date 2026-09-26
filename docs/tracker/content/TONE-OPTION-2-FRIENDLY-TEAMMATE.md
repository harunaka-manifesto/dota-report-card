# Tone option 2 — Friendly teammate (selected)

**Position:** a teammate who notices what happened and helps the player find the next useful thing. It combines Gojek/GoPay's approachable Indonesian address with Strava's concrete performance evidence and Duolingo's small next steps. This is an editorial inference from the [research](LOCALIZATION-RESEARCH.md), not copied brand language.

| Dimension | English | Indonesian |
|---|---|---|
| Address | you, your team; name the enemy or hero when needed | kamu, tim kamu; sebut lawan atau hero saat perlu |
| Rhythm | Short, active, one fact per clause | Ringkas, aktif, satu fakta per klausa |
| Game words | Keep known Dota terms | Hero, item, lane, role, ward, Smoke, gold, net worth tetap dipakai |
| Invitation | Helpful verb, sparing warmth | *Lihat*, *Cek*, *Coba lagi*; *yuk* hanya untuk ajakan ringan |
| Setbacks | Neutral and helpful | Tidak menyalahkan pemain atau bercanda soal kalah |
| Records | Celebrate only what the evidence proves | Rayakan rekor yang benar-benar terukur |

Examples applied to the bank:

| Use | EN target | ID target |
|---|---|---|
| Comeback | Your team was down {deficit:,} gold at {minute}:00, then won. | Tim kamu tertinggal {deficit:,} gold pada {minute}:00, lalu menang. |
| V2 enemy item | {hero} bought {item_name} at {time}. When {hero} buys this item as Carry in Standard, it's usually around {reference_median}. | {hero} membeli {item_name} pada {time}. Kalau {hero} membeli item ini saat main Carry di Standard, biasanya baru dibeli sekitar {reference_median}. |
| Usual value still forming | We need this number from 5 earlier {mode} matches as {role} before we can show what's usual for you. | Butuh angka ini dari 5 match {mode} sebelumnya saat kamu main {role} untuk tahu biasanya. |
| Retry | Couldn't finish this match review. Try again. | Ulasan pertandingan ini belum selesai. Coba lagi. |

## Guardrails

- Never imply an item purchase caused a result, was necessarily optimal, or completed a build.
- Preserve exact evidence limits: *at least*, previous fastest, sample size, patch, role and mode. Do not turn “no data” into a poor performance judgment.
- Keep statistical terms such as *median*, *baseline*, *metric* and *scope* in internal documentation. In player copy, explain the result in ordinary words. “Usually around” can express the median only when the sentence makes clear that it describes the same hero, role and mode **among matches where that item was bought**.
- Use *kamu*, not *Anda* or *gue/lu*. Avoid meme slang and forced hype. Indonesian game terms stay consistent rather than being translated literally.
- Keep placeholders exactly as specified by the code or copy contract. V1 and V2 card wording are different templates; existing V1 history stays identifiable.
- Status is part of the SSOT: a Figma target is not a shipped iOS string until implemented.

This option is selected for the Figma content bank because it stays approachable across wins, losses, unavailable states and detailed measurements.
