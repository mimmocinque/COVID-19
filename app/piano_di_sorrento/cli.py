"""Command line interface for exploring Piano di Sorrento municipal news."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from .data_source import Article, load_articles
from .knowledge_base import KnowledgeBase


def _print_intro(articles: list[Article]) -> None:
    if not articles:
        print(
            "Non sono riuscito a scaricare nessuna notizia. "
            "Controlla la connessione o riprova più tardi.",
            file=sys.stderr,
        )
        return
    print("\nBenvenuto! Ho raccolto le notizie più recenti dal sito del Comune di Piano di Sorrento.")
    print("Ecco gli ultimi articoli disponibili:")
    for idx, article in enumerate(articles[:5], start=1):
        published = article.published.strftime("%d/%m/%Y") if article.published else "Data non disponibile"
        print(f"  {idx}. {article.title} ({published})")
    print(
        "\nFai una domanda sul Comune di Piano di Sorrento. "
        "Digita 'esci' per terminare."
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Assistente interattivo che risponde utilizzando le notizie pubblicate su "
            "www.comune.pianodisorrento.na.it"
        )
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Cartella in cui salvare la cache delle notizie (default: home dell'utente).",
    )
    parser.add_argument(
        "--max-age",
        type=int,
        default=6,
        help="Numero di ore per cui considerare valida la cache locale (default: 6).",
    )
    parser.add_argument(
        "--feed-url",
        type=str,
        default="https://www.comune.pianodisorrento.na.it/feed/",
        help="URL del feed RSS del sito comunale.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=3,
        help="Numero massimo di articoli da mostrare in risposta a ogni domanda.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Timeout (in secondi) per il download del feed RSS.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        articles = load_articles(
            cache_dir=args.cache_dir,
            feed_url=args.feed_url,
            max_age_hours=args.max_age,
            timeout=args.timeout,
        )
    except Exception as exc:  # pragma: no cover - user feedback path
        print(f"Errore durante il caricamento delle notizie: {exc}", file=sys.stderr)
        return 1

    knowledge_base = KnowledgeBase(articles)
    _print_intro(knowledge_base.articles)

    if not knowledge_base.articles:
        return 1

    while True:
        try:
            question = input("\nDomanda > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nArrivederci!")
            break
        if question.lower() in {"", "esci", "exit", "quit"}:
            if question:
                print("Arrivederci!")
            break
        answer = knowledge_base.generate_answer(question, top_k=args.top)
        print(f"\n{answer}\n")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
