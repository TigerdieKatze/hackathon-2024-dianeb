import asyncio
from typing import Any, Dict
import socketio
from config import CONFIG, logger, RESULTS_FILE
from models import DataDTOFactory, RoundDataDTO
from advancedlogic import get_next_letter, add_word, word_list

SECRET = CONFIG['SECRET']
SERVER_URL = "https://games.uhno.de"

sio = socketio.AsyncClient()

# Global statistics variables
total_games = 0
total_wins = 0
error_counts_per_word_length = {}  # key: word_length, value: {'errors': total_errors, 'games': num_games}

def load_results():
    """Loads previous game results from RESULTS_FILE."""
    global total_games, total_wins, error_counts_per_word_length
    try:
        with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Parse the line
                # Expected format: 'win,word_length,error_count'
                parts = line.split(',')
                if len(parts) != 3:
                    logger.warning(f"Invalid line in results file: {line}")
                    continue
                result, word_length_str, error_count_str = parts
                word_length = int(word_length_str)
                error_count = int(error_count_str)
                total_games += 1
                if result == 'win':
                    total_wins += 1
                if word_length not in error_counts_per_word_length:
                    error_counts_per_word_length[word_length] = {'errors': 0, 'games': 0}
                error_counts_per_word_length[word_length]['errors'] += error_count
                error_counts_per_word_length[word_length]['games'] += 1
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

def handle_result(data: Dict[str, Any]) -> None:
    """Handles the end of the game."""
    logger.info("Game over!")

    global total_games, total_wins, error_counts_per_word_length

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

    # Save the result to RESULTS_FILE
    try:
        with open(RESULTS_FILE, 'a', encoding='utf-8') as f:
            result = 'win' if bot_won else 'loss'
            f.write(f"{result},{word_length},{your_score}\n")
    except Exception as e:
        logger.error(f"Error writing to results file: {e}")

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

    # Add the word to the word list if not already there
    if final_word:
        if final_word not in word_list:
            add_word(final_word)
        else:
            logger.debug(f"The word '{final_word}' is already in the word list.")

async def handle_round(data: Dict[str, Any]) -> str:
    """
    Handles each round by selecting the next best letter to guess.

    Args:
        data (Dict[str, Any]): The data dictionary containing round information.

    Returns:
        str: The next letter to guess.
    """
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

        next_letter = get_next_letter(round_data.word, round_data.guessed)
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
