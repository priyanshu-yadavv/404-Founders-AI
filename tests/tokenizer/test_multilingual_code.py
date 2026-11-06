"""
404 FOUNDERS — Unit Tests: Multilingual, Code & Mathematical Tokenization
Validates Unicode preservation, Hindi/Devanagari conjuncts, code syntax, and math notation.
"""

import pytest

from tokenizer import CustomBPETokenizer, TokenizerConfig, TokenizerEvaluator


@pytest.fixture
def multilingual_corpus():
    return [
        # Hindi / Devanagari
        "नमस्ते भारत! यह 404 FOUNDERS कृत्रिम बुद्धिमत्ता सहायक है।",
        "विज्ञान और गणितीय विश्लेषण हमारे मुख्य घटक हैं।",
        "कंप्यूटर प्रोग्रामिंग और सिस्टम सुरक्षा आवश्यक हैं।",

        # Code: Python, Rust, C++, SQL, Bash
        "def compute_hash(data: bytes, rounds: int = 1000) -> str:\n    return hashlib.sha256(data).hexdigest()",
        "fn calculate_metrics(values: &[f64]) -> Result<f64, SystemError> { Ok(values.iter().sum()) }",
        "int main(int argc, char** argv) { std::cout << \"404 FOUNDERS\\n\"; return 0; }",
        "SELECT user_id, COUNT(*) AS actions FROM audit_logs WHERE status == 'ACTIVE' GROUP BY user_id;",
        "find /var/log -type f -name '*.log' | xargs grep -i 'error' || true",

        # Mathematics and Scientific
        r"f(x) = \int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}",
        "E = m * c**2 where c = 2.99792458e+8 m/s and h = 6.62607015e-34 J*s",
        "Matrix transformation: A * x == b, det(A) != 0, lambda >= 0.001",

        # Major World Languages
        "El modelo de inteligencia artificial se entrena desde cero sin pesos previos.",
        "Das hybride neuronale Netzwerk unterstützt Multi-Mechanism-Attention.",
        "Модель искусственного интеллекта обучается с нуля.",
        "404 FOUNDERS 是一个多模态基础人工智能系统。",
        "الذكاء الاصطناعي بدون حدود للمستقبل.",
    ]


def test_unicode_preservation(multilingual_corpus):
    """Test 9: Verify non-destructive Unicode handling and exact round-trip reconstruction."""
    config = TokenizerConfig(vocab_size=350, min_frequency=1)
    tokenizer = CustomBPETokenizer(config=config)
    tokenizer.train_from_iterator(multilingual_corpus)

    for text in multilingual_corpus:
        encoded = tokenizer.encode(text)
        decoded = tokenizer.decode(encoded.ids, skip_special_tokens=True)
        assert decoded == text, f"Unicode corruption in: {text}\nDecoded: {decoded}"


def test_hindi_devanagari_tokenization():
    """Test 10: Verify Hindi text with mātrās, halant virama, and Devanagari conjuncts."""
    hindi_texts = [
        "नमस्ते भारत",
        "कृत्रिम बुद्धिमत्ता",
        "प्रोग्रामिंग और गणित",
        "सॉफ्टवेयर विकास",
    ]
    config = TokenizerConfig(vocab_size=120, min_frequency=1)
    tokenizer = CustomBPETokenizer(config=config)
    tokenizer.train_from_iterator(hindi_texts)

    for text in hindi_texts:
        encoded = tokenizer.encode(text)
        assert len(encoded.ids) > 0
        decoded = tokenizer.decode(encoded.ids)
        assert decoded == text, f"Hindi mismatch: expected '{text}', got '{decoded}'"

    # Verify that frequent conjunct characters participate in BPE merges
    assert len(tokenizer.merges) > 0


def test_programming_code_syntax():
    """Test 11: Verify that code symbols, indentation, and operators are not stripped or corrupted."""
    code_samples = [
        "def foo(x: int = 10) -> bool:\n    if x >= 0 and x != 42:\n        return True\n    return False",
        "const double PI = 3.1415926535; // constant",
        "x += 1; y -= 2; z *= 3; w /= 4; a //= 5;",
        "SELECT * FROM users WHERE age >= 18 AND status == 'ACTIVE';",
    ]
    config = TokenizerConfig(vocab_size=180, min_frequency=1)
    tokenizer = CustomBPETokenizer(config=config)
    tokenizer.train_from_iterator(code_samples)

    for code in code_samples:
        encoded = tokenizer.encode(code)
        decoded = tokenizer.decode(encoded.ids)
        assert decoded == code, f"Code syntax corrupted:\nExpected:\n{code}\nGot:\n{decoded}"
        # Operators must be present
        assert not any(tok == "<unk>" for tok in encoded.tokens)


def test_mathematical_notation():
    """Test 12: Verify mathematical symbols and scientific notation handling."""
    math_samples = [
        r"\int_{a}^{b} f(x) dx = F(b) - F(a)",
        "1.234e-05 <= alpha <= 9.876e+02",
        "det(M) == 0 => M^{-1} is undefined",
        "E = 1.602e-19 * V",
    ]
    config = TokenizerConfig(vocab_size=160, min_frequency=1)
    tokenizer = CustomBPETokenizer(config=config)
    tokenizer.train_from_iterator(math_samples)

    for math_str in math_samples:
        encoded = tokenizer.encode(math_str)
        decoded = tokenizer.decode(encoded.ids)
        assert decoded == math_str, f"Math corrupted:\nExpected: {math_str}\nGot: {decoded}"


def test_multilingual_evaluator_metrics(multilingual_corpus):
    """Test 13: Verify evaluation metrics (compression ratio, tokens per word, fertility)."""
    config = TokenizerConfig(vocab_size=300, min_frequency=1)
    tokenizer = CustomBPETokenizer(config=config)
    tokenizer.train_from_iterator(multilingual_corpus)

    evaluator = TokenizerEvaluator(tokenizer)
    metrics = evaluator.evaluate_sample("नमस्ते भारत! यह 404 FOUNDERS है।", language="hi")

    assert metrics.roundtrip_exact is True
    assert metrics.token_count > 0
    assert metrics.compression_ratio > 1.0  # UTF-8 bytes / token > 1
    assert metrics.tokens_per_word > 0.5
    assert metrics.fertility > 0.0
    assert metrics.unk_count == 0

    corpus_dict = {
        "hindi": [multilingual_corpus[0]],
        "code": [multilingual_corpus[3]],
        "math": [multilingual_corpus[8]],
    }
    corpus_summary = evaluator.evaluate_corpus(corpus_dict)
    assert "hindi" in corpus_summary
    assert "code" in corpus_summary
    assert "math" in corpus_summary
    assert corpus_summary["hindi"]["all_roundtrip_exact"] is True
    assert corpus_summary["code"]["all_roundtrip_exact"] is True
    assert corpus_summary["math"]["all_roundtrip_exact"] is True
