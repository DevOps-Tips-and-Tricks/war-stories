# Private ElevenLabs voice handoff

- Voice name in ElevenLabs: **Maintainer (DevOps Tips and Tricks)**
- Voice type: Instant Voice Clone
- Exact Episode 01 voice ID: `d7LpSgdCJ3SwwSFO6a5v`
- Set `ELEVENLABS_VOICE_ID=d7LpSgdCJ3SwwSFO6a5v` in the target project's private environment.
- Set `ELEVENLABS_API_KEY` separately from a workspace that can access this clone.

This handoff uses the ID saved by the production script. Keep it with the
target project's private configuration. Keep the existing approved audio
if a new project needs the same performance.

## Reuse the same clone in another project

1. Open **My Voices** in the ElevenLabs workspace that owns the clone. Find
   **Maintainer (DevOps Tips and Tricks)** and match its voice ID against the
   private handoff or the Mac’s `../video-scripts/0001-short/voice_id.txt`.
   The ID identifies the existing Instant Voice Clone across projects.
   Use an API key from a workspace with access to that voice and permission
   to generate speech. Save the key as `ELEVENLABS_API_KEY` and the exact
   ID as `ELEVENLABS_VOICE_ID` in the other project’s private environment.
2. Confirm that the voice is visible in the workspace. For an API lookup,
   request `GET /v1/voices/{voice_id}` with a key that has voice-read
   permission. Check the returned ID and name. If lookup fails, check the
   workspace and permissions before changing the voice ID.
   [ElevenLabs voice lookup](https://elevenlabs.io/docs/api-reference/voices/get)
3. Install the `elevenlabs` Python package in the target project’s environment
   and run the one-beat example below with the two variables exported. It
   requests the same model, language, voice settings, delivery direction
   and MP3 format as Episode 01. If the model is unavailable to the project’s
   key, check the workspace’s model access before choosing a replacement.
   [ElevenLabs speech with timing](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps)
4. Listen to the test take against an approved sample before generating the
   full script. For multiple beats, pass the neighbouring spoken lines as
   `previous_text` and `next_text` and keep each MP3 with its timing file.
   Retain approved takes when the exact performance matters.

```python
import base64
import json
import os
from pathlib import Path

from elevenlabs import ElevenLabs, VoiceSettings

client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
voice_id = os.environ["ELEVENLABS_VOICE_ID"]
direction = "[speaks fluent, near-native English with a light Persian accent; calm, low, measured]"
spoken = "D F says the disk is full. D U says it is almost empty."

take = client.text_to_speech.convert_with_timestamps(
    voice_id,
    text=f"{direction} {spoken}",
    model_id="eleven_v4",
    language_code="en",
    voice_settings=VoiceSettings(stability=0.95, similarity_boost=0.95),
    output_format="mp3_44100_128",
)

alignment = take.alignment
if alignment is None:
    raise RuntimeError("ElevenLabs returned no character alignment.")
start = "".join(alignment.characters).find(spoken)
if start < 0:
    raise RuntimeError("The alignment does not contain the expected spoken text.")
end = start + len(spoken)

Path("beat-01.mp3").write_bytes(base64.b64decode(take.audio_base_64))
Path("beat-01.json").write_text(
    json.dumps(
        {
            "chars": alignment.characters[start:end],
            "start": alignment.character_start_times_seconds[start:end],
            "end": alignment.character_end_times_seconds[start:end],
        },
        indent=2,
    ),
    encoding="utf-8",
)
```

For this beat, show `df` and `du` in the captions. The example saves the
spoken characters and their times. Use the pronunciation mapping above to
group them back into the display tokens.
