# Manual Console Setup Guide

This guide walks through setting up the Deepgram integration manually via the AWS Console.

## Step 1: Create the Secrets Manager Secret

1. Navigate to **AWS Secrets Manager** in your AWS Console
2. Click **Store a new secret**
3. Choose **Other type of secret**
4. Add the following key/value pair:
   - Key: `apiToken`
   - Value: `your-deepgram-api-key-here`
5. Under **Encryption key**, select your customer-managed KMS key
6. Click **Next**
7. Name the secret: `deepgram` (or your preferred name)
8. Add tags if desired
9. Click **Next** → **Next** → **Store**
10. Copy the **Secret ARN** for later use

## Step 2: Add Secret Resource Policy

1. In Secrets Manager, click on your `deepgram` secret
2. Scroll down to **Resource permissions**
3. Click **Edit permissions**
4. Paste the following policy (replace `<REGION>`, `<ACCOUNT_ID>`, `<INSTANCE_ID>`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "connect.amazonaws.com"
      },
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "*",
      "Condition": {
        "ArnLike": {
          "aws:SourceArn": "arn:aws:connect:<REGION>:<ACCOUNT_ID>:instance/<INSTANCE_ID>"
        }
      }
    }
  ]
}
```

5. Click **Save**

## Step 3: Update KMS Key Policy

1. Navigate to **AWS KMS** → **Customer managed keys**
2. Click on your encryption key
3. Click **Key policy** → **Edit**
4. Add this statement to the `Statement` array:

```json
{
  "Sid": "AllowConnectDecrypt",
  "Effect": "Allow",
  "Principal": {
    "Service": "connect.amazonaws.com"
  },
  "Action": [
    "kms:Decrypt",
    "kms:GenerateDataKey*"
  ],
  "Resource": "*",
  "Condition": {
    "ArnLike": {
      "aws:SourceArn": "arn:aws:connect:<REGION>:<ACCOUNT_ID>:instance/<INSTANCE_ID>"
    }
  }
}
```

5. Click **Save changes**

## Step 4: Configure Connect Instance (for STT)

1. Go to **Amazon Connect Console**
2. Click on your instance alias
3. Navigate to **Third-party integrations** (left sidebar)
4. Under **Speech services**, click **Add integration**
5. Configure:
   - Provider: **Deepgram**
   - Secrets Manager ARN: (paste your secret ARN)
   - Model: **nova-3-general**
6. Click **Save**

## Step 5: Create Contact Flow with Deepgram TTS

1. In Amazon Connect, go to **Routing** → **Contact flows**
2. Click **Create contact flow**
3. Add a **Set voice** block:
   - Click the block to configure
   - Select **Use text-to-speech**
   - Voice provider: **Deepgram**
   - Model: **aura-2**
   - Voice: **thalia**
   - Language: **en**
   - Secrets Manager ARN: (paste your secret ARN)
4. Add a **Play prompt** block:
   - Enter your text to speak
5. Add **Disconnect** block
6. Connect the blocks: Entry → Set voice → Play prompt → Disconnect
7. Click **Publish**

## Step 6: Associate Phone Number

1. Go to **Channels** → **Phone numbers**
2. Click on a phone number
3. Under **Contact flow / IVR**, select your new flow
4. Click **Save**

## Testing

Call your phone number and you should hear the Deepgram Thalia voice reading your message!

## Troubleshooting

If you don't hear audio:
- Check CloudWatch logs for your Connect instance
- Verify the secret ARN is correct in the flow
- Ensure the secret resource policy is applied correctly
- Verify the KMS key policy includes Connect
