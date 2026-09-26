# Item build patterns · 7.41 (b–e pooled)

Which key items each hero buys as Carry, Mid or Offlane, in which mode, and in what usual order. Built from de-identified STRATZ corpus aggregates pooled across patches 7.41b–7.41e, filtered through the reference artifact's coverage, purchase-rate and sample-size gates. Artifact digest (sha256 of `item_references.json`): `801853401f4181f2afb53525219468ce20a11d601e63ef8a975852c615aae852`.

**Build order is descriptive only; comparisons use hero × role × mode × item baselines and never the order.** See [ITEM-TIMINGS-V1.md](ITEM-TIMINGS-V1.md) for the backend contract this data feeds and [SSOT.md](SSOT.md) for Match Detail product ownership.

## Coverage summary

The reference artifact covers all 127 heroes × 3 core roles × 2 modes = 762 cells. This document covers every cell with a published reference (`reason: null`); the rest carry an explicit unavailable reason and no build claim.

| Reason | Cells | Meaning |
|---|---|---|
| Has references (documented below) | 153 | Cohort and item(s) cleared every population threshold |
| `sparse` | 397 | Fewer than 50 cohort games for this hero × role × mode |
| `patch_change_pending` | 196 | The 7.41f patch-change review suspended this hero or item pending current-letter evidence |
| `no_qualified_item` | 16 | Enough games, but no item cleared the purchase-count/purchase-rate thresholds (order is not a gate) |

153 hero × role × mode cells across 69 heroes are documented below.

## Heroes

### Abaddon

#### Carry

**Turbo** · 55 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 94% of games | 3:15 | 1 (98%) |

Typical sequence: Phase Boots

Abaddon leans on Mist Coil sustain and Aphotic Shield/Borrowed Time rather than burst items, so Phase Boots — pure mobility to stick to a target and land Coil/Curse of Avernus — is close to the entire build at this sample size.

#### Offlane

**Turbo** · 65 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 86% of games | 3:45 | 1 (93%) |

Typical sequence: Phase Boots

Same logic as carry: Abaddon's damage comes from spells and passives, not items, so Phase Boots to close distance and keep contact is nearly the whole build.

### Alchemist

#### Carry

**Standard** · 83 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Radiance | 89% of games | 15:15 | 2 (69%) |
| Blink Dagger | 60% of games | 20:45 | 4 (44%) |
| Black King Bar | 65% of games | 28:15 | 4 (33%) |

Typical sequence: Radiance → Blink Dagger → Black King Bar

**Turbo** · 103 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Radiance | 89% of games | 8:15 | 1 (50%) |
| Aghanim's Scepter | 84% of games | 11:15 | 3 (38%) |
| Blink Dagger | 57% of games | 16:15 | 4 (36%) |

Typical sequence: Radiance → Aghanim's Scepter → Blink Dagger

Alchemist buys Radiance first regardless of mode because Goblin's Greed gold and Unstable Concoction farm fund it early, and the burn synergizes with Acid Spray; Aghanim's Scepter (bigger, farther Concoction) and Blink Dagger or Black King Bar round out a build about farming into one big teamfight play.

#### Offlane

**Turbo** · 74 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Radiance | 82% of games | 8:45 | 2 (59%) |
| Aghanim's Scepter | 77% of games | 11:45 | 3 (44%) |

Typical sequence: Radiance → Aghanim's Scepter

The offlane version follows the same farm-into-Radiance plan, just slower — Aghanim's Scepter is the visible follow-up once Radiance is online.

### Arc Warden

#### Mid

**Turbo** · 55 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Boots of Travel | 91% of games | 9:45 | 3 (30%) |

Typical sequence: Boots of Travel

Arc Warden's plan is splitting the map with Tempest Double and taking two farming lanes at once, so Boots of Travel — usable on both the hero and, once summoned, effectively doubling map coverage — is the one item that clears the bar regardless of what else he buys.

### Axe

#### Offlane

**Standard** · 267 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 89% of games | 6:45 | 1 (84%) |
| Vanguard | 31% of games | 9:45 | 1 (52%) |
| Blink Dagger | 98% of games | 14:45 | 2 (45%) |
| Blade Mail | 97% of games | 16:45 | 3 (46%) |
| Black King Bar | 60% of games | 29:45 | 4 (68%) |
| Kaya | 24% of games | 30:45 | 6 (40%) |
| Aghanim's Scepter | 31% of games | 35:45 | 5 (33%) |
| Sange | 22% of games | 31:45 | 5 (43%) |
| Kaya and Sange | 21% of games | 33:45 | 7 (54%) |

Typical sequence: Phase Boots → Vanguard → Blink Dagger → Blade Mail → Black King Bar → Kaya → Aghanim's Scepter → Sange → Kaya and Sange

**Turbo** · 395 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 73% of games | 3:45 | 1 (74%) |
| Vanguard | 41% of games | 5:15 | 1 (54%) |
| Blink Dagger | 99% of games | 7:45 | 3 (39%) |
| Blade Mail | 94% of games | 8:45 | 2 (41%) |
| Black King Bar | 51% of games | 16:15 | 4 (42%) |
| Lotus Orb | 22% of games | 17:45 | 5 (29%) |
| Aghanim's Scepter | 62% of games | 17:45 | 5 (30%) |
| Crimson Guard | 22% of games | 17:15 | 5 (27%) |
| Boots of Travel | 33% of games | 20:15 | 6 (18%) |
| Overwhelming Blink | 35% of games | 24:45 | 7 (29%) |

Typical sequence: Phase Boots → Vanguard → Blink Dagger → Blade Mail → Black King Bar → Lotus Orb → Aghanim's Scepter → Crimson Guard → Boots of Travel → Overwhelming Blink

Axe's job is to walk in and land Berserker's Call: Phase Boots close the gap, Vanguard keeps him alive while farming Battle Hunger stacks, Blink Dagger makes the Call reliable, and Blade Mail punishes whoever tries to burst him during Counter Helix uptime. Black King Bar, Aghanim's Scepter and the Kaya line arrive once the initiation combo is already funded, letting him repeat Culling Blade picks.

### Bloodseeker

#### Carry

**Standard** · 54 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 96% of games | 7:15 | 1 (92%) |

Typical sequence: Phase Boots

**Turbo** · 78 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 85% of games | 3:45 | 1 (94%) |
| Black King Bar | 81% of games | 14:45 | 4 (38%) |
| Sange | 77% of games | 15:45 | 5 (27%) |
| Skull Basher | 78% of games | 16:15 | 5 (26%) |

Typical sequence: Phase Boots → Black King Bar → Sange → Skull Basher

Bloodseeker snowballs off Rupture, so Phase Boots — the only near-universal buy — exist purely to run down a target who can no longer flee; the turbo sample's Black King Bar and Sange/Skull Basher show him locking a Ruptured hero down for longer once games run long enough to afford it.

### Bristleback

#### Offlane

**Standard** · 144 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 56% of games | 9:45 | 1 (74%) |
| Vanguard | 56% of games | 9:45 | 1 (72%) |
| Lotus Orb | 50% of games | 23:45 | 2 (43%) |
| Blade Mail | 35% of games | 19:15 | 2 (43%) |
| Sange | 35% of games | 25:45 | 3 (38%) |

Typical sequence: Power Treads → Vanguard → Lotus Orb → Blade Mail → Sange

**Turbo** · 283 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 45% of games | 4:45 | 1 (76%) |
| Phase Boots | 27% of games | 5:45 | 2 (57%) |
| Vanguard | 54% of games | 5:15 | 1 (59%) |
| Blade Mail | 45% of games | 9:15 | 2 (37%) |
| Pipe of Insight | 23% of games | 11:15 | 2 (43%) |
| Lotus Orb | 36% of games | 13:45 | 4 (24%) |
| Aghanim's Scepter | 59% of games | 15:45 | 3 (20%) |
| Sange | 45% of games | 14:45 | 4 (21%) |
| Crimson Guard | 27% of games | 16:15 | 4 (31%) |
| Sange and Yasha | 38% of games | 15:15 | 6 (24%) |
| Yasha | 38% of games | 15:15 | 5 (36%) |
| Black King Bar | 29% of games | 19:45 | 5 (23%) |
| Assault Cuirass | 23% of games | 21:45 | 5 (26%) |

Typical sequence: Power Treads → Phase Boots → Vanguard → Blade Mail → Pipe of Insight → Lotus Orb → Aghanim's Scepter → Sange → Crimson Guard → Sange and Yasha → Yasha → Black King Bar → Assault Cuirass

Bristleback tanks and reflects damage while stacking Quill Spray, so Power Treads/Vanguard/Blade Mail/Lotus Orb all layer mitigation or damage-return around Viscous Nasal Goo; the longer turbo list adds Aghanim's Scepter and Assault Cuirass as he scales from lane tank into a frontline damage dealer.

### Chaos Knight

#### Carry

**Turbo** · 104 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 98% of games | 3:45 | 1 (86%) |
| Armlet | 53% of games | 6:45 | 2 (75%) |
| Echo Sabre | 56% of games | 7:45 | 2 (64%) |
| Yasha | 71% of games | 10:45 | 3 (46%) |
| Black King Bar | 51% of games | 17:15 | 6 (23%) |

Typical sequence: Power Treads → Armlet → Echo Sabre → Yasha → Black King Bar

Chaos Knight needs raw Strength and lifesteal to win extended duels: Armlet spikes damage and Strength, Echo Sabre and Yasha add stats and attack speed for his illusions, and Black King Bar lets him commit to a Reality-Phantasm all-in without being disabled first.

#### Offlane

**Standard** · 58 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 98% of games | 7:45 | 1 (93%) |

Typical sequence: Power Treads

**Turbo** · 88 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 99% of games | 4:15 | 1 (85%) |
| Echo Sabre | 60% of games | 8:45 | 2 (47%) |
| Yasha | 69% of games | 11:15 | 3 (46%) |

Typical sequence: Power Treads → Echo Sabre → Yasha

The offlane version follows the same stat-stacking plan, just slower — Power Treads alone clears the bar in standard, with Yasha and Echo Sabre showing up once turbo's pace lets him farm faster.

### Clinkz

#### Carry

**Standard** · 59 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 92% of games | 8:15 | 1 (100%) |
| Desolator | 90% of games | 17:15 | 2 (87%) |

Typical sequence: Power Treads → Desolator

**Turbo** · 84 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 73% of games | 3:45 | 1 (95%) |
| Desolator | 88% of games | 7:45 | 2 (61%) |
| Orchid Malevolence | 70% of games | 10:45 | 3 (41%) |
| Bloodthorn | 60% of games | 13:15 | 4 (30%) |

Typical sequence: Power Treads → Desolator → Orchid Malevolence → Bloodthorn

Clinkz bursts from Skeleton Walk stealth, so Desolator's armor shred is close to automatic on an agility right-clicker; turbo's extra tempo adds Orchid Malevolence and Bloodthorn to silence-lock a target before the burst window closes.

#### Mid

**Standard** · 88 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 98% of games | 7:15 | 1 (98%) |
| Desolator | 98% of games | 14:45 | 2 (90%) |
| Orchid Malevolence | 57% of games | 20:45 | 3 (72%) |
| Crystalys | 61% of games | 27:15 | 6 (39%) |

Typical sequence: Power Treads → Desolator → Orchid Malevolence → Crystalys

**Turbo** · 89 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Desolator | 97% of games | 7:15 | 2 (53%) |
| Orchid Malevolence | 81% of games | 10:15 | 3 (49%) |
| Bloodthorn | 79% of games | 13:45 | 4 (43%) |
| Crystalys | 78% of games | 15:15 | 4 (28%) |
| Boots of Travel | 56% of games | 18:45 | 6 (20%) |

Typical sequence: Desolator → Orchid Malevolence → Bloodthorn → Crystalys → Boots of Travel

Same stealth-burst identity as carry, with the added mid-lane luxury of Crystalys (standard) or Orchid/Bloodthorn (turbo) to guarantee the kill lands once he decloaks.

### Dark Seer

#### Offlane

**Turbo** · 120 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Arcane Boots | 84% of games | 4:15 | 1 (72%) |
| Blink Dagger | 82% of games | 11:15 | 3 (26%) |
| Mekansm | 57% of games | 9:15 | 2 (42%) |
| Aghanim's Scepter | 68% of games | 13:15 | 3 (23%) |
| Guardian Greaves | 55% of games | 10:45 | 3 (39%) |

Typical sequence: Arcane Boots → Blink Dagger → Mekansm → Aghanim's Scepter → Guardian Greaves

Dark Seer supports the team as much as he fights: Arcane Boots and Mekansm feed his and his allies' mana/health for Vacuum-into-Wall of Replica combos, Blink Dagger lands that combo reliably, and Aghanim's Scepter and Guardian Greaves extend the same utility into the late game.

### Dawnbreaker

#### Offlane

