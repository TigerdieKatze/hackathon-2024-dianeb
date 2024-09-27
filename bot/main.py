import asyncio
from typing import Any, Dict, Set
import socketio
from config import SECRET, logger, RESULTS_FILE, IsFarmBot
from models import DataDTOFactory, RoundDataDTO
from advancedlogic import (
    get_next_letter,
    handle_game_result,
)
import time

SERVER_URL = "https://games.uhno.de"

sio = socketio.AsyncClient()

# Global statistics variables
total_games = 0
total_wins = 0
total_new_words_added = 0  # New variable to track words added to the word list
error_counts_per_word_length = {}  # key: word_length, value: {'errors': total_errors, 'games': num_games}
total_time = 0
total_turns = 0

# Global variable for incorrect letters
incorrect_letters: Set[str] = set()
turn_times = []

def load_results():
    """Loads previous game results from RESULTS_FILE."""
    global total_games, total_wins, error_counts_per_word_length
    global total_time, total_turns, total_new_words_added
    total_time = 0
    total_turns = 0
    total_new_words_added = 0
    try:
        with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Parse the line
                # Expected format: 'win,word_length,error_count,total_time,num_turns,word_added'
                parts = line.split(',')
                if len(parts) != 6:
                    logger.warning(f"Invalid line in results file: {line}")
                    continue
                result, word_length_str, error_count_str, total_time_str, num_turns_str, word_added = parts
                word_length = int(word_length_str)
                error_count = int(error_count_str)
                total_time_game = float(total_time_str)
                num_turns_game = int(num_turns_str)
                total_games += 1
                if result == 'win':
                    total_wins += 1
                if word_length not in error_counts_per_word_length:
                    error_counts_per_word_length[word_length] = {'errors': 0, 'games': 0}
                error_counts_per_word_length[word_length]['errors'] += error_count
                error_counts_per_word_length[word_length]['games'] += 1
                total_time += total_time_game
                total_turns += num_turns_game
                if word_added == 'yes':
                    total_new_words_added += 1
        logger.info(f"Loaded previous results: {total_games} games, {total_wins} wins.")
    except FileNotFoundError:
        logger.info("Results file not found. Starting fresh statistics.")
    except Exception as e:
        logger.error(f"Error loading results: {e}")

@sio.event
async def connect() -> None:
    """Handles the connection event."""
    logger.info('Connected to the server!')
    await sio.emit('authenticate', SECRET, callback=handle_auth)

async def handle_auth(success: bool) -> None:
    """Handles authentication response."""
    if success:
        logger.info("Authentication successful")
    else:
        logger.error("Authentication failed")
        await sio.disconnect()

def handle_init(data: Dict[str, Any]) -> None:
    """Handles game initialization."""
    logger.info("New game initialized!")
    global incorrect_letters, turn_times
    incorrect_letters = set()  # Reset incorrect letters at the start of a new game
    turn_times = []  # Reset turn times

