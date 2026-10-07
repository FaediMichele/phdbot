# PHDBOT: guida per un assistente che aiuta l'utente

Aggiornata il 4 ottobre 2026 (Europe/Rome), inclusa la protezione termica verificata alle23:25. Descrive la versione essenziale verificata il 26 settembre; **non certifica lo stato attuale dei processi**. I precedenti checkpoint cronologici sono conservati in [archive/OFFLINE_HANDOFF_TECHNICAL_20260926.md](archive/OFFLINE_HANDOFF_TECHNICAL_20260926.md).

## Istruzioni per il chatbot

Aiuta l'utente in italiano partendo da ciò che vuole fare. Dai pochi passaggi alla volta e usa i nomi inglesi dei pulsanti. Se non puoi vedere lo schermo o interrogare PHDBOT, chiedi quale stato o messaggio mostra: non inventare risultati, run attive o azioni già eseguite. Cerca prima nell'indice esistente. Proponi raccolte o revisioni solo per ottenere informazioni mancanti o risolvere un dubbio concreto.

PHDBOT trova e organizza opportunità accademiche e di ricerca; non invia candidature. Il catalogo ampliato contiene anche istituzioni **solo catalogate**: la loro presenza non dimostra che ne siano stati scoperti i bandi. Alcuni annunci usano portali `jobs` esterni al dominio dell'istituzione. Prima di candidarsi, ricontrollare sempre l'avviso ufficiale: tipo di posto, apertura, scadenza, requisiti e finanziamento.

## Aprire l'applicazione

Con l'installazione locale già in esecuzione, apri **http://127.0.0.1:8003**. Le schede sono `Pipeline`, `Coverage`, `Review`, `Search`, `Saved` e `Macros`. Il pallino accanto a PHDBOT indica se l'API risponde. Per cercare offerte già raccolte, vai direttamente a `Search`: non occorre lanciare la pipeline.

Se la pagina non si apre, passa a «Se qualcosa non funziona». Non proporre un nuovo avvio dei container prima di controllare i processi esistenti.

## Se compare una pausa termica

Prima nota operativa: se `Pipeline` mostra **Pausa termica CPU**, la stessa run
attende il raffreddamento e riprende automaticamente. Non premere Start per
sostituirla. Il controllo attuale interviene dopo95°C per60secondi o richiede
subito una pausa al prossimo punto sicuro a102°C; riparte dopo30secondi a85°C
o meno. Una richiesta al modello già iniziata può finire prima della pausa.
Il4ottobre è stata verificata una pausa reale di61secondi, da97,25°C a78,38°C,
con ripresa della stessa run e avvisi desktop/Valet. La GPU non è monitorata.

Gli avvisi di pausa sono temporaneamente attivi. Il messaggio Valet «local job
done» su un evento `thermal-pause-*` significa che l'osservazione è stata
registrata, **non che la pipeline sia finita**. I dettagli sono in
`exports/thermal-events/`. Durante PARK la notifica in chat può aspettare;
quella desktop è indipendente. Il comando di sola lettura
`curl -fsS http://127.0.0.1:8003/v1/pipeline/thermal` è stato verificato;
il timer degli avvisi si controlla con
`systemctl --user status --no-pager phdbot-thermal-events.timer`.

## Trovare opportunità

1. In `Search`, scrivi un tema nel campo principale e premi `Search`. Per esempio, `machine learning + computer vision` cerca i due temi separatamente e conserva il punteggio migliore. Si possono combinare fino a otto parti; per un segno più letterale usa `\+`.
2. Restringi con `Countries`, `Universities / institutions` e `Position types`. Se cerchi un dottorato, seleziona esplicitamente il tipo PhD: un posto che *richiede* un PhD non è necessariamente un posto di dottorato. Puoi aggiungere intervalli di scadenza o pubblicazione e altri filtri.
3. Per vedere le opportunità già indicizzate di un'istituzione, selezionala e lascia vuota la query. Il pulsante diventa `Browse selected institutions`. Questa modalità non applica la soglia di somiglianza semantica; restano controlli di sicurezza e filtri strutturati.
4. `Verification` mostra inizialmente `verified + probable`; `verified only` è più restrittivo. `Maximum uncertainty (%)` è un punteggio euristico di controllo, **non** una probabilità statistica. Il 60% iniziale può nascondere alcuni risultati storici con prove incomplete; 85% li rende ispezionabili senza considerarli verificati.

