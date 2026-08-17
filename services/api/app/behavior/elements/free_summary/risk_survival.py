from app.behavior.elements.service import SummaryBehaviorContext, score_element


def score(context: SummaryBehaviorContext, key: str = "death_exposure"):
    return score_element(context, key)