**Standard** · 144 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 97% of games | 8:45 | 1 (97%) |
| Echo Sabre | 74% of games | 15:45 | 2 (86%) |
| Harpoon | 57% of games | 23:45 | 3 (57%) |
| Black King Bar | 56% of games | 29:45 | 4 (38%) |

Typical sequence: Phase Boots → Echo Sabre → Harpoon → Black King Bar

**Turbo** · 128 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 95% of games | 4:15 | 1 (97%) |
| Echo Sabre | 75% of games | 8:15 | 2 (74%) |
| Harpoon | 69% of games | 11:15 | 3 (56%) |
| Black King Bar | 59% of games | 16:45 | 4 (37%) |
| Assault Cuirass | 41% of games | 18:15 | 5 (34%) |
| Aghanim's Scepter | 50% of games | 19:45 | 5 (23%) |

Typical sequence: Phase Boots → Echo Sabre → Harpoon → Black King Bar → Assault Cuirass → Aghanim's Scepter

Dawnbreaker is a self-sufficient bruiser who wants to stay in a fight and heal off Solar Guardian; Phase Boots and Echo Sabre/Harpoon buy the stats and mobility to brawl, and Black King Bar (plus Assault Cuirass/Aghanim's Scepter in turbo) let her tank magic damage while landing Celestial Hammer returns.

### Death Prophet

#### Mid

**Standard** · 158 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Blink Dagger | 32% of games | 9:15 | 1 (92%) |
| Eul's Scepter of Divinity | 70% of games | 12:45 | 1 (58%) |
| Aghanim's Scepter | 60% of games | 20:15 | 2 (59%) |
| Boots of Travel | 62% of games | 19:45 | 3 (39%) |
| Black King Bar | 52% of games | 28:15 | 3 (36%) |

Typical sequence: Blink Dagger → Eul's Scepter of Divinity → Aghanim's Scepter → Boots of Travel → Black King Bar

**Turbo** · 128 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 59% of games | 5:15 | 1 (70%) |
| Eul's Scepter of Divinity | 85% of games | 7:45 | 2 (45%) |
| Aghanim's Scepter | 80% of games | 12:15 | 3 (41%) |
| Kaya | 48% of games | 15:15 | 4 (21%) |
| Sange | 45% of games | 16:15 | 5 (40%) |
| Black King Bar | 66% of games | 17:15 | 4 (35%) |
| Kaya and Sange | 45% of games | 16:15 | 7 (29%) |

Typical sequence: Phase Boots → Eul's Scepter of Divinity → Aghanim's Scepter → Kaya → Sange → Black King Bar → Kaya and Sange

Death Prophet's teamfighting hinges on standing still and channeling Exorcism, so Eul's Scepter of Divinity buys her a self-peel window and Aghanim's Scepter extends Exorcism's uptime and spirit count; boots (Blink in standard for a slower reposition, Phase in turbo) simply get her into channel range, and Black King Bar covers her thin HP pool.

### Doom

#### Offlane

**Standard** · 71 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 90% of games | 8:15 | 1 (75%) |
| Blink Dagger | 82% of games | 18:15 | 3 (64%) |

Typical sequence: Phase Boots → Blink Dagger

**Turbo** · 135 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 73% of games | 3:45 | 1 (91%) |
| Radiance | 53% of games | 9:45 | 2 (47%) |
| Blink Dagger | 84% of games | 9:45 | 3 (44%) |
| Black King Bar | 52% of games | 16:15 | 5 (33%) |
| Aghanim's Scepter | 68% of games | 19:15 | 6 (34%) |

Typical sequence: Phase Boots → Radiance → Blink Dagger → Black King Bar → Aghanim's Scepter

Doom needs to walk down one target and silence their items with his ultimate, so Phase Boots and Blink Dagger deliver him into range; turbo's faster farm adds Radiance for passive burn while he walks and Aghanim's Scepter to lock down a second hero.

### Drow Ranger

#### Carry

**Standard** · 214 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 100% of games | 7:45 | 1 (99%) |
| Yasha | 84% of games | 15:15 | 2 (51%) |
| Force Staff | 79% of games | 24:45 | 5 (54%) |
| Aghanim's Scepter | 32% of games | 35:45 | 8 (25%) |
| Butterfly | 48% of games | 34:45 | 7 (41%) |
| Black King Bar | 32% of games | 33:45 | 7 (34%) |
| Crystalys | 30% of games | 34:15 | 8 (31%) |

Typical sequence: Power Treads → Yasha → Force Staff → Aghanim's Scepter → Butterfly → Black King Bar → Crystalys

**Turbo** · 403 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 96% of games | 3:15 | 1 (98%) |
| Yasha | 57% of games | 8:15 | 3 (51%) |
| Force Staff | 74% of games | 11:45 | 3 (31%) |
| Shadow Blade | 33% of games | 12:45 | 3 (31%) |
| Butterfly | 74% of games | 17:15 | 7 (21%) |
| Crystalys | 57% of games | 17:45 | 9 (17%) |
| Black King Bar | 43% of games | 19:15 | 7 (21%) |
| Aghanim's Scepter | 48% of games | 18:45 | 3 (13%) |

Typical sequence: Power Treads → Yasha → Force Staff → Shadow Blade → Butterfly → Crystalys → Black King Bar → Aghanim's Scepter

Drow is a pure kiting right-clicker: Yasha and, later, Crystalys/Butterfly scale her attack speed and evasion, Force Staff gives the repositioning she has no other way to get, and Aghanim's Scepter/Black King Bar arrive as late luxuries once the core DPS package is funded.

#### Mid

**Turbo** · 113 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 57% of games | 3:45 | 1 (92%) |
| Yasha | 49% of games | 8:15 | 3 (45%) |
| Boots of Travel | 45% of games | 9:15 | 2 (47%) |
| Force Staff | 45% of games | 11:45 | 3 (35%) |
| Aghanim's Scepter | 54% of games | 17:15 | 5 (30%) |
| Butterfly | 66% of games | 17:45 | 7 (28%) |

Typical sequence: Power Treads → Yasha → Boots of Travel → Force Staff → Aghanim's Scepter → Butterfly

The mid version follows the same kiting-carry plan; the option of Boots of Travel reflects mid's stronger early gold lead letting her hit map-wide relevance sooner.

### Earthshaker

#### Mid

**Standard** · 72 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Blink Dagger | 99% of games | 11:15 | 1 (72%) |
| Kaya | 75% of games | 17:45 | 2 (43%) |

Typical sequence: Blink Dagger → Kaya

**Turbo** · 170 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Blink Dagger | 98% of games | 5:45 | 1 (66%) |
| Arcane Boots | 29% of games | 7:15 | 2 (76%) |
| Kaya | 71% of games | 12:15 | 3 (34%) |
| Aghanim's Scepter | 47% of games | 11:45 | 3 (44%) |
| Yasha | 59% of games | 14:45 | 6 (31%) |
| Refresher Orb | 45% of games | 17:15 | 4 (55%) |
| Crystalys | 32% of games | 13:15 | 8 (19%) |
| Black King Bar | 34% of games | 16:15 | 4 (22%) |
| Boots of Travel | 38% of games | 17:15 | 2 (29%) |
| Yasha and Kaya | 59% of games | 15:15 | 7 (38%) |

Typical sequence: Blink Dagger → Arcane Boots → Kaya → Aghanim's Scepter → Yasha → Refresher Orb → Crystalys → Black King Bar → Boots of Travel → Yasha and Kaya

Earthshaker's entire kit is Blink-into-Echo-Slam, so Blink Dagger is close to a day-one purchase; Kaya adds spell amplification to make that Echo Slam bigger, and the long turbo tail (Refresher Orb, Aghanim's Scepter) exists to double the same combo in extended games.

#### Offlane

**Standard** · 83 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Blink Dagger | 100% of games | 12:45 | 2 (76%) |
| Kaya | 66% of games | 20:15 | 3 (67%) |

Typical sequence: Blink Dagger → Kaya

**Turbo** · 160 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Arcane Boots | 46% of games | 3:45 | 1 (91%) |
| Blink Dagger | 95% of games | 6:45 | 2 (61%) |
| Kaya | 75% of games | 11:15 | 3 (51%) |
| Yasha | 62% of games | 15:15 | 4 (48%) |
| Aghanim's Scepter | 47% of games | 15:45 | 3 (24%) |
| Black King Bar | 51% of games | 17:45 | 3 (24%) |
| Yasha and Kaya | 62% of games | 15:15 | 5 (53%) |
| Refresher Orb | 54% of games | 21:15 | 6 (37%) |

Typical sequence: Arcane Boots → Blink Dagger → Kaya → Yasha → Aghanim's Scepter → Black King Bar → Yasha and Kaya → Refresher Orb

Same combo-first identity as mid — Blink Dagger and Kaya are the core, with Arcane Boots covering his mana-hungry stun chain once turbo games run long enough to need it.

### Enchantress

#### Mid

**Turbo** · 82 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Witch Blade | 83% of games | 8:15 | 2 (72%) |
| Boots of Travel | 82% of games | 9:45 | 3 (73%) |
| Force Staff | 96% of games | 13:15 | 4 (81%) |
| Aghanim's Scepter | 88% of games | 17:45 | 6 (81%) |
| Parasma | 73% of games | 19:45 | 7 (80%) |

Typical sequence: Witch Blade → Boots of Travel → Force Staff → Aghanim's Scepter → Parasma

Played as a farming carry, Enchantress leans on Impetus procs: Witch Blade adds cheap damage to that spell, Boots of Travel supports her strong sustained wave-clear and split push, and Aghanim's Scepter/Parasma turn her into a scaling spell-and-attack hybrid in the late game.

### Faceless Void

#### Carry

**Standard** · 226 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 99% of games | 7:45 | 1 (83%) |
| Battle Fury | 51% of games | 16:45 | 2 (76%) |
| Maelstrom | 50% of games | 18:15 | 3 (71%) |
| Yasha | 54% of games | 22:45 | 3 (62%) |
| Aghanim's Scepter | 33% of games | 30:45 | 5 (56%) |
| Crystalys | 34% of games | 30:45 | 6 (26%) |
| Black King Bar | 55% of games | 33:15 | 5 (35%) |
| Monkey King Bar | 28% of games | 38:15 | 6 (28%) |

Typical sequence: Power Treads → Battle Fury → Maelstrom → Yasha → Aghanim's Scepter → Crystalys → Black King Bar → Monkey King Bar

**Turbo** · 373 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 95% of games | 3:45 | 1 (86%) |
| Battle Fury | 34% of games | 8:15 | 2 (81%) |
| Maelstrom | 63% of games | 9:15 | 3 (52%) |
| Yasha | 48% of games | 11:45 | 3 (44%) |
| Black King Bar | 60% of games | 17:45 | 6 (23%) |
| Crystalys | 43% of games | 17:15 | 7 (19%) |
| Monkey King Bar | 41% of games | 19:15 | 5 (20%) |
| Butterfly | 41% of games | 19:15 | 7 (30%) |
| Aghanim's Scepter | 48% of games | 17:45 | 5 (26%) |

Typical sequence: Power Treads → Battle Fury → Maelstrom → Yasha → Black King Bar → Crystalys → Monkey King Bar → Butterfly → Aghanim's Scepter

Void farms fast with Battle Fury — Time Walk lets him reset positioning for safe split farming — and Maelstrom's cleave and proc rate multiply hard inside his own Chronosphere; Black King Bar, Monkey King Bar and Butterfly all exist to let him stand and swing uninterrupted while the ultimate is active.

### Gyrocopter

#### Carry

**Turbo** · 130 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 82% of games | 4:15 | 1 (96%) |
| Crystalys | 85% of games | 9:45 | 2 (38%) |
| Aghanim's Scepter | 81% of games | 10:45 | 3 (51%) |
| Black King Bar | 66% of games | 16:15 | 5 (33%) |

Typical sequence: Power Treads → Crystalys → Aghanim's Scepter → Black King Bar

Gyrocopter is a pure right-click carry whose Flak Cannon and Homing Missile want attack speed and crit, so Crystalys comes first for raw damage; Aghanim's Scepter upgrades Flak Cannon for teamfight cleave, and Black King Bar lets him stand still and channel through disables.

### Juggernaut

#### Carry

**Standard** · 368 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 81% of games | 7:15 | 1 (75%) |
| Battle Fury | 88% of games | 14:45 | 2 (72%) |
| Yasha | 85% of games | 19:15 | 3 (79%) |
| Blink Dagger | 55% of games | 26:45 | 6 (25%) |
| Butterfly | 52% of games | 30:15 | 5 (47%) |
| Aghanim's Scepter | 56% of games | 31:45 | 6 (47%) |
| Monkey King Bar | 25% of games | 34:15 | 5 (25%) |
| Skull Basher | 22% of games | 35:15 | 7 (29%) |
| Swift Blink | 21% of games | 41:15 | 8 (51%) |

