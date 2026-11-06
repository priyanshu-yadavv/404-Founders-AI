"""
404 FOUNDERS — Projection & Transformation Layers
Implements input projection, output projection, and gated SwiGLU feature transformations.
"""

from typing import Optional, Tuple
import math
import torch
import torch.nn as nn
import torch.nn.functional as F

from core.exceptions import ShapeMismatchError


class InputProjectionLayer(nn.Module):
    """
    Projects raw discrete token identifiers or continuous modality vectors
    into the internal latent representation space (d_model).
    Supports dual modes:
    1. Discrete token embedding lookup (when input is LongTensor)
    2. Continuous linear projection (when input is FloatTensor)
    """

    def __init__(
        self,
        d_model: int,
        vocab_size: Optional[int] = None,
        input_dim: Optional[int] = None,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size
        self.input_dim = input_dim

        if vocab_size is not None:
            self.embedding = nn.Embedding(vocab_size, d_model)
            # Standard initialization for embeddings
            nn.init.normal_(self.embedding.weight, mean=0.0, std=1.0 / math.sqrt(d_model))
        else:
            self.embedding = None

        if input_dim is not None:
            self.linear = nn.Linear(input_dim, d_model, bias=False)
            nn.init.normal_(self.linear.weight, mean=0.0, std=1.0 / math.sqrt(input_dim))
        else:
            self.linear = None

        if self.embedding is None and self.linear is None:
            raise ValueError("Either vocab_size or input_dim must be provided to InputProjectionLayer.")

        self.dropout = nn.Dropout(dropout) if dropout > 0.0 else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Project inputs into hidden dimension d_model.
        Args:
            x: Tensor of shape (batch, seq_len) for token IDs or (batch, seq_len, input_dim)
        Returns:
            Projected tensor of shape (batch, seq_len, d_model)
        """
        if x.dtype in (torch.int64, torch.int32):
            if self.embedding is None:
                raise ValueError("Received integer tokens but no vocab_size/embedding was configured.")
            out = self.embedding(x) * math.sqrt(self.d_model)
        elif x.is_floating_point():
            if self.linear is None:
                # If continuous input matches d_model directly
                if x.shape[-1] == self.d_model:
                    out = x
                else:
                    raise ShapeMismatchError(
                        f"Input dimension {x.shape[-1]} does not match d_model {self.d_model} and no linear projection configured."
                    )
            else:
                out = self.linear(x)
        else:
            raise TypeError(f"Unsupported input tensor dtype: {x.dtype}")

        return self.dropout(out)


class OutputProjectionLayer(nn.Module):
    """
    Unembeds hidden states back into target output logits.
    """

    def __init__(self, d_model: int, output_dim: int, bias: bool = False) -> None:
        super().__init__()
        self.d_model = d_model
        self.output_dim = output_dim
        self.linear = nn.Linear(d_model, output_dim, bias=bias)
        # Small standard deviation initialization for stable output bounds
        nn.init.normal_(self.linear.weight, mean=0.0, std=1.0 / math.sqrt(d_model))
        if bias and self.linear.bias is not None:
            nn.init.zeros_(self.linear.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Unembed representations.
        Args:
            x: Tensor of shape (batch, seq_len, d_model)
        Returns:
            Logits of shape (batch, seq_len, output_dim)
        """
        if x.shape[-1] != self.d_model:
            raise ShapeMismatchError(
                f"Expected last dimension {self.d_model}, got {x.shape[-1]}"
            )
        return self.linear(x)


class FeatureTransformationLayer(nn.Module):
    """
    Gated SwiGLU Feed-Forward Network.
    Computes:
        SwiGLU(x) = (SiLU(x @ W_gate) * (x @ W_up)) @ W_down
    where intermediate dimension is typically (4 * d_model * 2 / 3) rounded to multiple of 64.
    """

    def __init__(
        self,
        d_model: int,
        intermediate_dim: Optional[int] = None,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.d_model = d_model
        # Calculate standard 8/3 expansion for SwiGLU if unspecified
        if intermediate_dim is None:
            raw_dim = int(2 * d_model * 4 / 3)
            # Round up to nearest multiple of 64 for vector alignment
            intermediate_dim = ((raw_dim + 63) // 64) * 64
        self.intermediate_dim = intermediate_dim

        self.w_gate = nn.Linear(d_model, intermediate_dim, bias=False)
        self.w_up = nn.Linear(d_model, intermediate_dim, bias=False)
        self.w_down = nn.Linear(intermediate_dim, d_model, bias=False)

        # Scale-aware Gaussian initialization
        std_in = 1.0 / math.sqrt(d_model)
        std_out = 1.0 / math.sqrt(intermediate_dim)
        nn.init.normal_(self.w_gate.weight, mean=0.0, std=std_in)
        nn.init.normal_(self.w_up.weight, mean=0.0, std=std_in)
        nn.init.normal_(self.w_down.weight, mean=0.0, std=std_out)

        self.dropout = nn.Dropout(dropout) if dropout > 0.0 else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Execute gated forward transformation.
        Args:
            x: Tensor of shape (batch, seq_len, d_model)
        Returns:
            Transformed tensor of shape (batch, seq_len, d_model)
        """
        if x.shape[-1] != self.d_model:
            raise ShapeMismatchError(f"Expected d_model {self.d_model}, got {x.shape[-1]}")
        gate = F.silu(self.w_gate(x))
        up = self.w_up(x)
        activated = gate * up
        down = self.w_down(self.dropout(activated))
        return down
