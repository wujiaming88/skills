---
name: custom-imagegen
description: Generate and edit raster images through user-configured OpenAI-compatible POST /images/generations and /images/edits APIs using a custom model and API key. Use when Codex should create or transform photos, illustrations, textures, mockups, banners, or image variants with a private or third-party image model instead of the built-in image generator. Supports single and JSONL batch text-to-image generation, multi-image edits, masks, structured prompt augmentation, dry runs, and local file output.
---

# Custom Image Generator

Generate or edit images through configured OpenAI-compatible image endpoints. Keep credentials in environment variables and use the bundled CLI instead of writing one-off API clients.

## Capability boundary

- Support text-to-image generation through `POST /images/generations`.
- Support edits through `POST /images/edits` with 1–16 local images and an optional mask.
- Support distinct batch jobs through JSONL.
- Accept both `data[].b64_json` and `data[].url` responses.
- Treat `size`, `quality`, `background`, `output_format`, and provider-specific fields as pass-through options. Do not assume the configured model supports them.
- Do not use `/images/variations`; it is a legacy DALL-E 2 endpoint and is not needed for this workflow.

## Configure

Require these environment variables for live calls:

```bash
export CUSTOM_IMAGE_API_BASE_URL="https://provider.example/openai/v1"
export CUSTOM_IMAGE_API_KEY="..."
export CUSTOM_IMAGE_MODEL="provider-image-model"
```

Never ask the user to paste the full key into chat. Never pass it on the command line or print it. `CUSTOM_IMAGE_API_BASE_URL` may also contain a full `/images/generations` or `/images/edits` endpoint; the CLI normalizes it to the API root.

Prefer HTTPS. An `http://` base URL sends the Bearer API key without transport encryption; use it only on a trusted local or test network and rotate the key after exposure.

Live calls require the official Python SDK:

```bash
python3 -m pip install openai
```

Use the active environment's normal package manager when one is configured. `--dry-run` does not require the SDK or API key.

Read [references/api-contract.md](references/api-contract.md) when configuring or debugging a provider. Read [references/prompting.md](references/prompting.md) when shaping a non-trivial prompt.

## Workflow

1. Classify the request as generation or edit. Treat supplied images as edit targets or supporting inputs explicitly.
2. Determine whether the result is preview-only or belongs to the current project.
3. Preserve a specific prompt. Add only materially useful detail to a generic prompt.
4. Run `--dry-run` first when the endpoint, model, or provider-specific parameters are new.
5. Generate with `scripts/image_gen.py`; do not create a temporary SDK wrapper.
6. Inspect the output for subject, composition, text accuracy, and stated constraints.
7. Iterate with one targeted prompt change at a time.
8. Save project assets in the project. Do not overwrite existing files unless the user explicitly requests it.

## Generate one request

```bash
python3 {baseDir}/scripts/image_gen.py generate \
  --prompt "A candid, photorealistic night market crowded with people" \
  --size 1536x1024 \
  --quality high \
  --out output/custom-imagegen/night-market.png
```

Use `--base-url` or `--model` only to override the corresponding non-secret environment variable. Use `--extra-json` for documented provider fields:

```bash
python3 {baseDir}/scripts/image_gen.py generate \
  --prompt "A quiet mountain lake at dawn" \
  --extra-json '{"seed": 42}' \
  --out output/custom-imagegen/lake.png
```

## Edit images

Repeat `--image` for multiple inputs and use an optional PNG mask:

```bash
python3 {baseDir}/scripts/image_gen.py edit \
  --image product.png \
  --image material-reference.png \
  --mask mask.png \
  --prompt "Replace only the product material with brushed aluminum" \
  --input-fidelity high \
  --out output/custom-imagegen/product-edited.png
```

State edit invariants in the prompt, such as `change only the material; preserve shape, camera angle, lighting, and composition`. The mask is provider-interpreted and does not guarantee pixel-exact boundaries.

## Generate distinct batch jobs

Create a JSONL file with one prompt string or object per line:

```jsonl
{"prompt":"A ceramic mug in soft studio light","out":"mug.png"}
{"prompt":"A linen notebook on a wooden desk","out":"notebook.png","size":"1536x1024"}
```

Then run:

```bash
python3 {baseDir}/scripts/image_gen.py generate-batch \
  --input jobs.jsonl \
  --out-dir output/custom-imagegen
```

Batch generation is sequential so failures and provider costs remain easy to attribute. Use `--dry-run` to inspect every payload and output path without requiring the API key.

## Prompt structure

Use only relevant labeled lines:

```text
Use case: <taxonomy slug>
Asset type: <intended use>
Primary request: <main request>
Scene/backdrop: <environment>
Subject: <main subject>
Style/medium: <photo/illustration/3D>
Composition/framing: <framing and placement>
Lighting/mood: <lighting and mood>
Text (verbatim): "<exact text>"
Constraints: <must keep and must avoid>
Avoid: <negative constraints>
```

Pass these as CLI prompt fields when useful, or use `--no-augment` to send the prompt verbatim.

## Output rules

- Default to `output/custom-imagegen/output.png` for one-off project generation.
- Use semantic filenames for requested assets.
- Refuse to overwrite by default; use `--force` only when replacement is explicit.
- Render the saved image inline when the environment supports local image display.
- Report the saved path, final prompt, configured model, and any pass-through options used.