Typical sequence: Power Treads → Battle Fury → Yasha → Blink Dagger → Butterfly → Aghanim's Scepter → Monkey King Bar → Skull Basher → Swift Blink

**Turbo** · 475 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 43% of games | 3:15 | 1 (92%) |
| Power Treads | 54% of games | 3:15 | 1 (89%) |
| Battle Fury | 53% of games | 7:45 | 2 (84%) |
| Maelstrom | 34% of games | 6:45 | 2 (71%) |
| Yasha | 63% of games | 10:15 | 3 (64%) |
| Blink Dagger | 70% of games | 14:15 | 6 (21%) |
| Butterfly | 62% of games | 16:45 | 6 (27%) |
| Aghanim's Scepter | 78% of games | 17:15 | 5 (21%) |
| Monkey King Bar | 33% of games | 18:15 | 6 (20%) |
| Skull Basher | 40% of games | 18:15 | 7 (28%) |
| Sange | 37% of games | 20:15 | 8 (26%) |
| Swift Blink | 44% of games | 21:15 | 9 (20%) |
| Abyssal Blade | 30% of games | 21:45 | 9 (33%) |

Typical sequence: Phase Boots → Power Treads → Battle Fury → Maelstrom → Yasha → Blink Dagger → Butterfly → Aghanim's Scepter → Monkey King Bar → Skull Basher → Sange → Swift Blink → Abyssal Blade

Jugg farms fast with Battle Fury and Blade Fury, then layers Yasha, Butterfly and Monkey King Bar for the evasion and accuracy that make Omnislash connect; Blink Dagger lands the ultimate safely, and turbo's extra time supports Aghanim's Scepter and Swift Blink for repeated Omnislash resets.

### Kunkka

#### Mid

**Turbo** · 121 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 83% of games | 3:15 | 1 (98%) |
| Crystalys | 87% of games | 7:15 | 2 (52%) |
| Shadow Blade | 65% of games | 13:15 | 4 (23%) |
| Aghanim's Scepter | 64% of games | 22:45 | 8 (22%) |

Typical sequence: Phase Boots → Crystalys → Shadow Blade → Aghanim's Scepter

Kunkka wants to isolate one target with Tidebringer cleave and Torrent; Crystalys speeds up his early damage and farm, Shadow Blade gives him a surprise-initiation option beyond X Marks the Spot, and Aghanim's Scepter is a late luxury once the kill pattern is established.

#### Offlane

**Standard** · 111 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 97% of games | 7:15 | 1 (100%) |
| Crystalys | 65% of games | 19:45 | 4 (51%) |
| Shadow Blade | 50% of games | 19:45 | 3 (69%) |

Typical sequence: Phase Boots → Crystalys → Shadow Blade

**Turbo** · 88 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 74% of games | 3:45 | 1 (97%) |
| Crystalys | 67% of games | 8:45 | 2 (44%) |
| Aghanim's Scepter | 62% of games | 14:15 | 3 (33%) |

Typical sequence: Phase Boots → Crystalys → Aghanim's Scepter

Same Phase Boots-into-Crystalys-into-Shadow Blade core as mid; Aghanim's Scepter only shows up in turbo's longer games once the isolate-and-cleave pattern is already funded.

### Legion Commander

#### Carry

**Turbo** · 68 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Blink Dagger | 96% of games | 7:15 | 2 (40%) |
| Blade Mail | 93% of games | 7:45 | 2 (52%) |

Typical sequence: Blink Dagger → Blade Mail

Legion Commander needs to land Duel on the right target and win the trade, so Blink Dagger delivers her and Blade Mail punishes whoever bursts her or trades damage back during the Duel.

#### Mid

**Turbo** · 54 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Blink Dagger | 94% of games | 7:15 | 2 (47%) |

Typical sequence: Blink Dagger

Same Duel-first logic as carry — Blink Dagger alone clears the bar at this sample size, reflecting how completely her early game revolves around a single reliable initiation tool.

#### Offlane

**Standard** · 215 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 91% of games | 7:15 | 1 (94%) |
| Blink Dagger | 97% of games | 14:45 | 2 (61%) |
| Blade Mail | 98% of games | 17:45 | 3 (59%) |
| Black King Bar | 64% of games | 30:15 | 4 (77%) |
| Crystalys | 25% of games | 32:15 | 5 (42%) |
| Assault Cuirass | 25% of games | 37:45 | 5 (60%) |

Typical sequence: Phase Boots → Blink Dagger → Blade Mail → Black King Bar → Crystalys → Assault Cuirass

**Turbo** · 214 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 83% of games | 4:15 | 1 (81%) |
| Blade Mail | 96% of games | 7:45 | 2 (40%) |
| Blink Dagger | 99% of games | 8:15 | 2 (51%) |
| Black King Bar | 57% of games | 16:15 | 4 (43%) |
| Crystalys | 32% of games | 17:15 | 4 (31%) |
| Assault Cuirass | 27% of games | 18:15 | 6 (30%) |
| Aghanim's Scepter | 47% of games | 18:45 | 4 (31%) |

Typical sequence: Phase Boots → Blade Mail → Blink Dagger → Black King Bar → Crystalys → Assault Cuirass → Aghanim's Scepter

The offlane version farms longer before her first pick-off, adding Phase Boots, Black King Bar, Crystalys and Assault Cuirass/Aghanim's Scepter around the same Blink-into-Duel-into-Blade Mail core.

### Leshrac

#### Mid

**Turbo** · 58 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Kaya | 91% of games | 7:15 | 2 (57%) |

Typical sequence: Kaya

Leshrac's damage is almost entirely spell-based across Split Earth, Diabolic Edict and Lightning Storm, so Kaya's spell amplification is close to a mandatory first key item; nothing else clears the population bar because his follow-up items vary too much game to game.

### Lion

#### Mid

**Turbo** · 105 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Blink Dagger | 95% of games | 6:15 | 2 (57%) |
| Aghanim's Scepter | 76% of games | 11:45 | 3 (32%) |
| Echo Sabre | 50% of games | 12:15 | 3 (42%) |

Typical sequence: Blink Dagger → Aghanim's Scepter → Echo Sabre

Lion is a pick-off hero who needs Blink Dagger to land Hex-into-Finger of Death; Aghanim's Scepter upgrades Mana Drain for extra damage, and Echo Sabre adds stats so he survives being dove himself.

### Luna

#### Carry

**Standard** · 187 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 100% of games | 6:15 | 1 (99%) |
| Yasha | 98% of games | 14:45 | 3 (82%) |
| Butterfly | 62% of games | 28:15 | 5 (37%) |
| Black King Bar | 64% of games | 28:15 | 6 (43%) |
| Force Staff | 27% of games | 28:45 | 7 (36%) |

Typical sequence: Power Treads → Yasha → Butterfly → Black King Bar → Force Staff

**Turbo** · 255 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 98% of games | 3:45 | 1 (92%) |
| Yasha | 92% of games | 7:45 | 3 (56%) |
| Black King Bar | 69% of games | 16:15 | 5 (31%) |
| Butterfly | 71% of games | 16:15 | 5 (28%) |
| Aghanim's Scepter | 54% of games | 16:45 | 4 (22%) |
| Crystalys | 38% of games | 18:45 | 7 (26%) |
| Blink Dagger | 22% of games | 19:45 | 6 (30%) |

Typical sequence: Power Treads → Yasha → Black King Bar → Butterfly → Aghanim's Scepter → Crystalys → Blink Dagger

Luna's Lucent Beam and Moon Glaives reward attack speed and evasion, so Yasha and Butterfly are natural fits; Force Staff covers her lack of a built-in escape, and turbo's faster pace adds Aghanim's Scepter or Blink Dagger for extra utility.

#### Mid

**Turbo** · 74 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 69% of games | 3:45 | 1 (96%) |
| Yasha | 80% of games | 7:45 | 2 (47%) |
| Aghanim's Scepter | 76% of games | 14:45 | 5 (29%) |
| Black King Bar | 69% of games | 16:45 | 4 (25%) |

Typical sequence: Power Treads → Yasha → Aghanim's Scepter → Black King Bar

Same Power Treads-into-Yasha spine as carry, with Aghanim's Scepter and Black King Bar arriving faster thanks to mid's stronger early gold.

### Magnus

#### Mid

**Turbo** · 64 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Blink Dagger | 98% of games | 6:15 | 1 (38%) |

Typical sequence: Blink Dagger

Magnus mid is entirely about landing Reverse Polarity, so Blink Dagger is close to automatic and nothing else consistently clears the bar at this sample size.

#### Offlane

**Standard** · 166 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 69% of games | 7:45 | 1 (90%) |
| Blink Dagger | 100% of games | 13:15 | 2 (80%) |
| Echo Sabre | 41% of games | 20:15 | 3 (69%) |
| Aghanim's Scepter | 36% of games | 27:45 | 3 (48%) |
| Harpoon | 35% of games | 25:45 | 4 (72%) |
| Black King Bar | 51% of games | 32:15 | 5 (36%) |

Typical sequence: Power Treads → Blink Dagger → Echo Sabre → Aghanim's Scepter → Harpoon → Black King Bar

**Turbo** · 136 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 61% of games | 4:15 | 1 (78%) |
| Blink Dagger | 99% of games | 7:15 | 2 (56%) |
| Echo Sabre | 67% of games | 9:45 | 3 (51%) |
| Harpoon | 62% of games | 12:15 | 4 (54%) |
| Aghanim's Scepter | 40% of games | 16:45 | 6 (28%) |
| Black King Bar | 51% of games | 17:45 | 5 (36%) |

Typical sequence: Power Treads → Blink Dagger → Echo Sabre → Harpoon → Aghanim's Scepter → Black King Bar

The offlane version farms a little longer before the same Reverse-Polarity-first identity: Power Treads and Echo Sabre/Harpoon add stats first, then Blink Dagger and Aghanim's Scepter (longer Empower duration) extend his relevance into extra teamfights.

### Medusa

#### Carry

**Standard** · 113 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 99% of games | 7:15 | 1 (100%) |
| Yasha | 99% of games | 12:15 | 2 (96%) |
| Manta Style | 99% of games | 17:15 | 3 (93%) |
| Butterfly | 70% of games | 25:15 | 4 (90%) |
| Eye of Skadi | 59% of games | 32:15 | 5 (73%) |

Typical sequence: Power Treads → Yasha → Manta Style → Butterfly → Eye of Skadi

**Turbo** · 68 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 93% of games | 3:45 | 1 (94%) |
| Yasha | 91% of games | 7:15 | 2 (71%) |
| Manta Style | 90% of games | 9:45 | 3 (72%) |
| Butterfly | 74% of games | 15:45 | 4 (50%) |

Typical sequence: Power Treads → Yasha → Manta Style → Butterfly

Medusa scales through raw stats since Mystic Snake and Split Shot both reward Intelligence and attack speed; Manta Style cleanses illusions/debuffs cheaply, and Eye of Skadi/Butterfly are the standard armor-and-slow package for a ranged carry with no other escape.

### Meepo

#### Carry

**Standard** · 131 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 99% of games | 6:45 | 1 (92%) |
| Yasha | 85% of games | 11:45 | 2 (95%) |
| Sange and Yasha | 80% of games | 14:45 | 3 (79%) |
| Sange | 80% of games | 14:45 | 4 (80%) |
| Aghanim's Scepter | 42% of games | 31:15 | 6 (60%) |
| Eye of Skadi | 92% of games | 22:15 | 5 (97%) |

Typical sequence: Power Treads → Yasha → Sange and Yasha → Sange → Aghanim's Scepter → Eye of Skadi

Every clone needs the same items, so Meepo's 'build order' is really five copies of the same stat items bought in sequence — Power Treads, Yasha and Sange and Yasha come first because they multiply across clones, and Aghanim's Scepter/Eye of Skadi arrive once the fivefold gold income supports them.

### Monkey King

#### Carry

**Turbo** · 98 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 71% of games | 3:15 | 1 (99%) |
| Echo Sabre | 74% of games | 7:15 | 2 (68%) |
| Black King Bar | 81% of games | 15:15 | 4 (42%) |
| Harpoon | 58% of games | 15:15 | 5 (46%) |

Typical sequence: Power Treads → Echo Sabre → Black King Bar → Harpoon

Monkey King relies on Jingu Mastery stacks and Wukong's Command positioning; Echo Sabre gives cheap early stats and mobility, and Black King Bar/Harpoon let him stand in a fight and run down kited targets.

### Morphling

#### Carry

**Standard** · 92 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 100% of games | 6:45 | 1 (100%) |
| Vladmir's Offering | 75% of games | 12:15 | 2 (99%) |
| Yasha | 100% of games | 16:45 | 3 (70%) |
| Butterfly | 63% of games | 30:15 | 5 (53%) |

Typical sequence: Power Treads → Vladmir's Offering → Yasha → Butterfly

