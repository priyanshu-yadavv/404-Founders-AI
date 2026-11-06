#!/usr/bin/env python3
"""
404 FOUNDERS — Tokenizer Training Script
Trains an independent Custom BPE Tokenizer model from an input text corpus or JSONL file.
"""

import argparse
import sys
from pathlib import Path

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tokenizer import CustomBPETokenizer, TokenizerConfig


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train the 404 FOUNDERS Custom BPE Tokenizer from a text corpus."
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to training text or JSONL file.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="configs/tokenizer/tokenizer_model.json",
        help="Destination path for serialized tokenizer JSON artifact.",
    )
    parser.add_argument(
        "--vocab-size",
        type=int,
        default=512,
        help="Target vocabulary size (including special tokens).",
    )
    parser.add_argument(
        "--min-frequency",
        type=int,
        default=2,
        help="Minimum pair frequency threshold for merge generation.",
    )

    args = parser.parse_args()
    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading corpus from: {input_path}")
    corpus = []
    if input_path.suffix == ".jsonl":
        import json
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        obj = json.loads(line)
                        corpus.append(obj.get("content", obj.get("text", "")))
                    except json.JSONDecodeError:
                        pass
    else:
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    corpus.append(line.strip())

    print(f"Loaded {len(corpus):,} documents.")
    config = TokenizerConfig(vocab_size=args.vocab_size, min_frequency=args.min_frequency)
    tokenizer = CustomBPETokenizer(config=config)

    print(f"Training Custom BPE model (target vocab={args.vocab_size}, min_freq={args.min_frequency})...")
    tokenizer.train_from_iterator(corpus)

    out_path = Path(args.output)
    saved_path = tokenizer.save(out_path)
    print(f"Trained vocabulary size: {tokenizer.vocab_size:,}")
    print(f"Learned merge rules count: {len(tokenizer.merges):,}")
    print(f"Saved tokenizer artifact to: {saved_path}")


if __name__ == "__main__":
    main()
