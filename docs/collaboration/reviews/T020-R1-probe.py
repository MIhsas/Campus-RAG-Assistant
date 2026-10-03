"""Local-only all-zero PCM probe; uses an already running review demo."""
import argparse
import http.client
import io
import json
import wave

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=18833)
args = parser.parse_args()
buf = io.BytesIO()
with wave.open(buf, 'wb') as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(16000)
    wav.writeframes(bytes(32000))
conn = http.client.HTTPConnection('127.0.0.1', args.port, timeout=60)
conn.request('POST', '/api/v1/asr/transcribe', body=buf.getvalue(),
             headers={'Content-Type': 'audio/wav'})
response = conn.getresponse()
data = json.loads(response.read())
conn.close()
print(json.dumps({'status': response.status, 'body': data}, ensure_ascii=True))
assert response.status != 409, 'Service busy; run when the current transcription finishes'
assert not data.get('text', '').strip(), 'Digital silence was accepted as recognized speech'
