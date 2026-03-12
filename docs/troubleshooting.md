# Troubleshooting Guide

Common issues and their solutions when integrating Deepgram with Amazon Connect.

## Error Messages

### "Failed to retrieve credentials from Secrets Manager"

**Cause:** The secret resource policy doesn't allow Amazon Connect to access the secret.

**Solution:**
1. Verify the secret exists:
   ```bash
   aws secretsmanager describe-secret --secret-id deepgram --region us-west-2
   ```

2. Check the resource policy:
   ```bash
   aws secretsmanager get-resource-policy --secret-id deepgram --region us-west-2
   ```

3. Apply correct policy using the setup script:
   ```bash
   python3 scripts/connect_deepgram_setup.py setup \
     --region us-west-2 \
     --connect-instance-arn <your-instance-arn> \
     --kms-key-arn <your-kms-key-arn> \
     --secret-name deepgram \
     --apply --yes
   ```

### "KMS key access denied" / "AccessDeniedException"

**Cause:** The KMS key policy doesn't allow Amazon Connect to decrypt the secret.

**Solution:**
1. Check your KMS key policy includes this statement:
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

2. Run the setup script to automatically update the KMS policy.

### "Invalid API key" / "401 Unauthorized"

**Cause:** The Deepgram API key is incorrect, expired, or revoked.

**Solution:**
1. Verify your API key in [Deepgram Console](https://console.deepgram.com)
2. Create a new key if necessary
3. Update the secret:
   ```bash
   aws secretsmanager put-secret-value \
     --secret-id deepgram \
     --secret-string '{"apiToken":"YOUR_NEW_KEY_HERE"}' \
     --region us-west-2
   ```

### No Audio / Silence on Call

**Possible Causes:**

1. **TTS Engine format incorrect**
   - Must be: `deepgram:aura-2` (not `deepgram:aura2` or `aura-2`)

2. **Voice name incorrect**
   - Must be just the name: `thalia` (not `aura-2-thalia-en`)

3. **Secret ARN incorrect**
   - Check the ARN includes the random suffix (e.g., `deepgram-abc123`)

4. **Contact flow not published**
   - Flows must be published to take effect

**Debug Steps:**
1. Enable flow logging
2. Check CloudWatch logs at `/aws/connect/<instance-name>`
3. Look for `UpdateContactTextToSpeechVoice` action results

### "Contact flow error" / Flow Not Working

**Solution:**
1. Open the flow in Connect flow designer
2. Look for validation errors (red icons)
3. Verify all blocks are connected
4. Check the "Set voice" block has all required fields:
   - Voice provider: Deepgram
   - Model: aura-2
   - Voice: (voice name)
   - Language: (language code)
   - Secrets Manager ARN: (full ARN)
5. Save and Publish

## CloudWatch Debugging

### Enable Detailed Logging

Add this block at the start of your contact flow:
```json
{
  "Parameters": {"FlowLoggingBehavior": "Enabled"},
  "Type": "UpdateFlowLoggingBehavior"
}
```

### Finding Logs

1. Go to **CloudWatch → Log groups**
2. Find `/aws/connect/<instance-name>`
3. Search for your contact ID
4. Look for:
   - `UpdateContactTextToSpeechVoice` - TTS configuration
   - `MessageParticipant` - TTS playback
   - Any ERROR or WARN messages

### Log Example (Success)
```
{
  "ContactId": "abc-123",
  "Action": "UpdateContactTextToSpeechVoice",
  "Result": "Success",
  "Parameters": {
    "TextToSpeechEngine": "deepgram:aura-2",
    "TextToSpeechVoice": "thalia"
  }
}
```

### Log Example (Failure)
```
{
  "ContactId": "abc-123",
  "Action": "UpdateContactTextToSpeechVoice",
  "Result": "Failed",
  "Error": "Failed to retrieve credentials from external source"
}
```

## Network/Connectivity Issues

### Connect Cannot Reach Deepgram

Amazon Connect requires outbound connectivity to Deepgram's API. Ensure:
- No VPC restrictions blocking `api.deepgram.com`
- Security groups allow HTTPS outbound
- No WAF rules blocking the traffic

### Latency/Performance

If TTS playback is slow:
1. Check Deepgram service status
2. Ensure using regional endpoint closest to your Connect instance
3. Consider shorter TTS text chunks for faster first-byte response

## Secret Rotation

When rotating Deepgram API keys:

1. Create new key in Deepgram Console
2. Update secret (no downtime):
   ```bash
   aws secretsmanager put-secret-value \
     --secret-id deepgram \
     --secret-string '{"apiToken":"NEW_KEY"}' \
     --region us-west-2
   ```
3. Test with a call
4. Revoke old key in Deepgram Console

## Getting Help

If issues persist:
1. Open an issue in this repository
2. Include:
   - Error message (exact text)
   - CloudWatch log snippets
   - Your configuration (redact secrets!)
   - AWS region and Connect instance type
