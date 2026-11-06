#!/usr/bin/env python3
"""
404 FOUNDERS — Tokenizer Encoding Script
Encodes text using a trained Custom BPE Tokenizer model and prints token IDs.
"""

import argparse
import sys
from pathlib import Path

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tokenizer import CustomBPETokenizer


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Encode text using a trained 404 FOUNDERS Custom BPE Tokenizer."
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Path to serialized tokenizer JSON model.",
    )
    parser.add_argument(
        "--text",
        type=str,
        help="Input text string to encode.",
    )
    parser.add_argument(
        "--add-bos",
        action="store_true",
        help="Prepend <bos> token.",
    )
    parser.add_argument(
        "--add-eos",
        action="store_true",
        help="Append <eos> token.",
    )

    args = parser.parse_args()
    model_path = Path(args.model)
    if not model_path.is_file():
        print(f"Error: Tokenizer model not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    tokenizer = CustomBPETokenizer.load(model_path)
    input_text = args.text
    if input_text is None:
        input_text = sys.stdin.read().strip()

    result = tokenizer.encode(input_text, add_bos=args.add_bos, add_eos=args.add_eos)
    print(f"Tokens ({len(result.tokens)}): {result.tokens}")
    print(f"Token IDs ({len(result.ids)}): {result.ids}")


if __name__ == "__main__":
    main()
