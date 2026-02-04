#!/usr/bin/env python3
"""Telemetry & patch client for SonarSniffer

Provides:
- send_parse_report(...) : fire-and-forget POSTs a parse report
- fetch_pending_patches(...) : GETs pending patches from the server
- apply_patch(...) : safely apply limited patch types (currently: 'magic_variants')

Safety model:
- Code patches are NOT auto-applied. Only safe config-like patches (magic variants)
  are supported for auto-apply. Auto-apply must be explicitly enabled via
  environment variable or CLI flag.
"""

from __future__ import annotations

import os
import json
import logging
import platform
import threading
from typing import Optional, List, Dict, Any

try:
    import requests  # type: ignore
    _HAS_REQUESTS = True
except Exception:
    import urllib.request as _urllib_request  # type: ignore
    _HAS_REQUESTS = False

from .core_shared import load_magic_hdrs_from_file, register_magic_hdr
import hmac
import hashlib

LOGGER = logging.getLogger("sonarsniffer.telemetry")
DEFAULT_URL = os.environ.get(
    "SONARSNIFFER_TELEMETRY_URL", "https://sonarsniffer.example.com/api/v1/parse_reports"
)
AUTO_APPLY = os.environ.get("SONARSNIFFER_AUTO_APPLY_PATCHES", "false").lower() in (
    "1",
    "true",
    "yes",
)

# Secret used for HMAC signature verification (server and client must share)
PATCH_SECRET_ENV = os.environ.get("SONARSNIFFER_PATCH_SECRET", None)


