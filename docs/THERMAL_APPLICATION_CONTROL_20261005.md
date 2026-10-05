# Modulazione termica del programma — 5 ottobre 2026

## Decisione e ambito

L'utente preferisce modulare PHDBOT senza modificare il PC; la sicurezza precede
la velocità. Questo documento sostituisce la precedente priorità di provare il
profilo firmware balanced. Non sono stati modificati profili energetici, boost,
frequenze, ventole o TLP. È stato ripristinato il solo container Ollama dopo
l'esperimento CPU4, come autorizzato. Questa fase aggiunge ricerca e progetto,
non un nuovo controller in produzione.

## Precedenti pertinenti, con fonti primarie

| Progetto | Strategia documentata | Applicazione a PHDBOT |
| --- | --- | --- |
| [BOINC](https://github.com/BOINC/boinc/wiki/Preferences) | Distingue percentuale dei processori utilizzati e percentuale di tempo CPU; quest'ultima alterna lavoro e sospensione. | Separare quantità di lavoro simultaneo e ritmo nel tempo; non confondere quattro CPU equivalenti con un obiettivo termico. |
| [TThrottle](https://efmer.com/tthrottle/tthrottle-manual/) | Regola il tempo di esecuzione dei processi in base alla temperatura CPU/GPU, sospendendo brevemente i thread. | Precedente diretto per un duty cycle adattivo. È un programma Windows: copiare il principio, non installarlo su Linux né imitare alla cieca la sospensione dei processi GPU. |
| [Android ADPF](https://developer.android.com/games/optimize/adpf/thermal) | Usa stato termico e previsione del margine disponibile per ridurre il carico prima del throttling. | Usare andamento della temperatura e durata attesa del lavoro per anticipare il rallentamento. Le API Android non sono disponibili sul nostro host. |
| [ADPF, buone pratiche](https://developer.android.com/games/optimize/adpf/best-practices-adpf) | Regolazioni graduali e specifiche per il carico; profiling e prove prolungate. | Livelli piccoli e misurabili, una leva per prova. Ridurre il ritmo, senza abbassare l'affidabilità dei bandi. |
| [llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/docs/development/token_generation_performance_tips.md) | Troppi thread possono peggiorare l'inferenza; suggerisce misurare il numero adatto. | Un numero di thread controllato può essere migliore della quota Docker, ma il beneficio termico va misurato. |

Non emerge una curva periodica universalmente ottimale. La proposta è cercare un
carico sostenibile e correggerlo con feedback: rallentamento tempestivo, recupero
lento, pause solo quando necessarie. Una sequenza fissa di sprint e lunghe pause
ignora temperatura iniziale, carico delle pagine e altri programmi. Anche un duty
cycle riduce soprattutto il carico medio: una singola raffica può restare calda.
Queste sono deduzioni progettuali, non un risultato sperimentale su PHDBOT.

## Cosa esiste già e cosa manca

Verifica del codice corrente:

- `thermal.py` legge sensori CPU, applica isteresi temporale e blocca quando i
  sensori sono invalidi o troppo vecchi. Non monitora la temperatura GPU.
- `throttle_requested` esiste e viene esposto nello stato, ma non risulta
  collegato a un regolatore progressivo del lavoro applicativo.
- `pipeline/progress.py` attende il raffreddamento ai confini sicuri;
  `schema_gen.py` controlla prima dei tentativi di generazione.
- La chiamata schema a Ollama è non-streaming con timeout HTTP di 600 secondi:
  una pausa richiesta durante questa chiamata non ne interrompe il calcolo.
  Il limite di token già presente non garantisce un limite di temperatura.
- Le pipeline sono già serializzate e Ollama è configurato con parallelismo 1:
  non promettere vantaggi riducendo da molte a una richiesta quando è già una.

**Il guard attuale non garantisce un arresto immediato del carico a temperatura
critica.** Il messaggio nel codice dice esplicitamente "next safe boundary".
Le protezioni hardware restano necessarie. Prima di una prova pesante va risolto
o delimitato sperimentalmente questo intervallo di mancato controllo.

## Controller proposto, limitato a PHDBOT

1. Un solo punto di ammissione del lavoro costoso, condiviso dai percorsi modello:
   schema, review ed embedding. Il crawler non va considerato gratuito: browser
   e parsing possono anch'essi pesare sulla CPU.
2. Stato a livelli: normale, moderato, ridotto, pausa. Usare temperatura corrente,
   media smussata e pendenza su più campioni; l'emergenza usa comunque il valore
   grezzo, senza aspettare che la media salga. CPU e GPU hanno limiti distinti.
3. Ritmo adattivo: dopo lavoro costoso, introdurre un intervallo limitato in base
   al tempo di calcolo e allo stato termico. Le attese I/O già trascorse contano
   come recupero: evitare attese duplicate. Nessun credito accumulato che permetta
   una grande raffica dopo inattività. Un nuovo segnale caldo prevale sul timer.
4. Ridurre rapidamente il ritmo quando il calore cresce; rialzarlo gradualmente
   solo dopo raffreddamento stabile. Durata minima dei livelli e isteresi evitano
   oscillazioni. Guadagni e soglie si calibrano su dati, non su valori arbitrari.
5. Dimensionare thread e batch del backend con pochi profili verificati. Nel
   [codice Ollama 0.32.14](https://raw.githubusercontent.com/ollama/ollama/v0.32.14/api/types.go)
   num_thread, num_batch e num_ctx sono opzioni del runner impostate al caricamento:
   non sono manopole continue per una richiesta già in corso. Cambiarle spesso
   può comportare ricaricamenti; verificarne costo e supporto per ogni modello.
6. Conservare qualità, checkpoint e notifiche. Eventuali risultati interrotti
   non diventano rifiuti del bando e non consumano retry come errori di estrazione.
   Dopo un evento critico non ripartire automaticamente a pieno carico.

### Richieste lunghe: requisito preliminare di sicurezza

Progettare un percorso di cancellazione cooperativa con checkpoint. Chiudere la
connessione HTTP o cancellare una coroutine NON prova che Ollama abbia cessato
il lavoro: verificarlo lato server/runner e con utilizzo effettivo delle risorse.
Se non è verificabile, non presentarlo come protezione attiva. Lo streaming può
aiutare a osservare avanzamento e cancellare, ma non crea da solo una pausa del
calcolo. Non spezzare una generazione in molti prompt: ripetere il prefill può
consumare più tempo ed energia.

Non usare SIGSTOP/SIGCONT o docker pause sul servizio come primo approccio:
possono congelare timeout e richieste e non costituiscono prova di fermare kernel
GPU già inviati. Non introdurre PID/MPC complessi prima di aver identificato
risposta termica e ritardo degli attuatori. Nice/priorità non è un tetto di carico
su una macchina altrimenti libera.

## Validazione prima del rilascio

- Test deterministici con tracce termiche sintetiche: picco brusco, salita lenta,
  sensori persi/vecchi, recupero, stop dell'utente e assenza di raffiche al riavvio.
- Replay delle tracce già raccolte per verificare le decisioni del controller.
  Il replay non dimostra quale sarebbe stata la temperatura sotto un altro carico.
- Verifica separata della cancellazione effettiva del backend con lavoro breve
  e limitato, prima di esporre la macchina a un carico sostenuto.
- Poi canary con stessi input HTML, modello e qualità attesa, una variabile per
  volta. Misurare picco/p95 CPU e GPU, tempo sopra soglia, velocità di salita,
  durata totale incluse pause, estrazioni valide e lavoro sprecato/interrotto.
- Una prova breve controlla sicurezza e funzionamento; solo successivamente una
  prova più lunga e delimitata può verificare la stabilizzazione termica.

Nessuna wave o benchmark lanciato per questa ricerca. La prossima unità utile è
implementare e testare il controller in isolamento e verificare la cancellazione,
non modificare profili del PC. Il miglioramento termico e l'eventuale beneficio
sui tempi restano da misurare: la sicurezza può richiedere anche più tempo totale.
