from akef_cards.templates import (
    compare,
    compare_styles,
    contract_board,
    contract_detail,
    contract_midnight,
    factory_board,
    live_board,
    monument_board,
    monument_event,
    profile,
    profile_midnight,
    profile_poster,
    pulls_board,
    pulls_poster,
    roster_board,
    wiki_board,
    showcase,
    ingame,
)

TEMPLATES = {1: showcase.render, 2: ingame.render}
PROFILES = {1: profile, 2: profile_midnight, 3: profile_poster}
LIVE = {1: live_board.render, 2: live_board.render_dark}
FACTORY = {1: factory_board.render, 2: factory_board.render_dark}
PULLS = {1: pulls_board, 2: pulls_poster}
CONTRACT = {1: contract_board, 2: contract_midnight}
COMPARE = {1: compare.render, **compare_styles.STYLES}
