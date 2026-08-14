# Prompting guidance

## Specificity

- Preserve an already detailed prompt and normalize only its structure.
- Add composition, intended use, lighting, or practical layout only when it materially improves a generic request.
- Do not invent characters, brands, slogans, or narrative events.
- Quote exact in-image text and require verbatim rendering.

## Recommended order

Write scene and backdrop first, then subject, concrete details, composition, lighting, and constraints. For photorealism, name real textures and natural imperfections rather than relying only on words such as `8K` or `ultra detailed`.

## Taxonomy

Use a stable slug when it clarifies the request:

- `photorealistic-natural`
- `product-mockup`
- `ui-mockup`
- `infographic-diagram`
- `scientific-educational`
- `ads-marketing`
- `productivity-visual`
- `logo-brand`
- `illustration-story`
- `stylized-concept`
- `historical-scene`

## Example

```text
Use case: photorealistic-natural
Asset type: editorial photograph
Primary request: a crowded night market with strong everyday atmosphere
Scene/backdrop: narrow outdoor market street lined with food stalls
Subject: dense, naturally moving crowd and vendors cooking over open flames
Style/medium: candid photorealistic documentary photography
Composition/framing: eye-level wide shot with layered foreground and background
Lighting/mood: mixed warm stall lights and cool night ambience, light cooking smoke
Materials/textures: real skin, worn awnings, steam, oil sheen, metal cookware
Constraints: believable anatomy and crowd spacing; no staged poses; no watermark
Avoid: plastic skin; duplicated people; illegible prominent signs
```

## Iteration

Inspect the first output, identify the single most important mismatch, change only the corresponding prompt line, and regenerate to preserve useful qualities from the prior specification.

For edits, restate invariants on every iteration. Name exactly what may change and what must remain unchanged, including identity, geometry, pose, camera, lighting, text, or composition as applicable.