**Turbo** · 93 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 98% of games | 3:45 | 1 (98%) |
| Vladmir's Offering | 70% of games | 6:45 | 2 (97%) |
| Yasha | 99% of games | 9:15 | 3 (71%) |
| Butterfly | 62% of games | 16:15 | 5 (60%) |

Typical sequence: Power Treads → Vladmir's Offering → Yasha → Butterfly

Morphling wants attribute-shift flexibility plus cheap lifesteal to duel; Vladmir's Offering supplies that lifesteal and an aura early, and the Yasha-into-Butterfly spine is the standard evasion/attack-speed package for a ranged carry that already has strong native survivability via Waveform and Morph.

### Muerta

#### Carry

**Standard** · 64 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 100% of games | 7:15 | 1 (94%) |
| Maelstrom | 97% of games | 14:45 | 2 (89%) |

Typical sequence: Power Treads → Maelstrom

**Turbo** · 108 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 89% of games | 4:15 | 1 (95%) |
| Maelstrom | 96% of games | 8:15 | 2 (76%) |
| Force Staff | 48% of games | 14:45 | 5 (38%) |
| Black King Bar | 58% of games | 16:45 | 7 (27%) |
| Crystalys | 71% of games | 17:15 | 8 (22%) |

Typical sequence: Power Treads → Maelstrom → Force Staff → Black King Bar → Crystalys

Muerta's Dead Shot and gun spray want attack speed and a cheap proc item, so Maelstrom is the natural first spike; the turbo tail of Force Staff, Black King Bar and Crystalys covers survivability and mobility for the longer games turbo tends to produce.

### Nature's Prophet

#### Carry

**Turbo** · 91 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 86% of games | 3:45 | 1 (79%) |
| Maelstrom | 76% of games | 7:15 | 2 (64%) |

Typical sequence: Power Treads → Maelstrom

Nature's Prophet's game plan is global split-push farm efficiency through Sprout and Teleportation, so Power Treads into Maelstrom's cheap cleave is his first spike regardless of role.

#### Mid

**Turbo** · 148 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 85% of games | 3:15 | 1 (84%) |
| Maelstrom | 68% of games | 7:15 | 2 (53%) |
| Orchid Malevolence | 64% of games | 8:45 | 2 (37%) |
| Shadow Blade | 36% of games | 14:45 | 4 (22%) |
| Bloodthorn | 51% of games | 15:15 | 5 (28%) |
| Crystalys | 47% of games | 16:15 | 4 (26%) |
| Black King Bar | 43% of games | 15:45 | 4 (23%) |

Typical sequence: Power Treads → Maelstrom → Orchid Malevolence → Shadow Blade → Bloodthorn → Crystalys → Black King Bar

Same farm-efficiency identity as carry, with the mid sample adding pick-off tools — Orchid Malevolence, Shadow Blade, Bloodthorn — because a mid Nature's Prophet is also expected to gank off his global Teleportation.

#### Offlane

**Turbo** · 75 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 83% of games | 3:45 | 1 (76%) |
| Maelstrom | 69% of games | 7:45 | 2 (65%) |

Typical sequence: Power Treads → Maelstrom

Same Power Treads-into-Maelstrom core as the other roles; the offlane sample is smaller so fewer follow-up items clear the bar.

### Night Stalker

#### Offlane

**Standard** · 132 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 95% of games | 7:15 | 1 (96%) |
| Echo Sabre | 86% of games | 14:15 | 2 (78%) |
| Blink Dagger | 89% of games | 17:15 | 3 (72%) |
| Black King Bar | 73% of games | 26:45 | 4 (65%) |
| Harpoon | 44% of games | 32:15 | 5 (34%) |

Typical sequence: Phase Boots → Echo Sabre → Blink Dagger → Black King Bar → Harpoon

**Turbo** · 80 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 90% of games | 4:15 | 1 (93%) |
| Echo Sabre | 81% of games | 7:45 | 2 (62%) |
| Blink Dagger | 79% of games | 8:45 | 3 (44%) |
| Black King Bar | 70% of games | 15:45 | 4 (45%) |

Typical sequence: Phase Boots → Echo Sabre → Blink Dagger → Black King Bar

Night Stalker needs to close distance at night with Void and Hunter in the Night, so Phase Boots and Echo Sabre buy early mobility and stats, Blink Dagger extends his gap-close range further, and Black King Bar protects him from being burst down before he can initiate.

### Nyx Assassin

#### Offlane

**Turbo** · 93 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Arcane Boots | 61% of games | 3:45 | 1 (93%) |
| Dagon | 76% of games | 8:15 | 2 (55%) |
| Dagon 2 | 70% of games | 10:15 | 3 (55%) |
| Dagon 3 | 70% of games | 11:45 | 4 (51%) |
| Aghanim's Scepter | 73% of games | 15:45 | 2 (22%) |
| Dagon 4 | 67% of games | 13:15 | 5 (52%) |
| Dagon 5 | 62% of games | 15:15 | 6 (48%) |

Typical sequence: Arcane Boots → Dagon → Dagon 2 → Dagon 3 → Aghanim's Scepter → Dagon 4 → Dagon 5

Nyx's Dagon rush is a known burst build: Vendetta stealth guarantees the first hit, so stacking Dagon upgrades is a reliable one-shot combo, Arcane Boots cover the mana cost of casting it repeatedly, and Aghanim's Scepter (Mana Burn upgrade) rounds out the pure-magic-damage kit.

### Ogre Magi

#### Mid

**Turbo** · 155 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Arcane Boots | 37% of games | 3:15 | 1 (81%) |
| Hand of Midas | 92% of games | 5:15 | 1 (59%) |
| Blink Dagger | 80% of games | 9:15 | 3 (64%) |
| Boots of Travel | 50% of games | 8:15 | 2 (53%) |
| Aghanim's Scepter | 77% of games | 12:45 | 4 (28%) |
| Scythe of Vyse | 59% of games | 17:15 | 4 (26%) |
| Overwhelming Blink | 35% of games | 23:45 | 9 (22%) |

Typical sequence: Arcane Boots → Hand of Midas → Blink Dagger → Boots of Travel → Aghanim's Scepter → Scythe of Vyse → Overwhelming Blink

Ogre is unusually tanky and mana-efficient for a hero that plays like a semi-carry, so Hand of Midas accelerates his farm; Blink Dagger and Aghanim's Scepter both improve Fireblast/Multicast reliability, and Overwhelming Blink adds the mobility a naturally slow hero lacks.

#### Offlane

**Turbo** · 118 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Arcane Boots | 52% of games | 3:45 | 1 (80%) |
| Hand of Midas | 93% of games | 5:45 | 2 (53%) |
| Blink Dagger | 64% of games | 10:15 | 3 (34%) |
| Aghanim's Scepter | 68% of games | 12:45 | 3 (30%) |
| Scythe of Vyse | 45% of games | 17:45 | 5 (26%) |

Typical sequence: Arcane Boots → Hand of Midas → Blink Dagger → Aghanim's Scepter → Scythe of Vyse

Same Hand of Midas-first plan as mid; Scythe of Vyse gives a hard lockdown for allies to follow up on once his own Fireblast/Multicast combo is funded.

### Outworld Devourer

#### Mid

**Standard** · 88 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 80% of games | 6:45 | 1 (86%) |
| Witch Blade | 88% of games | 14:45 | 2 (70%) |
| Force Staff | 66% of games | 23:15 | 4 (41%) |

Typical sequence: Power Treads → Witch Blade → Force Staff

**Turbo** · 119 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 80% of games | 3:45 | 1 (89%) |
| Witch Blade | 89% of games | 7:15 | 2 (67%) |
| Blink Dagger | 82% of games | 9:15 | 3 (51%) |
| Force Staff | 71% of games | 11:15 | 4 (28%) |
| Black King Bar | 50% of games | 17:45 | 7 (23%) |
| Scythe of Vyse | 52% of games | 18:45 | 8 (23%) |
| Aghanim's Scepter | 57% of games | 18:15 | 7 (29%) |
| Parasma | 64% of games | 19:15 | 8 (29%) |

Typical sequence: Power Treads → Witch Blade → Blink Dagger → Force Staff → Black King Bar → Scythe of Vyse → Aghanim's Scepter → Parasma

OD's Arcane Orb hits harder with more Intelligence, so Witch Blade adds cheap Intelligence and damage on top of it; Force Staff (and, in turbo, Blink Dagger) cover his lack of built-in mobility, and Aghanim's Scepter/Scythe of Vyse extend Astral Imprisonment control in longer games.

### Pangolier

#### Mid

**Turbo** · 76 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Diffusal Blade | 92% of games | 6:15 | 1 (63%) |
| Blink Dagger | 78% of games | 10:45 | 3 (59%) |
| Aghanim's Scepter | 91% of games | 13:15 | 4 (45%) |
| Skull Basher | 76% of games | 16:45 | 5 (40%) |

Typical sequence: Diffusal Blade → Blink Dagger → Aghanim's Scepter → Skull Basher

Pangolier's Swashbuckle-into-Rolling Thunder combo wants attack speed and a way to keep a target in place, so Diffusal Blade's mana burn and slow come first; Blink Dagger and Skull Basher both help lock a target down for the stun-lock combo, and Aghanim's Scepter extends Shield Crash uptime.

#### Offlane

**Turbo** · 86 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 66% of games | 7:45 | 2 (47%) |
| Diffusal Blade | 65% of games | 8:15 | 2 (43%) |
| Aghanim's Scepter | 84% of games | 14:15 | 3 (43%) |
| Blink Dagger | 67% of games | 12:45 | 3 (40%) |
| Skull Basher | 77% of games | 16:45 | 5 (33%) |

Typical sequence: Power Treads → Diffusal Blade → Aghanim's Scepter → Blink Dagger → Skull Basher

Same combo-first plan as mid, with Power Treads added first since the offlane version farms a touch longer before committing to fights.

### Phantom Assassin

#### Carry

**Standard** · 237 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 95% of games | 7:45 | 1 (79%) |
| Battle Fury | 94% of games | 16:15 | 2 (73%) |
| Desolator | 72% of games | 22:45 | 3 (76%) |
| Black King Bar | 83% of games | 27:45 | 4 (57%) |
| Skull Basher | 67% of games | 30:45 | 5 (59%) |
| Sange | 48% of games | 35:45 | 6 (42%) |
| Abyssal Blade | 45% of games | 37:15 | 7 (43%) |

Typical sequence: Power Treads → Battle Fury → Desolator → Black King Bar → Skull Basher → Sange → Abyssal Blade

**Turbo** · 508 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 89% of games | 3:45 | 1 (83%) |
| Battle Fury | 65% of games | 8:15 | 2 (79%) |
| Desolator | 81% of games | 9:45 | 3 (43%) |
| Black King Bar | 84% of games | 13:45 | 4 (44%) |
| Skull Basher | 78% of games | 15:15 | 5 (38%) |
| Sange | 66% of games | 18:45 | 6 (39%) |
| Monkey King Bar | 21% of games | 20:15 | 8 (25%) |
| Abyssal Blade | 64% of games | 19:15 | 7 (38%) |
| Aghanim's Scepter | 32% of games | 23:45 | 9 (36%) |

Typical sequence: Power Treads → Battle Fury → Desolator → Black King Bar → Skull Basher → Sange → Monkey King Bar → Abyssal Blade → Aghanim's Scepter

PA is a critical-strike snowball carry: Battle Fury and Desolator both push her farm and crit damage up quickly, Black King Bar lets her survive disables that would otherwise stop Coup de Grace RNG from ever landing, and Skull Basher/Abyssal Blade lock a target in place long enough for a crit to connect.

#### Mid

**Turbo** · 86 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 65% of games | 3:45 | 1 (71%) |
| Desolator | 73% of games | 8:15 | 2 (40%) |
| Black King Bar | 67% of games | 13:45 | 4 (45%) |

Typical sequence: Power Treads → Desolator → Black King Bar

Same Power Treads-into-Desolator-into-Black King Bar core as carry, compressed into a shorter build since mid PA farms less before her first fight.

#### Offlane

**Turbo** · 59 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 86% of games | 4:15 | 1 (61%) |

Typical sequence: Power Treads

The offlane sample only clears Power Treads at this size, reflecting a smaller, more cautious build than her core-role farm pattern.

### Phantom Lancer

#### Carry

**Standard** · 423 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 99% of games | 6:45 | 1 (90%) |
| Yasha | 99% of games | 12:15 | 2 (85%) |
| Aghanim's Scepter | 89% of games | 22:15 | 4 (70%) |
| Orchid Malevolence | 64% of games | 31:15 | 5 (44%) |
| Eye of Skadi | 59% of games | 33:15 | 5 (51%) |
| Butterfly | 24% of games | 36:15 | 5 (34%) |
| Bloodthorn | 52% of games | 34:45 | 7 (42%) |

