---
name: connect-deepgram-setup
description: "Bootstrap Amazon Connect + Deepgram TTS/STT: create/update Secrets Manager secret, apply secret+KMS policies safely, and list valid Deepgram model IDs + voice IDs."
user-invocable: true
disable-model-invocation: false
---

# Amazon Connect + Deepgram Setup Skill

Use this skill to reliably configure Deepgram as a third-party TTS and STT provider in Amazon Connect **without** re-hitting the common failure modes:

- KMS decrypt denied (`Access to KMS is not allowed`)
- Secret schema mismatch (`secret could not be deserialized`)
- Wrong model string (must use exact Deepgram model names)

## What this skill does

1. **Secrets Manager**: create/update the Deepgram credential secret in the **required JSON schema**.
2. **Secret resource policy**: allow `connect.amazonaws.com` to call `secretsmanager:GetSecretValue` scoped to your instance.
3. **KMS key policy**: allow Connect + Secrets Manager to decrypt **only** for that secret using `kms:EncryptionContext:SecretARN`.
4. **Catalog**: list valid Deepgram **STT models** (Nova-3), **TTS models** (Aura-2), and **voice IDs**.

## Safety rules (important)

- Never paste API keys into chat, terminals with history, or code repos.
- Prefer using the script's interactive prompt (`--prompt-for-token`) so the token is not echoed.
- If you accidentally exposed a key, revoke/rotate it immediately in Deepgram Console.

## Prerequisites

- AWS credentials available locally (boto3 can call STS/Secrets Manager/KMS).
- Amazon Connect instance ARN.
- A customer-managed KMS key ARN in the **same region** (Secrets Manager cannot use the AWS-managed `aws/secretsmanager` key for this Connect integration).
- A Deepgram API key from https://console.deepgram.com/

## Deepgram Models Overview

### Speech-to-Text (STT) - Nova-3 Models

| Model ID | Description | Languages |
|----------|-------------|-----------|
| `nova-3-general` | General-purpose, highest accuracy | 10 languages |
| `nova-3-medical` | Medical terminology optimized | English |
| `nova-3-phonecall` | Phone call audio optimized | English |
| `nova-3-meeting` | Meeting/conference audio | English |

**Supported Languages (Nova-3 Multilingual):**
- English, Spanish, French, German, Hindi, Russian, Portuguese, Japanese, Italian, Dutch

### Text-to-Speech (TTS) - Aura-2 Models

Format: `aura-2-<voice>-<language>`

| Voice | Gender | Accent | Model Name Example |
|-------|--------|--------|-------------------|
| thalia | Feminine | American | `aura-2-thalia-en` |
| andromeda | Feminine | American | `aura-2-andromeda-en` |
| helena | Feminine | American | `aura-2-helena-en` |
| apollo | Masculine | American | `aura-2-apollo-en` |
| arcas | Masculine | American | `aura-2-arcas-en` |
| aries | Masculine | American | `aura-2-aries-en` |
| athena | Feminine | American | `aura-2-athena-en` |
| atlas | Masculine | American | `aura-2-atlas-en` |

**TTS Languages:** English (en), Spanish (es), German (de), French (fr), Dutch (nl), Italian (it), Japanese (ja)

## Commands

The skill includes a helper script:

- `~/.copilot/skills/connect-deepgram-setup/scripts/connect_deepgram_setup.py`

### 1) One-time setup (secret + policies)

```bash
python3 ~/.copilot/skills/connect-deepgram-setup/scripts/connect_deepgram_setup.py setup \
  --region us-west-2 \
  --connect-instance-arn arn:aws:connect:us-west-2:ACCOUNT_ID:instance/INSTANCE_ID \
  --secret-name deepgram \
  --kms-key-arn arn:aws:kms:us-west-2:ACCOUNT_ID:key/YOUR_KEY_ID \
  --prompt-for-token \
  --apply --yes
```

### 2) List valid models + voices

```bash
# List all available STT and TTS models
python3 ~/.copilot/skills/connect-deepgram-setup/scripts/connect_deepgram_setup.py catalog \
  --region us-west-2 \
  --secret-name deepgram \
  --language en
```

