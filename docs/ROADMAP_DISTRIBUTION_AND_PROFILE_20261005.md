# Distribuzione dati e profilo utente: valutazione iniziale

La prima release a copertura ampia richiede la maggior parte delle fonti non
problematiche elaborata e la maggior parte dei loro bandi correnti effettivamente
ricercabile. `catalogued`, `sources`, `positions` e `indexed` restano metriche
distinte. La UI e il motore di ricerca sono già usabili; questo obiettivo di
copertura è ancora da misurare e completare. Le fonti difficili non devono
bloccare le altre.

## Database iniziale scaricabile

Un bootstrap pubblico può evitare a ogni installazione l'intera scoperta e
estrazione. Partire dal [piano di esportazione esistente](DATA_BACKUP_AND_BOOTSTRAP.md):
manifest firmato/versionato, istituzioni, fonti pubbliche e opportunità correnti
con incertezza esplicita, senza dump PostgreSQL. Le informazioni private,
i prompt, il testo completo non redistribuibile e i dati utente restano fuori.
Il file deve specificare versione schema, timestamp, licenza dei dati, versione
del modello di embedding e hash; importazione in staging, controllo integrità,
poi commit atomico. Una fonte può essere ufficiale e comunque vietare il riuso
integrale delle descrizioni: serve un controllo dei diritti prima della
pubblicazione. L'aggiornamento differenziale dovrebbe usare ID stabili,
watermark `last_seen`, versioni di fonte e tombstone solo dopo riconferma;
non inferire chiusura dall'assenza in una sola scansione.

Per la ricerca semantica ci sono due opzioni: distribuire uno snapshot Qdrant
compatibile con la versione dell'indice, oppure distribuire metadati e far
creare gli embedding in locale. La prima accelera l'avvio ma richiede stesso
modello e contratto vettoriale, verifica della compatibilità e backup/recovery;
la seconda costa tempo/GPU. I [collection snapshots di Qdrant](https://qdrant.tech/documentation/operations/snapshots/)
sono una tecnologia disponibile, ma non sostituiscono il formato portabile dei
dati. Un'istanza esterna dovrebbe aggiornare solo fonti nuove/cambiate e
scadenze; le verifiche negative dovrebbero essere ricontrollate a intervalli.
Misurare prima quantità di dati, tempo d'importazione e costo incrementale.

Per condivisione tra installazioni preferire inizialmente release versionate e
contributi firmati in una coda di revisione: origine, licenza, provenienza,
identificatori stabili, deduplica e rollback. Non fondere automaticamente
record o verdetti ricevuti da terzi nell'indice pubblico. Una distribuzione
[P2P tramite Syncthing](https://docs.syncthing.net/users/faq.html) può
trasportare artefatti immutabili fra nodi fidati; non risolve da sola fiducia,
conflitti o moderazione. Valutarla dopo un import/export deterministico.

## Tab User e profilazione futura

La tab User viene introdotta vuota come spazio di navigazione, senza raccogliere
anagrafica o CV oggi. Per un futuro profilo locale: controlli di consenso,
export/cancellazione, separazione completa dal dataset pubblico e nessuna
sincronizzazione implicita. Preferenze per istituzioni seguite possono arrivare
prima del CV, perché richiedono meno dati sensibili. Non creare account e
servizi esterni per rendere utilizzabile la ricerca di base.

[JSON Resume](https://jsonresume.org/docs/013-schema-definitions) offre uno
schema aperto per import/export di CV strutturati; valutare mapping/versione
senza copiare un editor complesso. [Reactive Resume](https://docs.rxresu.me/)
è una possibile integrazione opzionale per creare e gestire CV, ma è
un'applicazione distinta con account, storage e ciclo di manutenzione propri:
non inserirla come dipendenza di PHDBOT. Una prima prova concreta sarebbe
importare un JSON Resume locale in una sandbox privata e usare soltanto campi
scelti dall'utente per migliorare filtri/ranking, conservando ricerca anonima.

## Priorità

1. Misurare il denominatore delle fonti non problematiche e la quota realmente
   ricercabile; completare la loro pipeline in batch utili e termicamente sicuri.
2. Prototipo di export/import pubblico su un sottoinsieme con test di idempotenza,
   privacy e compatibilità dell'indice.
3. Preferenze locali facoltative; integrazione CV solo dopo che ricerca e
   distribuzione iniziale funzionano.
