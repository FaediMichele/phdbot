# Prima release a copertura ampia: stato misurabile

L'essenziale funzionale è già utilizzabile, ma l'obiettivo di release ora
chiarito dall'utente è più ampio: la maggior parte delle fonti non problematiche
deve avere bandi correnti realmente ricercabili. Il denominatore deve escludere
solo fonti classificate problematiche con motivo verificabile, non tutte quelle
che non producono bandi. Una fonte valida con zero vacancy oggi conta come
coperta se il controllo della sezione jobs/careers è avvenuto e la verifica
negativa scade dopo un intervallo definito. Indici, sorgenti e opportunità
vanno misurati separatamente.

Il 5 ottobre, dopo la wave CPU4, l'audit read-only dei record active/current
coarse-index-candidate non indicizzati ha trovato 31.448 righe: solo 14
`searchable_without_reconciliation`; 21.782 con evidenza insufficiente, 5.921
con route non supportata e 2.924 con sorgente non sana. Sono conteggi di record,
non percentuali di fonti sane né di bandi veri. La semplice run `index` non
risolverebbe il grosso del problema. Artefatto locale:
`var/release-20261005/searchability-before.json`.

Il prossimo profiling deve raggruppare le tre cause per source family e schemi,
valutare campioni rappresentativi e stimare le fonti recuperabili senza GPU.
Poi batch di raccolta/diffusione indicizzazione per i casi sicuri, con limiti
termici e Valet wake solo al termine di cohort utili. Non riavviare run già fatte.

La verifica della pulizia preliminare ha risolto un dubbio sullo scope: lo
stadio index legge gli ID non indicizzati globalmente prima del limite, ma il
controllo Qdrant ha trovato zero vettori corrispondenti ai 58.577 ID non
indicizzati. Non è stato necessario modificare questa logica ordinaria.
Artefatto: `var/release-20261005/stale-index-preflight.json`.

Lavoro utile eseguito durante le modifiche UI:

- Schedule 3679 / run 3819: no-op dovuto a `name` erroneamente usato come
  etichetta anziché filtro. Conservato, nessun dato elaborato.
- Schedule 3680 / run 3820: qualità su sette fonti, 187 record elaborati,
  terminale done; circa 22 secondi fra avvio/fine schedule contro stima 120 s.
- Schedule 3681 / run 3821: indicizzazione limitata a 14 candidati, stimata
  120 secondi; conclusa con 14 record indicizzati in 156,44 secondi attivi
  (162,23 s fra avvio e fine schedule). Verificati i 14 marker SQL.

Prima di lasciare la coda: sei fonti con schema ok non hanno last_scraped_at
(ID 8259, 9404, 9565, 9566, 9954, 9955). La loro storia va verificata prima
di accodare nuovi job, per evitare duplicati di recovery pendenti. L'espansione
con generazione LLM richiede ancora gestione sicura delle richieste lunghe.
Il prossimo batch non dipende dalla disponibilità di token ma da queste verifiche.

Verifica del 5 ottobre, 19:10: nessuna schedule attiva o accodata. Le sei
fonti mai raccolte appartengono a recovery esistenti: run 274 fermata, run
1368/1504/1867 fallite per sorgenti irraggiungibili. Conservare i checkpoint;
non creare nuovi job equivalenti. Prima di Resume serve verificare la causa
e la raggiungibilità, e per 274 gli stadi LLM ancora pendenti.
