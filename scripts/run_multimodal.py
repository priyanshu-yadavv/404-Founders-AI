#!/usr/bin/env python3
"""
404 FOUNDERS — Developer Multimodal CLI Utility
Command-line driver for inspecting, preprocessing, and fusing Text, Image, Audio,
Speech, Video, and Document modalities.
"""

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from multimodal.modality_router import ModalityRouter


def print_banner() -> None:
    print("=" * 72)
    print("  404 FOUNDERS — Phase 08 Multimodal Intelligence System")
    print("  Tagline: Intelligence Without Boundaries.")
    print("=" * 72)


def list_capabilities() -> None:
    print("\n[SUPPORTED MODALITIES & PROCESSORS]")
    capabilities = [
        ("Text Intelligence", "English, Hindi (Devanagari), code, long-doc chunking, extractive QA"),
        ("Image Intelligence", "PNG, JPEG, WEBP, BMP, magic bytes validation, ViT patch extraction"),
        ("Audio Intelligence", "WAV, MP3, FLAC, OGG, M4A, STFT spectrograms, RMS energy, SNR"),
        ("Speech Recognition", "English & Hindi transcription, timestamped speech segmentation"),
        ("Speech Generation", "Text-to-speech formant synthesis, playable WAV audio generation"),
        ("Video Intelligence", "MP4, MOV, WEBM, bounded streaming, keyframe selection, scene transitions"),
        ("Document Intelligence", "PDF, DOCX, CSV, JSON, Markdown, TXT, prompt injection auditing"),
        ("Multimodal Fusion", "Early (concat), Intermediate (cross-attention), Late (adaptive gating)"),
    ]
    for idx, (name, desc) in enumerate(capabilities, 1):
        print(f"  {idx}. {name:<22} | {desc}")
    print("\nSecurity Invariants: Untrusted file boundary; prompt injection scans; zero external API leaks.\n")


def run_cli() -> None:
    parser = argparse.ArgumentParser(description="404 FOUNDERS Multimodal Intelligence CLI Driver")
    parser.add_argument("--text", "-t", type=str, help="Text query or prompt")
    parser.add_argument("--image", "-i", type=str, help="Path to image file (PNG, JPEG, WEBP, BMP)")
    parser.add_argument("--audio", "-a", type=str, help="Path to audio file (WAV, MP3, FLAC, OGG)")
    parser.add_argument("--video", "-v", type=str, help="Path to video file (MP4, MOV, WEBM)")
    parser.add_argument("--document", "-d", type=str, help="Path to document file (PDF, DOCX, CSV, TXT, MD)")
    parser.add_argument("--speech-tts", type=str, help="Text string to synthesize into spoken audio (TTS)")
    parser.add_argument("--output-wav", type=str, default="synthesized_speech.wav", help="Output path for synthesized audio")
    parser.add_argument("--fuse", action="store_true", help="Execute multi-stage multimodal fusion across provided inputs")
    parser.add_argument("--fusion-stage", type=str, default="EARLY", choices=["EARLY", "INTERMEDIATE", "LATE"], help="Fusion stage")
    parser.add_argument("--list-modalities", action="store_true", help="List all supported modalities and formats")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")

    args = parser.parse_args()

    if args.list_modalities or len(sys.argv) == 1:
        print_banner()
        list_capabilities()
        if len(sys.argv) == 1:
            print("Use --help to view available modality flags.")
        return

    router = ModalityRouter()

    # Direct TTS mode
    if args.speech_tts:
        print_banner()
        print(f"\n[SPEECH SYNTHESIS]: '{args.speech_tts}'")
        res_tts = router.speech_generator.synthesize(args.speech_tts)
        out_path = Path(args.output_wav)
        out_path.write_bytes(res_tts.audio_bytes)
        print(f"Generated {res_tts.duration_seconds}s WAV audio -> Saved to: {out_path.resolve()}")
        return

    # Load file payloads
    img_bytes = Path(args.image).read_bytes() if args.image else None
    aud_bytes = Path(args.audio).read_bytes() if args.audio else None
    vid_path = Path(args.video) if args.video else None
    doc_bytes = Path(args.document).read_bytes() if args.document else None

    filename_hints = {}
    if args.image:
        filename_hints["image"] = Path(args.image).name
    if args.audio:
        filename_hints["audio"] = Path(args.audio).name
    if args.video:
        filename_hints["video"] = Path(args.video).name
    if args.document:
        filename_hints["document"] = Path(args.document).name

    res = router.route_and_process(
        text=args.text,
        image_data=img_bytes,
        audio_data=aud_bytes,
        video_data=vid_path,
        document_data=doc_bytes,
        filename_hints=filename_hints,
        perform_fusion=args.fuse,
        fusion_stage=args.fusion_stage,
    )

    if args.json:
        out_dict = {
            "primary_modality": res.detection.primary_modality,
            "active_modalities": res.detection.active_modalities,
            "is_multimodal": res.detection.is_multimodal,
            "summary": res.combined_response_summary,
            "text": res.text_result.summary if res.text_result else None,
            "image": res.image_result.caption_hypothesis if res.image_result else None,
            "audio": res.audio_result.summary if res.audio_result else None,
            "video": res.video_result.video_summary if res.video_result else None,
            "document": res.document_result.summary if res.document_result else None,
            "document_safe": res.document_result.security_report.is_safe if res.document_result else None,
        }
        print(json.dumps(out_dict, indent=2))
    else:
        print_banner()
        print(f"\n[ACTIVE MODALITIES]: {', '.join(res.detection.active_modalities)}")
        print(f"[PRIMARY MODALITY]: {res.detection.primary_modality}")
        print(f"\n[SUMMARY]:\n{res.combined_response_summary}")
        if res.document_result:
            sec = res.document_result.security_report
            print(f"\n[DOCUMENT SECURITY AUDIT]: {'SAFE' if sec.is_safe else 'ALERT: INJECTION RISK'}")
        if res.fusion_output:
            print(f"\n[MULTIMODAL FUSION]: Stage={res.fusion_output.fusion_stage}, Tensor Shape={list(res.fusion_output.fused_representation.shape)}")
        print("\n" + "=" * 72)


if __name__ == "__main__":
    run_cli()
