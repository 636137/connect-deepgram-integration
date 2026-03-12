#!/usr/bin/env python3
"""Bootstrap Amazon Connect + Deepgram TTS/STT.

This script:
- Creates/updates a Secrets Manager secret in the schema Connect expects for Deepgram.
- Applies a resource policy to the secret so Connect can call GetSecretValue.
- Updates a customer-managed KMS key policy so Connect + Secrets Manager can decrypt that secret.
- Lists valid Deepgram STT models (Nova-3) and TTS models/voices (Aura-2).

It never prints the API token.
"""

from __future__ import annotations

import argparse
import getpass
import json
import re
import sys
import time
import urllib.request
import urllib.error
import warnings
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

try:
    from boto3.compat import PythonDeprecationWarning  # type: ignore
    warnings.filterwarnings("ignore", category=PythonDeprecationWarning)
except Exception:
    pass


# Deepgram STT Models (Nova-3)
DEEPGRAM_STT_MODELS = [
    ("nova-3-general", "General-purpose, highest accuracy, 10 languages"),
    ("nova-3-medical", "Medical terminology optimized, English"),
    ("nova-3-phonecall", "Phone call audio optimized, English"),
    ("nova-3-meeting", "Meeting/conference audio, English"),
    ("nova-2-general", "Previous generation, general-purpose"),
    ("nova-2-phonecall", "Previous generation, phone calls"),
]

# Deepgram TTS Voices (Aura-2)
DEEPGRAM_TTS_VOICES = [
    ("thalia", "Feminine", "American", "Clear, Confident, Energetic"),
    ("andromeda", "Feminine", "American", "Casual, Expressive"),
    ("helena", "Feminine", "American", "Caring, Friendly, Raspy"),
    ("apollo", "Masculine", "American", "Confident, Comfortable"),
    ("arcas", "Masculine", "American", "Natural, Smooth, Clear"),
    ("aries", "Masculine", "American", "Warm, Energetic, Caring"),
    ("amalthea", "Feminine", "Filipino", "Engaging, Cheerful"),
    ("athena", "Feminine", "American", "Calm, Smooth, Professional"),
    ("atlas", "Masculine", "American", "Confident, Approachable"),
    ("asteria", "Feminine", "American", "Default voice"),
    ("luna", "Feminine", "British", "British accent"),
    ("orion", "Masculine", "British", "British accent"),
    ("perseus", "Masculine", "American", "Deep, Authoritative"),
    ("angus", "Masculine", "Irish", "Irish accent"),
    ("orpheus", "Masculine", "American", "Warm, Storytelling"),
    ("hera", "Feminine", "American", "Professional, Warm"),
    ("zeus", "Masculine", "American", "Deep, Commanding"),
]

# Deepgram TTS Languages
DEEPGRAM_TTS_LANGUAGES = ["en", "es", "de", "fr", "nl", "it", "ja"]


def _die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)


def _http_get_json(url: str, api_key: str, timeout_s: int = 20) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Token {api_key}",
            "accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        body = resp.read()
        return json.loads(body)


def _get_account_id(region: str) -> str:
    sts = boto3.client("sts", region_name=region)
    return sts.get_caller_identity()["Account"]


def _get_secret(sm, secret_name: str) -> Optional[Dict[str, Any]]:
    try:
        return sm.describe_secret(SecretId=secret_name)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in {"ResourceNotFoundException"}:
            return None
        raise


def _ensure_secret(
    *,
    region: str,
    secret_name: str,
    kms_key_arn: str,
    prompt_for_token: bool,
    api_token_arg: Optional[str],
    apply: bool,
    yes: bool,
) -> str:
    sm = boto3.client("secretsmanager", region_name=region)

    api_token: Optional[str] = api_token_arg
    if prompt_for_token and not api_token:
        api_token = getpass.getpass("Enter Deepgram API token (input hidden): ").strip()
        if not api_token:
            _die("Empty token provided")

    existing = _get_secret(sm, secret_name)

    # Determine secret value (never print)
    secret_string: Optional[str] = None
    if api_token is not None:
        secret_string = _json_dumps({"apiToken": api_token})

    if not apply:
        print(
            f"[dry-run] Would {'create' if not existing else 'update'} secret '{secret_name}' in {region} with KMS key {kms_key_arn} and schema key apiToken"
        )
        if existing:
            return existing["ARN"]
        return "(secret ARN unknown until created)"

    if not yes:
        ans = input(f"Apply secret create/update for '{secret_name}'? [y/N] ").strip().lower()
        if ans not in {"y", "yes"}:
            _die("Aborted")

    if not existing:
        if secret_string is None:
            _die("Secret does not exist; re-run with --prompt-for-token or --api-token to set its value")
        resp = sm.create_secret(
            Name=secret_name,
            KmsKeyId=kms_key_arn,
            SecretString=secret_string,
            Description="Amazon Connect Deepgram TTS/STT credential (apiToken)",
        )
        arn = resp["ARN"]
        print(f"Created secret: {arn}")
        return arn

    # Secret exists: ensure KMS key set; optionally update value
    arn = existing["ARN"]
    update_kwargs: Dict[str, Any] = {"SecretId": secret_name}
    if kms_key_arn:
        update_kwargs["KmsKeyId"] = kms_key_arn
    if len(update_kwargs) > 1:
        sm.update_secret(**update_kwargs)

    if secret_string is not None:
        sm.put_secret_value(SecretId=secret_name, SecretString=secret_string)

    print(f"Updated secret: {arn}")
    return arn