### 3) Configure STT in Amazon Connect

After running `setup`, configure Deepgram as the Speech-to-Text provider:

1. In the Amazon Connect console, go to your instance settings
2. Navigate to "Third-party speech-to-text" provider settings
3. Set:
   - **Voice Provider**: Deepgram
   - **Model ID**: `nova-3-general` (or another Nova-3 model)
   - **Secrets Manager ARN**: The secret ARN from setup

### 4) Configure TTS in Contact Flow

In your contact flow, use a "Set voice" block:

```
Voice provider: Deepgram
Model: aura-2 (set manually)
Voice: thalia (set manually)
Language: en (set manually)
```

The combination creates the model string `aura-2-thalia-en`.

### 5) Render a contact flow JSON from template

```bash
python3 ~/.copilot/skills/connect-deepgram-setup/scripts/connect_deepgram_setup.py flow \
  --template-path "/path/to/exported-flow.json" \
  --output-path "/path/to/rendered-flow.json" \
  --region us-west-2 \
  --secret-name deepgram \
  --tts-model aura-2 \
  --tts-voice thalia \
  --tts-language en \
  --greeting-text "Hello! This is Deepgram in Amazon Connect. How can I help?"
```

### 6) Deploy the flow via APIs

```bash
python3 ~/.copilot/skills/connect-deepgram-setup/scripts/connect_deepgram_setup.py deploy \
  --region us-west-2 \
  --connect-instance-arn arn:aws:connect:us-west-2:ACCOUNT_ID:instance/INSTANCE_ID \
  --template-path "/path/to/exported-flow.json" \
  --output-path "/path/to/rendered-flow.json" \
  --secret-name deepgram \
  --tts-model aura-2 \
  --tts-voice thalia \
  --tts-language en \
  --phone-number "+18445551212" \
  --prompt-for-greeting
```

## Connect "Set voice" block rules for Deepgram

- **Model**: Use `aura-2` (the TTS model family)
- **Voice**: Use a voice name like `thalia`, `apollo`, `andromeda`
- **Language**: Use language code like `en`, `es`, `de`, `fr`
- **Secrets Manager ARN**: Must point to the secret containing JSON key `apiToken`

## Secret Schema

The secret must contain JSON with these keys:

```json
{
  "apiToken": "your-deepgram-api-key"
}
```

## Instance-Level STT Configuration

For Speech-to-Text, Deepgram is configured at the **instance level** (not per-flow):

1. Go to Amazon Connect Console → Your Instance → Third-party integrations
2. Select Deepgram as the speech provider
3. Enter the Secrets Manager ARN
4. Select the STT model (e.g., `nova-3-general`)

Once configured, all contact flows in the instance will use Deepgram for STT.

## Differences from ElevenLabs

| Feature | ElevenLabs | Deepgram |
|---------|------------|----------|
| TTS | Yes | Yes (Aura-2) |
| STT | No | Yes (Nova-3) |
| Voice ID format | UUID (e.g., `CwhRBWXzGAHq8TQ4Fs17`) | Name-based (e.g., `thalia`) |
| Model format | `eleven_multilingual_v2` | `aura-2-<voice>-<lang>` |
| API endpoint | api.elevenlabs.io | api.deepgram.com |
| Secret schema | `apiToken` + `apiTokenRegion` | `apiToken` only |

## References

- AWS: Configure third-party speech providers
  https://docs.aws.amazon.com/connect/latest/adminguide/configure-third-party-speech-providers.html

- Deepgram + Amazon Connect Integration
  https://developers.deepgram.com/docs/deepgram-with-amazon-connect

- Deepgram TTS Models (Aura-2)
  https://developers.deepgram.com/docs/tts-models

- Deepgram STT Models (Nova-3)
  https://developers.deepgram.com/docs/models

- Amazon Lex: Setting up Deepgram speech model
  https://docs.aws.amazon.com/lexv2/latest/dg/customizing-speech-deepgram-setup.html