Typical sequence: Power Treads → Yasha → Aghanim's Scepter → Orchid Malevolence → Eye of Skadi → Butterfly → Bloodthorn

**Turbo** · 221 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 98% of games | 3:15 | 1 (88%) |
| Yasha | 90% of games | 6:45 | 2 (74%) |
| Diffusal Blade | 23% of games | 8:15 | 2 (44%) |
| Aghanim's Scepter | 78% of games | 12:15 | 4 (41%) |
| Orchid Malevolence | 69% of games | 13:45 | 5 (36%) |
| Bloodthorn | 62% of games | 18:15 | 7 (34%) |
| Eye of Skadi | 66% of games | 18:45 | 5 (28%) |
| Butterfly | 38% of games | 20:15 | 9 (22%) |

Typical sequence: Power Treads → Yasha → Diffusal Blade → Aghanim's Scepter → Orchid Malevolence → Bloodthorn → Eye of Skadi → Butterfly

PL's whole plan is illusion volume and stats that multiply across every clone; Yasha and Aghanim's Scepter (an extra illusion) both scale that multiplier hardest, and Orchid Malevolence/Bloodthorn add single-target lockdown since his damage alone can otherwise be kited around.

### Primal Beast

#### Mid

**Standard** · 59 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 100% of games | 6:45 | 1 (100%) |
| Blink Dagger | 85% of games | 16:15 | 2 (88%) |

Typical sequence: Phase Boots → Blink Dagger

Primal Beast mid is a pure Onslaught-into-Trample initiator, so Phase Boots and Blink Dagger to close distance and land the stun chain make up close to the entire build at this sample size.

#### Offlane

**Turbo** · 94 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 89% of games | 3:45 | 1 (88%) |
| Aghanim's Scepter | 81% of games | 15:15 | 3 (32%) |

Typical sequence: Phase Boots → Aghanim's Scepter

Same initiation-first logic as mid, with Aghanim's Scepter (longer Uproar knockback range) replacing Blink Dagger in the turbo sample.

### Puck

#### Mid

**Standard** · 157 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 97% of games | 8:45 | 1 (68%) |
| Witch Blade | 97% of games | 13:45 | 2 (64%) |
| Blink Dagger | 94% of games | 18:45 | 3 (84%) |
| Eul's Scepter of Divinity | 35% of games | 26:45 | 4 (44%) |
| Parasma | 59% of games | 26:45 | 4 (58%) |
| Aghanim's Scepter | 41% of games | 33:45 | 5 (50%) |

Typical sequence: Power Treads → Witch Blade → Blink Dagger → Eul's Scepter of Divinity → Parasma → Aghanim's Scepter

**Turbo** · 104 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 80% of games | 4:15 | 1 (86%) |
| Witch Blade | 96% of games | 7:45 | 2 (62%) |
| Blink Dagger | 92% of games | 9:45 | 3 (68%) |
| Parasma | 67% of games | 17:15 | 4 (46%) |
| Aghanim's Scepter | 62% of games | 17:45 | 5 (42%) |

Typical sequence: Power Treads → Witch Blade → Blink Dagger → Parasma → Aghanim's Scepter

Puck's Illusory Orb-into-Phase Shift kit is a pick-off mid: Witch Blade adds cheap Intelligence and damage to Orb, Blink Dagger extends her already strong mobility for a guaranteed initiation, and Eul's Scepter/Aghanim's Scepter round out survivability and repeat burst.

### Pudge

#### Carry

**Turbo** · 88 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Blink Dagger | 90% of games | 8:45 | 2 (32%) |
| Aghanim's Scepter | 78% of games | 13:45 | 3 (29%) |

Typical sequence: Blink Dagger → Aghanim's Scepter

Pudge is a Hook-first pick-off hero in any role, so Blink Dagger for reliable Hook range and Aghanim's Scepter for extra cast range and cooldown reduction define the build regardless of where he's played.

#### Mid

**Turbo** · 261 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 50% of games | 3:45 | 1 (81%) |
| Blink Dagger | 94% of games | 6:15 | 2 (48%) |
| Vanguard | 20% of games | 6:45 | 1 (43%) |
| Blade Mail | 42% of games | 10:45 | 3 (35%) |
| Aghanim's Scepter | 82% of games | 12:15 | 3 (47%) |
| Boots of Travel | 31% of games | 13:15 | 2 (25%) |
| Pipe of Insight | 24% of games | 15:15 | 5 (42%) |
| Overwhelming Blink | 26% of games | 24:45 | 7 (34%) |

Typical sequence: Phase Boots → Blink Dagger → Vanguard → Blade Mail → Aghanim's Scepter → Boots of Travel → Pipe of Insight → Overwhelming Blink

Same Hook-first identity as carry, with Phase Boots and Vanguard added as he plays more like a tanky roamer who also has to hold a mid lane.

#### Offlane

**Standard** · 61 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 87% of games | 8:15 | 1 (89%) |
| Blink Dagger | 88% of games | 16:15 | 2 (69%) |

Typical sequence: Phase Boots → Blink Dagger

**Turbo** · 271 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 36% of games | 3:45 | 1 (91%) |
| Tranquil Boots | 22% of games | 2:15 | 1 (90%) |
| Vanguard | 26% of games | 3:45 | 1 (77%) |
| Blink Dagger | 88% of games | 7:15 | 2 (52%) |
| Blade Mail | 42% of games | 9:45 | 2 (37%) |
| Aghanim's Scepter | 78% of games | 13:15 | 3 (37%) |
| Black King Bar | 27% of games | 18:15 | 4 (31%) |
| Boots of Travel | 30% of games | 16:45 | 7 (19%) |
| Lotus Orb | 29% of games | 17:45 | 4 (32%) |

Typical sequence: Phase Boots → Tranquil Boots → Vanguard → Blink Dagger → Blade Mail → Aghanim's Scepter → Black King Bar → Boots of Travel → Lotus Orb

Same Blink-into-Aghanim's core, with Vanguard, Blade Mail and Tranquil/Boots of Travel reflecting his job as a tanky, disruptive laner rather than a pure right-click threat.

### Queen of Pain

#### Mid

**Standard** · 292 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 85% of games | 8:15 | 1 (98%) |
| Kaya | 90% of games | 13:45 | 2 (63%) |
| Sange | 56% of games | 21:15 | 3 (47%) |
| Aghanim's Scepter | 68% of games | 23:45 | 3 (38%) |
| Kaya and Sange | 56% of games | 21:45 | 4 (47%) |
| Veil of Discord | 34% of games | 29:15 | 7 (19%) |
| Eul's Scepter of Divinity | 27% of games | 31:15 | 6 (17%) |
| Black King Bar | 28% of games | 32:45 | 6 (28%) |
| Bloodstone | 27% of games | 33:45 | 8 (23%) |

Typical sequence: Power Treads → Kaya → Sange → Aghanim's Scepter → Kaya and Sange → Veil of Discord → Eul's Scepter of Divinity → Black King Bar → Bloodstone

**Turbo** · 283 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 56% of games | 4:45 | 1 (93%) |
| Kaya | 80% of games | 7:15 | 2 (45%) |
| Orchid Malevolence | 27% of games | 9:15 | 2 (50%) |
| Boots of Travel | 38% of games | 8:15 | 2 (40%) |
| Sange | 68% of games | 12:15 | 3 (34%) |
| Aghanim's Scepter | 74% of games | 14:45 | 4 (18%) |
| Eul's Scepter of Divinity | 41% of games | 15:45 | 3 (19%) |
| Kaya and Sange | 68% of games | 12:15 | 4 (35%) |
| Veil of Discord | 22% of games | 15:45 | 6 (25%) |
| Black King Bar | 37% of games | 17:45 | 6 (22%) |
| Linken's Sphere | 31% of games | 18:45 | 6 (29%) |
| Wind Waker | 23% of games | 23:45 | 9 (26%) |

Typical sequence: Power Treads → Kaya → Orchid Malevolence → Boots of Travel → Sange → Aghanim's Scepter → Eul's Scepter of Divinity → Kaya and Sange → Veil of Discord → Black King Bar → Linken's Sphere → Wind Waker

QoP is a spell-damage burst mid built around Sonic Wave and Scream of Pain, so the Kaya line is close to mandatory for spell amplification, and Aghanim's Scepter (Blink cooldown reduction) keeps her pick-off tempo up between rotations.

### Razor

#### Carry

**Turbo** · 122 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 63% of games | 3:45 | 1 (94%) |
| Yasha | 68% of games | 7:45 | 2 (39%) |
| Sange | 52% of games | 9:15 | 4 (28%) |
| Sange and Yasha | 50% of games | 9:45 | 3 (30%) |
| Black King Bar | 67% of games | 14:45 | 5 (26%) |
| Aghanim's Scepter | 43% of games | 22:15 | 9 (21%) |

Typical sequence: Power Treads → Yasha → Sange → Sange and Yasha → Black King Bar → Aghanim's Scepter

Razor wins fights by right-clicking through Static Link, so attack-speed and stat items like Yasha and Sange and Yasha come first, and Black King Bar lets him stand in range of a linked target instead of being disabled out of the fight.

#### Mid

**Turbo** · 147 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 60% of games | 4:15 | 1 (93%) |
| Yasha | 63% of games | 8:45 | 2 (30%) |
| Sange | 38% of games | 11:15 | 4 (30%) |
| Sange and Yasha | 35% of games | 11:45 | 5 (29%) |
| Black King Bar | 52% of games | 15:45 | 4 (26%) |
| Aghanim's Scepter | 47% of games | 20:15 | 5 (19%) |

Typical sequence: Power Treads → Yasha → Sange → Sange and Yasha → Black King Bar → Aghanim's Scepter

Same Yasha-into-Sange and Yasha spine as carry, reflecting the same right-click-through-Link game plan in the mid lane.

#### Offlane

**Turbo** · 243 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 35% of games | 3:45 | 1 (92%) |
| Power Treads | 54% of games | 3:15 | 1 (95%) |
| Blade Mail | 26% of games | 7:15 | 2 (77%) |
| Orchid Malevolence | 32% of games | 8:15 | 2 (59%) |
| Yasha | 58% of games | 9:15 | 2 (35%) |
| Sange | 28% of games | 11:45 | 3 (26%) |
| Sange and Yasha | 28% of games | 12:45 | 4 (34%) |
| Black King Bar | 76% of games | 15:45 | 4 (36%) |
| Bloodthorn | 21% of games | 18:15 | 4 (25%) |
| Aghanim's Scepter | 46% of games | 21:15 | 6 (22%) |

Typical sequence: Phase Boots → Power Treads → Blade Mail → Orchid Malevolence → Yasha → Sange → Sange and Yasha → Black King Bar → Bloodthorn → Aghanim's Scepter

Same core as the other roles, with Phase Boots and Blade Mail added since the offlane version needs more early durability to survive lane before Static Link comes online.

### Riki

#### Carry

**Turbo** · 174 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 95% of games | 3:15 | 1 (92%) |
| Diffusal Blade | 98% of games | 7:15 | 2 (88%) |
| Yasha | 70% of games | 9:45 | 3 (65%) |
| Skull Basher | 66% of games | 16:45 | 3 (25%) |
| Crystalys | 49% of games | 16:45 | 4 (28%) |
| Butterfly | 46% of games | 18:45 | 6 (29%) |
| Linken's Sphere | 29% of games | 18:45 | 6 (27%) |
| Sange | 53% of games | 21:45 | 8 (26%) |
| Disperser | 38% of games | 21:15 | 8 (21%) |
| Aghanim's Scepter | 33% of games | 24:15 | 12 (19%) |
| Abyssal Blade | 50% of games | 22:15 | 9 (26%) |

Typical sequence: Power Treads → Diffusal Blade → Yasha → Skull Basher → Crystalys → Butterfly → Linken's Sphere → Sange → Disperser → Aghanim's Scepter → Abyssal Blade

Riki's whole plan is picking off isolated targets from permanent invisibility, so Diffusal Blade's mana burn and slow and Skull Basher's stun both extend his burst window; the long late tail (Butterfly, Disperser, Abyssal Blade) reflects how survivable and greedy a well-farmed Riki becomes once ambushes are consistently landing.

#### Offlane

**Turbo** · 58 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 91% of games | 4:15 | 1 (92%) |
| Diffusal Blade | 93% of games | 8:15 | 2 (85%) |

Typical sequence: Power Treads → Diffusal Blade

Only Power Treads and Diffusal Blade clear the bar at this smaller sample, but the ambush-first identity is the same.

### Rubick

#### Mid

**Standard** · 70 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Blink Dagger | 73% of games | 19:15 | 3 (45%) |

Typical sequence: Blink Dagger

