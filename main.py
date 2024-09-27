import asyncio
import socketio
from config import CONFIG

SECRET = CONFIG['SECRET']
SERVER_URL = "https://games.uhno.de"

sio = socketio.AsyncClient()

# Prioritized letter list for guessing
LETTER_ORDER = ['E', 'N', 'S', 'I', 'R', 'A', 'T', 'D', 'H', 'U', 'L', 'C', 'G', 'M', 'O', 'B', 'W', 'F', 'K', 'Z', 'P', 'V', 'J', 'Y', 'X', 'Q']

@sio.event
async def connect():
    print('Verbunden!')
    await sio.emit('authenticate', SECRET, callback=handle_auth)

async def handle_auth(success):
    if success:
        print("Anmeldung erfolgreich")
    else:
        print("Anmeldung fehlgeschlagen")
        await sio.disconnect()

def handle_init(data):
    print("Neue Runde!")
    return None

def handle_result(data):
    print("Runde vorbei!")
    return None

async def handle_round(data):
    print("Round data received:", data)
    
    # Assuming data contains the current word state (e.g., 'H_LL_')
    current_word = data.get('word', None)  # Extract the current word pattern if available
    guessed_letters = data.get('guessed_letters', [])  # Get letters that have been guessed already

    if current_word:
        # Find next letter to guess based on LETTER_ORDER
        for letter in LETTER_ORDER:
            if letter not in guessed_letters:
                print(f"Guessing the next letter: {letter}")
                await sio.emit('guess', letter)  # Emit the guess event to the server
                break
    else:
        raise NotImplementedError("Word state not provided in the round data")

handlers = {
    'INIT': handle_init,
    'ROUND': handle_round,
    'RESULT': handle_result
}

@sio.event
async def data(data):
    t = data['type']
    handler = handlers.get(t)
    
    if handler:
        # Check if the handler is an async function
        if asyncio.iscoroutinefunction(handler):
            await handler(data)  # Await async handlers like handle_round
        else:
            handler(data)  # Call regular functions like handle_init, handle_result
    else:
        print("Unbekannte Nachricht: ", data)

@sio.event
async def disconnect():
    print('Verbindung beendet!')
    asyncio.get_event_loop().stop()

async def main():
    await sio.connect(SERVER_URL, transports=['websocket'])
    await sio.wait()

if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
        loop.close()
    except Exception as e:
        print(f"Error: {e}")
        print("Byebye")