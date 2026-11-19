from __future__ import annotations

from datetime import datetime, timezone

from akef.enka.build import ELEMENT, PROFESSION, element_icon
from akef.enka.gamedata import GameData
from akef.enka.skport import avatar_entry, element_of, english, rarity_of
from akef.errors import MissingGameData

from akef_cards.contract import Contract as ContractCard
from akef_cards.contract import Buff, ContractDetail, Contracts, Fighter, Foe, Run
from akef_cards.factory import Area, Cabin, Factory, Post, Region
from akef_cards.gacha import Hit, PullHistory, Track
from akef_cards.live import Contract, Echoes, Live, Meter, until
from akef_cards.monument import Clear, Event, Member, Monument, Stage
from akef_cards.roster import Roster, Trained


def live_from_skport(card) -> Live:
    base = card.base
    now = card.current_ts or datetime.now(timezone.utc)
    stamina = card.stamina
    credit = card.credit
    meters = [
        Meter("Daily activity", card.daily.current, card.daily.max),
        Meter("Weekly routine", card.weekly.score, card.weekly.total),
        Meter("Battle pass", card.battle_pass.cur_level, card.battle_pass.max_level),
        Meter("Credits", credit.count, credit.total,
              "claimed today" if credit.has_today else f"refresh in {until(credit.next_refresh_ts, now)}"),
    ]

    echoes = None
    season = next((s for s in card.war_echoes.seasons if s.end_ts is None or s.end_ts > now), None)
    if season:
        week = next((w for w in season.weeks if w.end_ts is None or w.end_ts > now), season.weeks[-1] if season.weeks else None)
        stages = [(g.name, g.star) for g in week.dungeon_groups] if week else []
        echoes = Echoes(season.name, week.name if week else "", season.stars, stages, week.end_ts if week else season.end_ts)

    contract = None
    running = [c for c in card.crisis_contract if c.gameplay_end_at_ts is None or c.gameplay_end_at_ts > now]
    if running:
        c = running[0]
        weekly = Meter("Weekly", c.weekly_mission.count, c.weekly_mission.total)
        contract = Contract(c.name.split(":", 1)[-1].strip(), c.highest, weekly, c.gameplay_end_at_ts, c.kv_image)

    return Live(
        name=base.name,
        uid=base.uid,
        level=base.level,
        region=base.server_name,
        avatar=base.avatar_url,
        sanity=Meter("Sanity", stamina.current, stamina.max),
        full_at=stamina.full_at,
        meters=meters,
        echoes=echoes,
        contract=contract,
        now=now,
    )


def _clear(dungeon, known=None) -> Clear | None:
    record = dungeon.best_record if dungeon else None
    if record is None:
        return None
    team = []
    for c in record.chars:
        name, _, art, element, profession, _ = (known or {}).get(c.char_id, ("", "", "", "", "", 0))
        element = element or c.element.value
        team.append(Member(c.avatar_url, element, int(c.rarity.value or 0), c.level, name, art, profession,
                           c.potential_level, element_icon(element) if element else ""))
    return Clear(record.seconds, record.cleared_at, team)


def monument_from_skport(card, monument) -> Monument:
    base = card.base
    now = card.current_ts or datetime.now(timezone.utc)
    known = _fighters(card)
    events = []
    for group in monument.groups:
        stages = []
        for pair in group.dungeon_groups:
            normal, hard = pair.normal_dungeon, pair.hard_dungeon
            head = normal or hard
            enemy = head.enemies[0].image_url if head and head.enemies else ""
            stages.append(Stage(
                name=head.name if head else "?",
                level=head.recommend_level if head else 0,
                enemy=enemy,
                normal=_clear(normal, known),
                agony=_clear(hard, known),
                normal_done=bool(normal and normal.is_pass),
                agony_done=bool(hard and hard.is_pass),
            ))
        medal = group.achieve
        first = next((p.normal_dungeon for p in group.dungeon_groups if p.normal_dungeon), None)
        rules = first.rules if first else []
        events.append(Event(
            name=group.name,
            art=group.pic,
            stages=stages,
            rules=rules,
            medal=medal.icon if medal else "",
            medal_level=medal.level if medal else 0,
            plated=bool(medal and medal.is_plated),
            running=group.is_in_activity,
            started=group.activity_start_ts,
        ))
    return Monument(base.name, base.uid, base.level, base.server_name, base.avatar_url, events, now)


# skport only sends a number per cabin, we match it to the cabins its crew's base skills name
CABINS = {0: "Control Nexus", 1: "Manufacturing Cabin", 2: "Growth Chamber", 5: "Reception Room"}


