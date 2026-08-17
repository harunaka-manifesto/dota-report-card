from app.behavior.elements.service import SummaryBehaviorContext, score_element


def score(context: SummaryBehaviorContext, key: str = "off_pool_performance"):
    return score_element(context, key)