def _put_secret_resource_policy(
    *,
    region: str,
    secret_arn: str,
    connect_instance_arn: str,
    account_id: str,
    apply: bool,
    yes: bool,
) -> None:
    sm = boto3.client("secretsmanager", region_name=region)

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowAmazonConnectGetSecretValueScopedToInstance",
                "Effect": "Allow",
                "Principal": {"Service": "connect.amazonaws.com"},
                "Action": "secretsmanager:GetSecretValue",
                "Resource": "*",
                "Condition": {
                    "ArnLike": {"aws:sourceArn": connect_instance_arn},
                    "StringEquals": {"aws:sourceAccount": account_id},
                },
            }
        ],
    }

    if not apply:
        print("[dry-run] Would attach Secrets Manager resource policy scoped to Connect instance")
        return

    if not yes:
        ans = input("Apply secret resource policy? [y/N] ").strip().lower()
        if ans not in {"y", "yes"}:
            _die("Aborted")

    sm.put_resource_policy(SecretId=secret_arn, ResourcePolicy=_json_dumps(policy))
    print("Attached/updated secret resource policy")


def _get_key_policy(kms, key_arn: str) -> Dict[str, Any]:
    return json.loads(kms.get_key_policy(KeyId=key_arn, PolicyName="default")["Policy"])


def _put_key_policy(kms, key_arn: str, policy: Dict[str, Any]) -> None:
    kms.put_key_policy(KeyId=key_arn, PolicyName="default", Policy=_json_dumps(policy))


def _upsert_kms_policy(
    *,
    region: str,
    kms_key_arn: str,
    connect_instance_arn: str,
    secret_arn: str,
    account_id: str,
    apply: bool,
    yes: bool,
) -> None:
    kms = boto3.client("kms", region_name=region)

    pol = _get_key_policy(kms, kms_key_arn)
    stmts: List[Dict[str, Any]] = list(pol.get("Statement") or [])

    sids = {
        "AllowSecretsManagerDecryptForDeepgramSecret",
        "AllowSecretsManagerCreateGrantForDeepgramSecret",
        "AllowConnectDecryptForDeepgramSecret",
    }
    stmts = [s for s in stmts if s.get("Sid") not in sids]

    # 1) Allow Secrets Manager to use the key when decrypting THIS secret.
    stmts.append(
        {
            "Sid": "AllowSecretsManagerDecryptForDeepgramSecret",
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": ["kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "kms:ViaService": f"secretsmanager.{region}.amazonaws.com",
                    "kms:EncryptionContext:SecretARN": secret_arn,
                }
            },
        }
    )
    stmts.append(
        {
            "Sid": "AllowSecretsManagerCreateGrantForDeepgramSecret",
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": ["kms:CreateGrant"],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "kms:ViaService": f"secretsmanager.{region}.amazonaws.com",
                    "kms:EncryptionContext:SecretARN": secret_arn,
                    "kms:GrantIsForAWSResource": "true",
                }
            },
        }
    )

    # 2) Allow Connect to decrypt the secret, scoped to instance + secret.
    stmts.append(
        {
            "Sid": "AllowConnectDecryptForDeepgramSecret",
            "Effect": "Allow",
            "Principal": {"Service": "connect.amazonaws.com"},
            "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
            "Resource": "*",
            "Condition": {
                "ArnLike": {"aws:sourceArn": connect_instance_arn},
                "StringEquals": {
                    "aws:sourceAccount": account_id,
                    "kms:EncryptionContext:SecretARN": secret_arn,
                },
            },
        }
    )

    pol["Statement"] = stmts

    if not apply:
        print("[dry-run] Would upsert 3 KMS key policy statements (Connect + Secrets Manager, scoped to this secret)")
        return

    if not yes:
        ans = input(f"Apply KMS key policy updates to {kms_key_arn}? [y/N] ").strip().lower()
        if ans not in {"y", "yes"}:
            _die("Aborted")

    _put_key_policy(kms, kms_key_arn, pol)
    print("Updated KMS key policy")


def _get_api_token_from_secret(region: str, secret_name: str) -> str:
    sm = boto3.client("secretsmanager", region_name=region)
    r = sm.get_secret_value(SecretId=secret_name)
    s = r.get("SecretString")
    if not s:
        _die("SecretString missing; secret may be binary")
    obj = json.loads(s)
    token = obj.get("apiToken") or obj.get("api_key") or obj.get("apiKey")
    if not token:
        _die("Secret does not contain apiToken (or api_key/apiKey)")
    return token


