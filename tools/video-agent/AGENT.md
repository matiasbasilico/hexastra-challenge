# HexAstra pitch production agent

Use this brief with a coding/video agent alongside the runner in this directory.

## Assignment

Produce a three-minute walkthrough of HexAstra from the team-supplied presentation, actual application recordings, and reviewed narration. The application is https://hexastra.pages.dev/. Use `?lang=en` or `?lang=es` to make recording language explicit. The approved Spanish narration uses Ignacio; do not change voice, scientific claims, or script without the team's instruction.

## Required inputs

- The current seven-slide PDF supplied by the team.
- The final reviewed script and action plan, provided as `plan.es.json` for the existing Spanish pitch.
- Actual guided and advanced recordings and the screenshots listed by `agent.py inspect`.
- Montserrat and Open Sans variable font files from their credited upstream sources.
- Licensed narration generated during an eligible ElevenLabs subscription. Keep the generation/plan record; do not assume that paying later changes the license of existing free-plan audio.

Do not bundle credentials, paid voice downloads, presentation source files, or large private build directories into the repository.

## Workflow

1. Read the repository README, method, and source register. Compare the PDF with the running app. Mark an unsupported claim for human review rather than silently inventing a result.
2. Inspect the PDF and render its pages. Confirm the seven-slide order, readable text, and all required input assets. Use `agent.py prepare` to create an external workspace.
3. Keep the presentation **stationary and fully visible**. The opening comparison uses zoomed 2D terrain; do not substitute the 3D globe in that opening. A brief fade or restrained overlay is acceptable. Do not pan/zoom the slides.
4. Introduce five dimensions before the demo. Show guided mode until the narration explicitly introduces advanced mode. Explain Arsia Mons and the dated orbital publication, the worldwide/continent/country search options, the real result, adjustable weights, layers, and the evidence.
5. Record the actual app. Do not mock API results or invent a score. If the live catalog changes, update the narration and presentation only with the team's review.
6. Obtain the narration with the approved voice and license. The agent must not buy a plan or generate chargeable audio without the user's authorization. Place supplied audio in the prepared workspace.
7. Align phrases using the included speech-alignment source. Listen to the sibilants, names, sentence edges, and every splice. Keep all phrases inside their shot windows without overlap.
8. Render exactly 180 seconds at 1920 × 1080 and 30 fps. Use the included locally synthesized music, ducked under narration. Preserve source/AI-use metadata and export subtitles.
9. Check the complete file with ffprobe and an FFmpeg decode, inspect representative frames, and listen to the entire output. Deliver the MP4, subtitle file, narration text, action plan, and a reproducible asset manifest.

The included `source/` files are the actual compositor/alignment/export sources used for the refined Spanish video, adapted to relative working-directory paths. They preserve the existing cut and timing logic; they are not a request to generate another video automatically.