def factory_from_skport(card) -> Factory:
    base = card.base
    regions = []
    for d in card.domain:
        posts = [Post(s.name, s.level, s.is_final_max_level, s.exp, s.exp_to_level_up, s.remain_money, s.money_max,
                      s.officer_char_avatar) for s in d.settlements]
        areas = []
        for a in d.areas:
            counts = [a.puzzle_count, a.trchest_count, a.equip_trchest_count, a.piece_count, a.blackbox_count, a.trstar_count]
            areas.append(Area(a.name, sum(c.count for c in counts), sum(c.total for c in counts)))
        regions.append(Region(d.name, d.level, d.money.count, d.money.total, posts, areas))
    cabins = [Cabin(r.type, r.level, [c.avatar_url for c in r.chars], CABINS.get(r.type, "Cabin"))
              for r in card.space_ship.rooms]
    return Factory(base.name, base.uid, base.level, base.server_name, base.avatar_url, regions, cabins,
                   card.current_ts or datetime.now(timezone.utc))


def _hits(pulls, hard, icon_for, element_for=None, portrait_for=None) -> list[Hit]:
    out, count = [], 0
    for p in pulls:
        if not p.is_free:
            count += 1
        if p.rarity == 6:
            out.append(Hit(p.name, icon_for(p.item_id), 6, count, hard, p.pool_name, p.pulled_at,
                           element_for(p.item_id) if element_for else "",
                           portrait_for(p.item_id) if portrait_for else ""))
            count = 0
    return out


