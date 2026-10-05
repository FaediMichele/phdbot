# Analisi delle wave e prossimi interventi

Verifica del 3 ottobre 2026; fotografia DB finale alle 02:03:55, Europe/Rome.
L'obiettivo di questa unità è verificare recovery, misurare le wave già eseguite
e preparare decisioni per gruppi di problemi. La release essenziale resta un
perimetro separato dal completamento del catalogo.

## Stato verificato

| Wave | Job previsti | Riusciti | Falliti | Ancora attivi | Media / mediana per job |
|---|---:|---:|---:|---:|---:|
| 2 | 1.600 | 1.595 | 5 | 0 | 125,8 / 86,2 s |
| 2.5 | 1.100 | 806 | 1 | 293 | 130,3 / 87,5 s sui terminali |

Wave 2.5: 269 programmati, 16 in attesa della pipeline, 7 in avvio e una
pipeline attiva (schedule 2492 → run 2626). Sono stati verificati tutti i job,
non solo la prima pagina dell'API. Le schedule non vengono necessariamente
eseguite in ordine crescente.

Il recupero della schedule 1698 è concluso sulla **stessa run 1806**, con due
tentativi e checkpoint conservati. Non è uno stato stale da azzerare.
La schedule 1736/run 1867 è invece fallita per paginazione BITE non supportata
sulle due varianti linguistiche della stessa bacheca. Va conservata e ripresa
solo dopo la diagnosi dell'adapter. Non richiede una nuova schedule.

I fallimenti di wave 2 sono 159/274, 162/276, 1266/1368, 1398/1504 e
1631/1739 (schedule/run). Tre registrano una pipeline fermata e non vengono
riavviati autonomamente; due hanno sorgenti differite dal crawler.

Valet: timer attivo, ultimo servizio oneshot concluso con successo. Il wake
1678 era già arrivato correttamente. Alla schedule **2778**, ancora programmata,
è stato aggiunto soltanto `governor_plan.valet_wake_root_id`, mantenendo ID,
stato, parametri, limiti, scadenza e autorizzazione. Una transazione condizionata
a una sola schedule non avviata ha applicato la modifica; il confronto API
prima/dopo ha verificato che solo il campo wake sia cambiato. Ricevuta:
`var/wave-analysis-20261003/schedule-2778-wake-receipt.json`.
Il wake indica un checkpoint finale: al risveglio occorre verificare tutti i
job, perché la fine dell'ultimo ID non è una barriera sui retry precedenti.

## Tempi e resa

Il benchmark 125,8 s usa `scheduled_jobs.started_at → finished_at`; include il
tempo necessario al scheduler per osservare la conclusione. Il tempo attivo
medio registrato dalla pipeline è circa 112 s: sono misure diverse, non una
regressione del benchmark. La mediana non va usata da sola per stimare una
coda con casi lenti. Gli ultimi 100 terminali della wave 2.5 hanno media
129,7 s e mediana 86,1 s: **circa 10,6 ore** per i 293 rimanenti nella fotografia.
È una stima di capacità, subordinata a disponibilità del computer, admission
e retry; non una scadenza o un motivo per fermare il lavoro.

| Risultato DB dei job terminali | Wave 2 | Wave 2.5 parziale |
|---|---:|---:|
| Righe raccolte | 3.677 | 2.409 |
| Marcatori d'indice attivi e non scaduti | 416 | 313 |
| Enti con almeno un marcatore corrente | 135 | 91 |

I marcatori SQL non certificano opportunità uniche né la presenza effettiva in
Qdrant: possono esistere duplicati linguistici/listing e filtri successivi.
Questo audit non li promuove a bandi verificati.

Wave 2 ha trovato 1.499 pagine fonte presso 493 enti. 788 enti sono
`no_listing` e 287 hanno discovery fallita. Una run `done` può quindi contenere
un esito negativo o un errore locale della fonte: occorre leggere i risultati
degli stadi. I casi `no_listing` durano mediamente 82,4 s e hanno indice zero;
le fasi successive risultano già vuote. La discovery è il costo prevalente
di questi casi, non un budget 3×3 sempre consumato integralmente.

La wave 2.5 ha terminato tutti gli 800 enti education (799 riusciti, 1 fallito),
con 311 marcatori correnti presso 89 enti. Solo 7 facility su 300 sono
terminali, con 2 marcatori presso 2 enti: non è ancora un confronto utile
per decidere la composizione della prossima wave.

Il riuso degli schemi esiste già: wave 2 registra 188 riusi. Il contatore
`generated` comprende anche preparazione di adapter e non conta esattamente
le chiamate Ollama. I tempi cumulativi storici di ogni stadio non sono salvati:
non è possibile ricostruire da questi dati né chiamate complete né GPU-secondi.

## Cluster di esclusione

L'audit deterministico esistente, eseguito senza modelli o scritture all'indice,
trova 28.313 record attivi/correnti e candidabili al primo filtro, privi di
`indexed_at`. Solo **14** passano già i controlli locali dell'audit; non è
ancora una verifica end-to-end dei filtri di ricerca e feedback.

