# Silk Mulberry 1.5 API Contract

Captured from https://rumik-silk.netlify.app/docs on 2026-05-24

## Endpoint

```
POST https://silk-api.rumik.ai/v1/tts
```

## Authentication

Bearer token in `Authorization` header:

```
Authorization: Bearer rk_live_•••••••••
```

API keys are generated in the Silk dashboard and shown only once. Store in `SILK_API_KEY` environment variable.

## Request Format

Content-Type: `application/json`

### Mulberry Model (Recommended for Rumik v1)

```json
{
  "model": "mulberry",
  "text": "Sahi jawab! Bahut badhiya.",
  "speaker": "speaker_1"
}
```

**Required fields:**
- `text` (string, max 2000 characters): The tutor line to synthesize
- `model` (string): "mulberry" for this version

**Optional fields for Mulberry:**
- `description` (string): Voice style hint, e.g. "warm, encouraging tone"
- `speaker` (string): "speaker_1", "speaker_2", "speaker_3", or "speaker_4"
- `f0_up_key` (integer, -12 to +12): Pitch shift in semitones
- `temperature` (float, default 0.6): Controls variance
- `top_p` (float, default 0.95): Nucleus sampling
- `top_k` (integer, default 50): Top-k sampling
- `repetition_penalty` (float, default 1.2): Penalizes repeated tokens
- `max_new_tokens` (integer, default 2048): Max output tokens

## Response Format

- Status: 200 OK
- Content-Type: `audio/wav`
- Body: 24 kHz mono WAV audio file (binary)

## Error Handling

All error responses return JSON of shape:

```json
{
  "error": "description",
  "code": "error_code"
}
```

**Status codes:**
- `400` – Malformed request (e.g., text exceeds 2000 chars, invalid speaker)
- `401` – Invalid or missing Bearer token
- `403` – Revoked API key
- `422` – Validation failed
- `429` – Rate limited (check `Retry-After` header)
- `503` – Upstream service unavailable

## Rumik Integration Notes

1. **Text validation before Silk call:** Validator.py enforces Silk-safe rules (max 180 chars, one tone tag, Roman script). Do not send invalid text to Silk.

2. **Tone tags:** Silk Mulberry doesn't use tone prefixes (those are for Muga). Instead, pass tone intent via the `description` field or rely on speaker selection.

3. **Latency budget:** Design doc allocates 5 seconds for Silk. If timeout occurs, fall back to text-only response.

4. **Speaker selection:** For a child-friendly voice, test speaker_1 and speaker_2. Document choice once tested.

## Sample cURL Test

```bash
curl -X POST https://silk-api.rumik.ai/v1/tts \
  -H "Authorization: Bearer $SILK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mulberry",
    "text": "Sahi jawab! Bahut badhiya.",
    "speaker": "speaker_1"
  }' \
  --output audio.wav
```

## WebSocket Streaming (Out of Scope for v1)

Silk also supports WebSocket streaming at `/v1/tts/ws-connect` for real-time PCM int16 little-endian @ 24 kHz mono. This is out of scope for the hackathon demo but may be useful for future latency improvements.
