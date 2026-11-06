"""
404 FOUNDERS — Inference Engine
Provides a robust, validated execution harness for the experimental neural core.
"""

from typing import Any, Dict, List, Optional
import torch

from core.exceptions import ArchitectureError, ShapeMismatchError
from core.intelligence.neural_core import NeuralCore, NeuralCoreConfig
from neural_architecture.interfaces import ModelOutput


class InferenceEngine:
    """
    Inference runtime interface for the experimental NeuralCore model.
    Handles:
    - Input shape and vocabulary range validation
    - Deterministic evaluation mode
    - Output tensor numerical validation (NaN / Inf protection)
    - Error translation and structured reporting
    """

    def __init__(
        self,
        model: Optional[NeuralCore] = None,
        config: Optional[NeuralCoreConfig] = None,
    ) -> None:
        self.model = model or NeuralCore(config=config)
        self.config = self.model.config
        # Ensure model is in evaluation mode
        self.model.eval()

    def validate_inputs(self, input_ids: Any) -> torch.Tensor:
        """
        Validate and convert raw input to valid LongTensor.
        Args:
            input_ids: List of ints, List of lists, or torch.Tensor
        Returns:
            Validated 2D torch.LongTensor (batch, seq_len)
        """
        if not isinstance(input_ids, torch.Tensor):
            try:
                tensor_input = torch.tensor(input_ids, dtype=torch.long)
            except Exception as e:
                raise ArchitectureError(f"Failed to convert inputs to torch.LongTensor: {e}")
        else:
            tensor_input = input_ids.long()

        if tensor_input.dim() == 1:
            tensor_input = tensor_input.unsqueeze(0)  # Convert (seq_len,) to (1, seq_len)
        elif tensor_input.dim() != 2:
            raise ShapeMismatchError(
                f"Expected 1D or 2D input tensor, got shape {tuple(tensor_input.shape)}"
            )

        if tensor_input.shape[1] == 0:
            raise ArchitectureError("Input sequence cannot be empty (seq_len = 0)")

        if tensor_input.shape[1] > self.config.max_seq_len:
            raise ArchitectureError(
                f"Sequence length {tensor_input.shape[1]} exceeds max_seq_len {self.config.max_seq_len}"
            )

        # Vocabulary bounds check
        if (tensor_input < 0).any() or (tensor_input >= self.config.vocab_size).any():
            min_val = tensor_input.min().item()
            max_val = tensor_input.max().item()
            raise ArchitectureError(
                f"Token IDs must be in range [0, {self.config.vocab_size - 1}], but found range [{min_val}, {max_val}]"
            )

        return tensor_input

    def validate_outputs(self, output: ModelOutput, expected_batch: int, expected_seq_len: int) -> None:
        """Ensure model logits are valid and free of numerical anomalies."""
        logits = output.logits
        if not isinstance(logits, torch.Tensor):
            raise ArchitectureError("Model output logits must be a torch.Tensor")

        expected_shape = (expected_batch, expected_seq_len, self.config.vocab_size)
        if logits.shape != expected_shape:
            raise ShapeMismatchError(
                f"Output logits shape {tuple(logits.shape)} does not match expected {expected_shape}"
            )

        # Check for NaN / Inf values
        if torch.isnan(logits).any() or torch.isinf(logits).any():
            raise ArchitectureError("Numerical instability detected: model outputs contain NaN or Inf values")

    def infer(
        self,
        input_ids: Any,
        context_hints: Optional[Dict[str, Any]] = None,
        return_hidden_states: bool = False,
    ) -> ModelOutput:
        """
        Execute validated forward inference pass.
        Args:
            input_ids: Token identifiers
            context_hints: Optional metadata hints (mode, tags)
            return_hidden_states: Whether to include intermediate representations
        Returns:
            ModelOutput with logits and metadata
        """
        tokens = self.validate_inputs(input_ids)
        batch_size, seq_len = tokens.shape

        with torch.no_grad():
            output = self.model(
                tokens,
                context_hints=context_hints,
                return_hidden_states=return_hidden_states,
            )

        self.validate_outputs(output, expected_batch=batch_size, expected_seq_len=seq_len)
        return output

    def generate_greedy_tokens(
        self,
        prompt_ids: List[int],
        max_new_tokens: int = 5,
        context_hints: Optional[Dict[str, Any]] = None,
    ) -> List[int]:
        """
        Step-by-step greedy autoregressive token prediction.
        """
        current_tokens = list(prompt_ids)
        for _ in range(max_new_tokens):
            if len(current_tokens) >= self.config.max_seq_len:
                break
            tokens_tensor = self.validate_inputs(current_tokens)
            output = self.infer(tokens_tensor, context_hints=context_hints)
            next_token_id = int(torch.argmax(output.logits[0, -1, :]).item())
            current_tokens.append(next_token_id)

        return current_tokens
