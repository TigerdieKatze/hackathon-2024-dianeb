import re
from collections import Counter
from typing import List, Dict, Set
from config import logger, WORD_LIST_FILE, DYNAMIC_DATA_FILE
import json
import os
import fcntl  # Import for file-based locking

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

# Precompute frequencies from the word list
def compute_letter_frequencies(words: List[str]) -> Dict[str, float]:
    letter_counts = Counter()
    total_letters = 0
    for word in words:
        for letter in word:
            letter_counts[letter] += 1
            total_letters += 1
    letter_frequencies = {letter: count / total_letters for letter, count in letter_counts.items()}
    return letter_frequencies

# Precompute frequencies
letter_frequencies = compute_letter_frequencies(word_list)

# Load dynamic data (weights)
def load_dynamic_data():
    if os.path.exists(DYNAMIC_DATA_FILE):
        try:
            with open(DYNAMIC_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"Error loading dynamic data: {e}")
    return {
        'weights': {
            'position_weight': 0.5,
            'ngram_weight': 0.3,
            'letter_weight': 0.2
        }
    }

dynamic_data = load_dynamic_data()

# Function to save dynamic data
def save_dynamic_data():
    try:
        # Use file-based locking
        with open(DYNAMIC_DATA_FILE, 'w', encoding='utf-8') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            json.dump(dynamic_data, f)
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        logger.error(f"Error saving dynamic data: {e}")

# Function to get the next letter to guess
def get_next_letter(word_state: str, guessed_letters: List[str], incorrect_letters: Set[str]) -> str:
    guessed_letters = set(letter.upper() for letter in guessed_letters)
    all_letters = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    unguessed_letters = all_letters - guessed_letters

    # Exclude incorrect letters
    possible_letters = unguessed_letters - incorrect_letters

    # Build a precise regex pattern from word_state
    word_state_regex = ''.join(['.' if c == '_' else re.escape(c) for c in word_state])
    pattern = f"^{word_state_regex}$"
    regex = re.compile(pattern)

    # Filter words matching the pattern and not containing incorrect letters
    matching_words = [
        word for word in word_list
        if regex.fullmatch(word) and not set(word) & incorrect_letters
    ]

    if matching_words:
        # Compute letter frequencies among matching words
        letter_counts = Counter()
        for word in matching_words:
            unique_letters_in_word = set(word) - guessed_letters
            letter_counts.update(unique_letters_in_word)
        if letter_counts:
            # Select the unguessed letter that appears most frequently
            next_letter = letter_counts.most_common(1)[0][0]
            logger.info(f"Selected next letter '{next_letter}' based on frequency among matching words.")
            return next_letter
        else:
            logger.info("All letters in matching words have been guessed.")
    else:
        logger.info("No matching words found.")

    # Fallback to overall letter frequency
    unguessed_letter_freq = {
        letter: freq for letter, freq in letter_frequencies.items()
        if letter in possible_letters
    }
    if unguessed_letter_freq:
        next_letter = max(unguessed_letter_freq, key=unguessed_letter_freq.get)
        logger.info(f"Selected next letter '{next_letter}' based on overall letter frequency.")
        return next_letter

    # If all else fails, select any unguessed letter
    if possible_letters:
        next_letter = possible_letters.pop()
        logger.warning(f"No letters left in frequency list. Selecting random unguessed letter '{next_letter}'.")
        return next_letter

    # All letters have been guessed
    logger.error("All letters have been guessed. Unable to select a valid letter.")
    return None

# Function to add a new word to the word list
def add_word(new_word: str) -> None:
    new_word = new_word.strip().upper()
    new_word = new_word.replace('Ä', 'AE').replace('Ö', 'OE').replace('Ü', 'UE').replace('ß', 'SS')
    if len(new_word) >= 5:
        try:
            # Use file-based locking
            with open(WORD_LIST_FILE, 'a+', encoding='utf-8') as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                f.seek(0)
                existing_words = set(line.strip().upper() for line in f)
                if new_word not in existing_words:
                    f.write('\n' + new_word)
                    f.flush()
                    os.fsync(f.fileno())
                    word_list.append(new_word)
                    global letter_frequencies
                    letter_frequencies = compute_letter_frequencies(word_list)
                    logger.info(f"Added new word '{new_word}' to the word list.")
                else:
                    logger.debug(f"Word '{new_word}' is already in the word list.")
                fcntl.flock(f, fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Error adding word to word list: {e}")
    else:
        logger.debug(f"Word '{new_word}' is too short.")

# Function to adjust weights based on performance
def adjust_weights(won: bool):
    weights = dynamic_data.get('weights', {})
    if won:
        # If the bot won, slightly increase the weights
        weights['letter_weight'] = min(weights.get('letter_weight', 0.2) + 0.05, 0.7)
    else:
        # If the bot lost, slightly decrease the weights
        weights['letter_weight'] = max(weights.get('letter_weight', 0.2) - 0.05, 0.1)
    # Ensure the weight does not exceed bounds
    dynamic_data['weights'] = weights
    save_dynamic_data()

# Function to reset dynamic data at the start of a new game
def reset_dynamic_data():
    # No need to reset incorrect letters as they are now managed in main.py
    pass

# Function to handle the result of the game
def handle_game_result(won: bool):
    adjust_weights(won)
    # No need to reset incorrect letters here