def handle_result(data: Dict[str, Any]) -> None:
    """Handles the end of the game."""
    logger.info("Game over!")

    global total_games, total_wins, error_counts_per_word_length, total_time, total_turns, turn_times
    global total_new_words_added

    # Initialize variables
    winners = []
    lowest_score = float('inf')

    # Iterate over players to find the lowest score and winner(s)
    for player in data['players']:
        if player['score'] < lowest_score:
            lowest_score = player['score']
            winners = [player['id']]
        elif player['score'] == lowest_score:
            winners.append(player['id'])

    # Determine if your bot is among the winners
    bot_won = data['self'] in winners

    if bot_won:
        logger.info("Your bot won!")
    else:
        logger.info(f"Player(s) with ID(s) {', '.join(winners)} won with a score of {lowest_score}")

    # Find your bot's score
    your_score = next((player['score'] for player in data['players'] if player['id'] == data['self']), None)
    if your_score is None:
        logger.error("Your bot's score not found in data.")
        your_score = 25  # Assume worst case

    logger.info(f"Your bot's score: {your_score}")

    # Update statistics
    total_games += 1
    if bot_won:
        total_wins += 1

    # Get the word length
    final_word = data.get('word', '').strip()
    word_length = len(final_word)

    # Update error counts per word length
    if word_length not in error_counts_per_word_length:
        error_counts_per_word_length[word_length] = {'errors': 0, 'games': 0}
    error_counts_per_word_length[word_length]['errors'] += your_score
    error_counts_per_word_length[word_length]['games'] += 1

    # Compute total time and number of turns
    game_total_time = sum(turn_times)
    game_num_turns = len(turn_times)
    if game_num_turns > 0:
        avg_time_per_turn = game_total_time / game_num_turns
    else:
        avg_time_per_turn = 0

    logger.info(f"Average time per turn: {avg_time_per_turn:.2f} seconds")

    # Check if the word was added to the word list
    word_added = 'no'

    # Save the result to RESULTS_FILE
    try:
        with open(RESULTS_FILE, 'a', encoding='utf-8') as f:
            result = 'win' if bot_won else 'loss'
            f.write(f"{result},{word_length},{your_score},{game_total_time},{game_num_turns},{word_added}\n")
    except Exception as e:
        logger.error(f"Error writing to results file: {e}")

    # Update global totals
    total_time += game_total_time
    total_turns += game_num_turns

    # Compute win percentage
    win_percentage = (total_wins / total_games) * 100
    logger.info(f"Win percentage: {win_percentage:.2f}% ({total_wins}/{total_games})")

    # Compute error count per word length percentage
    logger.info("Error count per word length:")
    for wl in sorted(error_counts_per_word_length.keys()):
        errors = error_counts_per_word_length[wl]['errors']
        games = error_counts_per_word_length[wl]['games']
        avg_errors = errors / games if games > 0 else 0
        logger.info(f"  Word Length {wl}: Average Errors {avg_errors:.2f} over {games} game(s)")

    # Adjust weights based on game result
    handle_game_result(bot_won)

    # Reset turn_times for the next game
    turn_times = []

async def handle_round(data: Dict[str, Any]) -> str:
    if IsFarmBot:
        logger.debug("FarmBot is enabled. Skipping round.")
        return ''

    global incorrect_letters, turn_times
    start_time = time.time()
    try:
        round_data: RoundDataDTO = DataDTOFactory.create_dto(
            data['type'],
            data['players'],
            data['log'],
            data['self'],
            data['word'],
            data['guessed']
        )
        logger.info(f"Round data received: Word state '{round_data.word}', Guessed letters {round_data.guessed}")

        # Update incorrect letters
        current_word_letters = set(round_data.word.replace('_', ''))
        incorrect_letters = set(letter for letter in round_data.guessed if letter not in current_word_letters)

        next_letter = await get_next_letter(round_data.word, round_data.guessed, incorrect_letters)
        if next_letter is None:
            logger.error("No valid letters left to guess.")
            # Select a random unguessed letter to avoid invalid move
            all_letters = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
            unguessed_letters = all_letters - set(round_data.guessed)
            if unguessed_letters:
                next_letter = unguessed_letters.pop()
                logger.warning(f"Selecting random unguessed letter '{next_letter}'.")
            else:
                # As a last resort, return a commonly used letter
                next_letter = 'E'
                logger.warning("All letters guessed. Defaulting to letter 'E'.")

        logger.info(f"Guessing the next letter: '{next_letter}'")
        return next_letter
    except Exception as e:
        logger.error(f"Error in handle_round: {e}")
        # Return a default letter to avoid making an invalid move
        return 'E'
    finally:
        end_time = time.time()
        turn_times.append(end_time - start_time)

handlers = {
    'INIT': handle_init,
    'RESULT': handle_result
}

@sio.event
async def data(data: Dict[str, Any]) -> Any:
    """Dispatches incoming data to the appropriate handler."""
    message_type = data.get('type')
    if message_type == 'ROUND':
        return await handle_round(data)
    elif message_type in handlers:
        handler = handlers[message_type]
        handler(data)
    else:
        logger.error(f"Unknown message type received: {data}")

@sio.event
async def disconnect() -> None:
    """Handles the disconnection event."""
    logger.error('Disconnected from the server!')

async def main() -> None:
    """Main function to start the client."""
    await sio.connect(SERVER_URL, transports=['websocket'])
    await sio.wait()

if __name__ == '__main__':
    # Load previous results
    load_results()
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error("Exiting")