def _read_json_file(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json_file(path: str, obj: Any) -> None:
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _describe_secret_arn(region: str, secret_name: str) -> str:
    sm = boto3.client("secretsmanager", region_name=region)
    return sm.describe_secret(SecretId=secret_name)["ARN"]


def _require_tty(what: str) -> None:
    if not sys.stdin.isatty():
        _die(f"{what} not provided and stdin is not interactive; pass it explicitly")


def _prompt_indexed(prompt: str, options: List[str], default_index: int = 1) -> int:
    if not options:
        _die("No options available")
    print(prompt)
    for i, o in enumerate(options, start=1):
        print(f"{i}) {o}")
    ans = input(f"Choose [default {default_index}]: ").strip()
    if not ans:
        return default_index - 1
    if ans.isdigit():
        n = int(ans)
        if 1 <= n <= len(options):
            return n - 1
    _die("Invalid choice")
    raise AssertionError("unreachable")


def _prompt_multiline_text(prompt: str) -> str:
    _require_tty("--prompt-for-greeting")
    print(prompt)
    print("Paste your phrase. Finish with an empty line:")
    lines = []
    while True:
        line = sys.stdin.readline()
        if line == "":
            break  # EOF
        line = line.rstrip("\n")
        if line == "":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _iter_actions(flow: Dict[str, Any]):
    for a in (flow.get("Actions") or []):
        if isinstance(a, dict):
            yield a


def _actions_by_type(flow: Dict[str, Any], action_type: str) -> List[Dict[str, Any]]:
    return [a for a in _iter_actions(flow) if a.get("Type") == action_type]


def _apply_greeting_text(flow: dict, greeting_text: str) -> int:
    """Apply greeting text to MessageParticipant and PlayPrompt actions when possible."""
    updated = 0

    for a in _actions_by_type(flow, "MessageParticipant"):
        params = a.setdefault("Parameters", {})
        if isinstance(params, dict):
            params["Text"] = greeting_text
            updated += 1

    for a in _actions_by_type(flow, "PlayPrompt"):
        params = a.setdefault("Parameters", {})
        if not isinstance(params, dict):
            continue

        if "Text" in params or isinstance(params.get("Text"), str):
            params["Text"] = greeting_text
            updated += 1
            continue
        if "PromptText" in params or isinstance(params.get("PromptText"), str):
            params["PromptText"] = greeting_text
            updated += 1
            continue

        prompts = params.get("Prompts")
        if isinstance(prompts, list):
            for p in prompts:
                if not isinstance(p, dict):
                    continue
                if "Text" in p or isinstance(p.get("Text"), str):
                    p["Text"] = greeting_text
                    updated += 1
                elif "PromptText" in p or isinstance(p.get("PromptText"), str):
                    p["PromptText"] = greeting_text
                    updated += 1

    return updated


def _build_deepgram_tts_model(model: str, voice: str, language: str) -> str:
    """Build Deepgram TTS model string: aura-2-<voice>-<language>"""
    return f"{model}-{voice}-{language}"


def _select_tts_voice(language: str) -> str:
    _require_tty("--tts-voice")
    opts = []
    for v in DEEPGRAM_TTS_VOICES:
        opts.append(f"{v[0]}  ({v[1]}, {v[2]}) - {v[3]}")
    idx = _prompt_indexed(f"Select a Deepgram TTS voice for language '{language}':", opts, default_index=1)
    return DEEPGRAM_TTS_VOICES[idx][0]


def _select_stt_model() -> str:
    _require_tty("--stt-model")
    opts = [f"{m[0]}  - {m[1]}" for m in DEEPGRAM_STT_MODELS]
    idx = _prompt_indexed("Select a Deepgram STT model:", opts, default_index=1)
    return DEEPGRAM_STT_MODELS[idx][0]


def _connect_instance_id_from_arn(instance_arn: str) -> str:
    m = re.search(r"instance/([0-9a-f\-]+)$", (instance_arn or "").strip())
    if not m:
        _die("Invalid --connect-instance-arn (expected ...:instance/INSTANCE_ID)")
    return m.group(1)


def _sanitize_flow_for_connect_api(flow: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(flow)
    md = out.get("Metadata")
    if isinstance(md, dict):
        allowed = {"ActionMetadata", "Annotations", "entryPointPosition"}
        out["Metadata"] = {k: v for k, v in md.items() if k in allowed}
    return out


def _list_all_phone_numbers(conn, instance_id: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    tok: Optional[str] = None
    while True:
        kwargs = {"InstanceId": instance_id}
        if tok:
            kwargs["NextToken"] = tok
        resp = conn.list_phone_numbers(**kwargs)
        out.extend(resp.get("PhoneNumberSummaryList") or [])
        tok = resp.get("NextToken")
        if not tok:
            break
    return out


def _resolve_phone_number_id(conn, instance_id: str, phone_number: Optional[str], phone_number_id: Optional[str]) -> Optional[str]:
    if phone_number_id:
        return phone_number_id

    nums = _list_all_phone_numbers(conn, instance_id)
    if phone_number:
        for n in nums:
            if (n or {}).get("PhoneNumber") == phone_number:
                return (n or {}).get("Id")
        _die(f"Phone number not found in Connect instance: {phone_number}")

    if len(nums) == 1:
        return (nums[0] or {}).get("Id")

    if not nums:
        return None

    _require_tty("--phone-number/--phone-number-id")
    opts = [f"{n.get('PhoneNumber')}  ({n.get('PhoneNumberType')}) id={n.get('Id')}" for n in nums]
    idx = _prompt_indexed("Select a phone number to associate:", opts, default_index=1)
    return (nums[idx] or {}).get("Id")


def _list_all_contact_flows(conn, instance_id: str, flow_types: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    tok: Optional[str] = None
    while True:
        kwargs: Dict[str, Any] = {"InstanceId": instance_id, "ContactFlowTypes": flow_types}
        if tok:
            kwargs["NextToken"] = tok
        resp = conn.list_contact_flows(**kwargs)
        out.extend(resp.get("ContactFlowSummaryList") or [])
        tok = resp.get("NextToken")
        if not tok:
            break
    return out


def _connect_flow_type_from_template(flow: Dict[str, Any]) -> str:
    md = flow.get("Metadata")
    if isinstance(md, dict):
        t = (md.get("type") or "").strip()
        if t == "contactFlow":
            return "CONTACT_FLOW"
        if t == "customerQueue":
            return "CUSTOMER_QUEUE"
        if t == "customerHold":
            return "CUSTOMER_HOLD"
        if t == "customerWhisper":
            return "CUSTOMER_WHISPER"
        if t == "outboundWhisper":
            return "OUTBOUND_WHISPER"
        if t == "agentHold":
            return "AGENT_HOLD"
        if t == "agentWhisper":
            return "AGENT_WHISPER"
        if t == "transferToAgent":
            return "TRANSFER_TO_AGENT"
        if t == "transferToQueue":
            return "TRANSFER_TO_QUEUE"
    return "CONTACT_FLOW"


def cmd_setup(args: argparse.Namespace) -> None:
    account_id = _get_account_id(args.region)

    if args.apply and not args.yes:
        print("This will modify AWS resources (Secrets Manager + KMS). Use --yes to skip prompts.")

    secret_arn = _ensure_secret(
        region=args.region,
        secret_name=args.secret_name,
        kms_key_arn=args.kms_key_arn,
        prompt_for_token=args.prompt_for_token,
        api_token_arg=getattr(args, 'api_token', None),
        apply=args.apply,
        yes=args.yes,
    )

    if args.apply:
        # Refresh ARN (ensure not the placeholder)
        sm = boto3.client("secretsmanager", region_name=args.region)
        secret_arn = sm.describe_secret(SecretId=args.secret_name)["ARN"]

    _put_secret_resource_policy(
        region=args.region,
        secret_arn=secret_arn,
        connect_instance_arn=args.connect_instance_arn,
        account_id=account_id,
        apply=args.apply,
        yes=args.yes,
    )

    _upsert_kms_policy(
        region=args.region,
        kms_key_arn=args.kms_key_arn,
        connect_instance_arn=args.connect_instance_arn,
        secret_arn=secret_arn,
        account_id=account_id,
        apply=args.apply,
        yes=args.yes,
    )

    print("")
    print("Next steps:")
    print("")
    print("For STT (Speech-to-Text):")
    print("  1. Go to Amazon Connect console → Your instance → Third-party integrations")
    print("  2. Select Deepgram as the speech provider")
    print(f"  3. Enter Secrets Manager ARN: {secret_arn}")
    print("  4. Select STT model: nova-3-general")
    print("")
    print("For TTS (Text-to-Speech) in contact flow -> Set voice:")
    print("  - Voice provider: Deepgram")
    print("  - Model: aura-2")
    print("  - Voice: thalia (or another voice)")
    print("  - Language: en (or another language)")
    print(f"  - Secrets Manager ARN: {secret_arn}")


def cmd_catalog(args: argparse.Namespace) -> None:
    print("=" * 60)
    print("DEEPGRAM STT MODELS (Nova-3)")
    print("=" * 60)
    print("Use these in Amazon Connect instance-level STT configuration:")
    print("")
    for model_id, desc in DEEPGRAM_STT_MODELS:
        print(f"  {model_id}")
        print(f"    └── {desc}")
    print("")

    print("=" * 60)
    print("DEEPGRAM TTS VOICES (Aura-2)")
    print("=" * 60)
    print("Use these in contact flow Set voice block:")
    print("  Model: aura-2")
    print("  Voice: <voice name below>")
    print(f"  Language: {args.language}")
    print("")
    print("Available voices:")
    for voice, gender, accent, desc in DEEPGRAM_TTS_VOICES:
        model_str = f"aura-2-{voice}-{args.language}"
        print(f"  {voice}")
        print(f"    └── {gender}, {accent} - {desc}")
        print(f"    └── Full model string: {model_str}")
    print("")

    print("=" * 60)
    print("DEEPGRAM TTS LANGUAGES")
    print("=" * 60)
    for lang in DEEPGRAM_TTS_LANGUAGES:
        print(f"  {lang}")
    print("")

    # Try to validate API key if secret exists
    try:
        api_key = _get_api_token_from_secret(args.region, args.secret_name)
        print("=" * 60)
        print("API KEY VALIDATION")
        print("=" * 60)
        # Test API key with a simple request
        url = "https://api.deepgram.com/v1/projects"
        try:
            result = _http_get_json(url, api_key)
            print(f"✓ API key is valid (found {len(result.get('projects', []))} project(s))")
        except urllib.error.HTTPError as e:
            print(f"✗ API key validation failed: HTTP {e.code}")
        except Exception as e:
            print(f"✗ API key validation failed: {e}")
    except Exception:
        print("(Secret not found or inaccessible - skipping API key validation)")


def cmd_flow(args: argparse.Namespace) -> None:
    """Render an import-ready Amazon Connect contact flow JSON from a template export."""

    flow = _read_json_file(args.template_path)
    if not isinstance(flow, dict):
        _die("Template JSON must be an object")

    meta = flow.get("Metadata") or {}
    if isinstance(meta, dict):
        if args.flow_name:
            meta["name"] = args.flow_name
        if args.flow_description is not None:
            meta["description"] = args.flow_description
        flow["Metadata"] = meta

    secret_arn = args.secret_arn
    if not secret_arn:
        secret_arn = _describe_secret_arn(args.region, args.secret_name)

    # Handle TTS voice selection
    tts_voice = args.tts_voice
    if tts_voice is None:
        tts_voice = _select_tts_voice(args.tts_language)

    tts_model = args.tts_model or "aura-2"
    tts_language = args.tts_language or "en"

    # Build the full Deepgram TTS model string
    full_model = _build_deepgram_tts_model(tts_model, tts_voice, tts_language)
    engine_string = f"deepgram:{full_model}"

    # Handle greeting text
    if getattr(args, "prompt_for_greeting", False) and args.greeting_text is None:
        t = _prompt_multiline_text("Enter the phrase to speak in the greeting prompt:")
        if not t:
            _die("Empty greeting text provided")
        args.greeting_text = t

    # Update TTS actions
    tts_actions = _actions_by_type(flow, "UpdateContactTextToSpeechVoice")
    for a in tts_actions:
        params = a.setdefault("Parameters", {})
        params["TextToSpeechEngine"] = engine_string
        params["TextToSpeechVoice"] = tts_voice
        params["ExternalCredentialSecretARN"] = secret_arn

    if args.greeting_text is not None:
        n = _apply_greeting_text(flow, args.greeting_text)
        if n == 0:
            _die("Template did not contain a MessageParticipant or PlayPrompt action with text to replace")

    _write_json_file(args.output_path, flow)
    print(f"Wrote contact flow JSON: {args.output_path}")
    print(f"TTS Model: {full_model}")
    print(f"TTS Voice: {tts_voice}")


def cmd_deploy(args: argparse.Namespace) -> None:
    """Render (optionally) and deploy a contact flow via Amazon Connect APIs."""

    conn = boto3.client("connect", region_name=args.region)
    instance_id = _connect_instance_id_from_arn(args.connect_instance_arn)

    flow = _read_json_file(args.template_path)
    if not isinstance(flow, dict):
        _die("Template JSON must be an object")

    # Get secret ARN
    secret_arn = args.secret_arn
    if not secret_arn:
        secret_arn = _describe_secret_arn(args.region, args.secret_name)

    # Handle TTS voice selection
    tts_voice = args.tts_voice
    if tts_voice is None:
        tts_voice = _select_tts_voice(args.tts_language or "en")

    tts_model = args.tts_model or "aura-2"
    tts_language = args.tts_language or "en"

    # Build the full Deepgram TTS model string
    full_model = _build_deepgram_tts_model(tts_model, tts_voice, tts_language)
    engine_string = f"deepgram:{full_model}"

    # Handle greeting text
    if getattr(args, "prompt_for_greeting", False) and args.greeting_text is None:
        t = _prompt_multiline_text("Enter the phrase to speak in the greeting prompt:")
        if not t:
            _die("Empty greeting text provided")
        args.greeting_text = t

    # Update TTS actions
    tts_actions = _actions_by_type(flow, "UpdateContactTextToSpeechVoice")
    for a in tts_actions:
        params = a.setdefault("Parameters", {})
        params["TextToSpeechEngine"] = engine_string
        params["TextToSpeechVoice"] = tts_voice
        params["ExternalCredentialSecretARN"] = secret_arn

    if args.greeting_text is not None:
        n = _apply_greeting_text(flow, args.greeting_text)
        if n == 0:
            print("Warning: Template did not contain a MessageParticipant or PlayPrompt action with text to replace")

    # Determine Connect name/description from overrides or template Metadata.
    md = flow.get("Metadata") if isinstance(flow, dict) else None
    md_name = (md.get("name") if isinstance(md, dict) else None) or None
    md_desc = (md.get("description") if isinstance(md, dict) else None) or ""

    flow_name = args.flow_name or md_name
    if not flow_name and not args.contact_flow_id:
        flow_name = f"Deepgram {tts_voice} {time.strftime('%Y%m%d-%H%M%S')}"
        print(f"Using default flow name: {flow_name}")

    if not flow_name:
        _die("Missing flow name. Provide --flow-name or ensure template Metadata.name exists.")

    flow_desc = md_desc
    if args.flow_description is not None:
        flow_desc = args.flow_description

    flow_type = args.flow_type or _connect_flow_type_from_template(flow)

    content_obj = _sanitize_flow_for_connect_api(flow)
    content = json.dumps(content_obj, separators=(",", ":"), ensure_ascii=False)

    contact_flow_id: Optional[str] = args.contact_flow_id
    if not contact_flow_id:
        flows = _list_all_contact_flows(conn, instance_id, [flow_type])
        matches = [f for f in flows if (f or {}).get("Name") == flow_name]
        if len(matches) == 1:
            contact_flow_id = matches[0].get("Id")
        elif len(matches) > 1:
            _require_tty("--contact-flow-id")
            opts = [f"{m.get('Id')}  ({m.get('Arn')})" for m in matches]
            idx = _prompt_indexed(f"Multiple flows named '{flow_name}' found; select one:", opts, default_index=1)
            contact_flow_id = matches[idx].get("Id")

    if contact_flow_id:
        conn.update_contact_flow_content(InstanceId=instance_id, ContactFlowId=contact_flow_id, Content=content)
        conn.update_contact_flow_name(
            InstanceId=instance_id, ContactFlowId=contact_flow_id, Name=flow_name, Description=flow_desc
        )
        conn.update_contact_flow_metadata(
            InstanceId=instance_id, ContactFlowId=contact_flow_id, ContactFlowState="ACTIVE"
        )
        print(f"Updated contact flow: {flow_name} ({contact_flow_id})")
    else:
        resp = conn.create_contact_flow(
            InstanceId=instance_id,
            Name=flow_name,
            Type=flow_type,
            Content=content,
            Description=flow_desc,
            Status="PUBLISHED",
        )
        contact_flow_id = resp.get("ContactFlowId")
        print(f"Created contact flow: {flow_name} ({contact_flow_id})")

    # Optionally write the rendered JSON to disk.
    if args.output_path:
        _write_json_file(args.output_path, flow)
        print(f"Wrote rendered flow JSON: {args.output_path}")

    # Associate phone number to this contact flow.
    phone_number_id = _resolve_phone_number_id(conn, instance_id, args.phone_number, args.phone_number_id)
    if phone_number_id:
        conn.associate_phone_number_contact_flow(
            InstanceId=instance_id, PhoneNumberId=phone_number_id, ContactFlowId=contact_flow_id
        )
        print(f"Associated phone number ({phone_number_id}) to contact flow ({contact_flow_id})")

    print("")
    print(f"TTS Model: {full_model}")
    print(f"TTS Voice: {tts_voice}")
    if args.phone_number:
        print(f"Test: call {args.phone_number} and confirm TTS plays with Deepgram voice.")


def cmd_configure_stt(args: argparse.Namespace) -> None:
    """Configure Deepgram STT for an Amazon Lex V2 bot locale."""
    region = args.region
    bot_id = args.bot_id
    locale_id = args.locale_id or "en_US"
    stt_model = args.stt_model or "nova-3-general"
    secret_name = args.secret_name

    # Get secret ARN
    sm = boto3.client("secretsmanager", region_name=region)
    try:
        secret = sm.describe_secret(SecretId=secret_name)
        secret_arn = secret["ARN"]
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
            _die(f"Secret '{secret_name}' not found in {region}. Run 'setup' command first.")
        raise

    print(f"Configuring Deepgram STT for bot {bot_id}, locale {locale_id}")
    print(f"  STT Model: {stt_model}")
    print(f"  Secret ARN: {secret_arn}")
    print("")

    lex = boto3.client("lexv2-models", region_name=region)

    # Get current bot locale settings
    try:
        locale = lex.describe_bot_locale(
            botId=bot_id,
            botVersion="DRAFT",
            localeId=locale_id
        )
    except ClientError as e:
        _die(f"Failed to describe bot locale: {e}")

    # Prepare the update
    update_params = {
        "botId": bot_id,
        "botVersion": "DRAFT",
        "localeId": locale_id,
        "nluIntentConfidenceThreshold": locale.get("nluIntentConfidenceThreshold", 0.4),
        "speechRecognitionSettings": {
            "speechModelPreference": "Deepgram",
            "speechModelConfig": {
                "deepgramConfig": {
                    "apiTokenSecretArn": secret_arn,
                    "modelId": stt_model
                }
            }
        }
    }

    # Preserve existing voice settings if present
    if locale.get("voiceSettings"):
        update_params["voiceSettings"] = locale["voiceSettings"]

    if not args.apply:
        print("[dry-run] Would update bot locale with Deepgram STT settings:")
        print(json.dumps(update_params["speechRecognitionSettings"], indent=2))
        print("")
        print("Run with --apply --yes to make changes.")
        return

    if not args.yes:
        ans = input("Apply Deepgram STT configuration? [y/N] ").strip().lower()
        if ans not in {"y", "yes"}:
            _die("Aborted")

    try:
        lex.update_bot_locale(**update_params)
        print("✓ Bot locale updated with Deepgram STT settings")
    except ClientError as e:
        _die(f"Failed to update bot locale: {e}")

    # Build the locale
    print("Building bot locale...")
    try:
        lex.build_bot_locale(
            botId=bot_id,
            botVersion="DRAFT",
            localeId=locale_id
        )
        print("✓ Bot locale build initiated")
    except ClientError as e:
        print(f"Warning: Failed to build bot locale: {e}")

    # Wait for build to complete
    print("Waiting for build to complete...")
    for _ in range(30):  # 60 seconds max
        time.sleep(2)
        try:
            status = lex.describe_bot_locale(
                botId=bot_id,
                botVersion="DRAFT",
                localeId=locale_id
            )
            build_status = status.get("botLocaleStatus", "")
            if build_status == "Built":
                print("✓ Bot locale built successfully")
                break
            elif build_status in {"Failed", "Deleting"}:
                print(f"✗ Build failed with status: {build_status}")
                if status.get("failureReasons"):
                    for reason in status["failureReasons"]:
                        print(f"  - {reason}")
                break
            else:
                print(f"  Status: {build_status}...")
        except Exception:
            pass
    else:
        print("Build timed out - check AWS Console for status")

    print("")
    print("Next steps:")
    print("  1. Verify in AWS Console: Lex > Bots > Your Bot > Locale > Speech model")
    print("  2. Test with Amazon Connect or Lex Console test feature")
    print("")
    print("Cost estimate (Deepgram Nova-3):")
    print("  Pay-As-You-Go: $0.0077/min ($0.46/hour)")
    print("  Growth Plan:   $0.0065/min ($0.39/hour) - requires $4K/year commitment")


def cmd_list_bots(args: argparse.Namespace) -> None:
    """List Lex V2 bots and their locales."""
    region = args.region
    lex = boto3.client("lexv2-models", region_name=region)

    try:
        bots = lex.list_bots()
    except ClientError as e:
        _die(f"Failed to list bots: {e}")

    bot_list = bots.get("botSummaries", [])
    if not bot_list:
        print(f"No Lex V2 bots found in {region}")
        return

    print(f"Lex V2 Bots in {region}:")
    print("")

    for bot in bot_list:
        bot_id = bot.get("botId", "")
        bot_name = bot.get("botName", "")
        print(f"  {bot_name} (ID: {bot_id})")

        # Get locales for this bot
        try:
            locales = lex.list_bot_locales(botId=bot_id, botVersion="DRAFT")
            for loc in locales.get("botLocaleSummaries", []):
                locale_id = loc.get("localeId", "")
                locale_name = loc.get("localeName", "")
                status = loc.get("botLocaleStatus", "")

                # Get speech settings
                try:
                    locale_detail = lex.describe_bot_locale(
                        botId=bot_id,
                        botVersion="DRAFT",
                        localeId=locale_id
                    )
                    speech = locale_detail.get("speechRecognitionSettings", {})
                    stt_provider = speech.get("speechModelPreference", "Amazon")
                    if speech.get("speechModelConfig", {}).get("deepgramConfig"):
                        stt_model = speech["speechModelConfig"]["deepgramConfig"].get("modelId", "")
                        stt_provider = f"Deepgram ({stt_model})"
                except Exception:
                    stt_provider = "Unknown"

                print(f"    └── {locale_id} ({locale_name}) - {status}")
                print(f"        STT: {stt_provider}")
        except Exception as e:
            print(f"    └── (failed to list locales: {e})")
        print("")


def main() -> None:
    p = argparse.ArgumentParser(prog="connect_deepgram_setup.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    # Setup command
    ps = sub.add_parser("setup", help="Create/update secret and apply Connect/KMS policies")
    ps.add_argument("--region", required=True)
    ps.add_argument("--connect-instance-arn", required=True)
    ps.add_argument("--secret-name", default="deepgram")
    ps.add_argument("--kms-key-arn", required=True)
    ps.add_argument("--prompt-for-token", action="store_true")
    ps.add_argument("--api-token", help="Deepgram API token (alternative to --prompt-for-token)")
    ps.add_argument("--apply", action="store_true")
    ps.add_argument("--yes", action="store_true")
    ps.set_defaults(func=cmd_setup)

    # Catalog command
    pc = sub.add_parser("catalog", help="List valid Deepgram STT models and TTS voices")
    pc.add_argument("--region", required=True)
    pc.add_argument("--secret-name", default="deepgram")
    pc.add_argument("--language", default="en", help="Language code for TTS (e.g., en, es, de)")
    pc.set_defaults(func=cmd_catalog)

    # Flow command
    pf = sub.add_parser("flow", help="Render a Connect contact flow JSON from a template export")
    pf.add_argument("--template-path", required=True, help="Path to an exported contact flow JSON (template)")
    pf.add_argument("--output-path", required=True, help="Where to write the rendered contact flow JSON")
    pf.add_argument("--region", required=True, help="AWS region (used to resolve --secret-name to an ARN)")
    pf.add_argument("--secret-arn", help="Secrets Manager secret ARN (if omitted, resolved from --secret-name)")
    pf.add_argument("--secret-name", default="deepgram", help="Secret name to resolve to an ARN")
    pf.add_argument("--tts-model", default="aura-2", help="Deepgram TTS model (default: aura-2)")
    pf.add_argument("--tts-voice", help="Deepgram TTS voice (e.g., thalia, apollo). If omitted, you'll be prompted.")
    pf.add_argument("--tts-language", default="en", help="Deepgram TTS language (default: en)")
    pf.add_argument("--greeting-text", help="Text for MessageParticipant and/or PlayPrompt action(s)")
    pf.add_argument("--prompt-for-greeting", action="store_true", help="Prompt interactively for the greeting phrase")
    pf.add_argument("--flow-name", help="Override contact flow name")
    pf.add_argument("--flow-description", help="Override contact flow description")
    pf.set_defaults(func=cmd_flow)

    # Deploy command
    pd = sub.add_parser("deploy", help="Render and deploy a contact flow via Connect APIs, then associate a phone number")
    pd.add_argument("--region", required=True)
    pd.add_argument("--connect-instance-arn", required=True)
    pd.add_argument("--template-path", required=True, help="Path to an exported contact flow JSON (template)")
    pd.add_argument("--output-path", help="Optional: write the rendered flow JSON to this path")
    pd.add_argument("--secret-arn", help="Secrets Manager secret ARN (if omitted, resolved from --secret-name)")
    pd.add_argument("--secret-name", default="deepgram")
    pd.add_argument("--tts-model", default="aura-2", help="Deepgram TTS model (default: aura-2)")
    pd.add_argument("--tts-voice", help="Deepgram TTS voice (e.g., thalia, apollo). If omitted, you'll be prompted.")
    pd.add_argument("--tts-language", default="en", help="Deepgram TTS language (default: en)")
    pd.add_argument("--greeting-text", help="Text for MessageParticipant and/or PlayPrompt action(s)")
    pd.add_argument("--prompt-for-greeting", action="store_true", help="Prompt interactively for the greeting phrase")
    pd.add_argument("--flow-name", help="Override contact flow name")
    pd.add_argument("--flow-description", help="Override contact flow description")
    pd.add_argument("--flow-type", help="Connect flow type (default inferred from template)")
    pd.add_argument("--contact-flow-id", help="If set, update this specific flow id instead of searching by name")
    pd.add_argument("--phone-number", help="E.164 phone number to associate (e.g., +18445551212)")
    pd.add_argument("--phone-number-id", help="Phone number id to associate")
    pd.set_defaults(func=cmd_deploy)

    # List bots command
    pl = sub.add_parser("list-bots", help="List Lex V2 bots and their STT configuration")
    pl.add_argument("--region", required=True)
    pl.set_defaults(func=cmd_list_bots)

    # Configure STT command
    pcs = sub.add_parser("configure-stt", help="Configure Deepgram STT for an Amazon Lex V2 bot locale")
    pcs.add_argument("--region", required=True)
    pcs.add_argument("--bot-id", required=True, help="Lex V2 bot ID")
    pcs.add_argument("--locale-id", default="en_US", help="Locale ID (default: en_US)")
    pcs.add_argument("--stt-model", default="nova-3-general", help="Deepgram STT model (default: nova-3-general)")
    pcs.add_argument("--secret-name", default="deepgram", help="Secrets Manager secret name")
    pcs.add_argument("--apply", action="store_true", help="Actually make changes")
    pcs.add_argument("--yes", action="store_true", help="Skip confirmation prompts")
    pcs.set_defaults(func=cmd_configure_stt)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