def _canonical_patch_content(patch: dict) -> bytes:
    # Produce deterministic JSON for signing/verification
    return json.dumps(patch.get("content", {}), sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_patch_hmac(patch: dict, secret: Optional[str] = None) -> str:
    # Resolve secret dynamically from environment if not provided
    if secret is None:
        # Debug: check env read visibility
        _env_val = os.getenv('SONARSNIFFER_PATCH_SECRET')
        # print for debug (temporary)
        # print('DEBUG: env inside compute_patch_hmac ->', repr(_env_val))
        secret = _env_val or PATCH_SECRET_ENV
    if not secret:
        raise RuntimeError("No patch secret configured")
    mac = hmac.new(secret.encode("utf-8"), _canonical_patch_content(patch), hashlib.sha256)
    return mac.hexdigest()


def verify_patch_signature(patch: dict, secret: Optional[str] = None) -> bool:
    """Verify a patch's HMAC signature (if present). Returns True if signature valid or no signature present and secret is None."""
    sig = patch.get("signature")
    if not sig:
        # No signature supplied - only accept if no secret configured
        return secret is None and (os.environ.get('SONARSNIFFER_PATCH_SECRET') is None and PATCH_SECRET_ENV is None)
    try:
        expected = compute_patch_hmac(patch, secret=secret)
        # HMAC compare in constant time
        return hmac.compare_digest(expected, str(sig))
    except Exception:
        return False


def _post_json_sync(url: str, data: dict, token: Optional[str], timeout: int = 5):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = json.dumps(data).encode("utf-8")
    try:
        if _HAS_REQUESTS:
            resp = requests.post(url, json=data, headers=headers, timeout=timeout)
            LOGGER.debug("Telemetry post status: %s", resp.status_code)
        else:
            req = _urllib_request.Request(url, data=payload, headers=headers, method="POST")
            with _urllib_request.urlopen(req, timeout=timeout) as resp:
                resp.read()
            LOGGER.debug("Telemetry post done (urllib)")
    except Exception as ex:
        LOGGER.debug("Telemetry post failed: %s", ex)


def send_parse_report(
    file_name: str,
    parser_used: str,
    success: bool,
    errors: int = 0,
    warnings: int = 0,
    samples_parsed: int = 0,
    duration_ms: int = 0,
    artifact_url: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
):
    url = url or DEFAULT_URL
    payload = {
        "file_name": file_name,
        "parser_used": parser_used,
        "success": success,
        "errors": errors,
        "warnings": warnings,
        "samples_parsed": samples_parsed,
        "duration_ms": duration_ms,
        "platform": platform.platform(),
        "artifact_url": artifact_url,
    }
    thread = threading.Thread(
        target=_post_json_sync, args=(url, payload, token), daemon=True
    )
    thread.start()


def _get_json_sync(url: str, token: Optional[str] = None, timeout: int = 5) -> Optional[Any]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        if _HAS_REQUESTS:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            LOGGER.debug("Patch fetch returned status: %s", resp.status_code)
            return None
        else:
            req = _urllib_request.Request(url, headers=headers, method="GET")
            with _urllib_request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                return json.loads(data.decode("utf-8"))
    except Exception as ex:
        LOGGER.debug("Patch fetch failed: %s", ex)
        return None


def fetch_pending_patches(url: Optional[str] = None, token: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch a list of pending patches from the telemetry server.

    Expected server response: JSON list of patch objects with at least:
      - id: opaque id
      - type: 'magic_variants' | 'config' | 'code'
      - created_by: str
      - description: str
      - content: dict
      - signature: optional (future)
    """
    base = (url or DEFAULT_URL).rstrip("/")
    endpoint = base.replace("/parse_reports", "/patches/pending")
    res = _get_json_sync(endpoint, token=token)
    if not res:
        return []
    if isinstance(res, list):
        return res
    # Some servers wrap results
    return res.get("patches", [])


def apply_patch(patch: Dict[str, Any], repo_root: Optional[str] = None) -> Dict[str, Any]:
    """Attempt to apply a patch safely and return a result dict.

    Supported patch types:
      - magic_variants: {'hex_values': ['0xDEADBEEF', '00AABBCC']}

    This will only modify `garmin_magic_variants.txt` and call
    `load_magic_hdrs_from_file`/`register_magic_hdr`. It will **not** apply
    arbitrary code patches. For code patches, the function will return a
    description to create a PR (manual review required).
    """
    repo_root = repo_root or os.getcwd()
    ptype = patch.get("type")
    pid = patch.get("id")
    result = {"id": pid, "applied": False, "reason": None}

    # Verify signature for safety-sensitive operations
    if not verify_patch_signature(patch):
        result["reason"] = "invalid or missing signature - not applied"
        return result

    if ptype == "magic_variants":
        content = patch.get("content") or {}
        hex_vals = content.get("hex_values") if isinstance(content, dict) else None
        if not hex_vals or not isinstance(hex_vals, list):
            result["reason"] = "invalid content"
            return result
        out_path = os.path.join(repo_root, "garmin_magic_variants.txt")
        # Read existing values
        existing = set()
        if os.path.exists(out_path):
            try:
                with open(out_path, 'r', encoding='utf-8') as fh:
                    for ln in fh:
                        ln = ln.strip().lower()
                        if not ln or ln.startswith('#'): continue
                        if ln.startswith('0x'):
                            ln = ln[2:]
                        try:
                            existing.add(int(ln, 16))
                        except Exception:
                            continue
            except Exception as ex:
                result["reason"] = f"failed to read existing file: {ex}"
                return result
        added = []
        for h in hex_vals:
            hs = str(h).strip().lower()
            if hs.startswith('0x'):
                hs = hs[2:]
            try:
                v = int(hs, 16)
            except Exception:
                continue
            if v not in existing:
                added.append(v)
                existing.add(v)
        if not added:
            result["reason"] = "no new values to add"
            return result
        # Append new values safely
        try:
            with open(out_path, 'a', encoding='utf-8') as fh:
                for v in added:
                    fh.write(f"0x{v:08X}\n")
                    register_magic_hdr(v)
            # Also reload to ensure load path covers everything
            load_magic_hdrs_from_file(out_path)
            result["applied"] = True
            result["added"] = [f"0x{v:08X}" for v in added]
            # Report application back to telemetry server
            try:
                report_patch_applied(pid, True, {"added": result["added"]})
            except Exception:
                pass
            return result
        except Exception as ex:
            result["reason"] = f"failed to write file: {ex}"
            # Report failure back to server
            try:
                report_patch_applied(pid, False, {"reason": result["reason"]})
            except Exception:
                pass
            return result

    # For code/config patches, return an informative message; require manual handling
    result["reason"] = f"unsupported patch type: {ptype} - manual review required"
    return result


def save_patch_locally(patch: Dict[str, Any], repo_root: Optional[str] = None) -> str:
    """Save a patch JSON to patches/pending/{id}.json under repo_root and return the path."""
    repo_root = repo_root or os.getcwd()
    pid = patch.get('id') or 'patch'
    target_dir = os.path.join(repo_root, 'patches', 'pending')
    os.makedirs(target_dir, exist_ok=True)
    out_path = os.path.join(target_dir, f'{pid}.json')
    with open(out_path, 'w', encoding='utf-8') as fh:
        json.dump(patch, fh, indent=2)
    return out_path


def submit_patch(patch: Dict[str, Any], url: Optional[str] = None, token: Optional[str] = None, timeout: int = 5) -> Optional[Dict[str, Any]]:
    """Submit a patch to the server for review. Returns server response JSON or None on failure."""
    base = (url or DEFAULT_URL).rstrip("/")
    endpoint = base.replace("/parse_reports", "/patches")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = json.dumps(patch).encode("utf-8")
    try:
        if _HAS_REQUESTS:
            resp = requests.post(endpoint, json=patch, headers=headers, timeout=timeout)
            if resp.status_code in (200, 201):
                return resp.json()
            LOGGER.debug("submit_patch returned status %s", resp.status_code)
            return None
        else:
            req = _urllib_request.Request(endpoint, data=payload, headers=headers, method="POST")
            with _urllib_request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                return json.loads(data.decode("utf-8"))
    except Exception as ex:
        LOGGER.debug("submit_patch failed: %s", ex)
        return None


def report_patch_applied(patch_id: str, applied: bool, details: Optional[dict] = None, url: Optional[str] = None, token: Optional[str] = None, timeout: int = 5) -> Optional[dict]:
    """Report back to the server that a patch was applied (or failed to apply)."""
    base = (url or DEFAULT_URL).rstrip("/")
    endpoint = base.replace("/parse_reports", f"/patches/{patch_id}/applied")
    payload = {"id": patch_id, "applied": bool(applied), "details": details or {}, "platform": platform.platform()}
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        if _HAS_REQUESTS:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=timeout)
            if resp.status_code in (200, 201):
                return resp.json()
            LOGGER.debug("report_patch_applied returned status %s", resp.status_code)
            return None
        else:
            req = _urllib_request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with _urllib_request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
    except Exception as ex:
        LOGGER.debug("report_patch_applied failed: %s", ex)
        return None


# Runtime error reporting -----------------------------------------------------
import uuid
import socket

SONARSNIFFER_TELEMETRY_ENABLE = os.environ.get("SONARSNIFFER_TELEMETRY_ENABLE", "true").lower() in ("1", "true", "yes")
SONARSNIFFER_TELEMETRY_TOKEN = os.environ.get("SONARSNIFFER_TELEMETRY_TOKEN")
SONARSNIFFER_TELEMETRY_SAMPLE_RATE = float(os.environ.get("SONARSNIFFER_TELEMETRY_SAMPLE_RATE", "1.0"))
SONARSNIFFER_TELEMETRY_MAX_ATTACHMENT_BYTES = int(os.environ.get("SONARSNIFFER_TELEMETRY_MAX_ATTACHMENT_BYTES", "65536"))

RUN_ID = os.environ.get("SONARSNIFFER_RUN_ID") or str(uuid.uuid4())


def _gather_system_info() -> dict:
    try:
        fqdn = socket.getfqdn()
    except Exception:
        fqdn = None
    return {
        "platform": platform.platform(),
        "node": platform.node(),
        "fqdn": fqdn,
        "python_version": platform.python_version(),
    }


def report_runtime_error(
    exc: Exception,
    feature_used: str = "unknown",
    processing_step: str = "unknown",
    details: Optional[dict] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
):
    """Report a runtime error (exceptions) to the telemetry endpoint.

    This is fire-and-forget and will not raise on failure. It attempts to capture
    a short traceback and any small log snippets (e.g., ffmpeg stderr) provided
    in details. Use env vars to configure destination and sampling.
    """
    try:
        if not SONARSNIFFER_TELEMETRY_ENABLE:
            LOGGER.debug("Telemetry disabled; skipping runtime error report")
            return None

        # Always send errors (no sampling) but respect the configured endpoint
        endpoint = (url or DEFAULT_URL).rstrip("/")
        endpoint = endpoint.replace("/parse_reports", "/runtime_errors")

        token = token or SONARSNIFFER_TELEMETRY_TOKEN

        trace = None
        try:
            import traceback

            trace = traceback.format_exc()
        except Exception:
            trace = str(exc)

        payload = {
            "run_id": RUN_ID,
            "feature_used": feature_used,
            "processing_step": processing_step,
            "error_message": str(exc),
            "stack_trace": trace,
            "platform": platform.platform(),
            "system": _gather_system_info(),
            "details": details or {},
        }

        # If details contains a path to a small log, read a tail snapshot
        try:
            if isinstance(details, dict):
                if "ffmpeg_error_log" in details:
                    p = details.get("ffmpeg_error_log")
                    if p and os.path.exists(p):
                        with open(p, 'rb') as fh:
                            fh.seek(0, os.SEEK_END)
                            size = fh.tell()
                            # Read last N bytes
                            read_bytes = min(size, SONARSNIFFER_TELEMETRY_MAX_ATTACHMENT_BYTES)
                            fh.seek(max(0, size - read_bytes))
                            snippet = fh.read().decode('utf-8', errors='ignore')
                            payload["ffmpeg_error_snippet"] = snippet
        except Exception:
            pass

        # Fire-and-forget thread
        th = threading.Thread(target=_post_json_sync, args=(endpoint, payload, token), daemon=True)
        th.start()
        LOGGER.info("Reported runtime error to telemetry endpoint: %s", endpoint)
    except Exception as ex:
        LOGGER.debug("report_runtime_error internal failure: %s", ex)
        return None