**Turbo** · 314 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phylactery | 48% of games | 5:15 | 1 (75%) |
| Arcane Boots | 27% of games | 5:45 | 2 (44%) |
| Kaya | 55% of games | 6:45 | 2 (50%) |
| Meteor Hammer | 22% of games | 5:45 | 2 (83%) |
| Power Treads | 21% of games | 6:15 | 3 (84%) |
| Blink Dagger | 91% of games | 10:15 | 4 (47%) |
| Boots of Travel | 57% of games | 8:45 | 1 (44%) |
| Aghanim's Scepter | 85% of games | 13:15 | 3 (35%) |
| Eul's Scepter of Divinity | 53% of games | 17:45 | 5 (20%) |
| Khanda | 25% of games | 17:45 | 5 (21%) |
| Wind Waker | 26% of games | 25:15 | 9 (29%) |

Typical sequence: Phylactery → Arcane Boots → Kaya → Meteor Hammer → Power Treads → Blink Dagger → Boots of Travel → Aghanim's Scepter → Eul's Scepter of Divinity → Khanda → Wind Waker

Rubick's value is Telekinesis and Fade Bolt plus whatever ultimate he's stolen, so Blink Dagger for positioning and Aghanim's Scepter (an extra spell-steal charge) are close to universal; the long turbo tail otherwise reflects that his itemization depends heavily on which spell he's holding that game.

#### Offlane

**Turbo** · 85 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Blink Dagger | 79% of games | 10:45 | 3 (43%) |
| Aghanim's Scepter | 74% of games | 15:15 | 4 (32%) |

Typical sequence: Blink Dagger → Aghanim's Scepter

Same two-item Blink-into-Aghanim's core as mid, at a smaller offlane sample.

### Sand King

#### Offlane

**Standard** · 51 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Blink Dagger | 100% of games | 13:45 | 2 (84%) |

Typical sequence: Blink Dagger

**Turbo** · 111 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Blink Dagger | 88% of games | 7:15 | 2 (55%) |
| Aghanim's Scepter | 74% of games | 14:15 | 3 (39%) |
| Eul's Scepter of Divinity | 50% of games | 16:15 | 3 (30%) |

Typical sequence: Blink Dagger → Aghanim's Scepter → Eul's Scepter of Divinity

Sand King initiates with Blink Dagger into Epicenter/Burrowstrike, so it's close to the entire standard build; turbo's extra time adds Eul's Scepter for setup and Aghanim's Scepter to extend Epicenter's pulse count.

### Silencer

#### Mid

**Turbo** · 138 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 70% of games | 4:15 | 1 (96%) |
| Force Staff | 79% of games | 9:45 | 2 (43%) |
| Witch Blade | 65% of games | 9:45 | 2 (48%) |
| Black King Bar | 36% of games | 18:15 | 6 (52%) |
| Parasma | 51% of games | 20:15 | 7 (37%) |

Typical sequence: Power Treads → Force Staff → Witch Blade → Black King Bar → Parasma

Silencer scales through Intelligence and passive Int steal via Glaives of Wisdom, so Witch Blade's cheap Intelligence and damage plus Force Staff's positioning support his slow, safe farming pattern before he becomes a global-silence teamfight closer.

### Skywrath Mage

#### Mid

**Turbo** · 284 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Rod of Atos | 94% of games | 5:45 | 1 (77%) |
| Boots of Travel | 82% of games | 8:45 | 2 (68%) |
| Kaya | 63% of games | 10:15 | 2 (27%) |
| Veil of Discord | 48% of games | 11:45 | 3 (82%) |
| Aghanim's Scepter | 87% of games | 15:45 | 4 (41%) |
| Phylactery | 47% of games | 17:15 | 5 (62%) |
| Sange | 39% of games | 16:15 | 4 (30%) |
| Scythe of Vyse | 28% of games | 19:45 | 6 (26%) |
| Kaya and Sange | 39% of games | 16:15 | 5 (30%) |
| Gleipnir | 60% of games | 19:45 | 6 (41%) |
| Khanda | 35% of games | 23:15 | 8 (87%) |
| Bloodstone | 27% of games | 25:15 | 9 (84%) |

Typical sequence: Rod of Atos → Boots of Travel → Kaya → Veil of Discord → Aghanim's Scepter → Phylactery → Sange → Scythe of Vyse → Kaya and Sange → Gleipnir → Khanda → Bloodstone

Skywrath is a pure burst-nuke mid whose Mystic Flare and Ancient Seal want spell amplification plus a way to root a target first, so Rod of Atos comes before the long tail of amplification items (the Kaya line, Veil of Discord, Gleipnir); Aghanim's Scepter is core for the extra Mystic Flare cast and lands mid-build once the burst combo is already funded.

### Slark

#### Carry

**Standard** · 201 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 98% of games | 7:15 | 1 (94%) |
| Diffusal Blade | 84% of games | 14:15 | 2 (83%) |
| Shadow Blade | 31% of games | 22:15 | 3 (57%) |
| Aghanim's Scepter | 61% of games | 25:15 | 3 (43%) |
| Black King Bar | 37% of games | 33:15 | 4 (39%) |

Typical sequence: Power Treads → Diffusal Blade → Shadow Blade → Aghanim's Scepter → Black King Bar

**Turbo** · 332 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 96% of games | 3:45 | 1 (97%) |
| Diffusal Blade | 76% of games | 6:45 | 2 (86%) |
| Echo Sabre | 32% of games | 9:15 | 2 (45%) |
| Shadow Blade | 46% of games | 12:15 | 3 (40%) |
| Orchid Malevolence | 21% of games | 12:15 | 3 (37%) |
| Aghanim's Scepter | 64% of games | 13:45 | 3 (39%) |
| Harpoon | 24% of games | 13:15 | 4 (33%) |
| Black King Bar | 37% of games | 18:45 | 4 (32%) |
| Skull Basher | 44% of games | 19:15 | 6 (21%) |
| Disperser | 38% of games | 20:45 | 5 (22%) |
| Eye of Skadi | 37% of games | 21:45 | 5 (20%) |
| Sange | 38% of games | 20:45 | 7 (22%) |
| Abyssal Blade | 32% of games | 22:45 | 8 (22%) |

Typical sequence: Power Treads → Diffusal Blade → Echo Sabre → Shadow Blade → Orchid Malevolence → Aghanim's Scepter → Harpoon → Black King Bar → Skull Basher → Disperser → Eye of Skadi → Sange → Abyssal Blade

Slark leeches stats with Essence Shift, so Diffusal Blade's mana burn feeds those procs while slowing a target for Pounce, and Shadow Blade/Echo Sabre give him a second gap-close or escape on top of Dark Pact; Black King Bar comes late since Pact already answers most disables.

### Snapfire

#### Mid

**Standard** · 92 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Boots of Travel | 89% of games | 11:15 | 1 (82%) |
| Kaya | 91% of games | 17:45 | 2 (52%) |
| Blink Dagger | 84% of games | 20:15 | 2 (39%) |
| Yasha | 80% of games | 24:15 | 4 (65%) |
| Yasha and Kaya | 80% of games | 24:45 | 5 (68%) |

Typical sequence: Boots of Travel → Kaya → Blink Dagger → Yasha → Yasha and Kaya

**Turbo** · 123 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Boots of Travel | 81% of games | 5:15 | 1 (77%) |
| Kaya | 72% of games | 7:45 | 2 (55%) |
| Blink Dagger | 82% of games | 9:15 | 3 (49%) |
| Yasha | 54% of games | 12:15 | 4 (77%) |
| Yasha and Kaya | 53% of games | 12:15 | 5 (75%) |

Typical sequence: Boots of Travel → Kaya → Blink Dagger → Yasha → Yasha and Kaya

Played as a spell-damage carry, Snapfire leans on Lava Cookie and Scatterblast, so Kaya's amplification comes early and Boots of Travel supports her strong wave-clear and split push; Blink Dagger lands Cookie on a priority target.

#### Offlane

**Turbo** · 73 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Blink Dagger | 71% of games | 10:15 | 2 (42%) |

Typical sequence: Blink Dagger

The offlane sample only clears Blink Dagger — the same combo-landing priority, just at a smaller sample.

### Sniper

#### Carry

**Standard** · 66 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 98% of games | 11:15 | 2 (51%) |
| Maelstrom | 91% of games | 11:45 | 1 (53%) |

Typical sequence: Power Treads → Maelstrom

**Turbo** · 228 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 83% of games | 3:15 | 1 (91%) |
| Maelstrom | 65% of games | 7:45 | 2 (39%) |
| Force Staff | 44% of games | 12:45 | 4 (31%) |
| Specialist's Array | 34% of games | 12:45 | 4 (19%) |
| Shadow Blade | 32% of games | 15:45 | 5 (21%) |
| Aghanim's Scepter | 49% of games | 15:15 | 3 (16%) |
| Crystalys | 57% of games | 16:45 | 7 (18%) |
| Monkey King Bar | 38% of games | 18:45 | 7 (16%) |
| Black King Bar | 25% of games | 20:45 | 5 (17%) |
| Boots of Travel | 24% of games | 25:15 | 12 (13%) |

Typical sequence: Power Treads → Maelstrom → Force Staff → Specialist's Array → Shadow Blade → Aghanim's Scepter → Crystalys → Monkey King Bar → Black King Bar → Boots of Travel

Sniper is a pure kiting right-clicker with long Take Aim range, so Maelstrom's proc and cleave is a near-automatic first damage item; the long turbo tail (Specialist's Array, Monkey King Bar, Shadow Blade) reflects how much survivability and repositioning he has to buy since he has almost none innately.

#### Mid

**Standard** · 184 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 96% of games | 7:15 | 1 (91%) |
| Maelstrom | 84% of games | 14:45 | 2 (62%) |
| Force Staff | 51% of games | 24:45 | 5 (37%) |
| Specialist's Array | 31% of games | 24:45 | 4 (25%) |
| Crystalys | 48% of games | 30:15 | 7 (27%) |
| Monkey King Bar | 28% of games | 35:45 | 7 (23%) |

Typical sequence: Power Treads → Maelstrom → Force Staff → Specialist's Array → Crystalys → Monkey King Bar

**Turbo** · 458 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 82% of games | 3:15 | 1 (88%) |
| Maelstrom | 52% of games | 7:15 | 2 (44%) |
| Force Staff | 41% of games | 12:45 | 5 (26%) |
| Specialist's Array | 34% of games | 12:45 | 3 (28%) |
| Aghanim's Scepter | 45% of games | 14:45 | 2 (19%) |
| Crystalys | 58% of games | 15:15 | 4 (20%) |
| Shadow Blade | 29% of games | 16:15 | 6 (20%) |
| Boots of Travel | 25% of games | 16:45 | 1 (29%) |
| Monkey King Bar | 41% of games | 18:15 | 6 (17%) |

Typical sequence: Power Treads → Maelstrom → Force Staff → Specialist's Array → Aghanim's Scepter → Crystalys → Shadow Blade → Boots of Travel → Monkey King Bar

Same Maelstrom-first plan as carry, matching his kiting-and-proccing game plan regardless of lane.

#### Offlane

**Turbo** · 72 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 71% of games | 3:45 | 1 (78%) |

Typical sequence: Power Treads

Only Power Treads clears the bar at this smaller offlane sample, consistent with a more defensive, lower-priority version of the same hero.

### Spirit Breaker

#### Mid

**Turbo** · 62 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 84% of games | 2:45 | 1 (98%) |
| Shadow Blade | 86% of games | 8:15 | 2 (60%) |

Typical sequence: Phase Boots → Shadow Blade

Spirit Breaker's entire early game is Charge of Darkness ganks, so Phase Boots and Shadow Blade both extend his gap-close and ambush range.

#### Offlane

**Turbo** · 167 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 82% of games | 3:15 | 1 (93%) |
| Shadow Blade | 79% of games | 9:45 | 2 (57%) |
| Yasha | 66% of games | 12:45 | 3 (36%) |
| Kaya | 45% of games | 14:45 | 4 (29%) |
| Aghanim's Scepter | 55% of games | 17:45 | 3 (18%) |
| Eul's Scepter of Divinity | 37% of games | 16:45 | 3 (23%) |
| Yasha and Kaya | 44% of games | 14:45 | 5 (32%) |

Typical sequence: Phase Boots → Shadow Blade → Yasha → Kaya → Aghanim's Scepter → Eul's Scepter of Divinity → Yasha and Kaya

