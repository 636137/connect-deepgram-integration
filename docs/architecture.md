# Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Amazon Connect                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Contact Flow                                  │   │
│  │                                                                      │   │
│  │   ┌──────────┐    ┌───────────────┐    ┌──────────────┐            │   │
│  │   │  Entry   │───▶│   Set Voice   │───▶│ Play Prompt  │            │   │
│  │   │  Point   │    │  (Deepgram)   │    │    (TTS)     │            │   │
│  │   └──────────┘    └───────┬───────┘    └──────┬───────┘            │   │
│  │                           │                    │                     │   │
│  │                           │                    ▼                     │   │
│  │                           │            ┌──────────────┐             │   │
│  │                           │            │  Get Input   │             │   │
│  │                           │            │    (STT)     │             │   │
│  │                           │            └──────────────┘             │   │
│  │                           │                                          │   │
│  └───────────────────────────┼──────────────────────────────────────────┘   │
│                              │                                               │
└──────────────────────────────┼───────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        AWS Secrets Manager                                    │
│  ┌────────────────────────────────────────┐                                  │
│  │         Secret: "deepgram"             │                                  │
│  │  ┌────────────────────────────────┐    │         ┌─────────────────────┐ │
│  │  │   apiToken: "dgp_xxx..."       │◀───┼─────────│    AWS KMS Key      │ │
│  │  │                                │    │         │   (Encryption)      │ │
│  │  └────────────────────────────────┘    │         └─────────────────────┘ │
│  └────────────────────────────────────────┘                                  │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │
                               │ HTTPS (encrypted)
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Deepgram Cloud                                      │
│                                                                               │
│   ┌───────────────────────────────┐    ┌───────────────────────────────┐    │
│   │         Nova-3 STT            │    │         Aura-2 TTS            │    │
│   │  ┌─────────────────────────┐  │    │  ┌─────────────────────────┐  │    │
│   │  │  • nova-3-general       │  │    │  │  • thalia (Female, US)  │  │    │
│   │  │  • nova-3-phonecall     │  │    │  │  • apollo (Male, US)    │  │    │
│   │  │  • nova-3-medical       │  │    │  │  • athena (Female, US)  │  │    │
│   │  │  • nova-3-meeting       │  │    │  │  • luna (Female, UK)    │  │    │
│   │  │                         │  │    │  │  • + 10 more voices     │  │    │
│   │  └─────────────────────────┘  │    │  └─────────────────────────┘  │    │
│   │       36+ Languages           │    │        7 Languages            │    │
│   └───────────────────────────────┘    └───────────────────────────────┘    │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### TTS (Text-to-Speech) Flow

```
1. Caller calls Connect phone number
2. Contact flow reaches "Play Prompt" block with Deepgram voice
3. Connect reads apiToken from Secrets Manager (using KMS to decrypt)
4. Connect calls Deepgram Aura-2 TTS API with text
5. Deepgram returns audio stream
6. Connect plays audio to caller
```

### STT (Speech-to-Text) Flow

```
1. Contact flow reaches "Get customer input" block
2. Caller speaks
3. Connect streams audio to Deepgram Nova-3 STT
4. Deepgram returns transcript
5. Connect uses transcript for routing/intent detection
```

## Security Model

```
┌─────────────────────────────────────────────────────────────────┐
│                     Security Boundaries                          │
│                                                                  │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │   Connect    │         │   Secrets    │                      │
│  │   Instance   │────────▶│   Manager    │                      │
│  │              │  IAM +   │    Secret    │                      │
│  │              │ Resource │              │                      │
│  └──────────────┘  Policy  └──────┬───────┘                      │
│                                   │                              │
│                            KMS Decrypt                           │
│                                   │                              │
│                            ┌──────▼───────┐                      │
│                            │   KMS Key    │                      │
│                            │  (CMK)       │                      │
│                            └──────────────┘                      │
│                                                                  │
│  Access Control:                                                 │
│  • Secret Resource Policy → only YOUR Connect instance           │
│  • KMS Key Policy → only YOUR Connect instance                   │
│  • No cross-account access                                       │
│  • No cross-instance access                                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Components

| Component | Purpose | AWS Service |
|-----------|---------|-------------|
| Secret | Stores Deepgram API key | Secrets Manager |
| KMS Key | Encrypts secret at rest | KMS |
| Resource Policy | Controls secret access | IAM |
| Contact Flow | Defines call routing and TTS/STT usage | Connect |
| Phone Number | Entry point for callers | Connect |
