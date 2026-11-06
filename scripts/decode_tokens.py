#!/usr/bin/env python3
"""
404 FOUNDERS — Tokenizer Decoding Script
Decodes a sequence of integer token IDs back into plain text.
"""

import argparse
import sys
from pathlib import Path

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tokenizer import CustomBPETokenizer


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Decode token IDs using a trained 404 FOUNDERS Custom BPE Tokenizer."
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Path to serialized tokenizer JSON model.",
    )
    parser.add_argument(
        "--ids",
        type=str,
        required=True,
        help="Comma-separated or space-separated token IDs (e.g. '2,71,73,85,3').",
    )
    parser.add_argument(
        "--keep-special",
        action="store_true",
        help="Retain special tokens in decoded string.",
    )

    args = parser.parse_args()
    model_path = Path(args.model)
    if not model_path.is_file():
        print(f"Error: Tokenizer model not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    tokenizer = CustomBPETokenizer.load(model_path)
    clean_ids_str = args.ids.replace(",", " ")
    token_ids = [int(x) for x in clean_ids_str.split() if x.strip().isdigit()]

    decoded_text = tokenizer.decode(token_ids, skip_special_tokens=not args.keep_special)
    print("Decoded Text:")
    print(decoded_text)


if __name__ == "__main__":
    main()
