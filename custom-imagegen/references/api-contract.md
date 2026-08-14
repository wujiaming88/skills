# API contract

## Required generation request

The CLI sends a JSON request to:

```text
POST <CUSTOM_IMAGE_API_BASE_URL>/images/generations
Authorization: Bearer <CUSTOM_IMAGE_API_KEY>
Content-Type: application/json
```

The minimum request body is:

```json
{
  "model": "configured-model",
  "prompt": "image prompt",
  "n": 1
}
```

`CUSTOM_IMAGE_API_BASE_URL` should normally end in `/openai/v1`. A full URL ending in `/images/generations` or `/images/edits` is normalized back to its API root. Only `http` and `https` URLs are allowed.

Prefer HTTPS. With an `http://` base URL, the Bearer API key is not protected by transport encryption. Limit HTTP to trusted local or test networks and rotate any key used over an untrusted path.

## Required edit request

The CLI uses the official OpenAI Python SDK to send multipart form data to:

```text
POST <CUSTOM_IMAGE_API_BASE_URL>/images/edits
Authorization: Bearer <CUSTOM_IMAGE_API_KEY>
Content-Type: multipart/form-data
```

It sends `model`, `prompt`, `n`, one or more `image` parts, and an optional `mask` part. Up to 16 local input images are accepted. Each image and mask must be non-empty and no larger than 50MB.

## Optional pass-through fields

The CLI sends `size`, `quality`, `background`, `output_format`, `output_compression`, `moderation`, `response_format`, and `user` only when explicitly provided. Edits additionally accept `input_fidelity`. Because model support varies, verify each option against the provider documentation before relying on it.

Use `--extra-json` for provider-specific body fields. It must be an object and cannot replace `model`, `prompt`, `n`, `image`, or `mask`.

## Accepted responses

Base64 response:

```json
{"data":[{"b64_json":"<base64 image>"}]}
```

URL response:

```json
{"data":[{"url":"https://download.example/image.png"}]}
```

The CLI never forwards the API key to a returned download URL. It rejects non-HTTP(S) download URLs.

## Declared limitations

- Local file input is supported for edits; File API IDs and remote edit-input URLs are not exposed by this CLI.
- Streaming partial images are not exposed.
- No assumption that transparency, size, quality, moderation, seeds, or negative prompts are supported.
- No automatic retry, because generation and edit requests may be billable and the provider's idempotency contract is unknown.
- Batch jobs run sequentially and stop on the first failure.

## Troubleshooting

- `401` or `403`: verify the locally configured API key and provider permissions; never paste the key into chat.
- `404`: verify whether the base URL includes `/openai/v1`; run `--dry-run` and inspect the computed endpoint.
- `400`: compare the dry-run payload with the provider schema and remove unsupported pass-through fields.
- Empty `data`: inspect provider-side moderation or quota logs.
- URL download failure: verify the returned URL is reachable from the current environment and has not expired.
- Edit upload failure: verify image count, file size, mask format, and model support for `input_fidelity`.
