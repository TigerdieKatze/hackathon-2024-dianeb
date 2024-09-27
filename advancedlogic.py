import re
from collections import Counter
from typing import List
from config import logger, WORD_LIST_FILE

# Load and process the word list
def load_word_list(file_path: str) -> List[str]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            words = f.read().splitlines()
    except FileNotFoundError:
        # If the file doesn't exist, start with an empty list
        logger.warning(f"Word list file not found at {file_path}. Starting with an empty list.")
        words = []
    except Exception as e:
        logger.error(f"Error loading word list: {e}")
        words = []

    processed_words = []
    for word in words:
        word = word.strip().upper()
        word = word.replace('Ä', 'AE').replace('Ö', 'OE').replace('Ü', 'UE').replace('ß', 'SS')
        if len(word) >= 5:
            processed_words.append(word)
    return processed_words

word_list = load_word_list(WORD_LIST_FILE)

# Function to get the next letter to guess
def get_next_letter(word_state: str, guessed_letters: List[str]) -> str:
    guessed_letters = [letter.upper() for letter in guessed_letters]
    all_letters = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    unguessed_letters = all_letters - set(guessed_letters)

    # Build regex pattern from word_state
    word_state_regex = re.escape(word_state).replace('_', '.')
    pattern = f".*{word_state_regex}.*"
    regex = re.compile(pattern)

    # Filter words matching the pattern
    matching_words = [word for word in word_list if regex.fullmatch(word)]

    if matching_words:
        # Count frequencies of unguessed letters in matching words
        letter_counts = Counter()
        for word in matching_words:
            for letter in set(word):
                if letter not in guessed_letters:
                    letter_counts[letter] += 1

        if letter_counts:
            # Return the most frequent unguessed letter
            next_letter = letter_counts.most_common(1)[0][0]
            logger.info(f"Selected next letter '{next_letter}' based on matching words.")
            return next_letter
        else:
            logger.info("All letters in matching words have been guessed.")
    else:
        logger.info("No matching words found.")

    # Guess based on overall letter frequency in German
    german_letter_frequency = [
        'E', 'N', 'I', 'S', 'R', 'A', 'T', 'D', 'H',
        'U', 'L', 'G', 'O', 'M', 'B', 'W', 'Z', 'K',
        'C', 'P', 'F', 'V', 'J', 'Y', 'X', 'Q'
    ]
    for letter in german_letter_frequency:
        if letter not in guessed_letters:
            logger.info(f"Selected next letter '{letter}' based on letter frequency.")
            return letter

    # If all letters have been guessed, return any unguessed letter
    if unguessed_letters:
        next_letter = unguessed_letters.pop()
        logger.warning(f"No letters left in frequency list. Selecting random unguessed letter '{next_letter}'.")
        return next_letter

    # All letters have been guessed
    logger.error("All letters have been guessed. Unable to select a valid letter.")
    return None

# Function to add a new word to the word list
def add_word(new_word: str) -> None:
    new_word = new_word.strip().upper()
    new_word = new_word.replace('Ä', 'AE').replace('Ö', 'OE').replace('Ü', 'UE').replace('ß', 'SS')
    if len(new_word) >= 5 and new_word not in word_list:
        word_list.append(new_word)
        # Optionally, write back to the file
        try:
            with open(WORD_LIST_FILE, 'a', encoding='utf-8') as f:
                f.write('\n' + new_word)
            logger.info(f"Added new word '{new_word}' to the word list.")
        except Exception as e:
            logger.error(f"Error adding word to word list: {e}")
    else:
        logger.debug(f"Word '{new_word}' is already in the word list or too short.")