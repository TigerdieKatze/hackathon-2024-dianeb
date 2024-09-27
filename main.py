import asyncio
import socketio
from config import CONFIG

SECRET = CONFIG['SECRET']
SERVER_URL = "https://games.uhno.de"

sio = socketio.AsyncClient()

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

def handle_round(data):
    raise NotImplementedError("handle_round function is not implemented yet")

handlers = {
    'INIT': handle_init,
    'ROUND': handle_round,
    'RESULT': handle_result }

@sio.event
async def data(data):
    t = data['type']
    if t in handlers:
        return handlers[t](data)
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
    except:
        print("Byebye")