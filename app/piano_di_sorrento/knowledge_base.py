"""Simple information retrieval utilities for municipal articles."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from .data_source import Article

_TOKEN_PATTERN = re.compile(r"[a-zA-ZÀ-ÖØ-öø-ÿ']+")


def _tokenize(text: str) -> List[str]:
    tokens = [token.lower() for token in _TOKEN_PATTERN.findall(text)]
    return [token for token in tokens if len(token) > 1]


@dataclass
class RetrievedArticle:
    article: Article
    score: float


class KnowledgeBase:
    """Lightweight TF-IDF based search on top of municipal articles."""

    def __init__(self, articles: Sequence[Article]):
        self._articles = list(articles)
        self._doc_vectors: List[Tuple[Dict[str, float], float]] = []
        self._idf: Dict[str, float] = {}
        if self._articles:
            self._build_index()

    @property
    def articles(self) -> Sequence[Article]:
        return self._articles

    def _build_index(self) -> None:
        doc_term_freqs: List[Counter[str]] = []
        doc_freq: Dict[str, int] = defaultdict(int)

        for article in self._articles:
            tokens = _tokenize(article.content or article.summary)
            term_freqs = Counter(tokens)
            doc_term_freqs.append(term_freqs)
            for token in term_freqs:
                doc_freq[token] += 1

        num_docs = sum(1 for term_freqs in doc_term_freqs if term_freqs)
        if num_docs == 0:
            return

        self._idf = {
            term: math.log((1 + num_docs) / (1 + freq)) + 1.0
            for term, freq in doc_freq.items()
        }

        for term_freqs in doc_term_freqs:
            if not term_freqs:
                self._doc_vectors.append(({}, 1.0))
                continue
            total_terms = sum(term_freqs.values())
            vector: Dict[str, float] = {}
            for term, freq in term_freqs.items():
                tf = freq / total_terms if total_terms else 0.0
                vector[term] = tf * self._idf.get(term, 0.0)
            norm = math.sqrt(sum(weight * weight for weight in vector.values()))
            if norm == 0:
                self._doc_vectors.append(({}, 1.0))
            else:
                self._doc_vectors.append((vector, norm))

    def search(self, question: str, top_k: int = 3) -> List[RetrievedArticle]:
        if not question.strip() or not self._idf:
            return []
        query_tokens = _tokenize(question)
        if not query_tokens:
            return []

        query_freqs = Counter(query_tokens)
        total_terms = sum(query_freqs.values())
        query_vector: Dict[str, float] = {}
        for term, freq in query_freqs.items():
            if term not in self._idf:
                continue
            tf = freq / total_terms
            query_vector[term] = tf * self._idf[term]
        if not query_vector:
            return []
        query_norm = math.sqrt(sum(weight * weight for weight in query_vector.values()))
        if query_norm == 0:
            return []

        scored: List[RetrievedArticle] = []
        for article, (doc_vector, doc_norm) in zip(self._articles, self._doc_vectors):
            if not doc_vector:
                continue
            dot_product = sum(query_vector.get(term, 0.0) * weight for term, weight in doc_vector.items())
            if dot_product == 0:
                continue
            score = dot_product / (query_norm * doc_norm)
            if score <= 0:
                continue
            scored.append(RetrievedArticle(article=article, score=score))

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def generate_answer(self, question: str, top_k: int = 3) -> str:
        matches = self.search(question, top_k=top_k)
        if not matches:
            return (
                "Non ho trovato informazioni specifiche nei comunicati del Comune. "
                "Prova a riformulare la domanda o visita il sito ufficiale."
            )

        lines: List[str] = [
            "Ecco cosa ho trovato nelle ultime notizie del Comune di Piano di Sorrento:",
        ]
        for match in matches:
            article = match.article
            published = (
                article.published.strftime("%d/%m/%Y") if article.published else "Data non disponibile"
            )
            lines.append(
                f"• {article.title} ({published}) — punteggio {match.score:.2f}\n  "
                f"{article.short_snippet()}\n  Leggi di più: {article.link}"
            )
        return "\n".join(lines)


__all__ = ["KnowledgeBase", "RetrievedArticle"]
