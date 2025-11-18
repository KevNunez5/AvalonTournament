import asyncio
import websockets
import requests
import jsonpickle

async def avalon_observer(loop):
    r = requests.post("http://localhost:8888/games", data={"nplayers": 10, "nbots": 10})

    uri = "ws://localhost:8888/ws"
    try:
        async with websockets.connect(
            uri,
            ping_interval=30,  # Send a Ping every 30 seconds
            ping_timeout=20    # Wait up to 20 seconds for a Pong
        ) as websocket:
            print("WebSocket connection established.")
            agent = None
            while True:
                message = await websocket.recv()
                print(f"Received message: {message}")
                message = jsonpickle.decode(message)

    except websockets.exceptions.ConnectionClosedOK:
        print("WebSocket connection closed gracefully.")
        loop.stop()
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"WebSocket connection closed with error: {e}")
        loop.stop()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        loop.stop()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    asyncio.ensure_future(avalon_observer(loop))
    loop.run_forever()