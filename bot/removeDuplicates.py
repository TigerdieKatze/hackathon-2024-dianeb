import os
from config import logger

WORD_LIST_FILE = './lists/wordlist.txt'

def remove_duplicates(file_path):
    if not os.path.exists(file_path):
        print(f"{file_path} does not exist.")
        return

    # Read all lines from the file
    with open(file_path, 'r', encoding='utf-8') as f:
        words = f.readlines()

    # Initialize a set for case-insensitive comparison and a list to store unique words
    seen_upper = set()
    unique_words = []
    total_words = 0  # Counter for valid words (non-empty and length >= 5)

    for word in words:
        word_clean = word.strip()
        if not word_clean:
            continue  # Skip empty lines
        if len(word_clean) < 5:
            continue  # Skip words with less than 5 letters
        total_words += 1
        word_upper = word_clean.upper()
        if word_upper not in seen_upper:
            seen_upper.add(word_upper)
            unique_words.append(word_clean)

    # Write the unique words back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        for word in unique_words:
            f.write(f"{word}\n")

    duplicates_removed = total_words - len(unique_words)
    logger.info(f"Removed {duplicates_removed} duplicates and words shorter than 5 letters from {file_path}")

remove_duplicates(WORD_LIST_FILE)