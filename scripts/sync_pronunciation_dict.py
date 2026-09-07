#!/usr/bin/env python3
"""
Sync the Google Doc pronunciation dictionary to Sarvam AI.

Fetches the publicly-shared Google Doc, parses the Original → Phonetic
table, and uploads it to Sarvam's pronunciation dictionary API via PUT.

Usage:
    # Preview what would be uploaded (no API call):
    python scripts/sync_pronunciation_dict.py --dry-run

    # Sync to Sarvam:
    python scripts/sync_pronunciation_dict.py

Environment variables:
    SARVAM_API_KEY                - required
    SARVAM_PRONUNCIATION_DICT_ID  - required (e.g. p_fc28888a)
"""

import argparse
import io
import json
import os
import re
import sys
import tempfile

import httpx
from dotenv import load_dotenv

load_dotenv()

# The Google Doc is shared as "anyone with the link".
_DOC_ID = "184qac6JB5AOCSGdHZyYJCLa-Hg6hmtZ9q0YPGaCn7JY"
_EXPORT_URL = f"https://docs.google.com/document/d/{_DOC_ID}/export?format=txt"

_SARVAM_DICT_URL = "https://api.sarvam.ai/text-to-speech/pronunciation-dictionary"

# These terms are mostly English tech words, but they appear in translated
# scripts too (code identifiers stay in English).  Registering them under
# every language Bulbul supports means they're corrected regardless of the
# target_language_code sent with each TTS request.
_ALL_LANGUAGES = [
    "en-IN", "hi-IN", "ta-IN", "te-IN", "mr-IN",
    "bn-IN", "kn-IN", "gu-IN", "ml-IN", "pa-IN", "od-IN",
]


def fetch_doc() -> str:
    """Download the Google Doc as plain text."""
    print(f"📥 Fetching Google Doc …")
    resp = httpx.get(_EXPORT_URL, follow_redirects=True, timeout=15)
    resp.raise_for_status()
    text = resp.text
    print(f"   ✓ {len(text)} bytes")
    return text


def parse_entries(raw: str) -> dict[str, str]:
    """
    Parse alternating-line Original / Phonetic pairs from the Google Doc.

    The text export puts each cell on its own tab-prefixed line:
        \\tData
        \\tDayta / Deyta
        \\tVariation
        \\tWayriation / Way-riation

    When the doc lists alternatives separated by '/', the first option is
    used (it's typically the one the team settled on).  Lines that look
    like notes rather than phonetic replacements are skipped.
    """
    entries = {}

    # Collect all tab-prefixed content lines, skipping the header and title
    cells = []
    header_seen = False
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Skip BOM, title, and lines without tab prefix
        if not line.startswith("\t"):
            # Mark when we've seen the header section
            if "original" in stripped.lower() or "phonetic" in stripped.lower():
                header_seen = True
            continue
        # Skip header cells themselves
        if not header_seen:
            if "original" in stripped.lower() or "phonetic" in stripped.lower():
                header_seen = True
                continue
        if "original spelling" in stripped.lower() or "phonetic spelling" in stripped.lower():
            continue
        cells.append(stripped)

    # Pair up: cells[0]=original, cells[1]=phonetic, cells[2]=original, …
    for i in range(0, len(cells) - 1, 2):
        original = cells[i].strip()
        phonetic = cells[i + 1].strip()

        if not original or not phonetic:
            continue

        # Skip notes (sentences longer than ~50 chars, or that read like
        # instructions rather than phonetic replacements)
        if len(phonetic) > 50 or re.search(r"\bshould\b|\bmust\b|\bnote\b", phonetic, re.I):
            print(f"   ⚠ Skipping note-like entry: {original!r} → {phonetic!r}")
            continue

        # Take the first alternative before '/'
        phonetic = phonetic.split("/")[0].strip()

        if not phonetic:
            continue

        entries[original] = phonetic

    return entries


def build_sarvam_json(entries: dict[str, str]) -> dict:
    """
    Build the JSON structure Sarvam's pronunciation dictionary API expects.

    Maps every entry to all supported languages so corrections apply
    regardless of which language the TTS request uses.
    """
    pronunciations = {}
    for lang in _ALL_LANGUAGES:
        pronunciations[lang] = dict(entries)

    return {"pronunciations": pronunciations}


def upload_to_sarvam(payload: dict, api_key: str, dict_id: str) -> dict:
    """PUT the pronunciation JSON to Sarvam's API as a multipart file upload."""

    print(f"\n📤 Uploading to Sarvam (dict_id={dict_id}) …")

    # Sarvam expects a multipart file upload with the JSON as a file
    json_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp.write(json_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            resp = httpx.put(
                _SARVAM_DICT_URL,
                params={"dict_id": dict_id},
                headers={"api-subscription-key": api_key},
                files={"file": ("pronunciation_dict.json", f, "application/json")},
                timeout=30,
            )
        resp.raise_for_status()
        result = resp.json()
        print(f"   ✓ Updated successfully")
        return result
    finally:
        os.unlink(tmp_path)


def main():
    parser = argparse.ArgumentParser(
        description="Sync Google Doc pronunciation dictionary to Sarvam AI"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and display the dictionary without uploading",
    )
    args = parser.parse_args()

    # --- Fetch & parse ---
    raw = fetch_doc()
    entries = parse_entries(raw)

    if not entries:
        print("❌ No entries parsed from the document")
        sys.exit(1)

    print(f"\n📖 Parsed {len(entries)} entries:")
    for original, phonetic in entries.items():
        print(f"   {original:20s} → {phonetic}")

    # --- Build payload ---
    payload = build_sarvam_json(entries)

    if args.dry_run:
        print(f"\n🔍 Dry run — JSON that would be uploaded:")
        # Show just the en-IN slice to avoid wall of text
        preview = {"pronunciations": {"en-IN": payload["pronunciations"]["en-IN"]}}
        print(json.dumps(preview, indent=2, ensure_ascii=False))
        print(f"\n   (× {len(_ALL_LANGUAGES)} languages)")
        print("   Pass without --dry-run to upload.")
        return

    # --- Upload ---
    api_key = os.getenv("SARVAM_API_KEY")
    dict_id = os.getenv("SARVAM_PRONUNCIATION_DICT_ID")

    if not api_key:
        print("❌ SARVAM_API_KEY not set")
        sys.exit(1)
    if not dict_id:
        print("❌ SARVAM_PRONUNCIATION_DICT_ID not set")
        sys.exit(1)

    result = upload_to_sarvam(payload, api_key, dict_id)
    print(f"\n✅ Sarvam dictionary {dict_id} synced with {len(entries)} entries")


if __name__ == "__main__":
    main()
