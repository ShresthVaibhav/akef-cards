import pytest

import akef
import akef_cards
from akef.wiki import wiki_page


def test_wiki_card():
    from akef_cards.templates import wiki_board

    doc = {"blockIds": ["a", "b"], "blockMap": {"a": {"text": {"inlineElements": [{"text": {"text": "\"Quote.\""}}]}},
                                                 "b": {"text": {"inlineElements": [{"text": {"text": "Bio."}}]}}}}
    item = akef.WikiItem.model_validate({
        "itemId": "1", "name": "Arcane", "brief": {"description": doc},
        "document": {"documentMap": {"d": doc},
                     "chapterGroup": [{"title": "Ability Matrix", "widgets": [{"id": "w", "title": "//Combat Skills"}]}],
                     "widgetCommonMap": {"w": {"tableList": [{"label": "Codename", "value": "Arcane"}, {"label": "Race", "value": "Liberi"}],
                                               "tabList": [], "tabDataMap": {"t": {"intro": {"name": "Gloompurge (Array Arcana: INT)", "type": "Ultimate", "description": "d"}}}}}},
    })
    page = wiki_page(item)
    assert (page.quote, page.bio, page.info) == ("Quote.", "Bio.", [("Race", "Liberi")])
    assert page.skills[0].name == "Gloompurge"
    assert wiki_board.render(page, {}).width == wiki_board.W


async def test_wiki_pages_render(tmp_path):
    from akef.wiki import Cost, Intel, Node, Potential, Story, Tier, WikiPage, WikiPart, WikiSkill

    page = WikiPage("Arcane", "", "Quote.", "Bio.", [("Race", "Liberi")],
                    skills=[WikiSkill("Gloompurge", "Ultimate", "", "ULTIMATE:\nBoom.")],
                    talents=[Node("Keen Mind", "Talent", "", [Tier("Keen Mind 1", "INT +8", "E1", [Cost("T-Creds", "", 1000)])])],
                    promotions=[Node("Promotion I", "Elite", "", [Tier("Promotion I", "Cap 40", "Lv 20", [])])],
                    potentials=[Potential("Watcher", "", "Stronger.")],
                    intel=[Intel("Faction", "HAS", ""), Intel("Expertise", "Formation", "Three as one.")],
                    stories=[Story("File 1", "Reach trust: Close", "A long story.")])
    cards = akef_cards.Cards(images=akef_cards.ImageCache(tmp_path))
    assert page.parts == list(WikiPart)
    assert len(await cards.render_wiki_pages(page)) == 6
    assert len(await cards.render_wiki_pages(page, [WikiPart.SKILLS, "lore"])) == 2
    assert WikiPart.TALENTS.needs_index and not WikiPart.LORE.needs_index
    with pytest.raises(ValueError):
        await cards.render_wiki(page, "nope")


def test_wiki_dark():
    from akef_cards.templates import wiki_board

    assert wiki_board.LIGHT["bg"] != wiki_board.DARK["bg"]
    assert wiki_board.P is wiki_board.LIGHT
