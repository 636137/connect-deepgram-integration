---
name: connect-deepgram-setup
description: "Bootstrap Amazon Connect + Deepgram TTS/STT: create/update Secrets Manager secret, apply secret+KMS policies safely, configure Lex bots for Deepgram STT, and deploy contact flows with Deepgram TTS."
user-invocable: true
disable-model-invocation: false
---

# Amazon Connect + Deepgram Setup Skill

Use this skill to reliably configure Deepgram as a third-party TTS and STT provider in Amazon Connect **without** re-hitting the common failure modes:

- KMS decrypt denied (`Access to KMS is not allowed`)
- Secret schema mismatch (`secret could not be deserialized`)
- Wrong model string (must use exact Deepgram model names)
- Contact flow creation errors (wrong action types)

## What this skill does

1. **Secrets Manager**: create/update the Deepgram credential secret in the **required JSON schema**.
2. **Secret resource policy**: allow **both** `connect.amazonaws.com` AND `lex.amazonaws.com` to call `secretsmanager:GetSecretValue` (required for TTS+STT).
3. **KMS key policy**: allow Connect + Lex + Secrets Manager to decrypt **only** for that secret using `kms:EncryptionContext:SecretARN`.
4. **Catalog**: list valid Deepgram **STT models** (Nova-3), **TTS models** (Aura-2), and **voice IDs**.
5. **Contact Flows**: create flows with proper action types for Lex bot integration (`ConnectParticipantWithLexBot`).

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

**Via API (Contact Flow JSON):**
```json
{
  "Type": "UpdateContactTextToSpeechVoice",
  "Parameters": {
    "TextToSpeechEngine": "deepgram:aura-2",
    "TextToSpeechVoice": "thalia",
    "ExternalCredentialSecretARN": "arn:aws:secretsmanager:us-west-2:ACCOUNT:secret:deepgram-XXXXX"
  }
}
```

### 5) List Lex V2 bots and STT configuration

```bash
python3 ~/.copilot/skills/connect-deepgram-setup/scripts/connect_deepgram_setup.py list-bots \
  --region us-west-2
```

This shows all Lex V2 bots and their current STT provider configuration.

### 6) Configure Deepgram STT for a Lex V2 bot

```bash
python3 ~/.copilot/skills/connect-deepgram-setup/scripts/connect_deepgram_setup.py configure-stt \
  --region us-west-2 \
  --bot-id YOUR_BOT_ID \
  --locale-id en_US \
  --stt-model nova-3-general \
  --secret-name deepgram \
  --apply --yes
```

This command:
- Updates the bot locale to use Deepgram STT
- Sets the Nova-3 model for speech recognition
- Automatically builds the bot locale
- Shows cost estimates

### 7) Render a contact flow JSON from template

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

### 8) Deploy the flow via APIs

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

## Secret Resource Policy (Critical!)

The secret resource policy must allow **BOTH** services:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowAmazonConnectGetSecretValue",
      "Effect": "Allow",
      "Principal": {"Service": "connect.amazonaws.com"},
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "*",
      "Condition": {
        "StringEquals": {"aws:sourceAccount": "YOUR_ACCOUNT_ID"},
        "ArnLike": {"aws:sourceArn": "arn:aws:connect:REGION:ACCOUNT:instance/INSTANCE_ID"}
      }
    },
    {
      "Sid": "AllowLexGetSecretValue",
      "Effect": "Allow",
      "Principal": {"Service": "lex.amazonaws.com"},
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "*",
      "Condition": {
        "StringEquals": {"aws:SourceAccount": "YOUR_ACCOUNT_ID"},
        "ArnLike": {"aws:SourceArn": "arn:aws:lex:REGION:ACCOUNT:bot-alias/*/*"}
      }
    }
  ]
}
```

**Why both?**
- `connect.amazonaws.com` - Required for TTS in contact flows
- `lex.amazonaws.com` - Required for STT via Lex bots

## Contact Flow Action Types (Important!)

When creating contact flows via API, use the correct action types:

| Use Case | Action Type | Notes |
|----------|-------------|-------|
| Set TTS voice | `UpdateContactTextToSpeechVoice` | Sets Deepgram TTS |
| Play prompt | `MessageParticipant` | Uses current TTS voice |
| DTMF input | `GetParticipantInput` | For keypress only |
| **Lex bot input** | `ConnectParticipantWithLexBot` | **For speech/STT** |

**Common mistake:** Using `GetParticipantInput` with `LexV2Bot` will fail. Use `ConnectParticipantWithLexBot` instead.

**Example flow action for Lex STT:**
```json
{
  "Identifier": "get-speech",
  "Type": "ConnectParticipantWithLexBot",
  "Parameters": {
    "Text": "How can I help you today?",
    "LexV2Bot": {
      "AliasArn": "arn:aws:lex:us-west-2:ACCOUNT:bot-alias/BOT_ID/ALIAS_ID"
    }
  },
  "Transitions": {
    "NextAction": "success",
    "Errors": [
      {"NextAction": "no-input", "ErrorType": "NoMatchingCondition"},
      {"NextAction": "no-input", "ErrorType": "InputTimeLimitExceeded"},
      {"NextAction": "error", "ErrorType": "NoMatchingError"}
    ]
  }
}
```

## Lex Bot STT Configuration

For Speech-to-Text, Deepgram is configured at the **Lex bot locale level**:

1. Go to Amazon Lex Console → Your Bot → Languages → en_US
2. Under "Advanced configuration", find "Speech model preference"
3. Select **Deepgram** and choose model (e.g., `nova-3-general`)
4. Build the bot locale

**Via CLI:**
```bash
python3 ~/.copilot/skills/connect-deepgram-setup/scripts/connect_deepgram_setup.py configure-stt \
  --region us-west-2 \
  --bot-id YOUR_BOT_ID \
  --locale-id en_US \
  --stt-model nova-3-general \
  --secret-name deepgram \
  --apply --yes
