"""Editable EN/ID copy and versioned discovery-sample rarity estimates."""
from __future__ import annotations

from typing import Any

from .achievement_rules import (
    ALL_ROLES,
    BADGE_TIERS,
    REPEATABLE_FEATS,
    ROLES,
    RULE_VERSION,
    TIER_VERSION,
)
from .achievements import IDS

# Copy tuple: English name, Indonesian name, English description, Indonesian
# description, English general hint, Indonesian general hint, English proof
# template, Indonesian proof template. Templates name factual stored proof keys.
COPY: dict[int, tuple[str, ...]] = {
    1: ("Double Record", "Dua Rekor", "Two role records in one match.", "Dua rekor peran dalam satu pertandingan.", "Beat more than one of your established role records in a match.", "Lampaui lebih dari satu rekor peranmu dalam satu pertandingan.", "New records: {strict_pb_metrics}.", "Rekor baru: {strict_pb_metrics}."),
    2: ("Clean Sweep", "Sapu Rekor", "At least three role records in one match.", "Setidaknya tiga rekor peran dalam satu pertandingan.", "Set several established role records together.", "Catat beberapa rekor peranmu sekaligus.", "New records: {strict_pb_metrics}.", "Rekor baru: {strict_pb_metrics}."),
    4: ("Record on a New Hero", "Rekor dengan Hero Baru", "A familiar role record, now on a different hero.", "Rekor peran yang sama, kini dengan hero berbeda.", "Set the same role record on more than one hero.", "Catat rekor peran yang sama dengan lebih dari satu hero.", "Hero {hero_id}; record metrics: {metric_ids}.", "Hero {hero_id}; metrik rekor: {metric_ids}."),
    6: ("Two Clocks Ahead", "Unggul di Dua Waktu", "Strong Carry farm at both 10 and 20 minutes.", "Farm Carry yang kuat pada menit 10 dan 20.", "Build a strong early last-hit count and keep your economy growing.", "Raih last hit tinggi sejak awal dan terus tingkatkan ekonomimu.", "{last_hits_at_10} last hits at 10:00; {net_worth_at_20} net worth at 20:00.", "{last_hits_at_10} last hit pada 10:00; net worth {net_worth_at_20} pada 20:00."),
    8: ("20-Minute Turnaround", "Balik Unggul di Menit 20", "Turn an early net-worth deficit against your role counterpart into a lead.", "Balikkan ketertinggalan net worth awal dari lawan seperanmu menjadi keunggulan.", "Trail the enemy player in your role early, then pass them by 20 minutes.", "Tertinggal dari lawan seperanmu di awal, lalu ungguli mereka pada menit 20.", "Net worth gap: {net_worth_gap_at_10} at 10:00, {net_worth_gap_at_20} at 20:00.", "Selisih net worth: {net_worth_gap_at_10} pada 10:00, {net_worth_gap_at_20} pada 20:00."),
    10: ("Gold Engine", "Mesin Emas", "A big midgame economy gain with few deaths.", "Kenaikan ekonomi besar di pertengahan game dengan sedikit kematian.", "Grow your net worth quickly from 10 to 20 minutes and keep deaths low.", "Tingkatkan net worth dengan cepat dari menit 10 hingga 20 dan jaga kematian tetap rendah.", "Net worth gained: {net_worth_gain_10_to_20}; deaths: {deaths}.", "Kenaikan net worth: {net_worth_gain_10_to_20}; kematian: {deaths}."),
    11: ("Mid Advantage, Real Siege", "Unggul Mid, Tekan Tower", "An early Mid economy lead paired with tower damage.", "Keunggulan ekonomi Mid sejak awal disertai damage ke tower.", "Lead the enemy Mid early and contribute meaningful tower damage.", "Ungguli Mid lawan sejak awal dan berikan damage berarti ke tower.", "Early lead: {net_worth_lead_at_10}; tower damage: {tower_damage}; team share: {team_tower_damage_share}.", "Keunggulan awal: {net_worth_lead_at_10}; damage tower: {tower_damage}; porsi tim: {team_tower_damage_share}."),
    13: ("Relentless Presence", "Hadir Terus", "High kill involvement with very few deaths.", "Terlibat dalam banyak kill dengan sangat sedikit kematian.", "Join a large share of your team's kills while staying alive.", "Terlibat dalam banyak kill tim sambil tetap bertahan hidup.", "Kill involvement: {kill_involvement}; deaths: {deaths}.", "Keterlibatan kill: {kill_involvement}; kematian: {deaths}."),
    14: ("Untouchable Contributor", "Kontributor Tak Tersentuh", "Double-digit assists without a death.", "Dua digit assist tanpa kematian.", "Help secure many kills and finish without dying.", "Bantu banyak kill dan selesaikan pertandingan tanpa mati.", "Assists: {assists}; deaths: {deaths}.", "Assist: {assists}; kematian: {deaths}."),
    15: ("Flawless Finisher", "Finisher Sempurna", "Double-digit kills without a death.", "Dua digit kill tanpa kematian.", "Score many hero kills and finish without dying.", "Raih banyak kill hero dan selesaikan pertandingan tanpa mati.", "Kills: {kills}; deaths: {deaths}.", "Kill: {kills}; kematian: {deaths}."),
    17: ("Five in a Flash", "Lima Kill Sekejap", "Five observed hero kills in a short window.", "Lima kill hero tercatat dalam waktu singkat.", "Chain five hero kills in a brief span.", "Raih lima kill hero dalam rentang waktu singkat.", "Five kills from {first_kill_seconds}s to {fifth_kill_seconds}s.", "Lima kill dari detik {first_kill_seconds} hingga {fifth_kill_seconds}."),
    18: ("Early Duelist", "Duelis Awal", "Multiple early hero kills without an early death.", "Beberapa kill hero di awal tanpa kematian awal.", "Find early hero kills and stay alive through the opening minutes.", "Raih kill hero di awal dan bertahan hidup selama menit pembuka.", "Before 10:00: {kills_before_10} kills, {deaths_before_10} deaths.", "Sebelum 10:00: {kills_before_10} kill, {deaths_before_10} kematian."),
    20: ("Fight Closer", "Penuntas Teamfight", "Three personal kills and no death in one detected fight.", "Tiga kill pribadi tanpa mati dalam satu teamfight terdeteksi.", "Finish a detected fight with several kills and no death.", "Selesaikan satu teamfight terdeteksi dengan beberapa kill tanpa mati.", "Detected fight: {fight}.", "Teamfight terdeteksi: {fight}."),
    22: ("Damage Anchor", "Andalan Damage", "Major allied hero-damage share in two separate fights.", "Porsi besar damage hero tim dalam dua teamfight terpisah.", "Deal a large share of allied hero damage more than once.", "Berikan porsi besar damage hero tim lebih dari sekali.", "Qualifying fights: {fights}.", "Teamfight yang memenuhi syarat: {fights}."),
    23: ("Clean Teamfight", "Teamfight Bersih", "Heavy damage in a fight with five enemy deaths and no allied deaths.", "Damage besar saat lima hero lawan mati tanpa kematian tim.", "Contribute major damage in a one-sided detected fight.", "Berikan damage besar dalam teamfight terdeteksi yang berat sebelah.", "Detected fight: {fight}.", "Teamfight terdeteksi: {fight}."),
    25: ("Behind but Fighting", "Tertinggal, Tetap Melawan", "A strong fight contribution while your team is behind in gold.", "Kontribusi besar dalam teamfight saat tim tertinggal emas.", "Deal a large share of fight damage while behind, with a favorable death trade.", "Berikan porsi besar damage teamfight saat tertinggal, dengan pertukaran kematian yang menguntungkan.", "Gold gap at {gold_checkpoint_seconds}s: {team_gold_gap}; fight: {fight}.", "Selisih emas pada detik {gold_checkpoint_seconds}: {team_gold_gap}; teamfight: {fight}."),
    30: ("Hero Specialist", "Spesialis Hero", "Repeat a difficult feat on the same hero across matches.", "Ulangi pencapaian sulit dengan hero yang sama di beberapa pertandingan.", "Earn the same uncommon feat with one hero across separate matches.", "Raih pencapaian langka yang sama dengan satu hero di pertandingan terpisah.", "Hero {hero_id}; feat: {feat_name}; qualifying matches: {distinct_matches}.", "Hero {hero_id}; pencapaian: {feat_name}; pertandingan yang memenuhi syarat: {distinct_matches}."),
    37: ("Vision Double Duty", "Dua Tugas Vision", "Place observers and earn credited observer-ward kills.", "Pasang observer dan dapatkan kredit penghancuran observer ward.", "Handle both observer placement and observer-ward removal in one match.", "Tangani pemasangan dan penghancuran observer ward dalam satu pertandingan.", "Observers placed: {observers_placed}; credited observer kills: {credited_observer_kills}.", "Observer dipasang: {observers_placed}; kredit penghancuran observer: {credited_observer_kills}."),
    41: ("Camp Architect", "Arsitek Camp", "Early stacks paired with strong kill involvement.", "Stack awal disertai keterlibatan kill yang tinggi.", "Stack camps by 20 minutes and stay active in team kills.", "Stack camp hingga menit 20 dan tetap aktif dalam kill tim.", "Stacks at 20:00: {stacks_at_20}; kill involvement: {kill_involvement}.", "Stack pada 20:00: {stacks_at_20}; keterlibatan kill: {kill_involvement}."),
    42: ("Support Everywhere", "Support di Mana-Mana", "High kill involvement and credited observer-ward kills.", "Keterlibatan kill tinggi dan kredit penghancuran observer ward.", "Contribute to fights and remove observer wards in one match.", "Berkontribusi dalam pertarungan dan hancurkan observer ward dalam satu pertandingan.", "Kill involvement: {kill_involvement}; credited observer kills: {credited_observer_kills}.", "Keterlibatan kill: {kill_involvement}; kredit penghancuran observer: {credited_observer_kills}."),
    44: ("Offlane Siege", "Gempuran Offlane", "Major tower damage from the Offlane.", "Damage besar ke tower dari Offlane.", "Deal substantial tower damage as an Offlaner.", "Berikan damage besar ke tower sebagai Offlaner.", "Tower damage: {tower_damage}; team share: {team_tower_damage_share}.", "Damage tower: {tower_damage}; porsi tim: {team_tower_damage_share}."),
    45: ("Siege without Dying", "Gempur Tanpa Mati", "A large share of team tower damage with no deaths.", "Porsi besar damage tower tim tanpa kematian.", "Lead the team's tower damage and finish alive.", "Pimpin damage tower tim dan selesaikan pertandingan tanpa mati.", "Team tower-damage share: {team_tower_damage_share}; deaths: {deaths}.", "Porsi damage tower tim: {team_tower_damage_share}; kematian: {deaths}."),
    49: ("Healing Hand", "Tangan Penyembuh", "Substantial hero healing and many assists.", "Pemulihan hero besar dan banyak assist.", "Restore hero health and contribute assists as a Support.", "Pulihkan kesehatan hero dan raih assist sebagai Support.", "Hero healing: {hero_healing}; assists: {assists}.", "Pemulihan hero: {hero_healing}; assist: {assists}."),
    50: ("Control Specialist", "Spesialis Kendali", "Substantial recorded hero-disable time and many assists.", "Durasi disable hero tercatat yang besar dan banyak assist.", "Control enemy heroes for long periods and contribute assists.", "Kendalikan hero lawan dalam waktu lama dan raih assist.", "Recorded disable seconds: {disable_seconds}; assists: {assists}.", "Detik disable tercatat: {disable_seconds}; assist: {assists}."),
}

