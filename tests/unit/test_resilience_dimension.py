from app.dna.dimensions.resilience import score
from app.dna.features.models import DnaFeatureSet
from app.dna.sessions import Session


def _features(
    after_loss: tuple[float, ...],
    *,
    after_win: float = 0.20,
) -> DnaFeatureSet:
    sessions = tuple(
        Session(f"session-{index}", (index, index + 100), index, index + 1)
        for index in range(10)
    )
    return DnaFeatureSet(
        matches=(),
        sessions=sessions,
        sample_size=40,
        transitions_after_win=tuple(after_win for _ in range(15)),
        transitions_after_loss=after_loss,
        transitions_after_two_losses=tuple(0.20 for _ in range(8)),
        dated_match_ids=tuple(range(40)),
        session_sensitivity_scores={
            60: {"resilience": 0.60},
            90: {"resilience": 0.60},
            120: {"resilience": 0.60},
        },
    )


def test_resilience_scores_shift_magnitude_not_direction() -> None:
    after_loss = tuple(0.50 for _ in range(15))
    inverse = _features(tuple(0.20 for _ in range(15)), after_win=0.50)
    positive = score(_features(after_loss))
    negative = score(inverse)

    assert positive.score == negative.score == 0.6
    assert next(item.value for item in positive.evidence if item.key == "effect_direction") == "more_after_loss"
    assert next(item.value for item in negative.evidence if item.key == "effect_direction") == "less_after_loss"


def test_resilience_neutral_signal_is_not_descriptor_eligible() -> None:
    result = score(_features(tuple(0.20 for _ in range(15))))

    assert result.score == 0.0
    assert result.label == "Resetting"
    assert result.descriptor_eligible is False
