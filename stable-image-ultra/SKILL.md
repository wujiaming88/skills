---
name: stable-image-ultra
description: >-
  Generate the highest quality photorealistic images using Stability AI's Stable Image Ultra
  and Stable Diffusion 3.5 Large models via AWS Bedrock. The most powerful text-to-image models
  on Bedrock. Supports multiple AWS auth methods: environment variables, credentials file,
  named profiles, IAM instance roles, SSO, or direct access keys.
  Use when the user asks for ultra-high-quality, photorealistic, or premium image generation.
  Triggers: "ultra quality image", "photorealistic image", "best quality image", "stable image ultra",
  "SD3.5", "stability ai", "ultra画质", "超高清图片", "照片级图片", "最高画质".
  Requires AWS Bedrock access with Stability AI models enabled in us-west-2.
  NOT for: editing existing images, generating video, or HTML/CSS canvas rendering.
  For budget/standard quality images, use nova-canvas skill instead.
---

# Stable Image Ultra

Generate the highest quality images on AWS Bedrock via Stability AI models.

## Models

| Model | ID | Strength | Price |
|-------|-----|---------|-------|
| **Stable Image Ultra 1.1** | `stability.stable-image-ultra-v1:1` | Photorealism, luxury, fine detail | ~$0.08/img |
| **SD 3.5 Large** | `stability.sd3-5-large-v1:0` | Creative diversity, prompt adherence | ~$0.06/img |

Default: Stable Image Ultra (highest quality).

## AWS Auth Methods

| Method | How to Use |
|--------|------------|
| **Bearer token** | `AWS_BEARER_TOKEN_BEDROCK` env var or `--bearer-token` |
| **Environment variables** | Set `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` |
| **Credentials file** | Configure `~/.aws/credentials` |
| **Named profile** | `--profile my-profile` or `AWS_PROFILE` env var |
| **Direct keys** | `--access-key AKIA... --secret-key ...` |
| **Temporary credentials** | Add `--session-token` with direct keys |
| **IAM instance role** | Auto-detected on EC2/ECS/Lambda |
| **AWS SSO** | Run `aws sso login` first |

Auto-detection order: direct keys → profile → bearer token → env vars → credentials file → instance role → SSO.

## Quick Start

```bash
# Stable Image Ultra (default, highest quality)
python3 {baseDir}/scripts/generate.py "your prompt" -o output.png

# Stable Diffusion 3.5 Large
python3 {baseDir}/scripts/generate.py "your prompt" -o output.png --model sd35

# With negative prompt
python3 {baseDir}/scripts/generate.py "your prompt" -o output.png --negative "blurry, low quality"

# With specific auth
python3 {baseDir}/scripts/generate.py "your prompt" -o output.png --profile work
```

## Parameters

| Flag | Default | Description |
|------|---------|-------------|
| `prompt` | — | Text description of the image (max 10,000 chars) |
| `-o, --output` | output.png | Output file path |
| `-m, --model` | `ultra` | Model: `ultra` or `sd35` |
| `-n, --count` | 1 | Number of images (1-5) |
| `--negative` | — | Negative prompt (what to avoid) |
| `--seed` | random | Seed for reproducibility |
| `--region` | us-west-2 | AWS region (Stability AI models require us-west-2) |
| `--profile` | — | AWS named profile |
| `--access-key` | — | AWS Access Key ID |
| `--secret-key` | — | AWS Secret Access Key |
| `--session-token` | — | AWS Session Token |
| `--bearer-token` | — | Bearer token (overrides env) |

## Workflow

1. Craft a detailed English prompt (Stability AI models perform best in English).
2. Choose model: `ultra` for photorealism, `sd35` for creative/artistic.
3. Run `generate.py` with `timeout=120`.
4. Send resulting image to user via `message` tool.

## Prompt Tips

- Detailed English prompts yield best results.
- Specify style: "photorealistic", "oil painting", "watercolor", "3D render", "anime".
- Use `--negative "blurry, low quality, text, watermark"` to exclude unwanted elements.
- Stable Image Ultra excels at: photorealism, luxury brands, fine textures, dynamic lighting.
- SD 3.5 Large excels at: diverse styles, complex compositions, typography, prompt following.

## Important Notes

- **Region**: Both models are available ONLY in `us-west-2` (Oregon). The script defaults to this region.
- **Pricing**: Ultra ~$0.08/image, SD3.5 Large ~$0.06/image.
- **API**: Very simple — request is just `{"prompt": "..."}`, response contains base64 images.
- For standard/budget images ($0.04/image), use the `nova-canvas` skill instead.
