from app.behavior.elements.service import SummaryBehaviorContext, score_element


def score(context: SummaryBehaviorContext, key: str = "hero_pool_breadth"):
    return score_element(context, key)
