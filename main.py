import asyncio
from typing import Any, Dict, Set, List
import socketio
from config import CONFIG, logger
from models import DataDTOFactory, RoundDataDTO
from randomLogic import get_next_letter

SECRET = CONFIG['SECRET']
SERVER_URL = "https://games.uhno.de"

sio = socketio.AsyncClient()

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
        logger.info("Authentication failed")
        await sio.disconnect()

def handle_init(data: Dict[str, Any]) -> None:
    """Handles game initialization."""
    logger.info("New game initialized!")

def handle_result(data: Dict[str, Any]) -> None:
    """Handles the end of the game."""
    logger.info("Game over!")

    winner = None
    lowest_score = float('inf')  # Initialize to a very high value

    for player in data['players']:
        if player['score'] < lowest_score:
            lowest_score = player['score']
            winner = player['id']

    if winner == data['self']:
        logger.info("Your bot won!")
    else:
        logger.info(f"Player with ID {winner} won with a score of {lowest_score}")

    with open('CorrectWords.txt', 'r+', encoding='utf-8') as file:
        inhalt = file.read()
        if data['word'] in inhalt:
            return
        else:
            file.write('\n' + data['word'])

async def handle_round(data: Dict[str, Any]) -> str:
    """
    Handles each round by selecting the next best letter to guess.

    Args:
        data (Dict[str, Any]): The data dictionary containing round information.

    Returns:
        str: The next letter to guess.
    """
    round_data: RoundDataDTO = DataDTOFactory.create_dto(
        data['type'],
        data['players'],
        data['log'],
        data['self'],
        data['word'],
        data['guessed']
    )
    logger.info(f"Round data received: {round_data.word}")

    return get_next_letter(round_data)

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
        logger.error("Unknown message type received:", data)

@sio.event
async def disconnect() -> None:
    """Handles the disconnection event."""
    logger.error('Disconnected from the server!')

async def main() -> None:
    """Main function to start the client."""
    await sio.connect(SERVER_URL, transports=['websocket'])
    await sio.wait()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error("Exiting")
