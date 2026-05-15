"""sci-html: academic HTML slide deck generator."""

from .models import Deck, Slide
from .parser import parse_deck
from .renderer import render_deck

__all__ = ["Deck", "Slide", "parse_deck", "render_deck"]
__version__ = "0.1.0"
