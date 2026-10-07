# Richieste utente e avanzamento

Aggiornato 7 ottobre 2026. Aggiornare a ogni unità conclusa, distinguendo
implementazione, validazione sul campo e proposte. La ricerca di soluzioni non
completa una richiesta di implementazione. Non fermare il lavoro indipendente
sulle fonti sane a causa di pochi recovery problematici.

## Priorità immediata: copertura utile

- [ ] Maggioranza delle fonti non problematiche e dei loro bandi correnti
  effettivamente ricercabile: definire denominatore e misurarlo, senza equiparare
  istituzioni/catalogo/record raccolti a bandi ricercabili.
- [ ] Aggiornare e raccogliere in batch le fonti sane con schemi/adapter esistenti.
  Batch 6 ottobre: 20 istituzioni, 40 fonti; ricevute in var/refresh-20261006/.
  Concluso20/20,230 upsert,330 quality,28 index in400s; incremento netto
  ancora da misurare. Secondo batch100 istituzioni/219 fonti preparato,
  stima2200s basata sul primo; ricevute var/refresh-20261006-b/.
- [ ] Espansione dinamica centri di ricerca, istituti e fondazioni; esplorare
  jobs/careers e ATS esterni. Non considerare finita l'attivazione del catalogo.
- [ ] Riparare per cluster evidence/screening/routing: audit 5 ottobre 31.448
  candidati, solo 14 direttamente indicizzabili, pubblicati dalla run3821.
- [ ] Recovery mirato via scheduler/governor_plan, conservando ID/checkpoint:
  IEM run1504; altre run1368/1867 richiedono correzione BITE;274 schema pendente.

## Sicurezza termica: applicazione, non impostazioni del PC

- [x] Guard CPU e notifiche pause/critici disponibili; pause ai confini delle unità.
- [x] Ricerca BOINC/TThrottle/ADPF/Ollama documentata in
  THERMAL_APPLICATION_CONTROL_20261005.md.
- [ ] Implementare controller adattivo del carico: isteresi, riduzione rapida,
  ripresa graduale, conteggio delle pause naturali; test isolati e replay.
- [ ] Verificare cancellazione effettiva del backend durante chiamate lunghe;
  chiudere la richiesta HTTP non prova che il calcolo sia terminato.
- [ ] Monitoraggio GPU e canary termico comparabile, una variabile alla volta.
- [ ] Misurare sicurezza, resa e durata incluse pause; mantenere notifiche critiche.
  Nessuna modifica a fan/clock/EPP/profilo energia del PC autorizzata da questa lista.

## Ottimizzazioni e autonomia

- [x] Scheduler persistente seriale, recupero crash e governor_plan disponibili.
- [x] Notifica Valet a fine batch verificata (wave-release-index14).
- [x] Scrape da schema memorizzato disponibile senza generazione LLM.
- [ ] Profiling quantitativo per stadio/famiglia: costo per opportunità ricercabile,
  chiamate modello/retry, zero fonti/zero risultati, p50/p95 e outlier.
- [ ] Generalizzare fast-path ATS, preflight economico, early exit e negative TTL.
- [ ] Anticipare validazione scope ambiguo dell'expansion nel preflight.
- [ ] Wave metadata e progresso/ETA aggiornato da tempi reali.
- [ ] Valutare batching globale indice e concorrenza I/O dopo profiling.
- [ ] Verificare stato attuale ottimizzazioni run70 senza rifarle: riuso schemi
  rivalidati, retry non moltiplicati, limiti generazioni, feedback per dimensione,
  riuso duplicati equivalenti, refresh differenziato e scadenza negativi.
- [ ] Ridurre checkpoint Codex: batch indipendenti ampi, analisi per cluster,
  una notifica aggregata; registrare perché la coda termina.

## Consegne e funzionalità

- [x] README: standalone/Valet opzionale, presentazione progetto, termica dopo pipeline.
- [x] Tab User vuota; salvati scaduti in accordion e grigi nel calendario.
- [x] Pubblicazione sulla repo originale Michele, branch feature (a6f23a9).
- [x] Guida operativa OFFLINE_HANDOFF disponibile; mantenerla aggiornata.
- [x] Backup locale e ripristino PostgreSQL verificato.
- [ ] Provare ripristino snapshot Qdrant e valutare seconda copia backup.
- [x] Valutazione preliminare database scaricabile, delta e profilo OSS documentata.
- [ ] Futuro: export pubblico verificabile, import/delta idempotenti; contributi
  validati prima di P2P. Nessun dato profilo nel dataset condiviso.
- [ ] Futuro: preferenze locali, JSON Resume/CV/portfolio/link e istituzioni seguite;
  integrazioni OSS opzionali, senza dipendenze obbligatorie per la ricerca base.
