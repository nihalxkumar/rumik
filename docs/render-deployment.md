# Deploying Rumik to Render

## Environment Variables

Add these to your Render service as environment variables:

### Required API Keys

- **`DEEPGRAM_API_KEY`** — Speech-to-text
  - Get from: https://console.deepgram.com/

- **`GEMINI_API_KEY`** — Tutor response generation
  - Get from: https://ai.google.dev/

- **`SILK_API_KEY`** — Text-to-speech synthesis
  - Get from: https://silk.rumik.ai/ (Mulberry 1.5)

### Optional Configuration

The app ships with sensible defaults for all other settings, but you can override:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DEEPGRAM_TIMEOUT` | `4` | STT timeout in seconds |
| `DEEPGRAM_MODEL` | `nova-2` | Deepgram model ID |
| `DEEPGRAM_LANGUAGE` | `hi` | Language code (hindi) |
| `GEMINI_TIMEOUT` | `3` | Tutor generation timeout |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model ID |
| `SILK_MODEL` | `mulberry` | Silk TTS model (mulberry recommended) |
| `SILK_TIMEOUT` | `5` | TTS timeout in seconds |
| `TURN_BUDGET` | `15` | Max latency for full /api/turn in seconds |

## Render Deployment Steps

1. **Push to GitHub** (if not already)
   ```bash
   git push origin main
   ```

2. **Create a Render service:**
   - Sign in to https://dashboard.render.com/
   - New → Web Service
   - Connect your GitHub repository
   - Select branch: `main`

3. **Configure the service:**
   - **Name:** `rumik` (or your choice)
   - **Environment:** Python 3.14
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port 8000`
   - **Plan:** Free or Starter (depending on expected traffic)

4. **Add environment variables:**
   - Go to **Environment** section
   - Add all three API keys (DEEPGRAM, GEMINI, SILK)
   - Optionally override timeout values if needed

5. **Deploy:**
   - Click **Create Web Service**
   - Render will automatically build and deploy on each push to `main`

## HTTPS & Microphone Access

The browser requires HTTPS for microphone access. Render automatically provides HTTPS at `https://<your-service-name>.onrender.com`, so microphone input will work out of the box.

## Monitoring & Logs

- Logs are available in the Render dashboard under **Logs**
- Check for API errors, timeout warnings, and service health

## First Test

Once deployed:
1. Open `https://<your-service-name>.onrender.com`
2. You should see the home screen
3. Tap "Practice" to test the full flow
4. Check Render logs if anything fails

## Troubleshooting

- **"No microphone"**: Ensure you're on HTTPS (Render handles this)
- **API key rejected**: Copy-paste carefully; keys are case-sensitive
- **Timeout errors**: Increase `SILK_TIMEOUT` or `GEMINI_TIMEOUT` if APIs are slow
- **500 errors**: Check Render logs for missing environment variables or API failures
