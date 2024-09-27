from typing import List
from models import RoundDataDTO
from config import logger

# Prioritized letter list for guessing
LETTER_ORDER: List[str] = [
    'E', 'N', 'S', 'I', 'R', 'A', 'T', 'D', 'H', 'U',
    'L', 'C', 'G', 'M', 'O', 'B', 'W', 'F', 'K', 'Z',
    'P', 'V', 'J', 'Y', 'X', 'Q'
]

def get_next_letter(round_data: RoundDataDTO) -> str:
    """Returns the next letter to guess."""
    for letter in LETTER_ORDER:
        if letter not in round_data.guessed:
            logger.info(f"Guessing the next letter: {letter}")
            return letter