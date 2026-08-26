# Figma Story map

Source: [Report / Story](https://www.figma.com/design/D3uhn7WPXFsX1DiCIVklyg/Report?node-id=364-359), page `364:359`. This is an implementation map, not a list of React routes. A/B/C/D frames are persistent component states.

## Section inventory

| Section node | Section | Frames | Representative frame IDs |
| --- | --- | ---: | --- |
| `365:678` | 00 — Components / Foundations | library | `365:841` Progress, `389:448` StoryShell |
| `366:823` | 01 — Arrival | 12 | `367:358` Analysis Complete, `367:794` Dominant Three, `367:894` Hero Silhouette |
| `366:824` | 02 — Heroes | 11 | `368:1642` Most Played Question, `368:2044` Results Added, `368:2170` Transition Into Pool |
| `366:825` | 03 — Pool Shape | 14 | `370:358` All Heroes, `370:993` Full Pool Map, `370:1133` Transfer Question |
| `366:826` | 04 — Transfer | 9 | `371:358` Boundary, `371:733` Evidence Summary, `371:821` Introduce Loss |
| `366:827` | 05 — Post-Loss | 9 | `372:358` Match Timeline, `372:664` Evidence Expanded, `372:748` Inside the Match |
| `366:828` | 06 — Combat Expression | 10 | `373:358` Quiet Signal, `373:924` Combat Evidence, `373:1071` Five Copies |
| `366:829` | 07 — Session Drift | 9 | `375:765` Session Skeleton, `375:1117` Session Evidence, `375:1226` Recurrence |
| `366:830` | 08 — Synthesis | 7 | `375:1283` Fragments, `375:1704` DNA Signature, `375:1856` One Finding Separates |
| `366:831` | 09 — Identity | 9 | `376:358` Empty Reveal Stage, `376:735` Supporting Evidence, `376:806` Full Identity Hero |
| `366:832` | 10 — Deep / Premium | 4 | `377:765` Card Recedes, `377:860` Deep Preview, `377:908` Premium CTA |
| `366:833` | 11 — Share | 9 | `377:950` Share Transition, `377:1454` Gallery, `377:1623` Download, `377:1703` End Card |
| `366:834` | 12 — Outcome Variants | 100 | 25 outcomes × phases A/B/C/D, complete map below |
| `366:835` | 13 — Edge Cases | 11 | complete map below |
| `401:1540` | 14 — Prototype / Smart Animate | 104 | 103 state frames + `401:9178` asset strip |

## Foundation contracts

`Story/StoryShell` (`389:448`) is 375×812 with `#07090C` canvas, 20px safe gutter, 335px content width, vertical flow, clipped decorative grid, flexible story area, and bottom action area. Functional content uses Auto Layout/normal flow; only decoration is absolute.

`Story/Progress` (`365:841`) has 14 equal segments: 335px total width, 4px height, 3px gap, 2px radius. Completed is `#61D8CC`; remaining is `#C9D3D01F`. The chapter header shown in screens is separately labeled `01 / 11` through `11 / 11`; do not equate those 11 chapters with the 14 narrative segments.

Typography is Plus Jakarta Sans: headline ExtraBold 30/34 −0.8px; body Medium 15/23; eyebrow Bold 11/15 with 1.25px tracking; metric Bold 26/30; labels/hints 10/14; button labels SemiBold 11/15.

Exact semantic tokens: `#07090C` canvas, `#0B0F14` analytical, `#10161C` collectible, `#F3F7F5` primary, `#8C9B98` secondary, `#566461` annotation, `#C9D3D01F` rule, `#8CA3A012` grid, `#61D8CC` breadth, `#6C9EFF` transfer, `#B8DF67` consistency. Observed family accents: `#A68BFF` post-loss, `#E7C55C` warning, `#F16482` loss.

Analytical evidence panels are 335px wide, 14px padding, 8px internal gap, square corners, analytical surface, and 1px low-opacity rule. Identity card is collectible, 270×347 reference, 5px radius. Share cards are collectible, 190×261 reference, 5px radius.

## Outcome variants: exhaustive A/B/C/D map

Every row is one stable `OutcomeSequence`; phases are `A = Reveal`, `B = Interpretation`, `C = Evidence`, `D = Expanded Evidence`. The node IDs are Figma references only; production renders configuration, not 100 components.

| Key | A Reveal | B Interpretation | C Evidence | D Expanded Evidence |
| --- | --- | --- | --- | --- |
| `hidden_center` | `382:380` | `382:441` | `382:506` | `382:578` |
| `names_wide_jobs_narrow` | `382:631` | `382:686` | `382:745` | `382:811` |
| `names_narrow_jobs_wide` | `382:864` | `382:919` | `382:978` | `382:1044` |
| `names_changed_jobs_held` | `382:1097` | `382:1161` | `382:1229` | `382:1304` |
| `clean_transfer` | `382:1357` | `382:1408` | `382:1463` | `382:1525` |
| `results_stop_first` | `382:1578` | `382:1629` | `382:1684` | `382:1746` |
| `expression_stops_first` | `382:1799` | `382:1850` | `382:1905` | `382:1967` |
| `involvement_boundary` | `382:2020` | `382:2071` | `382:2126` | `382:2188` |
| `exposure_boundary` | `382:2241` | `382:2292` | `382:2347` | `382:2409` |
| `localized_function_bottleneck` | `382:2462` | `382:2516` | `382:2574` | `382:2639` |
| `one_loss_runback` | `382:2692` | `382:2736` | `382:2784` | `382:2839` |
| `two_loss_switch` | `382:2892` | `382:2938` | `382:2988` | `382:3045` |
| `result_shaped_pool` | `382:3098` | `382:3143` | `382:3192` | `382:3248` |
| `result_invariant_response` | `382:3301` | `382:3345` | `382:3393` | `382:3448` |
| `adjustment_without_recovery` | `382:3501` | `382:3550` | `382:3603` | `382:3663` |
| `involvement_holds_exposure_moves` | `382:3716` | `382:3796` | `382:3880` | `382:3971` |
| `exposure_holds_involvement_moves` | `382:4024` | `382:4104` | `382:4188` | `382:4279` |
| `same_expression_different_results` | `382:4332` | `382:4394` | `382:4460` | `382:4533` |
| `different_expression_same_results` | `382:4586` | `382:4668` | `382:4754` | `382:4847` |
| `localized_variance` | `382:4900` | `382:4977` | `382:5058` | `382:5146` |
| `opening_game_signature` | `382:5199` | `382:5254` | `382:5313` | `382:5379` |
| `gradual_session_drift` | `382:5432` | `382:5487` | `382:5546` | `382:5612` |
| `predeclared_breakpoint` | `382:5665` | `382:5723` | `382:5785` | `382:5854` |
| `selection_only_drift` | `382:5907` | `382:5971` | `382:6039` | `382:6114` |
| `bounded_stopping_response` | `382:6167` | `382:6226` | `382:6289` | `382:6359` |

## Edge-case map

| Edge state | Node |
| --- | --- |
| Insufficient evidence | `383:358` |
| Neutral | `383:408` |
| Family skipped | `383:448` |
| Narrow pool | `383:483` |
| Extremely broad pool | `383:527` |
| Long player name | `383:647` |
| 200% text / Arrival | `383:694` |
| 200% text / Pool Shape | `383:738` |
| 200% text / Evidence | `383:828` |
| 200% text / Identity | `383:889` |
| 200% text / Premium CTA | `383:944` |

## Prototype intent

Prototype frames preserve the same top-level layer names: `Proto/BG`, `Proto/Visual`, `Proto/UI`, `Proto/Progress`, `Proto/Content`, and `Proto/Action`. Reuse stable DOM identity across stages: hero → list → pool; pool nodes → rings; session points → highlights; DNA fragments → signature; identity card back → front.

All 102 transitions use click-to-next with Smart Animate, 400ms, `EASE_IN_AND_OUT`. Implement transforms/opacity/clip-path on mounted objects; do not animate layout-heavy properties or recreate whole SVGs. Reduced motion removes spatial travel and 3D rotation, using immediate or short opacity changes.

## Production interpretation

Exact: shell geometry, tokens, typography, surface semantics, chapter order, disclosure hierarchy, visualization continuity, identity/share card dimensions, uncertainty states, progress semantics, and accessibility behavior.

Reusable: shell/header/action, 14-segment progress, primitive vocabulary, persistent visualization nodes, one presentation adapter, one story-step engine, one four-phase outcome renderer, and one share-card family. Figma sample values are examples and must never replace report-backed data.
