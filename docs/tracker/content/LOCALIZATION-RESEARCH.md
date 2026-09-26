# Indonesian companion-app voice research

Reviewed 2026-09-26 for Dota Tracker's English and Indonesian content bank. This is an editorial reference, not evidence that another app's voice improves retention. The examples below are paraphrased; the linked storefronts and help pages are the source.

## Comparable products and screens

| Product | Why it was sampled | Screen and language observation | Useful lesson |
|---|---|---|---|
| [Gojek](https://play.google.com/store/apps/details?hl=id&id=com.gojek.app) | Indonesian daily companion; Google Play lists 100M+ downloads and 4.4 stars. | Its Indonesian storefront and screenshot carousel put short service/action labels beside concrete benefits. Its [official app imagery](https://www.gojek.com/gobluebird/) shows quick actions and a compact home hierarchy. The listing addresses the reader as *kamu*. | Lead with the useful action or result; write to one person. |
| [GoPay](https://play.google.com/store/apps/details?hl=id&id=com.gojek.gopay) | Frequent-use Indonesian companion; Google Play lists 100M+ downloads and 4.7 stars. | The Indonesian listing uses familiar verbs for paying, transfers and checking spending. Its release note can be playful, while the account and safety material stays specific. | Warmth is possible without softening facts or error recovery. |
| [Strava](https://play.google.com/store/apps/details?hl=id&id=com.strava) | Performance companion; Google Play lists 100M+ downloads and 4.6 stars in Indonesian. | The app listing foregrounds recording, progress and community. Its [challenge guidance](https://support.strava.com/id/articles/15401916-tantangan-strava) names screen actions such as *Grup*, *Tantangan* and *Gabung*, and states eligibility plainly. Help copy is more formal than its motivating product framing. | Put the measured result first; explain eligibility only when relevant. |
| [Duolingo](https://play.google.com/web/store/apps/details?hl=id&id=com.duolingo) | A highly used progression companion; Google Play lists 500M+ downloads and 4.7 stars. | The Indonesian listing frames learning as short, approachable steps and addresses the reader as *kamu*. The screenshot carousel uses visible progress and small next actions. | Keep momentum through small, clear next steps; reserve celebration for a real milestone. |

These are popular comparison points, not a claim that they are the objectively “best” localized apps. Store ratings and download counts can change. Screenshots and listings are marketing surfaces; implementation copy still needs in-app review.

## Screen-level close reads

- **Gojek account entry:** its [login walkthrough](https://www.gojek.com/id-id/help/akun/cara-masuk-ke-akun-gojek) names the buttons *Masuk*, *Kirim OTP* and *Lanjutkan*. The greeting is familiar, while the OTP warning becomes direct and specific. Use that switch in Tracker: a warm entry point, exact steps for recovery or data access.
- **Gojek failure state:** its [display and notification help](https://www.gojek.com/id-id/help/akun/kendala-tampilan-dan-notifikasi) lists the observable symptoms before a short recovery sequence. Avoid a generic “something went wrong” if the Tracker can name which match detail is missing.
- **GoPay spending report:** the [feature walkthrough](https://gopay.co.id/blog/laporan-pengeluaran-aplikasi-gopay) starts from the home-screen amount already spent, then shows totals, a weekly chart, top categories and history. Its invitation can use *yuk*, but the measurement labels stay literal. Tracker should lead with the match fact and keep playful language out of the numerical claim.
- **Strava challenge:** the [Indonesian help flow](https://support.strava.com/id/articles/15401916-tantangan-strava) uses screen labels *Grup*, *Tantangan* and *Gabung*, with eligibility stated beside the action. Keep Tracker button labels short and put sample or mode limits close to a metric.

These are observable UI labels and official walkthroughs, not copied strings for Tracker. They support a familiar voice with a stricter factual register for metrics, safety and failures.

## What carries into Dota Tracker

**Inference from the sources:** a companion voice can be direct and familiar in both languages while keeping the evidence precise. Use *kamu* in Indonesian, short active sentences, and game terms players already use: hero, item, lane, role, ward, Smoke, gold and net worth. English uses direct *you/your* and equally short sentences. Gojek/GoPay's playful touches work for invitations and success; Strava's restraint is better for comparisons, losses, uncertainty and missing data.

The app must never turn timing into a win-cause claim. An item card reports a recorded purchase and a scoped reference. It does not say the purchase completed a build, won a fight, or was the right choice. Do not call a low sample “usual.” Preserve placeholders, formatting markers, Standard/Turbo distinctions, role, hero, patch and evidence status.

## Editorial decision

Apply [Option 2 — Friendly teammate](TONE-OPTION-2-FRIENDLY-TEAMMATE.md) to the Figma content bank. Options [1](TONE-OPTION-1-CALM-SCOUT.md) and [3](TONE-OPTION-3-PLAYFUL-CASTER.md) remain alternatives for review. The Figma bank is the **target copy**; backend source strings and iOS rendering are separate implementation states until synchronized.