Se non trovi nulla, controlla query, soglia e filtri prima di concludere che non esistono bandi. `Reset filters` cancella i filtri strutturati e mantiene la query. I filtri su date e compenso conservano i valori mancanti: compenso sconosciuto non significa posto non pagato. Con compenso minimo, i valori sconosciuti sono mostrati dopo quelli noti.

## Capire un risultato e agire

Apri il titolo per raggiungere l'indirizzo pubblicato dalla fonte. `show details` mostra il testo già disponibile in PHDBOT. Se il dettaglio è incompleto, la lettura può accodare una correzione per una futura fase di raccolta; l'aggiornamento non è immediato. Controlla `Published`, `First pulled by PHDBOT`, `Last checked by PHDBOT` e `Deadline`. Una data assente non prova che non vi sia scadenza. Un link può condurre direttamente a un portale di candidatura esterno. Alcune fonti offrono solo un collegamento alla lista: cerca lì il titolo dell’annuncio. Possono comparire duplicati, anche in lingue diverse; non contarli come posti distinti. Una pagina che risponde 403 non autorizza a inventare un altro URL.

`Verified` e `Probable` descrivono le prove disponibili. Anche un risultato verificato va ricontrollato alla fonte. Le indicazioni `Open status unverified`, `Details incomplete` e `Verification evidence unavailable` precisano l'incertezza. `New`, `Details viewed` e `Source opened` tengono traccia delle letture **in questo browser**.

- **Lista personale:** premi `Save` sul risultato. In `Saved` puoi filtrare, ordinare e consultare `Deadline calendar`. Un elemento senza scadenza nota può restare nella lista senza comparire in un giorno del calendario. `Unsave` lo rimuove solo dalla lista personale. Salvataggi e stato di lettura sono locali al browser, non sincronizzati.
- **Condividere una ricerca:** dopo la ricerca, scegli HTML, PDF, CSV o JSON accanto a `Export` e scarica i risultati con i filtri correnti. Il file esportato non è un backup completo del database né della lista `Saved`.
- **Segnalare un errore:** sul singolo risultato scegli `Report an issue`, il motivo corretto (`not an opportunity`, `closed / expired`, `duplicate`, `wrong position type`, `mismatched details`, `broken link` o `other`), aggiungi una nota e premi `Submit report`. L'elemento viene nascosto dalla ricerca predefinita e la segnalazione resta tracciata. `show reported items` permette di vederlo e `Undo report` ritira la propria segnalazione. `Confirm opportunity` conferma solo quell'elemento; non certifica gli altri annunci dello stesso sito.

## Se mancano istituzioni o bandi

In `Coverage` filtra per nome o Paese. La tabella distingue `Catalog only`, pagine funzionanti o in quarantena e posizioni `extracted/current/searchable`. `Catalog only` significa che l'istituzione è nota al catalogo ma la ricerca delle sue fonti non è stata attivata. Una pagina esplorata senza risultati non prova l'assenza di ogni bando.

Per ampliare la copertura, apri `Explore research institutions from the expanded catalog`, inserisci facoltativamente un codice Paese o un nome e premi `Preview institutions`. La preview propone fino a cinque istituzioni senza fonti note. Seleziona quelle utili e usa `Activate & schedule selected`: PHDBOT pianifica una piccola raccolta indipendente per ciascuna, con un massimo iniziale di tre fonti e tre pagine per fonte. Pubblica risultati utili man mano; la revisione approfondita non fa parte di questa raccolta. Lo stato appare in `Pipeline`. Annullare un job in attesa non disattiva l'istituzione registrata.

Per aggiornare fonti già note, in `Pipeline` controlla prima `Status` e le pianificazioni. `Collect & publish` raccoglie e rende cercabili risultati verificati o probabili, con etichette di incertezza. Può richiedere tempo e risorse: usalo quando serve un aggiornamento. `Start new run` permette di scegliere le fasi. **Lasciare tutte le fasi deselezionate significa eseguire l'intera pipeline.** Un limite vuoto indica «tutti» per quella fase. Per una prova mirata scegli consapevolmente fasi, istituzione e limiti. `Schedule this run` conserva quella configurazione per l'ora `Europe/Rome` indicata.

