"""
404 FOUNDERS — Multimodal Fusion Engine
Implements hybrid multi-stage fusion:
- Early Fusion: Modality projection & sequence-level concatenation with modality embeddings.
- Intermediate Fusion: Cross-modal attention layer with LayerScale and RMSNorm.
- Late Fusion: Decision-level gating and confidence pooling across active streams.
"""

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

from neural_architecture.layers.normalization import CustomRMSNorm


class ModalityType(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"


@dataclass
class MultimodalInput:
    """Encapsulates modality tensor payloads and presence flags."""
    text_tensor: Optional[torch.Tensor] = None       # Shape: (batch, seq_len, d_model) or (batch, seq_len)
    image_tensor: Optional[torch.Tensor] = None      # Shape: (batch, num_patches, d_model)
    audio_tensor: Optional[torch.Tensor] = None      # Shape: (batch, time_steps, d_model)
    video_tensor: Optional[torch.Tensor] = None      # Shape: (batch, num_frames, d_model)
    document_tensor: Optional[torch.Tensor] = None   # Shape: (batch, num_chunks, d_model)
    active_modalities: List[ModalityType] = field(default_factory=list)
    alignment_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FusionOutput:
    """Output representation from multi-stage fusion."""
    fused_representation: torch.Tensor             # Shape: (batch, fused_len, d_model) or (batch, d_model)
    fusion_stage: str                              # "EARLY", "INTERMEDIATE", "LATE"
    active_modalities: List[str]
    missing_modalities: List[str]
    modality_weights: Dict[str, float]
    metadata: Dict[str, Any]


class EarlyFusionLayer(nn.Module):
    """
    Early Fusion Layer.
    Maps heterogeneous modality features into a shared embedding dimension,
    adds learned modality segment embeddings, and concatenates along sequence length.
    """

    def __init__(self, d_model: int = 128) -> None:
        super().__init__()
        self.d_model = d_model
        # 5 Modality type embeddings (TEXT=0, IMAGE=1, AUDIO=2, VIDEO=3, DOCUMENT=4)
        self.modality_embeddings = nn.Embedding(5, d_model)

        # Modality projection adapters if inputs are in raw feature dims
        self.image_projector = nn.Linear(768, d_model, bias=False)  # 16x16 patch * 3 = 768
        self.audio_projector = nn.Linear(257, d_model, bias=False)  # STFT 512 / 2 + 1 = 257
        self.video_projector = nn.Linear(768, d_model, bias=False)

    def forward(self, inputs: MultimodalInput) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Concatenate available modality sequences.
        Returns:
            fused_sequence: (batch, total_seq_len, d_model)
            attention_mask: (batch, total_seq_len)
        """
        batch_size = 1
        device = torch.device("cpu")
        sequences: List[torch.Tensor] = []
        masks: List[torch.Tensor] = []

        mod_indices = {
            ModalityType.TEXT: 0,
            ModalityType.IMAGE: 1,
            ModalityType.AUDIO: 2,
            ModalityType.VIDEO: 3,
            ModalityType.DOCUMENT: 4,
        }

        # 1. Text
        if inputs.text_tensor is not None:
            t = inputs.text_tensor
            device = t.device
            batch_size = t.shape[0]
            if t.dim() == 2:
                # Token IDs: project to d_model via simple embedding-like projection or one-hot
                t = F.one_hot(t.long() % self.d_model, num_classes=self.d_model).float()
            elif t.shape[-1] != self.d_model:
                t = F.interpolate(t.unsqueeze(1), size=(t.shape[1], self.d_model)).squeeze(1)

            t = t + self.modality_embeddings(torch.tensor(mod_indices[ModalityType.TEXT], device=device))
            sequences.append(t)
            masks.append(torch.ones((batch_size, t.shape[1]), device=device))

        # 2. Image
        if inputs.image_tensor is not None:
            img = inputs.image_tensor
            device = img.device
            batch_size = img.shape[0]
            if img.shape[-1] == 768:
                img = self.image_projector(img)
            elif img.shape[-1] != self.d_model:
                img = nn.Linear(img.shape[-1], self.d_model, bias=False).to(device)(img)

            img = img + self.modality_embeddings(torch.tensor(mod_indices[ModalityType.IMAGE], device=device))
            sequences.append(img)
            masks.append(torch.ones((batch_size, img.shape[1]), device=device))

        # 3. Audio
        if inputs.audio_tensor is not None:
            aud = inputs.audio_tensor
            device = aud.device
            batch_size = aud.shape[0]
            if aud.shape[-1] == 257:
                aud = self.audio_projector(aud)
            elif aud.shape[-1] != self.d_model:
                aud = nn.Linear(aud.shape[-1], self.d_model, bias=False).to(device)(aud)

            aud = aud + self.modality_embeddings(torch.tensor(mod_indices[ModalityType.AUDIO], device=device))
            sequences.append(aud)
            masks.append(torch.ones((batch_size, aud.shape[1]), device=device))

        # 4. Video
        if inputs.video_tensor is not None:
            vid = inputs.video_tensor
            device = vid.device
            batch_size = vid.shape[0]
            if vid.shape[-1] == 768:
                vid = self.video_projector(vid)
            elif vid.shape[-1] != self.d_model:
                vid = nn.Linear(vid.shape[-1], self.d_model, bias=False).to(device)(vid)

            vid = vid + self.modality_embeddings(torch.tensor(mod_indices[ModalityType.VIDEO], device=device))
            sequences.append(vid)
            masks.append(torch.ones((batch_size, vid.shape[1]), device=device))

        if not sequences:
            # Fallback zero token
            empty_seq = torch.zeros((batch_size, 1, self.d_model), device=device)
            empty_mask = torch.zeros((batch_size, 1), device=device)
            return empty_seq, empty_mask

        fused_seq = torch.cat(sequences, dim=1)
        fused_mask = torch.cat(masks, dim=1)

        return fused_seq, fused_mask


class CrossModalAttentionFusion(nn.Module):
    """
    Intermediate Fusion Layer.
    Implements multi-head cross-attention bridging primary and secondary modalities
    with pre-RMSNorm and LayerScale residual stabilization.
    """

    def __init__(self, d_model: int = 128, n_heads: int = 4) -> None:
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads

        self.norm_q = CustomRMSNorm(d_model)
        self.norm_kv = CustomRMSNorm(d_model)

        self.q_proj = nn.Linear(d_model, d_model, bias=False)
        self.k_proj = nn.Linear(d_model, d_model, bias=False)
        self.v_proj = nn.Linear(d_model, d_model, bias=False)
        self.out_proj = nn.Linear(d_model, d_model, bias=False)

        # LayerScale parameter initialized to 0.1 for smooth residual warmup
        self.gamma = nn.Parameter(torch.ones(d_model) * 0.1)

    def forward(
        self,
        x_target: torch.Tensor,
        x_source: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Cross-attend from x_target (Query) to x_source (Key/Value).
        Args:
            x_target: (batch, seq_len_q, d_model)
            x_source: (batch, seq_len_kv, d_model)
        Returns:
            fused_target: (batch, seq_len_q, d_model)
        """
        b, t_q, _ = x_target.shape
        _, t_kv, _ = x_source.shape

        q = self.q_proj(self.norm_q(x_target)).view(b, t_q, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(self.norm_kv(x_source)).view(b, t_kv, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(self.norm_kv(x_source)).view(b, t_kv, self.n_heads, self.head_dim).transpose(1, 2)

        # Scaled dot-product attention
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.head_dim)
        if attention_mask is not None:
            # Expand mask: (b, 1, 1, t_kv)
            mask_expanded = attention_mask.view(b, 1, 1, t_kv)
            scores = scores.masked_fill(mask_expanded == 0, float("-inf"))

        attn_weights = F.softmax(scores, dim=-1)
        attn_out = torch.matmul(attn_weights, v)  # (b, n_heads, t_q, head_dim)
        attn_out = attn_out.transpose(1, 2).contiguous().view(b, t_q, self.d_model)

        # LayerScale + Residual
        return x_target + self.gamma * self.out_proj(attn_out)


class LateFusionAggregator(nn.Module):
    """
    Late Fusion Layer.
    Combines pooled representations or prediction vectors from independent modality streams
    using learned softmax attention gating weights.
    """

    def __init__(self, d_model: int = 128, num_modalities: int = 4) -> None:
        super().__init__()
        self.d_model = d_model
        self.num_modalities = num_modalities
        self.gate = nn.Linear(d_model, 1, bias=False)

    def forward(self, modality_representations: List[torch.Tensor]) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Pool representations and compute adaptive gating weights.
        Args:
            modality_representations: List of tensors, each of shape (batch, d_model)
        Returns:
            fused_representation: (batch, d_model)
            modality_weights: (batch, num_active_modalities)
        """
        if not modality_representations:
            raise ValueError("No modality representations provided for late fusion.")

        # Stack pooled vectors: (batch, k, d_model)
        stacked = torch.stack(modality_representations, dim=1)
        # Compute scalar score per modality: (batch, k, 1)
        scores = self.gate(stacked)
        weights = F.softmax(scores, dim=1)  # (batch, k, 1)

        fused = torch.sum(stacked * weights, dim=1)  # (batch, d_model)
        return fused, weights.squeeze(-1)


class MultimodalFusionEngine(nn.Module):
    """
    Central Multimodal Fusion Engine.
    Executes early, intermediate, and late multi-stage fusion across
    Text, Image, Audio, Video, and Document modalities.
    """

    def __init__(self, d_model: int = 128, n_heads: int = 4) -> None:
        super().__init__()
        self.d_model = d_model
        self.early_fusion = EarlyFusionLayer(d_model=d_model)
        self.intermediate_fusion = CrossModalAttentionFusion(d_model=d_model, n_heads=n_heads)
        self.late_fusion = LateFusionAggregator(d_model=d_model)

    def fuse(
        self,
        inputs: MultimodalInput,
        stage: str = "EARLY",
    ) -> FusionOutput:
        """
        Execute multi-stage multimodal fusion across provided streams.
        Args:
            inputs: MultimodalInput dataclass with available modality tensors
            stage: "EARLY", "INTERMEDIATE", or "LATE"
        Returns:
            FusionOutput dataclass
        """
        stage_upper = stage.upper()
        active: List[str] = []
        if inputs.text_tensor is not None:
            active.append("TEXT")
        if inputs.image_tensor is not None:
            active.append("IMAGE")
        if inputs.audio_tensor is not None:
            active.append("AUDIO")
        if inputs.video_tensor is not None:
            active.append("VIDEO")
        if inputs.document_tensor is not None:
            active.append("DOCUMENT")

        all_mods = ["TEXT", "IMAGE", "AUDIO", "VIDEO", "DOCUMENT"]
        missing = [m for m in all_mods if m not in active]

        if not active:
            raise ValueError("Cannot perform multimodal fusion: all input modality tensors are None.")

        weights_dict: Dict[str, float] = {}

        if stage_upper == "EARLY":
            fused_seq, mask = self.early_fusion(inputs)
            # Uniform initial weights across active modalities
            w = round(1.0 / len(active), 3)
            weights_dict = {m: w for m in active}
            return FusionOutput(
                fused_representation=fused_seq,
                fusion_stage="EARLY",
                active_modalities=active,
                missing_modalities=missing,
                modality_weights=weights_dict,
                metadata={"total_sequence_length": fused_seq.shape[1], "mask_sum": int(mask.sum().item())},
            )

        elif stage_upper == "INTERMEDIATE":
            # Intermediate cross-attention: primary target attends to secondary
            early_seq, _ = self.early_fusion(inputs)
            # Split early sequence in half or attend early_seq onto itself
            fused_rep = self.intermediate_fusion(early_seq, early_seq)
            w = round(1.0 / len(active), 3)
            weights_dict = {m: w for m in active}
            return FusionOutput(
                fused_representation=fused_rep,
                fusion_stage="INTERMEDIATE",
                active_modalities=active,
                missing_modalities=missing,
                modality_weights=weights_dict,
                metadata={"cross_attention_heads": self.intermediate_fusion.n_heads},
            )

        elif stage_upper == "LATE":
            # Pool each active modality sequence to (batch, d_model)
            pooled_reps: List[torch.Tensor] = []
            if inputs.text_tensor is not None:
                pooled_reps.append(inputs.text_tensor.mean(dim=1) if inputs.text_tensor.dim() == 3 else inputs.text_tensor)
            if inputs.image_tensor is not None:
                pooled_reps.append(inputs.image_tensor.mean(dim=1))
            if inputs.audio_tensor is not None:
                pooled_reps.append(inputs.audio_tensor.mean(dim=1))
            if inputs.video_tensor is not None:
                pooled_reps.append(inputs.video_tensor.mean(dim=1))
            if inputs.document_tensor is not None:
                pooled_reps.append(inputs.document_tensor.mean(dim=1))

            # Ensure all pooled tensors have shape (batch, d_model)
            normalized_pooled = []
            for rep in pooled_reps:
                if rep.shape[-1] != self.d_model:
                    proj = nn.Linear(rep.shape[-1], self.d_model, bias=False).to(rep.device)
                    rep = proj(rep)
                normalized_pooled.append(rep)

            fused_vec, late_weights = self.late_fusion(normalized_pooled)
            w_list = late_weights[0].tolist() if late_weights.dim() >= 2 else late_weights.tolist()
            if isinstance(w_list, float):
                w_list = [w_list]
            weights_dict = {m: round(w, 4) for m, w in zip(active, w_list)}

            return FusionOutput(
                fused_representation=fused_vec,
                fusion_stage="LATE",
                active_modalities=active,
                missing_modalities=missing,
                modality_weights=weights_dict,
                metadata={"late_fusion_pooling": "adaptive_gate"},
            )

        else:
            raise ValueError(f"Invalid fusion stage: '{stage}'. Must be 'EARLY', 'INTERMEDIATE', or 'LATE'.")