def pulls_from_skport(data: GameData, card, pulls, after=None) -> PullHistory:
    base = card.base
    if after is not None and not isinstance(after, datetime):
        after = datetime(after.year, after.month, after.day, tzinfo=timezone.utc)
    portraits, half_body = {}, {}
    for op in card.chars:
        try:
            sid = avatar_entry(data, op)["StrId"]
        except MissingGameData:
            continue
        portraits[sid] = op.char_data.avatar_sq_url
        half_body[sid] = op.char_data.avatar_rt_url

    def operator_icon(item_id):
        return portraits.get(item_id) or f"https://enka.network/ui/ef/charremoteicon/icon_{item_id}.png"

    def weapon_icon(item_id):
        return f"https://enka.network/ui/ef/itemicon/{item_id}.png" if item_id else ""

    def element(item_id):
        found = data.avatar_by_str.get(item_id)
        return ELEMENT.get(found[1]["Element"], "") if found else ""

    limited = [p for p in pulls.operators if p.banner in ("special", "rerun", "joint")]
    operators = _hits(limited, 80, operator_icon, element, half_body.get)
    operators += _hits(pulls.banner("standard"), 80, operator_icon, element, half_body.get)
    operators += _hits(pulls.banner("beginner"), 50, operator_icon, element, half_body.get)
    weapons = []
    for pool in pulls.weapon_pools:
        weapons += _hits(pulls.weapon_banner(pool), 40, weapon_icon)
    operators.sort(key=lambda h: h.when or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    weapons.sort(key=lambda h: h.when or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    # pity needs every pull, the date only narrows what the card lists and counts
    def recent(items, when):
        return [i for i in items if after is None or (when(i) and when(i) >= after)]

    operators, weapons = recent(operators, lambda h: h.when), recent(weapons, lambda h: h.when)
    op_pulls, weapon_pulls = recent(pulls.operators, lambda p: p.pulled_at), recent(pulls.weapons, lambda p: p.pulled_at)

    tracks = [Track(p.name, p.banner, p.since_six, p.hard, p.banner_pulls, p.featured_at) for p in pulls.pity()]
    return PullHistory(
        name=base.name,
        uid=base.uid,
        level=base.level,
        region=base.server_name,
        avatar=base.avatar_url,
        tracks=tracks,
        operators=operators,
        weapons=weapons,
        total=len(op_pulls),
        free=sum(p.is_free for p in op_pulls),
        weapon_total=len(weapon_pulls),
        fives=sum(p.rarity == 5 for p in op_pulls),
        weapon_fives=sum(p.rarity == 5 for p in weapon_pulls),
        after=after,
        now=card.current_ts or datetime.now(timezone.utc),
    )


def contracts_from_skport(card) -> Contracts:
    base = card.base
    now = card.current_ts or datetime.now(timezone.utc)
    entries = []
    for c in card.crisis_contract:
        medal = c.achieve
        entries.append(ContractCard(
            name=c.name.split(":", 1)[-1].strip(),
            best=c.highest,
            attempts=c.challenge_count,
            art=c.header_image or c.kv_image,
            missions=[
                Meter("Weekly missions", c.weekly_mission.count, c.weekly_mission.total),
                Meter("Indicators", c.indicator_mission.count, c.indicator_mission.total),
                Meter("Stage missions", c.stage_mission.count, c.stage_mission.total),
            ],
            medal=medal.icon if medal else "",
            medal_level=medal.level if medal else 0,
            plated=bool(medal and medal.is_plated),
            starts=c.start_at_ts,
            ends=c.gameplay_end_at_ts,
        ))
    running = [e for e in entries if e.ends is None or e.ends > now]
    current = running[0] if running else (entries[0] if entries else None)
    return Contracts(base.name, base.uid, base.level, base.server_name, base.avatar_url, current,
                     [e for e in entries if e is not current], now)


def _fighters(card):
    out = {}
    for op in card.chars:
        d = op.char_data
        out[d.id] = (op.name, d.avatar_sq_url, d.avatar_rt_url, element_of(d), english(d.profession, PROFESSION, str.upper),
                     op.rarity)
    return out


def contract_detail_from_skport(card, detail) -> ContractDetail:
    base = card.base
    s = detail.status
    medal = s.achieve
    contract = ContractCard(
        name=s.name.split(":", 1)[-1].strip(), best=s.highest, attempts=s.challenge_count,
        art=s.header_image or s.kv_image,
        missions=[Meter("Weekly missions", s.weekly_mission.count, s.weekly_mission.total),
                  Meter("Indicators", s.indicator_mission.count, s.indicator_mission.total),
                  Meter("Stage missions", s.stage_mission.count, s.stage_mission.total)],
        medal=medal.achievement_data.init_icon if medal else "", medal_level=medal.level if medal else 0,
        plated=bool(medal and medal.is_plated), starts=s.start_at_ts, ends=s.gameplay_end_at_ts)
    known = _fighters(card)
    runs = []
    for r in detail.history.records:
        team = []
        for c in r.chars:
            name, square, art, element, profession, rarity = known.get(c.char_id, ("", c.avatar_url, "", "", "", 0))
            team.append(Fighter(name, square or c.avatar_url, art, element, element_icon(element) if element else "",
                                profession, rarity, c.level, c.potential_level))
        runs.append(Run(team, r.seconds, r.waves, r.score, r.cleared, r.is_best, r.played_at))
    runs.sort(key=lambda r: (not r.best, -r.score, r.seconds))
    buffs = [Buff(i.name, i.icon, i.text, i.score, i.is_unlock) for i in detail.indicators]
    foes = [Foe(e.name, e.image_url, e.level, e.ability) for e in detail.stage.enemies]
    return ContractDetail(base.name, base.uid, base.level, base.server_name, base.avatar_url, contract, runs, buffs, foes,
                          card.current_ts or datetime.now(timezone.utc))


def roster_from_skport(card) -> Roster:
    base = card.base
    operators = []
    for op in card.chars:
        d = op.char_data
        weapon = op.weapon
        gem = weapon.gem if weapon else None
        gear = [(e.equip_data.icon_url, int(e.equip_data.level.value or 0), rarity_of(e)) for e in op.equips]
        operators.append(Trained(
            name=op.name,
            rarity=op.rarity,
            element=element_of(d),
            element_icon=element_icon(element_of(d)),
            portrait=d.avatar_sq_url,
            level=op.level,
            promotion=op.evolve_phase,
            potential=op.potential_level,
            skills=[op.skill_level(s.id) for s in d.skills],
            talents=(len(op.unlocked_talents), len(op.talents)),
            weapon=weapon.name if weapon else "",
            weapon_icon=weapon.weapon_data.icon_url if weapon else "",
            weapon_rarity=weapon.rarity if weapon else 0,
            weapon_level=weapon.level if weapon else 0,
            weapon_refine=weapon.refine_level if weapon else 0,
            essence=gem.name.replace("Â", "").partition("·")[2] if gem else "",
            essence_rarity=int(gem.gem_data.template_id.rsplit("_", 1)[-1]) if gem and gem.gem_data else 0,
            gear=gear,
        ))
    operators.sort(key=lambda o: (-o.rarity, -o.progress, o.name))
    return Roster(base.name, base.uid, base.level, base.server_name, base.avatar_url, operators,
                  card.current_ts or datetime.now(timezone.utc))