Same Charge-first plan as mid; the longer offlane item list (Eul's Scepter, the Kaya line) shows him transitioning into a bruiser who adds spell amplification to Greater Bash's magic component.

### Storm Spirit

#### Mid

**Standard** · 244 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 99% of games | 8:15 | 1 (99%) |
| Witch Blade | 84% of games | 16:45 | 2 (57%) |
| Kaya | 94% of games | 18:15 | 3 (44%) |
| Orchid Malevolence | 36% of games | 18:45 | 2 (52%) |
| Black King Bar | 57% of games | 26:15 | 4 (33%) |
| Sange | 52% of games | 27:45 | 4 (39%) |
| Kaya and Sange | 52% of games | 28:15 | 5 (39%) |
| Parasma | 43% of games | 34:45 | 7 (34%) |
| Aghanim's Scepter | 40% of games | 38:45 | 7 (32%) |

Typical sequence: Power Treads → Witch Blade → Kaya → Orchid Malevolence → Black King Bar → Sange → Kaya and Sange → Parasma → Aghanim's Scepter

**Turbo** · 175 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 82% of games | 3:45 | 1 (97%) |
| Kaya | 93% of games | 8:45 | 3 (44%) |
| Witch Blade | 70% of games | 8:45 | 2 (46%) |
| Orchid Malevolence | 51% of games | 9:15 | 2 (51%) |
| Sange | 65% of games | 12:45 | 4 (58%) |
| Kaya and Sange | 65% of games | 12:45 | 5 (58%) |
| Linken's Sphere | 36% of games | 17:15 | 6 (24%) |
| Black King Bar | 61% of games | 16:15 | 6 (25%) |
| Parasma | 55% of games | 18:15 | 7 (34%) |
| Aghanim's Scepter | 57% of games | 20:15 | 7 (25%) |

Typical sequence: Power Treads → Kaya → Witch Blade → Orchid Malevolence → Sange → Kaya and Sange → Linken's Sphere → Black King Bar → Parasma → Aghanim's Scepter

Storm Spirit's Ball Lightning is powered by mana pool and spell amplification, so the Kaya line is close to mandatory, and Orchid Malevolence/Witch Blade both add cheap Intelligence plus a way to lock a target down before a Static Remnant burst; Black King Bar lets him land in the middle of a fight without being chain-disabled.

### Sven

#### Carry

**Standard** · 96 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 100% of games | 6:45 | 1 (96%) |
| Echo Sabre | 99% of games | 16:15 | 3 (87%) |
| Blink Dagger | 85% of games | 19:15 | 4 (76%) |
| Black King Bar | 86% of games | 25:15 | 5 (53%) |
| Crystalys | 79% of games | 26:15 | 6 (39%) |
| Harpoon | 69% of games | 31:15 | 8 (33%) |

Typical sequence: Power Treads → Echo Sabre → Blink Dagger → Black King Bar → Crystalys → Harpoon

**Turbo** · 168 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 93% of games | 3:15 | 1 (94%) |
| Echo Sabre | 94% of games | 8:15 | 3 (62%) |
| Blink Dagger | 82% of games | 10:15 | 4 (56%) |
| Crystalys | 87% of games | 13:15 | 6 (36%) |
| Black King Bar | 78% of games | 14:15 | 5 (50%) |
| Harpoon | 73% of games | 15:45 | 8 (36%) |
| Monkey King Bar | 33% of games | 20:45 | 9 (24%) |
| Aghanim's Scepter | 36% of games | 20:45 | 8 (17%) |
| Swift Blink | 44% of games | 21:15 | 9 (32%) |

Typical sequence: Power Treads → Echo Sabre → Blink Dagger → Crystalys → Black King Bar → Harpoon → Monkey King Bar → Aghanim's Scepter → Swift Blink

Sven wins fights with Storm Bolt into Great Cleave, so Blink Dagger for reliable stun range and Black King Bar to survive while cleaving are close to mandatory; Echo Sabre and Crystalys layer stats and attack speed onto Warcry uptime.

### Templar Assassin

#### Carry

**Turbo** · 77 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 99% of games | 3:45 | 1 (99%) |
| Desolator | 99% of games | 8:15 | 2 (72%) |
| Blink Dagger | 99% of games | 11:15 | 4 (45%) |
| Crystalys | 82% of games | 14:45 | 5 (46%) |
| Force Staff | 74% of games | 15:45 | 8 (30%) |

Typical sequence: Power Treads → Desolator → Blink Dagger → Crystalys → Force Staff

TA needs armor shred and burst for Psi Blades meld attacks, so Desolator is close to automatic, and Blink Dagger both delivers her into range and sets up Refraction trades.

#### Mid

**Turbo** · 53 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Blink Dagger | 96% of games | 9:15 | 3 (51%) |

Typical sequence: Blink Dagger

Only Blink Dagger clears the bar in the shorter mid sample, reflecting the same meld-and-trade game plan.

### Terrorblade

#### Carry

**Standard** · 131 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 98% of games | 6:45 | 1 (93%) |
| Yasha | 95% of games | 13:45 | 2 (86%) |
| Eye of Skadi | 67% of games | 30:15 | 5 (41%) |
| Force Staff | 38% of games | 30:15 | 6 (38%) |

Typical sequence: Power Treads → Yasha → Eye of Skadi → Force Staff

**Turbo** · 134 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 96% of games | 3:45 | 1 (99%) |
| Yasha | 97% of games | 6:45 | 2 (89%) |
| Eye of Skadi | 66% of games | 17:15 | 5 (30%) |
| Black King Bar | 62% of games | 17:45 | 4 (22%) |
| Force Staff | 52% of games | 17:45 | 6 (29%) |
| Butterfly | 44% of games | 18:45 | 8 (20%) |

Typical sequence: Power Treads → Yasha → Eye of Skadi → Black King Bar → Force Staff → Butterfly

Terrorblade scales illusions through Sunder and raw stats, so Yasha and Eye of Skadi both boost his and his illusions' damage or slow, while Force Staff/Butterfly cover the mobility and evasion he otherwise lacks as a melee carry with no escape besides Metamorphosis.

### Tidehunter

#### Offlane

**Standard** · 120 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 89% of games | 9:15 | 1 (91%) |
| Vladmir's Offering | 70% of games | 14:45 | 2 (76%) |
| Blink Dagger | 83% of games | 18:45 | 3 (61%) |
| Aghanim's Scepter | 46% of games | 29:45 | 4 (47%) |

Typical sequence: Phase Boots → Vladmir's Offering → Blink Dagger → Aghanim's Scepter

**Turbo** · 125 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 73% of games | 4:15 | 1 (89%) |
| Vladmir's Offering | 50% of games | 6:45 | 2 (68%) |
| Blink Dagger | 92% of games | 10:15 | 3 (33%) |
| Aghanim's Scepter | 56% of games | 16:15 | 4 (29%) |

Typical sequence: Phase Boots → Vladmir's Offering → Blink Dagger → Aghanim's Scepter

Tidehunter initiates Ravage off Blink Dagger, so that's the ultimate priority; Vladmir's Offering gives cheap lifesteal and armor to farm and tank early, and Phase Boots close the gap before the Blink is even needed.

### Timbersaw

#### Offlane

**Standard** · 86 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Arcane Boots | 80% of games | 9:45 | 1 (91%) |
| Kaya | 86% of games | 16:45 | 2 (66%) |
| Blink Dagger | 67% of games | 19:15 | 3 (50%) |
| Sange | 67% of games | 24:45 | 4 (40%) |
| Kaya and Sange | 67% of games | 25:15 | 5 (41%) |

Typical sequence: Arcane Boots → Kaya → Blink Dagger → Sange → Kaya and Sange

**Turbo** · 163 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 49% of games | 4:45 | 1 (95%) |
| Arcane Boots | 45% of games | 4:15 | 1 (96%) |
| Kaya | 93% of games | 7:45 | 2 (80%) |
| Sange | 87% of games | 11:15 | 3 (55%) |
| Kaya and Sange | 87% of games | 11:15 | 4 (56%) |
| Pipe of Insight | 38% of games | 13:15 | 5 (61%) |
| Aghanim's Scepter | 59% of games | 16:45 | 6 (28%) |
| Eul's Scepter of Divinity | 49% of games | 19:15 | 7 (35%) |

Typical sequence: Power Treads → Arcane Boots → Kaya → Sange → Kaya and Sange → Pipe of Insight → Aghanim's Scepter → Eul's Scepter of Divinity

Timbersaw scales purely off Intelligence via Timber Chain and Whirling Death, so the Kaya line is close to mandatory for both damage and mana sustain, and Arcane Boots cover his very high mana costs while farming trees.

### Tinker

#### Mid

**Standard** · 163 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Kaya | 98% of games | 8:15 | 1 (96%) |
| Blink Dagger | 99% of games | 12:15 | 2 (94%) |
| Aether Lens | 79% of games | 20:45 | 3 (46%) |
| Sange | 71% of games | 19:45 | 3 (45%) |
| Aghanim's Scepter | 65% of games | 22:45 | 3 (30%) |
| Kaya and Sange | 71% of games | 19:45 | 4 (45%) |
| Eul's Scepter of Divinity | 32% of games | 31:15 | 7 (34%) |
| Ethereal Blade | 41% of games | 34:15 | 6 (21%) |

Typical sequence: Kaya → Blink Dagger → Aether Lens → Sange → Aghanim's Scepter → Kaya and Sange → Eul's Scepter of Divinity → Ethereal Blade

**Turbo** · 129 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Kaya | 90% of games | 4:45 | 1 (78%) |
| Blink Dagger | 100% of games | 6:15 | 2 (78%) |
| Aether Lens | 58% of games | 10:45 | 3 (45%) |
| Aghanim's Scepter | 84% of games | 13:15 | 3 (38%) |
| Yasha | 44% of games | 14:15 | 4 (30%) |
| Yasha and Kaya | 44% of games | 14:15 | 5 (30%) |
| Eul's Scepter of Divinity | 47% of games | 19:15 | 8 (23%) |
| Arcane Blink | 48% of games | 22:15 | 9 (24%) |

Typical sequence: Kaya → Blink Dagger → Aether Lens → Aghanim's Scepter → Yasha → Yasha and Kaya → Eul's Scepter of Divinity → Arcane Blink

Tinker's March of the Machines-into-Laser combo scales with spell amplification and cast range, so Kaya and Aether Lens both extend his safe, long-range farming and pick-off pattern, and Blink Dagger lets him reposition immediately after Rearm resets his cooldowns.

### Tiny

#### Carry

**Standard** · 50 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 100% of games | 5:45 | 1 (100%) |
| Echo Sabre | 100% of games | 13:15 | 2 (100%) |

Typical sequence: Power Treads → Echo Sabre

Tiny's early Toss-into-Tree combo one-shots with almost no items, so Echo Sabre's cheap stats and active are close to the entire early build at this sample size, before he transitions into later Aghanim's Scepter builds not yet reflected here.

#### Offlane

**Turbo** · 75 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Echo Sabre | 73% of games | 8:15 | 2 (60%) |
| Blink Dagger | 76% of games | 9:45 | 2 (44%) |

Typical sequence: Echo Sabre → Blink Dagger

An offlane Tiny leans more on Blink Dagger to land Toss/Grow on a chosen target, alongside the same Echo Sabre stat base.

### Troll Warlord

#### Carry

**Turbo** · 77 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Yasha | 66% of games | 10:15 | 3 (53%) |
| Black King Bar | 83% of games | 15:45 | 5 (25%) |

Typical sequence: Yasha → Black King Bar

Troll is a pure attack-speed right-clicker through Battle Trance and Fervor, so Yasha is close to automatic, and Black King Bar lets him stand and swing through disables during his ultimate window.

### Tusk

#### Offlane

**Turbo** · 70 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Blink Dagger | 79% of games | 9:45 | 2 (56%) |

Typical sequence: Blink Dagger

Tusk's whole kit — Snowball, Walrus Punch, Tag Team — is initiation-first, so Blink Dagger is essentially the entire early build at this sample size.

### Vengeful Spirit

#### Carry

**Turbo** · 86 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 88% of games | 3:15 | 1 (96%) |
| Specialist's Array | 71% of games | 7:45 | 2 (67%) |
| Yasha | 62% of games | 10:45 | 3 (55%) |
| Aghanim's Scepter | 85% of games | 11:45 | 2 (33%) |
| Butterfly | 63% of games | 17:15 | 6 (24%) |

Typical sequence: Power Treads → Specialist's Array → Yasha → Aghanim's Scepter → Butterfly

Played as a right-click hero rather than pure support, Vengeful Spirit leans on Wave of Terror's armor break and Nether Swap for kills, so Aghanim's Scepter (Nether Swap on cooldown) and stat-stick items like Yasha carry her damage output.

#### Mid

**Turbo** · 79 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 94% of games | 3:45 | 1 (99%) |
| Aghanim's Scepter | 80% of games | 9:45 | 2 (49%) |
| Yasha | 66% of games | 9:45 | 3 (54%) |

Typical sequence: Power Treads → Aghanim's Scepter → Yasha

Same off-role carry pattern as carry — Aghanim's Scepter and Yasha both scale her right-click damage once she isn't purely support-itemized.

### Venomancer

#### Offlane

**Turbo** · 97 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Spirit Vessel | 55% of games | 6:45 | 1 (64%) |
| Aghanim's Scepter | 66% of games | 15:45 | 3 (25%) |

Typical sequence: Spirit Vessel → Aghanim's Scepter

Venomancer's Poison Nova and Plague Wards want Spirit Vessel's health-regen reduction to make Nova ticks lethal, and Aghanim's Scepter extends Plague Ward count and duration for his signature late-game push.

### Viper

#### Mid

**Turbo** · 123 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Boots of Travel | 59% of games | 8:15 | 1 (34%) |
| Force Staff | 42% of games | 10:45 | 3 (39%) |
| Black King Bar | 46% of games | 18:45 | 5 (18%) |
| Aghanim's Scepter | 47% of games | 18:45 | 2 (24%) |

Typical sequence: Boots of Travel → Force Staff → Black King Bar → Aghanim's Scepter

Viper mid kites with Nethertoxin and Corrosive Skin, so Boots of Travel supports a split-push farming pattern, and Black King Bar/Aghanim's Scepter both let him commit to extended DPS trades once Viper Strike is on cooldown.

#### Offlane

**Turbo** · 80 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 64% of games | 3:45 | 1 (90%) |

Typical sequence: Power Treads

Only Power Treads clears the bar in the offlane sample, consistent with a more conservative laning version of the same kiting hero.

### Void Spirit

#### Mid

**Standard** · 97 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 86% of games | 8:15 | 1 (81%) |
| Spirit Vessel | 57% of games | 13:15 | 2 (51%) |
| Aghanim's Scepter | 70% of games | 26:15 | 3 (41%) |
| Yasha | 58% of games | 24:45 | 3 (41%) |

Typical sequence: Power Treads → Spirit Vessel → Aghanim's Scepter → Yasha

**Turbo** · 197 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Spirit Vessel | 51% of games | 6:45 | 1 (74%) |
| Power Treads | 77% of games | 5:45 | 1 (51%) |
| Mage Slayer | 29% of games | 9:15 | 2 (41%) |
| Aghanim's Scepter | 81% of games | 13:15 | 3 (43%) |
| Yasha | 54% of games | 12:45 | 4 (39%) |
| Black King Bar | 25% of games | 19:15 | 4 (20%) |

Typical sequence: Spirit Vessel → Power Treads → Mage Slayer → Aghanim's Scepter → Yasha → Black King Bar

Void Spirit's Aether Remnant-into-Dissimilate combo wants Spirit Vessel's health-regen denial plus Intelligence, and Aghanim's Scepter reworks Astral Step for extra mobility and damage, matching his dive-and-reset playstyle.

#### Offlane

**Turbo** · 97 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 61% of games | 4:15 | 1 (100%) |
| Blade Mail | 62% of games | 8:15 | 2 (97%) |
| Radiance | 59% of games | 14:15 | 3 (86%) |
| Aghanim's Scepter | 67% of games | 15:45 | 4 (32%) |

Typical sequence: Phase Boots → Blade Mail → Radiance → Aghanim's Scepter

The offlane version is a tankier, farm-first take on the same dive kit — Phase Boots and Blade Mail replace some of the mid build's mobility items, while Radiance and Aghanim's Scepter fund a longer game.

### Weaver

#### Carry

**Standard** · 115 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Diffusal Blade | 65% of games | 10:45 | 1 (96%) |
| Linken's Sphere | 71% of games | 20:15 | 2 (85%) |
| Crystalys | 87% of games | 25:45 | 3 (50%) |

Typical sequence: Diffusal Blade → Linken's Sphere → Crystalys

**Turbo** · 275 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 80% of games | 3:45 | 1 (98%) |
| Desolator | 37% of games | 7:45 | 2 (46%) |
| Orchid Malevolence | 61% of games | 7:45 | 2 (77%) |
| Diffusal Blade | 50% of games | 10:15 | 3 (81%) |
| Linken's Sphere | 29% of games | 14:15 | 2 (33%) |
| Crystalys | 82% of games | 14:15 | 5 (37%) |
| Bloodthorn | 57% of games | 13:45 | 4 (52%) |
| Specialist's Array | 25% of games | 14:45 | 4 (44%) |
| Black King Bar | 39% of games | 18:15 | 4 (25%) |
| Butterfly | 38% of games | 21:15 | 7 (36%) |
| Eye of Skadi | 23% of games | 23:45 | 9 (42%) |

Typical sequence: Power Treads → Desolator → Orchid Malevolence → Diffusal Blade → Linken's Sphere → Crystalys → Bloodthorn → Specialist's Array → Black King Bar → Butterfly → Eye of Skadi

Weaver's Shukuchi-into-Geminate Attack rewards attack speed and a way to lock a target during a burst window, so Diffusal Blade's slow and Orchid Malevolence/Bloodthorn's silence both extend that window; Linken's Sphere covers his fragile HP pool since he has few other defensive options.

#### Offlane

**Turbo** · 89 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 79% of games | 3:45 | 1 (94%) |
| Orchid Malevolence | 66% of games | 8:15 | 2 (81%) |
| Diffusal Blade | 58% of games | 10:15 | 3 (83%) |
| Bloodthorn | 64% of games | 14:15 | 4 (60%) |
| Crystalys | 80% of games | 15:45 | 5 (41%) |

Typical sequence: Power Treads → Orchid Malevolence → Diffusal Blade → Bloodthorn → Crystalys

Same pick-off pattern as carry, at a shorter offlane sample.

### Windranger

#### Carry

**Turbo** · 110 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 63% of games | 3:45 | 1 (84%) |
| Maelstrom | 52% of games | 7:15 | 2 (47%) |
| Crystalys | 71% of games | 11:45 | 2 (31%) |
| Black King Bar | 58% of games | 16:15 | 5 (33%) |

Typical sequence: Power Treads → Maelstrom → Crystalys → Black King Bar

Windranger's Shackleshot-into-Focus Fire kit wants attack speed for the duel and Maelstrom's cheap proc rate is a natural early fit for Focus Fire's bonus attack speed.

#### Mid

**Standard** · 64 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Maelstrom | 91% of games | 14:45 | 2 (60%) |

Typical sequence: Maelstrom

**Turbo** · 157 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 44% of games | 4:15 | 1 (91%) |
| Maelstrom | 68% of games | 6:45 | 2 (57%) |
| Blink Dagger | 40% of games | 10:45 | 2 (27%) |
| Black King Bar | 60% of games | 14:45 | 3 (26%) |
| Crystalys | 62% of games | 14:15 | 3 (23%) |
| Boots of Travel | 43% of games | 15:45 | 2 (16%) |
| Aghanim's Scepter | 40% of games | 21:45 | 9 (21%) |

Typical sequence: Power Treads → Maelstrom → Blink Dagger → Black King Bar → Crystalys → Boots of Travel → Aghanim's Scepter

Same Maelstrom-and-attack-speed core as carry, with Blink Dagger and Boots of Travel added for the mobility to land Shackleshot from an unusual angle.

#### Offlane

**Turbo** · 132 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Power Treads | 60% of games | 4:15 | 1 (91%) |
| Maelstrom | 59% of games | 7:15 | 2 (59%) |
| Blink Dagger | 42% of games | 12:45 | 3 (34%) |
| Crystalys | 55% of games | 14:15 | 2 (25%) |
| Black King Bar | 49% of games | 17:15 | 5 (32%) |
| Boots of Travel | 42% of games | 16:15 | 3 (22%) |

Typical sequence: Power Treads → Maelstrom → Blink Dagger → Crystalys → Black King Bar → Boots of Travel

Same core as the other roles, at a shorter offlane sample.

### Wraith King

#### Carry

**Standard** · 92 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 80% of games | 6:45 | 1 (93%) |
| Radiance | 75% of games | 17:15 | 2 (74%) |
| Blink Dagger | 74% of games | 21:15 | 3 (49%) |

Typical sequence: Phase Boots → Radiance → Blink Dagger

**Turbo** · 313 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 84% of games | 3:45 | 1 (89%) |
| Radiance | 58% of games | 9:45 | 2 (55%) |
| Desolator | 60% of games | 11:15 | 2 (44%) |
| Shadow Blade | 25% of games | 11:45 | 3 (70%) |
| Blink Dagger | 71% of games | 11:45 | 3 (54%) |
| Echo Sabre | 28% of games | 13:15 | 2 (26%) |
| Harpoon | 24% of games | 15:15 | 5 (25%) |
| Black King Bar | 39% of games | 18:45 | 5 (31%) |
| Assault Cuirass | 38% of games | 17:45 | 6 (28%) |
| Monkey King Bar | 21% of games | 19:45 | 5 (27%) |
| Skull Basher | 28% of games | 20:15 | 6 (22%) |
| Aghanim's Scepter | 55% of games | 19:45 | 7 (18%) |
| Sange | 30% of games | 21:15 | 8 (24%) |
| Abyssal Blade | 22% of games | 23:15 | 9 (30%) |

Typical sequence: Phase Boots → Radiance → Desolator → Shadow Blade → Blink Dagger → Echo Sabre → Harpoon → Black King Bar → Assault Cuirass → Monkey King Bar → Skull Basher → Aghanim's Scepter → Sange → Abyssal Blade

Wraith King is nearly unkillable off Reincarnation, so his items lean toward pure damage output — Radiance for passive burn and farm, Desolator for armor shred — and the long turbo tail of crowd-control and damage items reflects how safely he can commit to fights with a second life in reserve.

#### Offlane

**Standard** · 178 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 93% of games | 6:45 | 1 (98%) |
| Radiance | 87% of games | 16:45 | 2 (90%) |
| Blink Dagger | 82% of games | 20:15 | 3 (81%) |
| Orchid Malevolence | 53% of games | 25:15 | 4 (89%) |
| Assault Cuirass | 29% of games | 33:15 | 5 (27%) |
| Bloodthorn | 40% of games | 31:15 | 5 (81%) |
| Black King Bar | 40% of games | 34:45 | 6 (44%) |

Typical sequence: Phase Boots → Radiance → Blink Dagger → Orchid Malevolence → Assault Cuirass → Bloodthorn → Black King Bar

**Turbo** · 194 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Phase Boots | 82% of games | 3:45 | 1 (96%) |
| Radiance | 55% of games | 10:15 | 2 (56%) |
| Desolator | 39% of games | 8:45 | 2 (62%) |
| Shadow Blade | 30% of games | 12:15 | 3 (69%) |
| Blink Dagger | 68% of games | 12:15 | 3 (44%) |
| Black King Bar | 41% of games | 18:45 | 5 (29%) |
| Aghanim's Scepter | 63% of games | 18:45 | 5 (19%) |
| Assault Cuirass | 42% of games | 19:15 | 5 (30%) |

Typical sequence: Phase Boots → Radiance → Desolator → Shadow Blade → Blink Dagger → Black King Bar → Aghanim's Scepter → Assault Cuirass

Same Phase Boots-into-Radiance-into-Blink core as carry; Orchid Malevolence and Bloodthorn in the standard sample add single-target lockdown for a slower-farming offlane version.

### Zeus

#### Mid

**Standard** · 137 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Arcane Boots | 84% of games | 7:15 | 1 (97%) |
| Kaya | 86% of games | 13:15 | 2 (69%) |
| Aghanim's Scepter | 90% of games | 23:45 | 3 (54%) |
| Refresher Orb | 56% of games | 32:45 | 4 (39%) |
| Yasha | 44% of games | 31:15 | 5 (27%) |
| Yasha and Kaya | 43% of games | 31:45 | 6 (27%) |

Typical sequence: Arcane Boots → Kaya → Aghanim's Scepter → Refresher Orb → Yasha → Yasha and Kaya

**Turbo** · 261 cohort games

| Item | Bought in | Median | Usual order (share) |
|---|---|---|---|
| Arcane Boots | 77% of games | 3:45 | 1 (97%) |
| Kaya | 77% of games | 7:15 | 2 (59%) |
| Phylactery | 35% of games | 9:15 | 2 (36%) |
| Aghanim's Scepter | 93% of games | 11:45 | 3 (54%) |
| Refresher Orb | 70% of games | 17:45 | 4 (36%) |
| Yasha | 35% of games | 16:45 | 4 (21%) |
| Eul's Scepter of Divinity | 36% of games | 16:15 | 4 (22%) |
| Khanda | 27% of games | 18:45 | 5 (31%) |
| Boots of Travel | 26% of games | 22:15 | 1 (21%) |
| Yasha and Kaya | 33% of games | 16:45 | 7 (23%) |
| Wind Waker | 23% of games | 23:45 | 10 (20%) |

Typical sequence: Arcane Boots → Kaya → Phylactery → Aghanim's Scepter → Refresher Orb → Yasha → Eul's Scepter of Divinity → Khanda → Boots of Travel → Yasha and Kaya → Wind Waker

Zeus's global, mana-hungry nukes — Arc Lightning and Thundergod's Wrath — make Arcane Boots and the Kaya line close to mandatory for both sustain and amplification, and Aghanim's Scepter/Refresher Orb both directly multiply his ultimate's damage output.