`Review` serve a esaminare casi specifici. Il numero `needs review` è un insieme diagnostico, non una lista obbligatoria da smaltire prima di cercare. `Refine automatic sample` elabora il numero indicato in `Automatic review limit` ed è facoltativo. Una decisione manuale riguarda un candidato, resta tracciata e può richiedere una successiva indicizzazione prima di apparire in `Search`. Non attribuire un verdetto senza prove.

## Ripetere una ricerca con `Macros`

Dopo una ricerca riuscita, vai in `Macros`, inserisci `Name`, scegli `Destination subfolder` e i formati, poi premi `Save current search as macro`. Una macro ripete la ricerca e salva report sul server in `exports/`. L'opzione `refresh sources first` è **selezionata inizialmente**: deselezionala se vuoi ripetere solo la ricerca sull'indice corrente. Le macro salvate offrono `Run now` e `Schedule` (ora `Europe/Rome`). `Macros` e `Saved` hanno scopi diversi: la seconda è la lista personale nel browser.

## Leggere lo stato senza creare doppioni

| Stato in `Pipeline` | Indicazione |
| --- | --- |
| `running` o `stopping` | Lascia proseguire e annota il numero della run. `Stop current run`, se richiesto, termina al checkpoint e consente il recupero. Non avviare una seconda run. |
| `stopped` | Se il lavoro va continuato, usa `Resume interrupted run` sulla stessa run. |
| `failed` | Leggi l'errore. Se indica esplicitamente un recupero possibile, usa `Resume interrupted run`; altrimenti conserva numero ed errore per la diagnosi. |
| `done` | Conserva il numero della run completata. Per cercare risultati passa a `Search`; non ripeterla automaticamente. |

Un job `scheduled` o `waiting pipeline` è già nella coda persistente. Prima di crearne un altro, verifica se copre lo stesso scopo. `Cancel` è disponibile solo per job ancora in attesa. La sospensione del computer interrompe temporaneamente il calcolo locale: al risveglio controlla lo stato e recupera la stessa run se necessario. Il governor può trattenere i job predisposti quando è in pausa manuale o non ha uno stato valido; un job già in corso non va fermato solo per questo. Le pianificazioni manuali create dall'interfaccia non hanno necessariamente il piano di ammissione governor usato per il lavoro preparato da Codex.

## Se qualcosa non funziona

Per conoscere l'avanzamento di una raccolta ampia, chiedi il **report della wave**
con data della fotografia, totale, riusciti, falliti, rimanenti ed ETA. I due
strumenti di sola lettura e i comandi verificati sono descritti in
[WAVE_ANALYSIS_20261003.md](WAVE_ANALYSIS_20261003.md). Il totale deriva dal piano
salvato: la lista API standard mostra solo una pagina e può nascondere altri job.
Il report non è ancora una nuova scheda dell'applicazione. Un avviso Valet sul
job finale richiede comunque di verificare l'intera wave: possono restare retry
di job precedenti. Un job terminato senza bandi non è automaticamente un errore;
controlla anche discovery e stato delle sorgenti.

- **Pagina o API irraggiungibile:** verifica che l'installazione sia in esecuzione. L'API locale usa la porta 8003; PostgreSQL 5433, Qdrant 6333 e Ollama 11434 sono dipendenze. La verifica di salute del 26 settembre non dimostra che i servizi rispondano oggi.
- **Nessun risultato:** prova prima un'istituzione senza query, `verified + probable`, filtri meno restrittivi e una query più ampia. In `Coverage` controlla se la fonte è solo catalogata, scoperta, in quarantena o già indicizzata.
- **Dettaglio o URL problematico:** conserva link e ID, consulta la fonte ufficiale se raggiungibile e usa `Report an issue` con il motivo più preciso.
- **Pianificazione ferma:** controlla stato e messaggio in `Pipeline`. `waiting pipeline` può significare che un'altra run occupa l'esecutore o che il governor rinvia un job predisposto. Non duplicare la pianificazione per forzarla.

