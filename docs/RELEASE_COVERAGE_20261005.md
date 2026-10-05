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

Una run index limitata a 14 non è stata accodata subito: l'implementazione
corrente, anche con `limit`, legge globalmente gli `indexed_at IS NULL` e invia
una cancellazione vettoriale per tutti gli ID stale prima di applicare il limite.
Con oltre 31mila candidati esclusi, richiede prima un controllo del comportamento
dell'indice/backup. È un blocco tecnico concreto; non riempire la coda con run
poco utili o apparentemente piccole ma con effetti globali.
