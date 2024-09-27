import time
from collections import Counter
from typing import List, Dict, Set
from config import IsFarmBot, logger, WORD_LIST_FILE, DYNAMIC_DATA_FILE
import json
import os
import fcntl
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed

# Precomputed letter frequencies loaded from pickle files
single_letter_freq: Dict[str, Dict[str, float]] = {}
pair_letter_freq: Dict[tuple, Dict[str, float]] = {}
overall_letter_freq: Dict[str, float] = {}

# Clean wordlist loaded from pickle file
word_list: List[str] = []
word_list_mtime: float = 0.0  # Modification time of the word list file

def load_precomputed_frequencies():
    global single_letter_freq, pair_letter_freq, overall_letter_freq
    try:
        with open('single_letter_freq.pkl', 'rb') as f:
            single_letter_freq = pickle.load(f)
        with open('pair_letter_freq.pkl', 'rb') as f:
            pair_letter_freq = pickle.load(f)
        with open('overall_letter_freq.pkl', 'rb') as f:
            overall_letter_freq = pickle.load(f)
        logger.info("Loaded precomputed letter frequencies successfully.")
    except FileNotFoundError as e:
        logger.error(f"Precomputed frequency file not found: {e}. Please run preprocess.py first.")
    except Exception as e:
        logger.error(f"Error loading precomputed frequencies: {e}")

def load_clean_wordlist(pickle_file: str = 'clean_wordlist.pkl') -> None:
    global word_list, word_list_mtime
    try:
        current_mtime = os.path.getmtime(pickle_file)
    except FileNotFoundError:
        logger.error(f"Clean wordlist file not found at {pickle_file}. Please run preprocess.py first.")
        word_list = []
        word_list_mtime = 0.0
        return
    except Exception as e:
        logger.error(f"Error accessing clean wordlist file: {e}")
        return

    if word_list_mtime == current_mtime:
        # Word list is up-to-date; no need to reload
        return

    start_time = time.time()  # Start timing
    try:
        with open(pickle_file, 'rb') as f:
            word_list = pickle.load(f)
        word_list_mtime = current_mtime
        logger.info(f"Loaded clean wordlist with {len(word_list)} words in {time.time() - start_time:.4f} seconds.")
    except Exception as e:
        logger.error(f"Error loading clean wordlist: {e}")
        word_list = []

def load_dynamic_data():
    start_time = time.time()
    if os.path.exists(DYNAMIC_DATA_FILE):
        try:
            with open(DYNAMIC_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            end_time = time.time()
            logger.info(f"Loaded dynamic data in {end_time - start_time:.4f} seconds.")
            return data
        except Exception as e:
            logger.error(f"Error loading dynamic data: {e}")
    end_time = time.time()
    logger.info(f"No dynamic data found. Using default weights. Operation took {end_time - start_time:.4f} seconds.")
    return {
        'weights': {
            'entropy_weight': 0.7,
            'frequency_weight': 0.3
        }
    }

dynamic_data = load_dynamic_data()

def save_dynamic_data():
    start_time = time.time()
    try:
        with open(DYNAMIC_DATA_FILE, 'w', encoding='utf-8') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            json.dump(dynamic_data, f)
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f, fcntl.LOCK_UN)
        end_time = time.time()
        logger.info(f"Saved dynamic data in {end_time - start_time:.4f} seconds.")
    except Exception as e:
        logger.error(f"Error saving dynamic data: {e}")

# Initialize word list and letter frequencies
load_clean_wordlist()
load_precomputed_frequencies()

def filter_word(word: str, word_state: str, incorrect_letters: Set[str]) -> bool:
    """
    Checks if a word matches the current word_state and doesn't contain any incorrect letters.
    """
    if len(word) != len(word_state):
        return False
    for wc, sc in zip(word, word_state):
        if sc == '_':
            if wc in incorrect_letters:
                return False
        else:
            if wc != sc:
                return False
    return True

def get_possible_words(word_state: str, guessed_letters: List[str], incorrect_letters: Set[str]) -> List[str]:
    """
    Filters the word_list to find all possible words that match the current word_state.
    Utilizes multithreading for efficient processing.
    """
    start_time = time.time()
    word_state = word_state.upper()
    incorrect_letters = set(letter.upper() for letter in incorrect_letters)
    guessed_letters_set = set(letter.upper() for letter in guessed_letters)

    possible_words = []
    num_threads = 8  # Adjust based on your CPU cores

    def worker(words_chunk):
        matched = []
        for word in words_chunk:
            if filter_word(word, word_state, incorrect_letters):
                matched.append(word)
        return matched

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        chunk_size = len(word_list) // num_threads
        futures = []
        for i in range(num_threads):
            start = i * chunk_size
            if i == num_threads - 1:
                end = len(word_list)
            else:
                end = (i + 1) * chunk_size
            futures.append(executor.submit(worker, word_list[start:end]))
        for future in as_completed(futures):
            possible_words.extend(future.result())

    logger.info(f"Filtered possible words in {time.time() - start_time:.4f} seconds. {len(possible_words)} words found.")
    return possible_words