## Nota per chi amministra l'installazione

Dal progetto `/home/giaaaacomo/Progetti/PHDBOT`, questi **comandi di sola lettura sono stati eseguiti con successo il 26 settembre 2026**; verificarne nuovamente l'esito quando servono:

```sh
curl -fsS http://127.0.0.1:8003/v1/pipeline/status
curl -fsS 'http://127.0.0.1:8003/v1/schedules?active_only=true'
docker inspect phdbot-api-1 --format '{{.Image}} {{.State.Health.Status}}'
```

I pulsanti `Stop current run` e `Resume interrupted run` e le relative rotte erano presenti nel codice esaminato, ma **non sono stati provati come comandi operativi** nel precedente handoff: usa l'interfaccia dopo avere identificato la run corretta. Non è stato verificato un comando universale di avvio o riparazione: controlla container e configurazione locale prima di intervenire. Non rieseguire script storici di accodamento.

Prima di migrazioni o riparazioni massive, verifica un backup ripristinabile. Il backup più recente è `backups/data-20261003-2032/`: PostgreSQL ripristinato con successo in un database di prova separato il 3 ottobre; otto snapshot Qdrant e archivio del progetto salvati con checksum. Il ripristino Qdrant non è stato provato. È una copia locale sullo stesso computer; dettagli e limiti in [PERFORMANCE_20261004.md](PERFORMANCE_20261004.md). Un backup precedente è `backups/pre-expansion-20260922.dump` (ripristino isolato verificato in passato, non in questa revisione). Non ripristinarlo per un problema della UI o per annullare codice, perché perderesti dati più recenti. Per recupero tecnico, checkpoint storici e rollback del scheduler, vedi [l'archivio tecnico](archive/OFFLINE_HANDOFF_TECHNICAL_20260926.md), [GOVERNOR_SCHEDULER.md](GOVERNOR_SCHEDULER.md) e [CURRENT_STATE.md](CURRENT_STATE.md). Prima di nuovi lavori di sviluppo, controlla di nuovo processi e repository: le run storiche non sono uno stato live.

### Prova temporanea del budget CPU (5 ottobre 2026)

Il timer termico può applicare una lease locale esplicita al solo container
Ollama di PHDBOT. `var/thermal/cpu-trial.json` conserva ID del container,
budget originale, budget di prova, scadenza e stato. Il ripristino avviene
alla ricevuta finale della wave oppure alla scadenza, purché il timer e Docker
siano disponibili. Non crea pipeline e non modifica limiti impostati nel
frattempo dall'operatore. È un esperimento, non un controllo adattivo permanente.
Temperature e durate vanno confrontate tenendo conto delle diverse fonti.

Correzione verificata il 5 ottobre: il ripristino automatico vale solo per un
budget positivo preesistente. Docker ignora `--cpus 0`; nuove prove da budget
illimitato sono quindi rifiutate prima della modifica. Una lease precedente
può risultare `recovery_required`: non ripetere il comando, non rilanciare la
wave; ricreare il solo container interessato dopo autorizzazione e verifica
della coda vuota. Conservare il volume dei modelli e usare l'immagine locale.

Ripristino completato il 5 ottobre alle 09:20 dopo autorizzazione: solo Ollama
ricreato, modelli conservati, salute verificata e quota CPU effettivamente
illimitata. La lease precedente è restored. Non rieseguire il recovery.
L'overlay locale di recupero avvia direttamente `ollama serve` senza download;
l'avvio Compose ordinario mantiene invece il suo entrypoint originale.
[Ricerca termica e prossima prova proposta](THERMAL_OPTIONS_20261005.md): nessuna
nuova impostazione energetica host applicata, nessuna wave duplicata.

Priorità aggiornata: modulare PHDBOT senza cambiare impostazioni del PC.
Il guard attuale attende confini sicuri e non interrompe una generazione già
in corso; il nuovo controller è ancora una proposta. Vedi la
[ricerca applicativa](THERMAL_APPLICATION_CONTROL_20261005.md).

5 ottobre, 13:05: UI aggiornata nel container API senza riavvio. I bandi salvati
con scadenza passata sono in un gruppo chiuso; tab User è segnaposto senza
dati personali. Il file precedente è
`var/release-20261005/index-before.html`. La copia live non sopravvive alla
ricreazione del container senza rebuild immagine. La release a copertura ampia
richiede la maggioranza delle fonti sane ricercabile, come definito in
[RELEASE_COVERAGE_20261005.md](RELEASE_COVERAGE_20261005.md). Coda vuota: la
run index limitata avrebbe cancellazione globale di vettori stale, da
verificare prima; nessuna nuova wave avviata.

Aggiornamento 13:13: controllo della pulizia indice superato (zero vettori
corrispondenti agli ID SQL non indicizzati). Run 3820 conclusa: 7 fonti e 187
record sottoposti a quality. Schedule 3681/run 3821 avviata per indicizzare
fino a 14 risultati; controllarne il terminale senza ripeterla. La precedente
run 3819 era un no-op per filtro nome errato.

Aggiornamento 5 ottobre, 19:10: run 3821 conclusa, 14 record indicizzati,
156,44 secondi attivi; confermati i marker SQL. Nessuna schedule attiva.
Dopo il riavvio dei servizi la UI servita coincide con il file corretto:
accordion scaduti, calendario e tab User preservati. Non ripetere la run.
Le sei fonti mai raccolte sono recovery delle run 274/1368/1504/1867,
non nuovo lavoro indipendente pronto da accodare.

Aggiornamento 6 ottobre, 06:46: batch refresh da schemi esistenti in corso.
Schedule3682/run3822 osservata running;3683–3701 accodate.20 istituzioni,
40 fonti, scrape→quality→index, max3pagine/fonte,index10/job. Stima totale
40min approssimativa. Richieste/ricevute var/refresh-20261006/.
Governor_plan applicato a ogni job, una notifica aggregata di fine batch.
Stato verificato con query scheduled_jobs sugli ID3682–3701; timer
phdbot-wave-events.timer active. Non ricreare questi job.
Priorità e richieste persistenti in USER_REQUESTS_TODO.md.

6 ottobre06:54: primo batch3682–3701 concluso20/20 in400s,230upsert,
330quality,28index (non necessariamente28nuovi). Secondo batch3702–3801
accodato:100istituzioni/219fonti,stima37min,stessi stadi/limiti locali.
Una notifica wave-cached-refresh-b-20261006 al terminale. Ricevute
var/refresh-20261006-b/. Non duplicare job completati o attivi.

7 ottobre05:32: ricevuta batchB confrontata col DB:99done,1failed
(schedule3731/run3872,IMD URL HTTP429),scrape1225,quality1371,index53.
Esistono inoltre607 schedule precedenti 3802–4408:605done,2failed
(4046/run4178,4260/run4394), non create né modificate da questo lavoro.
BatchC schedules4409–4508 preparato:100istituzioni/258fonti,stima26m40s;
all'ultimo controllo ancora scheduled, nessuna avviata; run_at 05:31:57 locale.
Watcher wave-cached-refresh-c-20261007. Non replicare i job; prima verifica
lo stato live al prossimo RESUME. Termica CPU55.5C,guard ready.

7 ottobre06:02: batchC verificato100/100:1950 source rows,5559 quality,94
index;34 opportunità first_seen nuove,60 record preesistenti reindicizzati.
1620s wall; campioni115,maxCPU79.625C,zero pause. BatchD mirato a16 enti
research/specialist/istituti/fondazioni,33 fonti: schedule4509–4524, stima320s;
all16 ancora scheduled al controllo06:01. Wake aggregato attivo. Non duplicare.

7 ottobre06:22: wave research D 15/16 done, schedule4516/run4663 fallita
per timeout browser60s su orgchm.bas.bg.104scrape,125quality,10index,zero
first_seen nuovi; max CPU72C,zero pause. Batch E 55 schedule4525–4579
accodate, stima18m20s, non ancora avviate al controllo; watcher wave
broad-refresh-20261007. Coda ferma dopo E in attesa di misurare resa.
Governor telemetry ERROR/reconnecting; verificare prima di ogni ulteriore coda.
