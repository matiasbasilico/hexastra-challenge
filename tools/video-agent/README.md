# HexAstra video production agent

This folder packages the actual source workflow for the refined 180-second Ignacio pitch, its reviewed shot/narration plan, and an operating brief in [AGENT.md](AGENT.md). The source is portable; media inputs and private accounts remain outside the repository.

## Contents

- `agent.py`: workspace preparation, plan validation, input inspection, alignment, render, export, and music commands.
- `plan.es.json`: the final Spanish narration and action timing used for the existing refined pitch. Spanish text is source narration, not untranslated documentation.
- `source/`: the production compositor, speech-alignment helpers, renderer, music generator, and exporter.
- `assets/dimensions.es.png`: the code-drawn five-dimension graphic used in that pitch.
- `requirements.txt`: Python dependencies. FFmpeg/ffprobe and Poppler (`pdfinfo`, `pdftoppm`) are system prerequisites.

The sources do not include the supplied PDF, original voice recordings, credentials, downloaded map tiles, full videos, or workstation-specific build folders.

## Prepare

```bash
python3 -m venv /tmp/hexastra-video-env
/tmp/hexastra-video-env/bin/pip install -r tools/video-agent/requirements.txt
/tmp/hexastra-video-env/bin/python tools/video-agent/agent.py inspect
/tmp/hexastra-video-env/bin/python tools/video-agent/agent.py prepare \
  --workdir /tmp/hexastra-pitch --pdf /path/to/presentation.pdf
/tmp/hexastra-video-env/bin/python tools/video-agent/agent.py inspect --workdir /tmp/hexastra-pitch
```

`inspect` lists required inputs and fails when the workspace is incomplete. `prepare` validates a 180-second plan, copies the production source into the external workspace, renders a supplied PDF, and writes the timestamped narration text. It does not generate or purchase voice audio.

The runtime plan retains its existing field names and asset paths so the original compositor remains compatible. Place recordings under `inputs/demos/`, screenshots under `build/v2/shots/`, rendered slides under `build/pdf-nuevo/slides-video/`, and font files under `build/fonts/`. `inspect` reports the exact filenames.

## Audio and rendering

For the original two-pass audio workflow, supply `inputs/audio/base.mp3`; `inputs/audio/intro.mp3` and an aligned `inputs/audio/hook.wav` can preserve the approved introduction and opening. When using a separate intro pass, provide the matching `intro-frases.json` timing list in the prepared alignment directory. Use the final canonical script when regenerating the entire narration.

```bash
/tmp/hexastra-video-env/bin/python tools/video-agent/agent.py music --workdir /tmp/hexastra-pitch
/tmp/hexastra-video-env/bin/python tools/video-agent/agent.py align --workdir /tmp/hexastra-pitch
/tmp/hexastra-video-env/bin/python tools/video-agent/agent.py render --workdir /tmp/hexastra-pitch
/tmp/hexastra-video-env/bin/python tools/video-agent/agent.py export --workdir /tmp/hexastra-pitch
```

Rendering requires all listed media inputs. The retained alignment source uses faster-whisper and may download its public model on first execution. The compositor imports edge-tts for its optional development-voice path; the approved final narration is supplied ElevenLabs audio. No TTS provider is called by the `prepare` or `inspect` commands.

## English presentation recordings

The guided and advanced English GIFs are recorded from the actual bilingual app. Use the repository's recording script with an explicit `?lang=en` URL; see the root README for the public GIF/MP4 links and capture instructions. These recordings do not require generating a new voice track.

## Rights and disclosure

Follow the root README's external-resource register and unresolved permission notes. Credit ElevenLabs, fonts, scientific data, basemaps, and production tools as applicable. Confirm rights to the supplied PDF imagery and voice generation. Keep scientific numbers sourced, missing evidence explicit, and AI assistance disclosed. Do not claim that the supplied license audit has already cleared every input.
