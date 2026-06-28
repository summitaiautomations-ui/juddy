"""Disc data model — what we know about a single disc."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Disc:
    brand: str
    mold: str
    plastic: str
    weight: Optional[int] = None
    color: Optional[str] = None
    condition: Optional[int] = None
    special_run: Optional[str] = None
    notes: Optional[str] = None

    def to_prompt(self) -> str:
        """Render as a structured prompt for the listing generator."""
        lines = [
            f"Brand: {self.brand}",
            f"Mold: {self.mold}",
            f"Plastic: {self.plastic}",
        ]
        if self.weight:
            lines.append(f"Weight: {self.weight}g")
        if self.color:
            lines.append(f"Color: {self.color}")
        if self.condition is not None:
            lines.append(f"Condition: {self.condition}/10 sleeve rating")
        if self.special_run:
            lines.append(f"Special run: {self.special_run}")
        if self.notes:
            lines.append(f"Notes from seller: {self.notes}")
        return (
            "Generate eBay + BST listings for this disc golf disc:\n\n"
            + "\n".join(lines)
        )
