import asyncio
import time
import re
from collections import Counter
from typing import List, Dict, Set
from config import logger, SINGLE_LETTER_FREQ_FILE, PAIR_LETTER_FREQ_FILE, OVERALL_LETTER_FREQ_FILE, CLEAN_WORDLIST_FILE, CLEAN_WORDLIST_FILE_E, CLEAN_WORDLIST_FILE_NE, THREADCOUNT
import os
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from numba import njit
import numpy as np
import logging

# Suppress Numba debug logs
numba_logger = logging.getLogger('numba')
numba_logger.setLevel(logging.WARNING)


# Precomputed letter frequencies loaded from pickle files
single_letter_freq: Dict[str, Dict[str, float]] = {}
pair_letter_freq: Dict[tuple, Dict[str, float]] = {}
overall_letter_freq: Dict[str, float] = {}

# Clean wordlist loaded from pickle file
word_list: List[str] = []
word_list_e: List[str] = []
word_list_ne: List[str] = []
word_list_mtime: float = 0.0  # Modification time of the word list file

def load_precomputed_frequencies():
    global single_letter_freq, pair_letter_freq, overall_letter_freq
    try:
        with open(SINGLE_LETTER_FREQ_FILE, 'rb') as f:
            single_letter_freq = pickle.load(f)
        with open(PAIR_LETTER_FREQ_FILE, 'rb') as f:
            pair_letter_freq = pickle.load(f)
        with open(OVERALL_LETTER_FREQ_FILE, 'rb') as f:
            overall_letter_freq = pickle.load(f)
        logger.info("Loaded precomputed letter frequencies successfully.")
    except FileNotFoundError as e:
        logger.error(f"Precomputed frequency file not found: {e}. Please run preprocess.py first.")
    except Exception as e:
        logger.error(f"Error loading precomputed frequencies: {e}")

def load_clean_wordlist(pickle_file: str = CLEAN_WORDLIST_FILE) -> None:
    global word_list, word_list_e, word_list_ne, word_list_mtime
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
        with open(CLEAN_WORDLIST_FILE_E, 'rb') as f:
            word_list_e = pickle.load(f)
        with open(CLEAN_WORDLIST_FILE_NE, 'rb') as f:
            word_list_ne = pickle.load(f)
        word_list_mtime = current_mtime
        logger.info(f"Loaded clean wordlist with {len(word_list)} words in {time.time() - start_time:.4f} seconds.")
    except Exception as e:
        logger.error(f"Error loading clean wordlist: {e}")
        word_list = []

# Initialize word list and letter frequencies
load_clean_wordlist()
load_precomputed_frequencies()

def build_regex_pattern(word_state: str) -> re.Pattern:
    """
    Builds a regex pattern from the word_state.
    '_' is replaced with '.', and known letters are escaped.
    The pattern is compiled for faster matching.
    """
    # Replace '_' with '.', escape other characters
    word_state_regex = ''.join(['.' if c == '_' else re.escape(c) for c in word_state.upper()])
    # Since word length is unknown, allow any number of characters before and after
    pattern = f"{word_state_regex}"  # Match the entire word
    regex = re.compile(pattern)
    return regex

def filter_word(word: str, regex: re.Pattern, incorrect_letters: Set[str]) -> bool:
    """
    Checks if a word matches the regex pattern and doesn't contain any incorrect letters.
    """
    if not regex.search(word):
        return False
    if set(word).intersection(incorrect_letters):
        return False
    return True