```

**Note:** The Lex test console may show "Connect Unlimited AI not onboarded" error, but **runtime calls work correctly**. Test via actual phone calls.

## CloudWatch Log Evidence

When Deepgram is working, CloudWatch logs (`/aws/connect/<instance>`) show:

```json
{
  "ContactFlowModuleType": "GetUserInput",
  "Parameters": {
    "Engine": "deepgram:aura-2",
    "Voice": "thalia",
    "BotAliasArn": "arn:aws:lex:..."
  },
  "Results": "Fallbackintent"
}
```

Key evidence:
- `Engine: deepgram:aura-2` - Proves Deepgram TTS
- `Results: <intent>` - Proves STT transcription worked

## Differences from ElevenLabs

| Feature | ElevenLabs | Deepgram |
|---------|------------|----------|
| TTS | Yes | Yes (Aura-2) |
| STT | No | Yes (Nova-3) |
| Voice ID format | UUID (e.g., `CwhRBWXzGAHq8TQ4Fs17`) | Name-based (e.g., `thalia`) |
| Model format | `eleven_multilingual_v2` | `aura-2-<voice>-<lang>` |
| API endpoint | api.elevenlabs.io | api.deepgram.com |
| Secret schema | `apiToken` + `apiTokenRegion` | `apiToken` only |

## Pricing & Cost Estimates

### Deepgram Nova-3 STT (Speech-to-Text)

| Plan | Price per Minute | Price per Hour | Annual Commitment |
|------|------------------|----------------|-------------------|
| Pay-As-You-Go | $0.0077 | $0.46 | None |
| Growth Plan | $0.0065 | $0.39 | $4,000/year |

**Example costs (Pay-As-You-Go):**
- 1,000 minutes/month: $7.70/month
- 10,000 minutes/month: $77/month
- 100,000 minutes/month: $770/month

### Deepgram Aura-2 TTS (Text-to-Speech)

| Plan | Price per 1K Characters |
|------|------------------------|
| Pay-As-You-Go | $0.015 |
| Growth Plan | Contact Deepgram |

### Comparison with AWS Native Services

| Service | Deepgram | AWS Native |
|---------|----------|------------|
| STT | $0.0077/min | $0.024/min (Transcribe) |
| TTS | $0.015/1K chars | $0.016/1K chars (Polly Neural) |

Deepgram Nova-3 STT is ~68% cheaper than Amazon Transcribe with reportedly higher accuracy.

## Troubleshooting

### "Connect Unlimited AI not onboarded" Error

**Symptom:** Lex test console shows this error when testing STT.

**Solution:** This is a console-specific issue. The runtime works correctly. Test by:
1. Creating a contact flow with `ConnectParticipantWithLexBot` action
2. Associating a phone number
3. Calling the phone number and speaking

### Contact Flow Creation Fails with InvalidContactFlowException

**Symptom:** API returns `InvalidContactFlowException` with no details.

**Common causes:**
1. Using `GetParticipantInput` with `LexV2Bot` - Use `ConnectParticipantWithLexBot` instead
2. Missing `ExternalCredentialSecretARN` in TTS voice action
3. Wrong `TextToSpeechEngine` format - must be `deepgram:aura-2`

### TTS Works but STT Doesn't

**Check:**
1. Secret policy includes `lex.amazonaws.com` principal
2. Lex bot locale has Deepgram speech model configured
3. Lex bot is associated with Connect instance
4. Bot alias is built (not just draft)

### CloudWatch Shows No Deepgram Evidence

**Check:**
1. Flow logging is enabled (`UpdateFlowLoggingBehavior` action)
2. Look in `/aws/connect/<instance-name>` log group
3. Filter for `deepgram` or `Engine`

## Proven Working Configuration

Tested and verified on 2026-03-12:

- **Instance:** maximus-gov-ccaas-in-a-box-1
- **Region:** us-west-2
- **TTS Engine:** `deepgram:aura-2`
- **TTS Voice:** `thalia`
- **STT Model:** `nova-3-general`
- **Lex Bot:** QnaBot with Deepgram speech model
- **Phone:** +1-844-593-5770

## References

- AWS: Configure third-party speech providers
  https://docs.aws.amazon.com/connect/latest/adminguide/configure-third-party-speech-providers.html

- AWS: Third-party STT in Amazon Connect
  https://docs.aws.amazon.com/connect/latest/adminguide/configure-third-party-stt.html

- Deepgram + Amazon Connect Integration
  https://developers.deepgram.com/docs/deepgram-with-amazon-connect

- Deepgram TTS Models (Aura-2)
  https://developers.deepgram.com/docs/tts-models

- Deepgram STT Models (Nova-3)
  https://developers.deepgram.com/docs/models

- Amazon Lex: Setting up Deepgram speech model
  https://docs.aws.amazon.com/lexv2/latest/dg/customizing-speech-deepgram-setup.html

- Connect Flow Language: ConnectParticipantWithLexBot
  https://docs.aws.amazon.com/connect/latest/APIReference/participant-actions-connectparticipantwithlexbot.html
