import asyncio
import json
import os
import socket
import websockets

async def test_elevenlabs_ws():
    uri = "wss://api.elevenlabs.io/v1/text-to-speech/ws"

    headers = {
        "xi-api-key": os.getenv("ELEVEN_LABS_API_KEY")
    }

    payload = {
        "text": "Willkommen bei firstclass!",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8
        },
        "voice_id": "g6xIsTj2HwM6VR4iXFCw",
        "model_id": "eleven_multilingual_v2"
    }

    # Forciere IPv4
    async with websockets.connect(uri, extra_headers=headers, family=socket.AF_INET) as websocket:
        print("✅ Verbunden mit ElevenLabs WS")

        await websocket.send(json.dumps(payload))

        while True:
            try:
                message = await websocket.recv()
                if isinstance(message, bytes):
                    print(f"📥 Audio-Chunk empfangen: {len(message)} Bytes")
                else:
                    print(f"ℹ️ Message: {message}")
            except websockets.exceptions.ConnectionClosed:
                print("🔌 Verbindung geschlossen")
                break

if __name__ == "__main__":
    asyncio.run(test_elevenlabs_ws())