# Frozen v1 rules evaluated on eligible Standard player-matches, with evaluable-only
# denominators, from 1,511 unique parsed Standard matches (2025-08 to 2026-09-29):
# the authorized local research corpus plus 1,026 recently parsed matches fetched from
# OpenDota for net-worth and death-log fields. A selected sample, not the population;
# the counts are references for the frozen tiers, which never move. Review:
# docs/tracker/architecture/evidence/achievement-threshold-review-2026-09-29.md.
RATE_COUNTS: dict[int, tuple[int, int, str]] = {
    6: (26, 830, "CORPUS"), 8: (46, 1660, "CORPUS"), 10: (79, 2490, "CORPUS"),
    11: (31, 848, "CORPUS"), 13: (202, 11600, "CORPUS"), 14: (97, 11600, "CORPUS"),
    15: (67, 11600, "CORPUS"), 17: (211, 10846, "CORPUS"), 18: (422, 3914, "CORPUS"),
    20: (1121, 6960, "CORPUS"), 22: (1045, 6960, "CORPUS"), 23: (420, 6960, "CORPUS"),
    25: (279, 6960, "CORPUS"), 37: (301, 4639, "CORPUS"), 41: (74, 1916, "CORPUS"),
    42: (1049, 4640, "CORPUS"), 44: (226, 2320, "CORPUS"), 45: (33, 4640, "CORPUS"),
    49: (383, 4640, "CORPUS"), 50: (313, 4634, "CORPUS"),
}
# Bands for a corpus rate: Common >=20%, Rare 5%-<20%, Epic 1%-<5%, Legendary <1%.
BANDS = (("COMMON", 0.20), ("RARE", 0.05), ("EPIC", 0.01), ("LEGENDARY", 0.0))