async def get_possible_words(word_state: str, guessed_letters: List[str], incorrect_letters: Set[str]) -> List[str]:
    """
    Filters the word_list to find all possible words that match the current word_state.
    Utilizes multithreading for efficient processing.
    """
    start_time = time.time()
    regex = build_regex_pattern(word_state)
    incorrect_letters = set(letter.upper() for letter in incorrect_letters)
    
    updated_wordlist = word_list

    if 'E' not in (letter.upper() for letter in incorrect_letters):
        logger.debug("Using wordlist with 'E'")
        updated_wordlist = word_list_e
    elif 'E' in (letter.upper() for letter in incorrect_letters):
        logger.debug("Using wordlist without 'E'")
        updated_wordlist = word_list_ne

    possible_words = []
    num_threads = THREADCOUNT

    def worker(words_chunk):
        matched = []
        for word in words_chunk:
            if filter_word(word, regex, incorrect_letters):
                matched.append(word)
        return matched

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        chunk_size = max(len(updated_wordlist) // num_threads, 1)
        futures = []
        for i in range(num_threads):
            start = i * chunk_size
            end = (i + 1) * chunk_size if i != num_threads - 1 else len(updated_wordlist)
            futures.append(executor.submit(worker, updated_wordlist[start:end]))
        for future in as_completed(futures):
            possible_words.extend(future.result())

    logger.info(f"Filtered possible words in {time.time() - start_time:.4f} seconds. {len(possible_words)} words found.")
    return possible_words

@njit
def letter_freq_worker(words_chunk, guessed_letters_bitmask):
    """
    Numba-optimized worker function to compute letter frequencies.
    
    Parameters:
    - words_chunk (np.ndarray): 2D array of ASCII values representing words.
    - guessed_letters_bitmask (int): Bitmask representing guessed letters.
    
    Returns:
    - np.ndarray: Array of counts for each letter a-z.
    """
    local_counter = np.zeros(26, dtype=np.int32)  # For letters a-z
    
    num_words, word_length = words_chunk.shape
    
    for i in range(num_words):
        word_bitmask = 0
        
        # Create a bitmask for unique letters in the word
        for j in range(word_length):
            char = words_chunk[i, j]
            if char == 0:
                break  # Reached padding
            idx = char - 97  # 'a' has ASCII 97
            if 0 <= idx < 26:
                word_bitmask |= (1 << idx)
        
        # Exclude guessed letters
        available_bitmask = word_bitmask & (~guessed_letters_bitmask)
        
        # Update the counter
        for k in range(26):
            if (available_bitmask >> k) & 1:
                local_counter[k] += 1
                
    return local_counter

async def compute_letter_frequencies(possible_words: List[str], guessed_letters_set: Set[str]) -> Dict[str, int]:
    """
    Computes the frequency of each letter in the possible_words.
    Utilizes Numba for efficient processing.
    Returns a dictionary with letter frequencies.
    """
    start_time = time.time()
    letter_counts = Counter()
    num_threads = THREADCOUNT

    # Initialize with the first 100 words
    words_subset = possible_words[:100]

    # Preprocess words: convert to lowercase and filter non-alphabetic characters
    sanitized_words = [''.join(filter(str.isalpha, word.lower())) for word in words_subset]

    # Determine the maximum word length for fixed-length array
    max_length = max(len(word) for word in sanitized_words) if sanitized_words else 0

    # Create a 2D NumPy array filled with zeros (padding shorter words)
    words_np = np.zeros((len(sanitized_words), max_length), dtype=np.int32)

    for i, word in enumerate(sanitized_words):
        ascii_values = [ord(char) for char in word]
        words_np[i, :len(ascii_values)] = ascii_values

    # Convert guessed_letters_set to lowercase and create a bitmask
    guessed_letters = set(letter.lower() for letter in guessed_letters_set)
    guessed_letters_bitmask = 0
    for letter in guessed_letters:
        idx = ord(letter) - ord('a')
        if 0 <= idx < 26:
            guessed_letters_bitmask |= (1 << idx)

    # Since Numba functions are not async, run them in a separate thread to avoid blocking
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Split the words_np into chunks for each thread
        chunk_size = max(len(sanitized_words) // num_threads, 1)
        futures = []
        for i in range(num_threads):
            start = i * chunk_size
            end = (i + 1) * chunk_size if i != num_threads - 1 else len(sanitized_words)
            chunk = words_np[start:end]
            futures.append(loop.run_in_executor(executor, letter_freq_worker, chunk, guessed_letters_bitmask))
        
        # Gather results as they complete
        results = await asyncio.gather(*futures)
    
    for count_array in results:
    # Convert lowercase letters to uppercase in the dictionary
        uppercase_counts = {chr(65 + i): count for i, count in enumerate(count_array)}  # 65 is ASCII for 'A'
        letter_counts.update(uppercase_counts)

    logger.info(f"Computed letter frequencies in {time.time() - start_time:.4f} seconds.")
    return dict(letter_counts)

# Define all uppercase English letters
all_letters = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    
# Define German letter frequencies
german_letter_freq = {
    'E': 17.40,
    'N': 9.78,
    'I': 7.55,
    'S': 7.27,
    'R': 7.00,
    'A': 6.51,
    'T': 6.15,
    'D': 5.08,
    'H': 4.76,
    'U': 4.35,
    'L': 3.44,
    'C': 3.06,
    'G': 3.01,
    'M': 2.53,
    'O': 2.51,
    'B': 1.89,
    'W': 1.89,
    'F': 1.66,
    'K': 1.21,
    'Z': 1.13,
    'P': 0.79,
    'V': 0.67,
    'J': 0.27,
    'Y': 0.04,
    'X': 0.03,
    'Q': 0.02
}

word_not_found = False

async def get_next_letter(word_state: str, guessed_letters: List[str], incorrect_letters: Set[str]) -> str:
    start_time = time.time()

    global word_not_found
    word_not_found = False

    # Always guess 'E' first if it hasn't been guessed yet
    if 'E' not in (letter.upper() for letter in guessed_letters):
        logger.info("Guessing 'E' as it is the most common German letter.")
        return 'E'

    guessed_letters_set = set(letter.upper() for letter in guessed_letters)
    possible_words = await get_possible_words(word_state, guessed_letters, incorrect_letters)
    if not possible_words:
        logger.warning("No possible words computed.")

        word_not_found = True
        
        # Determine unguessed letters
        unguessed_letters = all_letters - guessed_letters_set
    
        if unguessed_letters:
            # Sort unguessed letters by German frequency
            sorted_unguessed = sorted(
                unguessed_letters,
                key=lambda letter: german_letter_freq.get(letter, 0),
                reverse=True
            )
            first_guess = sorted_unguessed[0]
            logger.warning(f"Guessing the first unguessed letter: {first_guess}")
            return first_guess
        else:
            logger.warning("No unguessed letters remaining.")
            return None  # Or handle this case as needed

    letter_frequencies = await compute_letter_frequencies(possible_words, guessed_letters_set)

    if not letter_frequencies:
        logger.warning("No letter frequencies computed.")
    
        # Determine unguessed letters
        unguessed_letters = all_letters - guessed_letters_set
    
        if unguessed_letters:
            # Sort unguessed letters by German frequency
            sorted_unguessed = sorted(
                unguessed_letters,
                key=lambda letter: german_letter_freq.get(letter, 0),
                reverse=True
            )
            first_guess = sorted_unguessed[0]
            logger.warning(f"Guessing the first unguessed letter: {first_guess}")
            return first_guess
        else:
            logger.warning("No unguessed letters remaining.")
            return None  # Or handle this case as needed

    # Find the letter with the highest frequency
    next_letter = max(letter_frequencies, key=letter_frequencies.get)
    end_time = time.time()
    logger.info(f"Selected next letter '{next_letter}' based on highest frequency in {end_time - start_time:.4f} seconds.")
    return next_letter

def reset_dynamic_data():
    pass

def handle_game_result(won: bool):
    start_time = time.time()
    end_time = time.time()
    logger.info(f"Handled game result in {end_time - start_time:.4f} seconds.")
