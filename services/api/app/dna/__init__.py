"""Deterministic Free Dota DNA analytics."""

__all__ = ["analyze_dna"]

def __getattr__(name: str):
    if name == "analyze_dna":
        from app.dna.pipeline import analyze_dna

        return analyze_dna
    raise AttributeError(name)