def band(rate: float) -> str:
    return next(name for name, floor in BANDS if rate >= floor)


def rarity_key(ident: int) -> tuple[int, float, int]:
    """Sort key, rarest first: frozen tier, then corpus rate (unmeasured last), then id."""
    order = [name for name, _ in reversed(BANDS)]
    counts = RATE_COUNTS.get(ident)
    return (order.index(BADGE_TIERS[ident]), counts[0] / counts[1] if counts else 1.0, ident)


def rarity(ident: int) -> dict[str, Any] | None:
    """The frozen tier plus its corpus reference. The tier never moves with live data."""
    tier = BADGE_TIERS.get(ident)
    if tier is None:
        return None
    counts = RATE_COUNTS.get(ident)
    if counts is None:  # history badges: tier from the history simulation, no static rate
        return {"version": TIER_VERSION, "tier": tier, "rate": None, "numerator": None,
                "denominator": None, "source": "MODEL", "provisional": False}
    hits, eligible, source = counts
    return {"version": TIER_VERSION, "tier": tier, "rate": hits / eligible,
            "numerator": hits, "denominator": eligible, "source": source, "provisional": False}


REPEATABLE_IDS = REPEATABLE_FEATS


def catalog_entry(ident: int, locale: str) -> dict[str, Any]:
    if ident not in IDS:
        raise KeyError(ident)
    name_en, name_id, description_en, description_id, hint_en, hint_id, proof_en, proof_id = COPY[ident]
    indonesian = locale == "id"
    return {"id": ident, "order": IDS.index(ident) + 1,
            "key": f"match-achievement-{ident}", "asset_key": f"match-achievement-{ident}",
            "rule_version": RULE_VERSION, "roles": sorted(ROLES.get(ident, ALL_ROLES)),
            "name": name_id if indonesian else name_en,
            "description": description_id if indonesian else description_en,
            "how_to": hint_id if indonesian else hint_en,
            "proof_template": proof_id if indonesian else proof_en}
