## Proprietary Notice

This code is proprietary to **Maximus**. **No public license is granted**. See [`NOTICE`](./NOTICE).

---

# Amazon Connect + Deepgram Integration

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![AWS](https://img.shields.io/badge/AWS-Amazon%20Connect-orange)](https://aws.amazon.com/connect/)
[![Deepgram](https://img.shields.io/badge/Deepgram-Nova--3%20%7C%20Aura--2-blue)](https://deepgram.com/)

> **Enterprise-grade Speech-to-Text (STT) and Text-to-Speech (TTS) integration for Amazon Connect contact centers using Deepgram's Nova-3 and Aura-2 AI models.**

<p align="center">
  <img src="docs/architecture.png" alt="Architecture Diagram" width="800">
</p>

## 🎯 What This Does

This integration enables Amazon Connect contact centers to use **Deepgram's industry-leading speech AI** instead of Amazon's native Polly/Transcribe services:

| Feature | Technology | Benefit |
|---------|------------|---------|
| **Speech-to-Text** | Deepgram Nova-3 | 30% lower word error rate than alternatives |
| **Text-to-Speech** | Deepgram Aura-2 | Natural, expressive neural voices |
| **Real-time** | WebSocket streaming | Sub-300ms latency |
| **Multi-language** | 36+ languages | Global contact center support |

### Key Benefits

- 🎙️ **Superior Accuracy** - Nova-3 delivers state-of-the-art transcription accuracy
- 🗣️ **Natural Voices** - Aura-2 voices sound human, not robotic
- ⚡ **Low Latency** - Real-time streaming for IVR and agent assist
- 🌍 **Global Coverage** - Support for 36+ languages and regional accents
- 🔐 **Enterprise Security** - AWS Secrets Manager + KMS encryption
- 💰 **Cost Effective** - Competitive pricing vs. native AWS services

---

## 📋 Prerequisites

Before you begin, ensure you have:

| Requirement | Details |
|-------------|---------|
| **AWS Account** | With permissions to create/manage Connect, Secrets Manager, KMS, IAM |
| **Amazon Connect Instance** | Active instance in a [supported region](#supported-regions) |
| **Deepgram Account** | Sign up at [console.deepgram.com](https://console.deepgram.com) |
| **Deepgram API Key** | Create in Deepgram Console → Settings → API Keys |
| **AWS CLI v2** | [Install guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |
| **Python 3.9+** | With `boto3` installed (`pip install boto3`) |
| **Customer-Managed KMS Key** | In your target AWS region |

### Supported Regions

Amazon Connect + Deepgram integration is available in:

| Region | Code | Connect Endpoint |
|--------|------|------------------|
| US East (N. Virginia) | `us-east-1` | ✅ |
| US West (Oregon) | `us-west-2` | ✅ |
| EU (Frankfurt) | `eu-central-1` | ✅ |
| EU (London) | `eu-west-2` | ✅ |
| Asia Pacific (Sydney) | `ap-southeast-2` | ✅ |
| Asia Pacific (Tokyo) | `ap-northeast-1` | ✅ |
| Asia Pacific (Singapore) | `ap-southeast-1` | ✅ |
| Canada (Central) | `ca-central-1` | ✅ |

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/connect-deepgram-integration.git
cd connect-deepgram-integration
```

### Step 2: Get Your Deepgram API Key

1. Go to [console.deepgram.com](https://console.deepgram.com)
2. Navigate to **Settings → API Keys**
3. Click **Create a New API Key**
4. Give it a name (e.g., "Amazon Connect Integration")
5. Copy the key (you won't see it again!)

### Step 3: Get Your AWS Resource ARNs

```bash
# Find your Connect instance ARN
aws connect list-instances --region us-west-2

# Find or create a KMS key ARN
aws kms list-keys --region us-west-2
```

### Step 4: Run the Setup Script

```bash
python3 scripts/connect_deepgram_setup.py setup \
  --region us-west-2 \
  --connect-instance-arn "arn:aws:connect:us-west-2:123456789012:instance/abc-123-def" \
  --kms-key-arn "arn:aws:kms:us-west-2:123456789012:key/xyz-789" \
  --api-token "YOUR_DEEPGRAM_API_KEY" \
  --apply --yes
```

**What this does:**
- ✅ Creates a Secrets Manager secret with your Deepgram API key
- ✅ Encrypts the secret with your KMS key
- ✅ Applies resource policy allowing Connect to read the secret
- ✅ Updates KMS key policy for Connect access

### Step 5: Create a Test Contact Flow

```bash
python3 scripts/connect_deepgram_setup.py deploy \
  --region us-west-2 \
  --connect-instance-arn "arn:aws:connect:us-west-2:123456789012:instance/abc-123-def" \
  --secret-name deepgram \
  --flow-name "Deepgram TTS Demo" \
  --tts-voice thalia \
  --tts-model aura-2 \
  --prompt-text "Hello! This is Deepgram text to speech. How can I help you today?" \
  --apply --yes
```

### Step 6: Test It!

Call your Connect phone number and hear Deepgram's Thalia voice!

---

## 🎤 Deepgram Models & Voices

### Speech-to-Text (STT) - Nova-3 Models

| Model ID | Use Case | Languages | Description |
|----------|----------|-----------|-------------|
| `nova-3-general` | **Recommended** | 36+ | Highest accuracy, general purpose |
| `nova-3-phonecall` | Phone calls | English | Optimized for telephony audio |
| `nova-3-medical` | Healthcare | English | Medical terminology |
| `nova-3-meeting` | Meetings | English | Multi-speaker, conference audio |
| `nova-2-general` | Legacy | 30+ | Previous generation |

### Text-to-Speech (TTS) - Aura-2 Voices

#### English Voices

| Voice | Gender | Accent | Personality |
|-------|--------|--------|-------------|
| `thalia` | Female | American | Clear, confident, energetic |
| `andromeda` | Female | American | Casual, expressive |
| `helena` | Female | American | Caring, friendly, raspy |
| `athena` | Female | American | Calm, smooth, professional |
| `asteria` | Female | American | Default voice |
| `luna` | Female | British | British accent |
| `apollo` | Male | American | Confident, comfortable |
| `arcas` | Male | American | Natural, smooth, clear |
| `aries` | Male | American | Warm, energetic, caring |
| `atlas` | Male | American | Confident, approachable |
| `amalthea` | Female | Filipino | Engaging, cheerful |

#### Multi-Language Voices

| Voice | Languages | Notes |
|-------|-----------|-------|
| `thalia` | en, es, de, fr | Multi-lingual capable |
| `asteria` | en, es | Spanish variant available |
| `apollo` | en, es, de | German variant available |
| `orpheus` | en | Storytelling optimized |
| `angus` | en | Irish accent |
| `perseus` | en | Deep, authoritative |

### Supported Languages (STT)

<details>
<summary>Click to expand full language list (36+ languages)</summary>

| Language | Code | Nova-3 Support |
|----------|------|----------------|
| English (US) | `en-US` | ✅ |
| English (UK) | `en-GB` | ✅ |
| English (AU) | `en-AU` | ✅ |
| Spanish | `es` | ✅ |
| Spanish (Latin America) | `es-419` | ✅ |
| French | `fr` | ✅ |
| French (Canada) | `fr-CA` | ✅ |
| German | `de` | ✅ |
| Italian | `it` | ✅ |
| Portuguese | `pt` | ✅ |
| Portuguese (Brazil) | `pt-BR` | ✅ |
| Dutch | `nl` | ✅ |
| Japanese | `ja` | ✅ |
| Korean | `ko` | ✅ |
| Chinese (Mandarin) | `zh` | ✅ |
| Chinese (Cantonese) | `zh-HK` | ✅ |
| Hindi | `hi` | ✅ |
| Russian | `ru` | ✅ |
| Turkish | `tr` | ✅ |
| Polish | `pl` | ✅ |
| Ukrainian | `uk` | ✅ |
| Vietnamese | `vi` | ✅ |
| Indonesian | `id` | ✅ |
| Malay | `ms` | ✅ |
| Thai | `th` | ✅ |
| Swedish | `sv` | ✅ |
| Norwegian | `no` | ✅ |
| Danish | `da` | ✅ |
| Finnish | `fi` | ✅ |
| Greek | `el` | ✅ |
| Czech | `cs` | ✅ |
| Romanian | `ro` | ✅ |
| Hungarian | `hu` | ✅ |
| Bulgarian | `bg` | ✅ |
| Tamil | `ta` | ✅ |
| Telugu | `te` | ✅ |

</details>

### TTS Language Codes

| Language | Code | Available Voices |
|----------|------|------------------|
| English | `en` | All voices |
| Spanish | `es` | thalia, asteria, apollo |
| German | `de` | thalia, apollo |
| French | `fr` | thalia |
| Dutch | `nl` | thalia |
| Italian | `it` | thalia |
| Japanese | `ja` | Limited |

---

## 📁 Repository Structure

```
connect-deepgram-integration/
├── README.md                    # This file
├── SKILL.md                     # GitHub Copilot CLI skill definition
├── LICENSE                      # MIT License
├── scripts/
│   └── connect_deepgram_setup.py   # Main setup/deployment script
├── templates/
│   ├── basic-tts-flow.json      # Simple TTS demo flow
│   ├── ivr-with-stt.json        # IVR with speech recognition
│   └── agent-assist-flow.json   # Real-time agent assistance
├── docs/
│   ├── architecture.png         # Architecture diagram
│   ├── console-setup.md         # Manual console setup guide
│   └── troubleshooting.md       # Common issues and solutions
└── examples/
    ├── lambda/                  # Lambda function examples
    └── cloudformation/          # IaC templates
```

---

## 🔧 CLI Commands Reference

### `setup` - Create Secret and Configure Policies

```bash
python3 scripts/connect_deepgram_setup.py setup \
  --region <aws-region> \
  --connect-instance-arn <instance-arn> \
  --kms-key-arn <kms-key-arn> \
  --secret-name deepgram \
  --api-token <your-deepgram-api-key> \
  --apply --yes
```

| Flag | Required | Description |
|------|----------|-------------|
| `--region` | ✅ | AWS region (e.g., `us-west-2`) |
| `--connect-instance-arn` | ✅ | Full ARN of your Connect instance |
| `--kms-key-arn` | ✅ | ARN of customer-managed KMS key |
| `--secret-name` | ❌ | Secret name (default: `deepgram`) |
| `--api-token` | ✅* | Deepgram API key |
| `--prompt-for-token` | ✅* | Interactive token entry (alternative) |
| `--apply` | ❌ | Actually make changes (vs dry-run) |
| `--yes` | ❌ | Skip confirmation prompts |

*Either `--api-token` or `--prompt-for-token` required for new secrets

### `catalog` - List Available Models and Voices

```bash
python3 scripts/connect_deepgram_setup.py catalog \
  --region us-west-2 \
  --secret-name deepgram \
  --language en
```

### `flow` - Render a Contact Flow Template

```bash
python3 scripts/connect_deepgram_setup.py flow \
  --region us-west-2 \
  --connect-instance-arn <instance-arn> \
  --secret-name deepgram \
  --template templates/basic-tts-flow.json \
  --tts-voice thalia \
  --tts-model aura-2 \
  --output rendered-flow.json
```

### `deploy` - Create Flow and Associate Phone Number

```bash
python3 scripts/connect_deepgram_setup.py deploy \
  --region us-west-2 \
  --connect-instance-arn <instance-arn> \
  --secret-name deepgram \
  --flow-name "My Deepgram Flow" \
  --tts-voice thalia \
  --tts-model aura-2 \
  --prompt-text "Welcome to our contact center." \
  --phone-number "+18001234567" \
  --apply --yes
```

---

## 🤖 GitHub Copilot CLI Integration

This repository includes a **GitHub Copilot CLI skill** for seamless integration with the Copilot CLI agent.

### Installing the Skill

```bash
# Copy skill to your Copilot skills directory
mkdir -p ~/.copilot/skills/connect-deepgram-setup
cp SKILL.md ~/.copilot/skills/connect-deepgram-setup/
cp -r scripts ~/.copilot/skills/connect-deepgram-setup/
```

### Using the Skill

Once installed, you can invoke the skill naturally in Copilot CLI:

```
> Use the connect-deepgram-setup skill to configure Deepgram TTS for my Connect instance
```

Or be more specific:

```
> Set up Deepgram integration for my Connect instance in us-west-2 using the Thalia voice
```

The skill will:
1. Guide you through required parameters
2. Create/update the Secrets Manager secret
3. Configure KMS and IAM policies
4. Optionally deploy a test contact flow

See [SKILL.md](SKILL.md) for complete skill documentation.

---

## 🔐 Security Best Practices

### API Key Security

- ✅ **Always** use Secrets Manager - never hardcode API keys
- ✅ **Always** use customer-managed KMS keys for encryption
- ✅ Rotate API keys periodically via Deepgram Console
- ✅ Use least-privilege IAM policies

### Secret Resource Policy

The setup script applies this resource policy to your secret. **Both services are required:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowConnectGetSecretValue",
      "Effect": "Allow",
      "Principal": {
        "Service": "connect.amazonaws.com"
      },
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "*",
      "Condition": {
        "StringEquals": {"aws:sourceAccount": "<account-id>"},
        "ArnLike": {
          "aws:SourceArn": "arn:aws:connect:<region>:<account>:instance/<instance-id>"
        }
      }
    },
    {
      "Sid": "AllowLexGetSecretValue",
      "Effect": "Allow",
      "Principal": {
        "Service": "lex.amazonaws.com"
      },
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "*",
      "Condition": {
        "StringEquals": {"aws:SourceAccount": "<account-id>"},
        "ArnLike": {
          "aws:SourceArn": "arn:aws:lex:<region>:<account>:bot-alias/*/*"
        }
      }
    }
  ]
}
```

> **⚠️ Important:** The `lex.amazonaws.com` principal is required for STT to work via Lex bots. Without it, TTS will work but STT will fail.

### KMS Key Policy

The setup script adds these statements to your KMS key policy:

```json
{
  "Sid": "AllowConnectDecrypt",
  "Effect": "Allow",
  "Principal": {
    "Service": "connect.amazonaws.com"
  },
  "Action": ["kms:Decrypt", "kms:GenerateDataKey*"],
  "Resource": "*",
  "Condition": {
    "ArnLike": {
      "aws:SourceArn": "arn:aws:connect:<region>:<account>:instance/<instance-id>"
    }
  }
}
```

---

## 🔄 Manual Console Setup (Alternative)

If you prefer manual setup via the AWS Console:

### 1. Create Secret in Secrets Manager

1. Go to **AWS Secrets Manager** → **Store a new secret**
2. Select **Other type of secret**
3. Add key/value: `apiToken` = `your-deepgram-api-key`
4. Select your **KMS key** for encryption
5. Name it `deepgram`
6. Add resource policy (see Security section above)

### 2. Configure Connect Instance

1. Go to **Amazon Connect** → Your instance → **Third-party integrations**
2. Under **Speech services**, click **Add integration**
3. Select **Deepgram** as the provider
4. Enter your **Secrets Manager ARN**
5. Select STT model: **nova-3-general**
6. Save

### 3. Create Contact Flow

1. Go to **Contact flows** → **Create contact flow**
2. Add **Set voice** block:
   - Voice provider: **Deepgram**
   - Model: **aura-2**
   - Voice: **thalia**
   - Language: **en**
   - Secrets Manager ARN: (paste your secret ARN)
3. Add **Play prompt** block with your message
4. Save and publish

---

## 🐛 Troubleshooting

### Common Issues

<details>
<summary><b>Error: "Failed to retrieve credentials from Secrets Manager"</b></summary>

**Cause:** Secret resource policy doesn't allow Connect access.

**Fix:**
```bash
python3 scripts/connect_deepgram_setup.py setup \
  --region us-west-2 \
  --connect-instance-arn <your-arn> \
  --kms-key-arn <your-key-arn> \
  --secret-name deepgram \
  --apply --yes
```
</details>

<details>
<summary><b>Error: "KMS key access denied"</b></summary>

**Cause:** KMS key policy doesn't include Connect service.

**Fix:** Ensure your KMS key policy includes the `connect.amazonaws.com` service principal with `kms:Decrypt` permission.
</details>

<details>
<summary><b>Error: "Invalid API key"</b></summary>

**Cause:** Deepgram API key is incorrect or expired.

**Fix:**
1. Verify key in Deepgram Console
2. Update secret value:
```bash
aws secretsmanager put-secret-value \
  --secret-id deepgram \
  --secret-string '{"apiToken":"NEW_KEY_HERE"}' \
  --region us-west-2
```
</details>

<details>
<summary><b>No audio playback / silence</b></summary>

**Cause:** TTS model/voice string format incorrect.

**Fix:** Ensure flow uses exact format:
- Engine: `deepgram:aura-2`
- Voice: `thalia` (just the name, no prefix)
</details>

<details>
<summary><b>Error: "Connect Unlimited AI not onboarded" in Lex Console</b></summary>

**Cause:** This is a Lex test console-specific error. **Runtime calls work correctly.**

**Fix:** Don't test via Lex console. Instead:
1. Create a contact flow with `ConnectParticipantWithLexBot` action
2. Associate a phone number
3. Call the number to test STT in production

This error does NOT affect real calls through Connect.
</details>

<details>
<summary><b>Error: "InvalidContactFlowException" when creating flow via API</b></summary>

**Cause:** Using wrong action type for Lex bot integration.

**Fix:** Use `ConnectParticipantWithLexBot` instead of `GetParticipantInput` for speech/STT:

```json
{
  "Type": "ConnectParticipantWithLexBot",
  "Parameters": {
    "Text": "How can I help you?",
    "LexV2Bot": {
      "AliasArn": "arn:aws:lex:us-west-2:ACCOUNT:bot-alias/BOT_ID/ALIAS_ID"
    }
  }
}
```

**Note:** `GetParticipantInput` is for DTMF (keypress) only. For speech recognition with Lex bots, always use `ConnectParticipantWithLexBot`.
</details>

<details>
<summary><b>TTS works but STT doesn't</b></summary>

**Cause:** Secret policy missing `lex.amazonaws.com` principal.

**Fix:** Update secret resource policy to include both services:
- `connect.amazonaws.com` - for TTS
- `lex.amazonaws.com` - for STT via Lex

Run the setup command again to fix the policy.
</details>

### Debug Logging

Enable CloudWatch logging in your contact flow:

```json
{
  "Parameters": {"FlowLoggingBehavior": "Enabled"},
  "Type": "UpdateFlowLoggingBehavior"
}
```

View logs: **CloudWatch → Log groups → /aws/connect/<instance-name>**

When Deepgram is working correctly, you'll see log entries like:

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

**Key evidence:**
- `Engine: deepgram:aura-2` - Confirms Deepgram TTS is active
- `Results: <intent>` - Confirms STT transcribed speech and Lex matched an intent

---

## ✅ Verified Working Configuration

This integration was tested and verified on **2026-03-12**:

| Component | Value |
|-----------|-------|
| Region | us-west-2 |
| TTS Engine | `deepgram:aura-2` |
| TTS Voice | `thalia` |
| STT Model | `nova-3-general` |
| Lex Bot | QnaBot with Deepgram speech model |
| Test Phone | +1-844-593-5770 |

CloudWatch logs confirmed `Engine: deepgram:aura-2` and successful intent recognition.

---

## 📊 Cost Comparison

| Service | Pricing Model | Approximate Cost |
|---------|---------------|------------------|
| **Deepgram Nova-3 STT** | Per audio minute | $0.0043/min (Pay-as-you-go) |
| **Deepgram Aura-2 TTS** | Per character | $0.015/1K chars |
| **Amazon Transcribe** | Per audio second | $0.024/min (standard) |
| **Amazon Polly** | Per character | $0.016/1K chars (neural) |

*Pricing as of March 2026. Check [deepgram.com/pricing](https://deepgram.com/pricing) for current rates.*

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🔗 Resources

- [Deepgram Documentation](https://developers.deepgram.com/)
- [Deepgram Console](https://console.deepgram.com)
- [Amazon Connect Documentation](https://docs.aws.amazon.com/connect/)
- [Amazon Connect Third-Party Integration Guide](https://docs.aws.amazon.com/connect/latest/adminguide/third-party-integration.html)
- [GitHub Copilot CLI Documentation](https://docs.github.com/en/copilot/using-github-copilot/using-github-copilot-in-the-command-line)

---

<p align="center">
  <b>Built with ❤️ for the contact center community</b><br>
  <sub>Questions? Open an issue or reach out!</sub>
</p>

<!-- BEGIN COPILOT CUSTOM AGENTS -->
## GitHub Copilot Custom Agents (Maximus Internal)

This repository includes **GitHub Copilot custom agent profiles** under `.github/agents/` to speed up planning, documentation, and safe reviews.

### Included agents
- `implementation-planner` — Creates detailed implementation plans and technical specifications for this repository.
- `readme-creator` — Improves README and adjacent documentation without modifying production code.
- `security-auditor` — Performs a read-only security review (secrets risk, risky patterns) and recommends fixes.
- `amazon-connect-solution-engineer` — Designs and integrates Amazon Connect solutions for this repository (IAM-safe, CX/ops focused).

### How to invoke

- **GitHub.com (Copilot coding agent):** select the agent from the agent dropdown (or assign it to an issue) after the `.agent.md` files are on the default branch.
- **GitHub Copilot CLI:** from the repo folder, run `/agent` and select one of the agents, or run:
  - `copilot --agent <agent-file-base-name> --prompt "<your prompt>"`
- **IDEs:** open Copilot Chat and choose the agent from the agents dropdown (supported IDEs), backed by the `.github/agents/*.agent.md` files.

References:
- Custom agents configuration: https://docs.github.com/en/copilot/reference/custom-agents-configuration
- Creating custom agents: https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/create-custom-agents
<!-- END COPILOT CUSTOM AGENTS -->
