# ElevenLabs voiceover with the maintainer’s cloned voice

Episode 01 used an ElevenLabs Instant Voice Clone made from the maintainer’s
own cold-open voice memo. We used it for the six-beat `df` versus `du` Short
and for a long-form pilot with a live, to-camera teaching pause. The
maintainer found the clone close enough to his own voice and chose it for the
pilot. The Short’s script, pronunciations and final visual cues are in the
[Episode 01 narration notes](../stories/0001-deleting-the-largest-log-file-did-not-free-the-full-volume/0001-short-narration.md).

## What made the voice sound closer

We first shortlisted stock voices using pitch level, pitch range, speaking
rate and brightness. That gave us comparable previews, but matching those
numbers did little to establish whether a voice sounded like the maintainer.
Keep a clean excerpt of the real voice beside the test takes and let the
maintainer judge accent, timbre and delivery by ear.

We compared takes of the same opening beat. Moving the stability and
similarity sliders had little effect on the pitch. Giving the model a delivery
direction for fluent English with a light Persian accent made a bigger
difference for this voice.

| Opening-beat take | Stability | Similarity boost | Estimated median pitch |
| --- | ---: | ---: | ---: |
| Original recording | | | 97 Hz |
| First clone take | 0.60 | 0.85 | 121 Hz |
| Higher settings | 0.80 | 0.95 | 125 Hz |
| Final settings, plain | 0.95 | 0.95 | 125 Hz |
| Final settings, with delivery direction | 0.95 | 0.95 | 113 Hz |

The six selected Short takes measured roughly 107–109 Hz. These are
estimates from the session’s acoustic comparison, which helped track changes
in pitch. Accent and resemblance were listening decisions.

The working setup for Episode 01 was `eleven_v4`, `language_code="en"`,
`stability=0.95` and `similarity_boost=0.95` with this direction at the start
of each beat:

> [speaks fluent, near-native English with a light Persian accent; calm, low, measured]

Start with one or two representative beats and save both takes before
changing the settings again. Include a line with commands and a line with a
contrast or emphasis the voice needs to land. Once those work, generate the
full script. The settings above record the Episode 01 result and can serve as
the starting point for the next comparison.

## Generate in beats and cut to the audio

1. **Write for the ear.** Use short sentences and preserve the technical
   meaning in each beat. Keep the text that ElevenLabs reads separate from the
   caption spelling. The local script uses `{display|spoken}`, for example
   `{df|D F}`, `{du|D U}`, `{rm|R M}` and
   `{lsof +L1|L S O F, plus L one}`.
2. **Save each take with its timestamps.** The generation script requests
   audio and character alignment together and passes the neighbouring beats
   as context. It saves a matching MP3 and alignment JSON per beat. It
   locates the spoken text in the returned alignment and drops the delivery
   tag’s characters so the caption offsets match the script.
3. **Check the spoken output.** Listen for command names, stress and any
   audible delivery tag. Transcribing the six Short beats back with
   ElevenLabs Scribe gave us a second check on the intended words. The
   selected takes matched the narration, and the tag stayed out of the
   transcript. Give edited beats new audio and alignment together.
4. **Join the final takes before rendering.** The join step measures each MP3
   with `ffprobe`, inserts 0.55 seconds of silence between beats, and writes
   the 48 kHz mono `narration.wav` and `words.json`. Use those actual word and
   beat times for captions, terminal highlights and animation. Word count put
   the Short narration at roughly 56 seconds. The selected narration was
   68.4 seconds. Regenerate the timing file and affected visuals if a take
   changes length.
5. **Check the rendered cut.** Inspect frames at known word times and review
   the mix at normal playback speed. The Short’s commands use their literal
   spelling on screen, and captions sit above the Shorts controls. The
   Episode 01 mix measured about −15.9 LUFS with a −1.5 dBTP peak in the
   production check. The episode’s publishing notes record the decision to
   select YouTube’s altered-content setting for this cut.

## Put a real camera take between narrated scenes

For the long-form pilot, the generated voice explained the demo, then the
scene froze for the maintainer’s live teaching point. Record and time the
camera clip first. Render the hold to match that clip, then shift the
remaining captions by the inserted duration. Keep the pause’s narration
track silent so the camera audio has the floor. Match the camera clip’s
loudness to the clone, with noise reduction or voice enhancement limited to the
camera clip if needed. Listen across both joins.

The pilot exported an FCPXML timeline for Final Cut Pro. The CapCut handoff
provided three rendered clips and a separate SRT shifted for the hold.
Place the camera overlay over the middle clip. The detailed handoff is local at
`video-scripts/0001-long-pilot/CAPCUT.md`.

## Where the Mac workflow lives

- `video-scripts/0001-short/voice.py` contains the clone, speech and join
  commands. Use the existing clone for another take. The one-time clone call
  needed a key with voice-creation access. With the SDK used in that session,
  passing `labels` as a Python dictionary fixed clone validation. The SDK
  performed the JSON encoding.
- `video-scripts/0001-short/voicematch.py` compares the acoustic measurements
  above. `render3.py` renders the final Short from the approved audio and word
  timing. The local `requirements.txt` lists the production dependencies.
- When working in `video-scripts/0001-short/`, the existing command for a test
  take is `.venv/bin/python voice.py speak 1`. Set `VOICE_DIRECTION` to the
  bracketed text above and point `BEATS_DIR` at a separate scratch directory
  to retain the approved take. After selecting a replacement, move its MP3
  and JSON together into the working beat set and run
  `.venv/bin/python voice.py join`. The join uses `ffmpeg` and `ffprobe`.
- The pilot supplies its own script via `BEATS_FILE` and uses separate
  `BEATS_DIR` and `OUT_DIR` paths. Its renderer reads the matching
  `narration.wav` and `words.json`.
- Keep the API key in the ignored repo-root `.env` and the voice identifier,
  sample recordings, takes, alignment files and video masters in the ignored
  production workspace or other private storage.

## Reuse the same clone in another project

1. Open **My Voices** in the ElevenLabs workspace that owns the clone. Find
   **Maintainer (DevOps Tips and Tricks)** and match its voice ID against the
   private handoff or the Mac’s `video-scripts/0001-short/voice_id.txt`.
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