def compute_letter_frequencies(possible_words: List[str], guessed_letters_set: Set[str]) -> Dict[str, int]:
    """
    Computes the frequency of each letter in the possible_words.
    Utilizes multithreading for efficient processing.
    Returns a dictionary with letter frequencies.
    """
    start_time = time.time()
    letter_counts = Counter()
    num_threads = 8  # Adjust based on your CPU cores

    def worker(words_chunk):
        local_counter = Counter()
        for word in words_chunk:
            unique_letters = set(word) - guessed_letters_set
            local_counter.update(unique_letters)
        return local_counter

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        chunk_size = len(possible_words) // num_threads
        futures = []
        for i in range(num_threads):
            start = i * chunk_size
            if i == num_threads - 1:
                end = len(possible_words)
            else:
                end = (i + 1) * chunk_size
            futures.append(executor.submit(worker, possible_words[start:end]))
        for future in as_completed(futures):
            letter_counts.update(future.result())

    logger.info(f"Computed letter frequencies in {time.time() - start_time:.4f} seconds.")
    return dict(letter_counts)

def get_next_letter(word_state: str, guessed_letters: List[str], incorrect_letters: Set[str]) -> str:
    start_time = time.time()

    # Always guess 'E' first if it hasn't been guessed yet
    if 'E' not in guessed_letters:
        logger.info("Guessing 'E' as it is the most common German letter.")
        return 'E'

    possible_words = get_possible_words(word_state, guessed_letters, incorrect_letters)
    if not possible_words:
        logger.warning("No possible words found. Guessing a random unguessed letter 'A'.")
        return 'A'  # Fallback to 'A' if no words are possible

    guessed_letters_set = set(letter.upper() for letter in guessed_letters)
    letter_frequencies = compute_letter_frequencies(possible_words, guessed_letters_set)

    if not letter_frequencies:
        logger.warning("No letter frequencies found. Guessing a random unguessed letter 'A'.")
        return 'A'

    # Find the letter with the highest frequency
    next_letter = max(letter_frequencies, key=letter_frequencies.get)
    end_time = time.time()
    logger.info(f"Selected next letter '{next_letter}' based on highest frequency in {end_time - start_time:.4f} seconds.")
    return next_letter

def add_word(new_word: str) -> None:
    global word_list, overall_letter_freq
    start_time = time.time()
    new_word = new_word.strip().upper()
    new_word = new_word.replace('Ä', 'AE').replace('Ö', 'OE').replace('Ü', 'UE').replace('ß', 'SS')
    if len(new_word) >= 5:
        try:
            # Use file-based locking
            with open(WORD_LIST_FILE, 'a+', encoding='utf-8') as f:
                if not IsFarmBot:
                    fcntl.flock(f, fcntl.LOCK_EX)
                f.seek(0)
                existing_words = set(line.strip().upper() for line in f)
                if new_word not in existing_words:
                    f.write('\n' + new_word)
                    f.flush()
                    os.fsync(f.fileno())
                    logger.info(f"Added new word '{new_word}' to the word list.")
                    # Update word_list and overall_letter_freq
                    word_list.append(new_word)
                    unique_letters = set(new_word)
                    for letter in unique_letters:
                        if letter in overall_letter_freq:
                            overall_letter_freq[letter] += 1
                        else:
                            overall_letter_freq[letter] = 1
                    # Normalize overall_letter_freq
                    total_unique_letters = sum(overall_letter_freq.values())
                    overall_letter_freq = {k: v / total_unique_letters for k, v in overall_letter_freq.items()}
                else:
                    logger.info(f"Word '{new_word}' is already in the word list.")
                if not IsFarmBot:
                    fcntl.flock(f, fcntl.LOCK_UN)
            # Update the modification time after adding the word
            global word_list_mtime
            word_list_mtime = os.path.getmtime(WORD_LIST_FILE)
            end_time = time.time()
            logger.info(f"add_word function completed in {end_time - start_time:.4f} seconds.")
        except Exception as e:
            logger.error(f"Error adding word to word list: {e}")
    else:
        logger.debug(f"Word '{new_word}' is too short.")
        end_time = time.time()
        logger.info(f"add_word function completed in {end_time - start_time:.4f} seconds.")

def adjust_weights(won: bool):
    start_time = time.time()
    weights = dynamic_data.get('weights', {})
    if won:
        weights['entropy_weight'] = min(weights.get('entropy_weight', 0.7) + 0.01, 0.9)
        weights['frequency_weight'] = 1 - weights['entropy_weight']
    else:
        weights['entropy_weight'] = max(weights.get('entropy_weight', 0.7) - 0.01, 0.5)
        weights['frequency_weight'] = 1 - weights['entropy_weight']
    dynamic_data['weights'] = weights
    save_dynamic_data()
    end_time = time.time()
    logger.info(f"Adjusted weights in {end_time - start_time:.4f} seconds. New weights: {weights}")

def reset_dynamic_data():
    pass

def handle_game_result(won: bool):
    start_time = time.time()
    adjust_weights(won)
    end_time = time.time()
    logger.info(f"Handled game result in {end_time - start_time:.4f} seconds.")
