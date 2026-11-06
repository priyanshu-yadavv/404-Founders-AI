"""
404 FOUNDERS — Training/Datasets/Ingestion
Dataset ingestion across text, code, math, scientific, cybersecurity, and multilingual corpora.
"""

from training.datasets.ingestion.dataset_ingestor import (
    ALL_DOMAINS,
    DOMAIN_CODE,
    DOMAIN_CYBERSECURITY,
    DOMAIN_GENERAL_TEXT,
    DOMAIN_INSTRUCTION,
    DOMAIN_MATH,
    DOMAIN_MULTILINGUAL,
    DOMAIN_MULTIMODAL_METADATA,
    DOMAIN_SCIENTIFIC,
    DOMAIN_SYNTHETIC,
    DataRecord,
    DatasetIngestor,
)

__all__ = [
    "ALL_DOMAINS",
    "DOMAIN_CODE",
    "DOMAIN_CYBERSECURITY",
    "DOMAIN_GENERAL_TEXT",
    "DOMAIN_INSTRUCTION",
    "DOMAIN_MATH",
    "DOMAIN_MULTILINGUAL",
    "DOMAIN_MULTIMODAL_METADATA",
    "DOMAIN_SCIENTIFIC",
    "DOMAIN_SYNTHETIC",
    "DataRecord",
    "DatasetIngestor",
]
