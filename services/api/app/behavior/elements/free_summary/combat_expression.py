from app.behavior.elements.service import SummaryBehaviorContext, score_element


def score(context: SummaryBehaviorContext, key: str = "combat_involvement"):
    return score_element(context, key)