| Causa | Record | Interpretazione e prossima verifica |
|---|---:|---|
| Evidenza insufficiente | 18.823 | 13.625 sono `other`; separare navigazione da ruoli di ricerca plausibili, poi verificare pochi esempi per famiglia. Non allentare globalmente il gate. |
| Percorso di evidenza non supportato | 5.922 | Separare asset/URL non pertinenti da fetch falliti o temporaneamente indisponibili. Retry solo quando esistono fonte e percorso affidabili. |
| Fonte non sana | 2.793 | Riparazione a livello di schema/bacheca prima di ulteriori review dei singoli record. |

I controlli di proprietà della fonte hanno differito 110 pagine in wave 2 e
63 nella prima fotografia di wave 2.5. Alcuni esempi sono job board di altre
istituzioni trovate dalla ricerca: rimuovere il controllo introdurrebbe errori.
Occorre conservare e rivalidare la provenienza dei link jobs/ATS esterni.

Un mass-reconcile dei circa 28 mila record ha un ritorno immediato molto basso.
La stessa cautela vale per una deep review uniforme: non ripara una sorgente
irraggiungibile e non trasforma una pagina di navigazione in un bando.

## Valutazione delle direzioni proposte

| Proposta | Decisione |
|---|---|
| Cluster-first e meno risvegli | Adottati come protocollo operativo; report aggregato e un solo wake finale sulla wave esistente. |
| Batch grandi e comparabili | Già in corso; attendere la componente facility prima di scegliere altri volumi. Dimensionare con tempi e resa del cluster, non solo numero di enti. |
| Preflight economico | Utile. L'ambiguità nasce da `ILIKE '%nome%'`, non solo da nomi identici; il futuro preflight deve riusare tale criterio. Un dry-run centralizzato è preferibile a un'altra implementazione divergente. Nessuna modifica urgente all'endpoint in questa unità. |
| Fast-path noti | Adapter Workday/BITE e riuso di schemi rivalidati sono già presenti. Estendere solo famiglie con evidenza di un problema condiviso; BITE è un candidato concreto. |
| Early exit | Già presente per stadi senza fonti e per alcuni stati della pagina. Una mancata parola jobs nella home non basta per rifiutare un ente. |
| Concorrenza per risorsa | Da misurare dopo telemetria per stadio; preservare ora la serializzazione e il recovery dimostrato. |
| Index globale a batch pieni | Da misurare: non dimostrato che sia il collo di bottiglia. Molti job non producono alcun candidato; il batching da solo non risolve evidenza e qualità. |
| Coverage separata da review profonda | Già rispettata dalle wave: nessuna fase evidence/review/review2/enrich. Conservare la ricerca provvisoria con filtri e incertezza. |
| Reconciliation per cluster | Prioritaria rispetto a un rilancio globale; scegliere campioni di ruoli plausibili su fonti sane e misurare il guadagno reale prima di estendere. |
| Profiling quantitativo | Prima parte completata. Aggiungere in futuro tempi durevoli per stadio e contatori effettivi di chiamate: non dedurli dai contatori schema. |
| Wave ID e UX | Primo strumento read-only pronto: manifest delle schedule, conteggi, ETA recente, resa e gruppi. Non è ancora una nuova schermata o tabella DB. Metadata nativi e una vera barriera di fine wave restano il passo successivo. |

## Strumenti verificati e prossimo checkpoint

Comandi eseguiti con successo dal repository il 3 ottobre:

```sh
python3 scripts/capture_catalog_waves.py \
  --plan var/catalog-population-20260928/wave2-plan.json \
  --plan var/catalog-population-20260928/wave2_5-plan.json \
  --output var/wave-analysis-20261003/snapshot-local-date.json
python3 scripts/catalog_wave_report.py \
  --snapshot var/wave-analysis-20261003/snapshot-local-date.json \
  --plan var/catalog-population-20260928/wave2_5-plan.json \
  --output var/wave-analysis-20261003/wave2_5-report.json
```

La cattura usa una transazione PostgreSQL read-only repeatable-read, timeout
45 s e data Europe/Rome; il report lavora solo sul file. Nessun nuovo modello,
scheduler o ciclo di polling. Test mirati su conteggi, mapping tra istituzioni
e schedule, pesi dei cluster, ETA, manifest incompleti/duplicati; Ruff e mypy
passati. Nessun deploy durante la raccolta.

La coda nota contiene già 293 job utili, circa 10,6 ore nella fotografia finale.
Nessuna nuova wave o reindicizzazione è stata accodata. Le ulteriori fonti del
catalogo non sono state rivalutate globalmente; non si dichiara esaurito il lavoro.
I nuovi batch di riparazione dipendono dalla selezione dei cluster e da prove
live rappresentative; gli stop manuali storici rimangono preservati. Al wake
2778: fotografare una volta tutte le schedule del manifest, confrontare
education/facility, distinguere negativi da errori tecnici, scegliere al massimo
pochi cluster con un criterio di accettazione, poi lasciare eseguire un batch
autonomo sufficiente a misurarli. Non ricominciare dalle istituzioni una per una.
