"""FinBERT-based financial sentiment analysis.

Uses the ProsusAI/finbert transformer model to score financial text
(Reddit posts, news headlines) with positive/negative/neutral sentiment.
Supports batched inference with GPU acceleration when available.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import torch
from loguru import logger
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.utils.config import get_config


class SentimentAnalyzer:
    """Finance-specific sentiment analysis using FinBERT.

    Unlike general-purpose sentiment tools (VADER, TextBlob), FinBERT is
    trained on financial corpus data and understands domain-specific
    language ("bearish", "short squeeze", "guidance raised", etc.).

    Attributes:
        model_name: HuggingFace model identifier.
        tokenizer: FinBERT tokenizer.
        model: FinBERT classification model.
        device: Compute device (cuda/mps/cpu).
        batch_size: Inference batch size.
        max_length: Maximum token length per input.
    """

    LABELS = ["positive", "negative", "neutral"]

    def __init__(self) -> None:
        cfg = get_config()
        self.model_name: str = cfg.features.sentiment.model
        self.batch_size: int = cfg.features.sentiment.batch_size
        self.max_length: int = cfg.features.sentiment.max_length
        self.aggregation: str = cfg.features.sentiment.aggregation

        # Select best available device
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")

        logger.info(
            "Loading FinBERT model: {model} on {device}",
            model=self.model_name,
            device=self.device,
        )

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()

        logger.info("FinBERT loaded successfully")

    @torch.no_grad()
    def score_texts(self, texts: list[str]) -> list[dict[str, float]]:
        """Score a list of texts for financial sentiment.

        Args:
            texts: List of text strings to analyze.

        Returns:
            List of dicts with keys: positive, negative, neutral, compound.
            Compound score ranges from -1 (most negative) to +1 (most positive).
        """
        results: list[dict[str, float]] = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]

            # Filter empty texts
            batch = [t if t and len(t.strip()) > 0 else "neutral" for t in batch]

            encodings = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            ).to(self.device)

            outputs = self.model(**encodings)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

            for prob in probs.cpu().numpy():
                scores = {label: float(p) for label, p in zip(self.LABELS, prob)}
                # Compound score: positive - negative (range: -1 to 1)
                scores["compound"] = scores["positive"] - scores["negative"]
                results.append(scores)

        return results

    def score_dataframe(self, df: pd.DataFrame, text_column: str = "combined_text") -> pd.DataFrame:
        """Add sentiment scores to a DataFrame.

        Handles [SEP]-delimited multi-text fields by scoring each
        segment individually and aggregating.

        Args:
            df: Input DataFrame with text column.
            text_column: Name of the text column to analyze.

        Returns:
            DataFrame with added sentiment score columns.
        """
        if text_column not in df.columns:
            logger.warning("Column {col} not found in DataFrame", col=text_column)
            return df

        logger.info(
            "Scoring sentiment for {n} rows using {col}",
            n=len(df),
            col=text_column,
        )

        sentiment_scores = []

        for idx, text in enumerate(df[text_column]):
            if not text or text.strip() == "":
                sentiment_scores.append(
                    {"positive": 0.33, "negative": 0.33, "neutral": 0.34, "compound": 0.0}
                )
                continue

            # Split multi-text fields and score individually
            segments = [s.strip() for s in text.split("[SEP]") if s.strip()]

            if not segments:
                sentiment_scores.append(
                    {"positive": 0.33, "negative": 0.33, "neutral": 0.34, "compound": 0.0}
                )
                continue

            segment_scores = self.score_texts(segments)

            # Aggregate segment scores
            if self.aggregation == "weighted_mean":
                # Weight by text length (longer = more informative)
                weights = np.array([len(s) for s in segments], dtype=float)
                weights /= weights.sum()
                agg_scores = {}
                for key in self.LABELS + ["compound"]:
                    values = np.array([s[key] for s in segment_scores])
                    agg_scores[key] = float(np.average(values, weights=weights))
            elif self.aggregation == "median":
                agg_scores = {}
                for key in self.LABELS + ["compound"]:
                    agg_scores[key] = float(np.median([s[key] for s in segment_scores]))
            else:  # mean
                agg_scores = {}
                for key in self.LABELS + ["compound"]:
                    agg_scores[key] = float(np.mean([s[key] for s in segment_scores]))

            sentiment_scores.append(agg_scores)

            if (idx + 1) % 100 == 0:
                logger.info("Scored {n}/{total} rows", n=idx + 1, total=len(df))

        # Add sentiment columns
        scores_df = pd.DataFrame(sentiment_scores)
        scores_df.columns = [f"sentiment_{c}" for c in scores_df.columns]

        result = pd.concat([df.reset_index(drop=True), scores_df], axis=1)

        logger.info(
            "Sentiment scoring complete | "
            "Avg compound: {avg:.3f} | "
            "Positive: {pos:.1%} | Negative: {neg:.1%}",
            avg=result["sentiment_compound"].mean(),
            pos=(result["sentiment_compound"] > 0.1).mean(),
            neg=(result["sentiment_compound"] < -0.1).mean(),
        )

        return result
