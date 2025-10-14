# Assistente notizie Piano di Sorrento

Questa cartella contiene un'applicazione da riga di comando che raccoglie le
ultime notizie pubblicate sul sito del [Comune di Piano di
Sorrento](https://www.comune.pianodisorrento.na.it) e consente di porre domande
in linguaggio naturale. Le risposte sono basate su un piccolo motore di ricerca
interno che analizza gli articoli presenti nel feed RSS comunale.

## Requisiti

L'applicazione utilizza esclusivamente librerie Python standard e può quindi
essere eseguita senza dipendenze aggiuntive. È necessario disporre di una
connessione Internet per scaricare il feed RSS.

## Utilizzo

```bash
python -m app.piano_di_sorrento.cli
```

Durante l'esecuzione l'app scarica (o legge dalla cache locale) gli articoli
recenti, costruisce un indice full-text e poi risponde alle domande
mostrando i comunicati più pertinenti.

Parametri opzionali disponibili:

* `--cache-dir`: cartella in cui salvare la cache degli articoli (default: home
  dell'utente).
* `--max-age`: numero massimo di ore per cui la cache viene considerata valida
  (default: 6).
* `--feed-url`: URL del feed RSS comunale (default: feed principale).
* `--top`: numero di articoli suggeriti per ogni risposta (default: 3).
* `--timeout`: timeout in secondi per il download del feed RSS (default: 10).

## Limiti

Nel presente ambiente di sviluppo non è possibile effettuare richieste HTTP,
pertanto il download reale dei contenuti non è stato eseguito durante i test.
L'applicazione è stata progettata per funzionare in un ambiente con accesso a
Internet.
