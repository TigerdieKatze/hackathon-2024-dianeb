import re
from collections import Counter, defaultdict
from typing import List, Dict, Set
from config import logger, WORD_LIST_FILE
import json
import os

# Path for storing dynamic weights
DYNAMIC_DATA_FILE = os.path.join('./data', 'dynamic_data.json')

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

def compute_positional_letter_frequencies(words: List[str]) -> List[Dict[str, float]]:
    max_length = max(len(word) for word in words)
    position_counts = [Counter() for _ in range(max_length)]
    total_counts = [0] * max_length
    for word in words:
        for i, letter in enumerate(word):
            position_counts[i][letter] += 1
            total_counts[i] += 1
    position_frequencies = []
    for i in range(max_length):
        position_frequencies.append({letter: count / total_counts[i] for letter, count in position_counts[i].items()})
    return position_frequencies

def compute_ngram_frequencies(words: List[str], n: int) -> Dict[str, float]:
    ngram_counts = Counter()
    total_ngrams = 0
    for word in words:
        word = f"{' ' * (n - 1)}{word}{' ' * (n - 1)}"  # Pad the word with spaces
        for i in range(len(word) - n + 1):
            ngram = word[i:i + n]
            ngram_counts[ngram] += 1
            total_ngrams += 1
    ngram_frequencies = {ngram: count / total_ngrams for ngram, count in ngram_counts.items()}
    return ngram_frequencies

# Precompute frequencies
letter_frequencies = compute_letter_frequencies(word_list)
positional_letter_frequencies = compute_positional_letter_frequencies(word_list)
bigram_frequencies = compute_ngram_frequencies(word_list, 2)
trigram_frequencies = compute_ngram_frequencies(word_list, 3)

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
        with open(DYNAMIC_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(dynamic_data, f)
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
        # Initialize scores for each unguessed letter
        letter_scores = defaultdict(float)

        for word in matching_words:
            for i, letter in enumerate(word):
                if word_state[i] == '_' and letter not in guessed_letters:
                    # Positional frequency score
                    position_freq = positional_letter_frequencies[i].get(letter, 0)

                    # N-gram frequency score
                    ngram_score = 0
                    # Bigram (n=2)
                    if i > 0:
                        bigram = word[i - 1] + letter
                        ngram_score += bigram_frequencies.get(bigram, 0)
                    if i < len(word_state) - 1 and word_state[i + 1] != '_':
                        bigram = letter + word_state[i + 1]
                        ngram_score += bigram_frequencies.get(bigram, 0)
                    # Trigram (n=3)
                    if i > 1:
                        trigram = word[i - 2] + word[i - 1] + letter
                        ngram_score += trigram_frequencies.get(trigram, 0)
                    if i < len(word_state) - 2 and word_state[i + 1] != '_' and word_state[i + 2] != '_':
                        trigram = letter + word_state[i + 1] + word_state[i + 2]
                        ngram_score += trigram_frequencies.get(trigram, 0)

                    # Morphological analysis (prefixes and suffixes)
                    morphological_score = 0
                    common_prefixes = ['UN', 'VER', 'BE', 'ENT', 'ER']
                    common_suffixes = ['EN', 'UNG', 'ER', 'CHEN', 'LICH']
                    if i == 0 and ''.join(word[:3]) in common_prefixes:
                        morphological_score += 0.1
                    if i >= len(word) - 3 and ''.join(word[-3:]) in common_suffixes:
                        morphological_score += 0.1

                    # Overall letter frequency score
                    letter_freq = letter_frequencies.get(letter, 0)

                    # Dynamic weights
                    weights = dynamic_data.get('weights', {})
                    position_weight = weights.get('position_weight', 0.5)
                    ngram_weight = weights.get('ngram_weight', 0.3)
                    letter_weight = weights.get('letter_weight', 0.2)

                    # Weighted sum of scores
                    total_score = (
                        position_freq * position_weight +
                        ngram_score * ngram_weight +
                        letter_freq * letter_weight +
                        morphological_score
                    )
                    letter_scores[letter] += total_score

        if letter_scores:
            # Select the letter with the highest cumulative score
            next_letter = max(letter_scores, key=letter_scores.get)
            logger.info(f"Selected next letter '{next_letter}' based on advanced scoring system.")
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
    if len(new_word) >= 5 and new_word not in word_list:
        word_list.append(new_word)
        # Update frequencies with the new word
        global letter_frequencies, positional_letter_frequencies, bigram_frequencies, trigram_frequencies
        letter_frequencies = compute_letter_frequencies(word_list)
        positional_letter_frequencies = compute_positional_letter_frequencies(word_list)
        bigram_frequencies = compute_ngram_frequencies(word_list, 2)
        trigram_frequencies = compute_ngram_frequencies(word_list, 3)
        # Optionally, write back to the file
        try:
            with open(WORD_LIST_FILE, 'a', encoding='utf-8') as f:
                f.write('\n' + new_word)
            logger.info(f"Added new word '{new_word}' to the word list.")
        except Exception as e:
            logger.error(f"Error adding word to word list: {e}")
    else:
        logger.debug(f"Word '{new_word}' is already in the word list or too short.")

# Function to adjust weights based on performance
def adjust_weights(won: bool):
    weights = dynamic_data.get('weights', {})
    if won:
        # If the bot won, slightly increase the weights
        weights['position_weight'] = min(weights.get('position_weight', 0.5) + 0.01, 0.7)
        weights['ngram_weight'] = min(weights.get('ngram_weight', 0.3) + 0.005, 0.5)
    else:
        # If the bot lost, slightly decrease the weights
        weights['position_weight'] = max(weights.get('position_weight', 0.5) - 0.01, 0.3)
        weights['ngram_weight'] = max(weights.get('ngram_weight', 0.3) - 0.005, 0.1)
    # Ensure the weights sum to 1
    total = weights['position_weight'] + weights['ngram_weight'] + weights.get('letter_weight', 0.2)
    weights['letter_weight'] = 1 - (weights['position_weight'] + weights['ngram_weight'])
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