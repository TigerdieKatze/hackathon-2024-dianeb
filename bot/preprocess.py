import os
import pickle
import unicodedata
from collections import defaultdict, Counter
from config import logger, SINGLE_LETTER_FREQ_FILE, PAIR_LETTER_FREQ_FILE, OVERALL_LETTER_FREQ_FILE, CLEAN_WORDLIST_FILE

WORD_LIST_FILE = './lists/wordlist.txt'

def remove_accents(input_str: str) -> str:
    """
    Removes accents from the input string.
    Converts characters like 'É' to 'E'.
    """
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

def load_word_list(file_path: str) -> list:
    """
    Loads and processes the word list from the specified file path.
    Normalizes words by removing accents and replacing specific German characters.
    Skips words containing non-standard characters after normalization.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            words = f.read().splitlines()
        processed_words = set()

        for word in words:
            word = word.strip().upper()
            word = word.replace('Ä', 'AE').replace('Ö', 'OE').replace('Ü', 'UE').replace('ß', 'SS')
            word = remove_accents(word)
            # After removing accents, ensure that word contains only A-Z
            if all('A' <= c <= 'Z' for c in word) and len(word) >= 5:
                processed_words.add(word)
            else:
                logger.debug(f"Skipping word with non-standard characters: {word}")
        return list(processed_words)
    except Exception as e:
        logger.error(f"Error loading word list: {e}")
        return []

def precompute_frequencies(word_list: list) -> tuple:
    """
    Precomputes single and pair letter frequencies from the word list.
    Also computes overall letter frequencies.
    Returns three dictionaries: single_letter_freq, pair_letter_freq, overall_letter_freq.
    """
    single_letter_freq = {}
    pair_letter_freq = {}
    overall_letter_freq = Counter()

    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    letter_set = set(letters)

    # Build an index mapping from letters to words containing them
    letter_to_words = {letter: set() for letter in letters}
    for word in word_list:
        unique_letters = set(word)
        overall_letter_freq.update(unique_letters)  # Update overall frequencies
        for letter in unique_letters:
            if letter in letter_to_words:
                letter_to_words[letter].add(word)
            else:
                # This should not happen as we've normalized the words
                logger.warning(f"Encountered unexpected letter '{letter}' in word '{word}'")

    # Precompute frequencies for single letters
    for letter in letters:
        counter = Counter()
        words_with_letter = letter_to_words[letter]
        for word in words_with_letter:
            letters_in_word = set(word) - {letter}
            counter.update(letters_in_word)
        total = sum(counter.values())
        if total > 0:
            freq_dict = {l: count / total for l, count in counter.items()}
            single_letter_freq[letter] = freq_dict

    # Precompute frequencies for letter pairs
    for i in range(len(letters)):
        for j in range(i + 1, len(letters)):
            letter1 = letters[i]
            letter2 = letters[j]
            words_with_both = letter_to_words[letter1] & letter_to_words[letter2]
            counter = Counter()
            for word in words_with_both:
                letters_in_word = set(word) - {letter1, letter2}
                counter.update(letters_in_word)
            total = sum(counter.values())
            if total > 0:
                freq_dict = {l: count / total for l, count in counter.items()}
                pair_letter_freq[(letter1, letter2)] = freq_dict

    # Compute overall letter frequencies
    total_unique_letters = sum(overall_letter_freq.values())
    if total_unique_letters > 0:
        overall_letter_freq = {letter: count / total_unique_letters for letter, count in overall_letter_freq.items()}
    else:
        overall_letter_freq = {}

    return single_letter_freq, pair_letter_freq, overall_letter_freq

def save_frequencies(single_letter_freq: dict, pair_letter_freq: dict, overall_letter_freq: dict) -> None:
    """
    Saves the precomputed frequencies to pickle files.
    """
    try:
        with open(SINGLE_LETTER_FREQ_FILE, 'wb') as f:
            pickle.dump(single_letter_freq, f)
        with open(PAIR_LETTER_FREQ_FILE, 'wb') as f:
            pickle.dump(pair_letter_freq, f)
        with open(OVERALL_LETTER_FREQ_FILE, 'wb') as f:
            pickle.dump(overall_letter_freq, f)
        logger.info("Precomputed frequencies saved successfully.")
    except Exception as e:
        logger.error(f"Error saving frequency files: {e}")

def save_clean_wordlist(word_list: list) -> None:
    """
    Saves the cleaned word list to a pickle file for efficient loading.
    """
    try:
        with open(CLEAN_WORDLIST_FILE, 'wb') as f:
            pickle.dump(word_list, f)
        logger.info("Clean wordlist saved successfully.")
    except Exception as e:
        logger.error(f"Error saving clean wordlist: {e}")

if __name__ == '__main__':
    logger.info("Starting pre-processing of wordlist.")
    word_list = load_word_list(WORD_LIST_FILE)
    logger.info(f"Total processed words: {len(word_list)}")
    single_letter_freq, pair_letter_freq, overall_letter_freq = precompute_frequencies(word_list)
    save_frequencies(single_letter_freq, pair_letter_freq, overall_letter_freq)
    save_clean_wordlist(word_list)
    logger.info("Pre-processing completed successfully.")