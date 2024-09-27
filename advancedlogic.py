import re
from collections import Counter
from typing import List, Dict
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

def compute_bigram_frequencies(words: List[str]) -> Dict[str, float]:
    bigram_counts = Counter()
    total_bigrams = 0
    for word in words:
        for i in range(len(word) - 1):
            bigram = word[i:i+2]
            bigram_counts[bigram] += 1
            total_bigrams += 1
    bigram_frequencies = {bigram: count / total_bigrams for bigram, count in bigram_counts.items()}
    return bigram_frequencies

# Precompute frequencies
letter_frequencies = compute_letter_frequencies(word_list)
positional_letter_frequencies = compute_positional_letter_frequencies(word_list)
bigram_frequencies = compute_bigram_frequencies(word_list)

# Function to get the next letter to guess
def get_next_letter(word_state: str, guessed_letters: List[str]) -> str:
    guessed_letters = set(letter.upper() for letter in guessed_letters)
    all_letters = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    unguessed_letters = all_letters - guessed_letters

    # Build a precise regex pattern from word_state
    word_state_regex = ''.join(['.' if c == '_' else re.escape(c) for c in word_state])
    pattern = f"^{word_state_regex}$"
    regex = re.compile(pattern)

    # Filter words matching the pattern
    matching_words = [word for word in word_list if regex.fullmatch(word)]

    if matching_words:
        # Initialize scores for each unguessed letter
        letter_scores = Counter()

        for word in matching_words:
            for i, letter in enumerate(word):
                if word_state[i] == '_' and letter not in guessed_letters:
                    # Positional frequency score
                    position_freq = positional_letter_frequencies[i].get(letter, 0)

                    # Bigram frequency score
                    bigram_score = 0
                    # Left bigram (if previous letter is known)
                    if i > 0 and word_state[i - 1] != '_':
                        left_bigram = word_state[i - 1] + letter
                        bigram_score += bigram_frequencies.get(left_bigram, 0)
                    # Right bigram (if next letter is known)
                    if i < len(word_state) - 1 and word_state[i + 1] != '_':
                        right_bigram = letter + word_state[i + 1]
                        bigram_score += bigram_frequencies.get(right_bigram, 0)

                    # Overall letter frequency score
                    letter_freq = letter_frequencies.get(letter, 0)

                    # Weighted sum of scores (weights can be adjusted)
                    total_score = (position_freq * 0.5) + (bigram_score * 0.3) + (letter_freq * 0.2)
                    letter_scores[letter] += total_score

        if letter_scores:
            # Select the letter with the highest cumulative score
            next_letter = letter_scores.most_common(1)[0][0]
            logger.info(f"Selected next letter '{next_letter}' based on weighted scoring system.")
            return next_letter
        else:
            logger.info("All letters in matching words have been guessed.")
    else:
        logger.info("No matching words found.")

    # Fallback to overall letter frequency in German
    unguessed_letter_freq = {letter: freq for letter, freq in letter_frequencies.items() if letter not in guessed_letters}
    if unguessed_letter_freq:
        next_letter = max(unguessed_letter_freq, key=unguessed_letter_freq.get)
        logger.info(f"Selected next letter '{next_letter}' based on overall letter frequency.")
        return next_letter

    # If all else fails, select any unguessed letter
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
        # Update frequencies with the new word
        global letter_frequencies, positional_letter_frequencies, bigram_frequencies
        letter_frequencies = compute_letter_frequencies(word_list)
        positional_letter_frequencies = compute_positional_letter_frequencies(word_list)
        bigram_frequencies = compute_bigram_frequencies(word_list)
        # Optionally, write back to the file
        try:
            with open(WORD_LIST_FILE, 'a', encoding='utf-8') as f:
                f.write('\n' + new_word)
            logger.info(f"Added new word '{new_word}' to the word list.")
        except Exception as e:
            logger.error(f"Error adding word to word list: {e}")
    else:
        logger.debug(f"Word '{new_word}' is already in the word list or too short.")
