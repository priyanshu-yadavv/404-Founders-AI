"""
Unit tests for CrossModalContextManager.
Verifies multi-turn multimodal interaction caching, memory-bounded history eviction,
cross-modal coreference resolution, and aggregated context representation.
"""

import pytest

from multimodal.context_manager import CrossModalContextManager, MultimodalContextTurn


@pytest.fixture
def context_mgr():
    return CrossModalContextManager()


def test_add_turn_and_history(context_mgr):
    turn = context_mgr.add_turn(
        user_query="Inspect this document",
        active_modalities=["DOCUMENT"],
        document_summary="System architecture specification v1.0",
        assistant_response="Document analyzed: 4 pages, zero vulnerabilities.",
    )

    assert isinstance(turn, MultimodalContextTurn)
    assert turn.turn_id == 1
    assert len(context_mgr.history) == 1
    assert turn.document_summary == "System architecture specification v1.0"


def test_bounded_history_eviction(context_mgr):
    # Add 15 turns; limit is 10
    for i in range(15):
        context_mgr.add_turn(
            user_query=f"Turn query {i+1}",
            active_modalities=["TEXT"],
            assistant_response=f"Answer {i+1}",
        )

    assert len(context_mgr.history) == 10
    # First turn in history should be turn 6 (1 to 5 evicted)
    assert context_mgr.history[0].turn_id == 6
    assert context_mgr.history[-1].turn_id == 15


def test_resolve_cross_modal_reference(context_mgr):
    context_mgr.add_turn(
        user_query="Analyze this photo",
        active_modalities=["IMAGE"],
        image_caption="A Dell Latitude 5400 workstation running Linux kernel.",
    )
    context_mgr.add_turn(
        user_query="Read this PDF report",
        active_modalities=["DOCUMENT"],
        document_summary="Quarterly financial audit report.",
    )

    # Reference to the image
    img_ref = context_mgr.resolve_cross_modal_reference("What was shown in the picture?")
    assert img_ref is not None
    assert img_ref["matched_modality"] == "IMAGE"
    assert "Dell Latitude" in img_ref["artifact_context"]

    # Reference to the document
    doc_ref = context_mgr.resolve_cross_modal_reference("Explain the document")
    assert doc_ref is not None
    assert doc_ref["matched_modality"] == "DOCUMENT"
    assert "financial audit" in doc_ref["artifact_context"]

    # Unrelated query without media references
    no_ref = context_mgr.resolve_cross_modal_reference("Hello, how are you?")
    assert no_ref is None


def test_aggregated_context(context_mgr):
    context_mgr.add_turn(
        user_query="Analyze speech",
        active_modalities=["AUDIO"],
        audio_transcript="Hello from 404 FOUNDERS voice engine.",
    )
    summary = context_mgr.get_aggregated_context()
    assert "Turn 1" in summary
    assert "AUDIO" in summary
    assert "voice engine" in summary
