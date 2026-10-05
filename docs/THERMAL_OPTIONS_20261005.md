# Gestione termica: ricerca e proposta, 5 ottobre 2026

## Risultato operativo

Ripristino Ollama autorizzato ed eseguito alle 09:20, a coda vuota e sotto lock
pipeline: container sano, stessa immagine e stesso inventario dei modelli nel
volume persistente. NanoCpus=0 e cgroup `cpu.max=max 100000` verificati.
La lease CPU4 è `restored`; ricevuta locale in
`var/thermal-20261005/recovery-receipt.json`. Non ripetere il recovery.

I due esperimenti precedenti non dimostrano un vantaggio del limite CPU4:
carichi diversi, picchi simili, pause ancora necessarie. Vedi
[confronto misurato](THERMAL_TRIAL_20261005.md). La ricerca seguente identifica
possibilità, non risultati termici già ottenuti.

## Hardware e controlli realmente disponibili

Lenovo Legion 7 16ACHg6 (82N6), Ryzen 7 5800H, RTX 3080 Laptop 16 GB.
Base NotePal XL inclinata e ventilata, secondo l'utente. Kernel 7.0.0-34-generic.

- Profilo ACPI attuale **performance**; disponibili low-power, balanced,
  performance, custom.
- Driver CPU amd-pstate-epp, modalità active; governor powersave, EPP
  balance_performance. In questo driver powersave non significa frequenza
  bassa fissa. EPP balance_power e power disponibili; dynamic non disponibile.
- Boost abilitato; limite superiore CPU letto circa 4,465 GHz.
- TLP attivo; power-profiles-daemon, tuned e thermald inattivi.
  La configurazione esplicita letta include PLATFORM_PROFILE_ON_BAT=low-power.
  Non è stata modificata la configurazione energetica dell'host.
- NVIDIA in idle: 41°C, circa 17 W; power.limit=N/A, default=115 W,
  min=1 W, max=165 W. Questi estremi NON provano che sia possibile impostare
  un limite: nessuna scrittura GPU provata. Il primo tentativo nella sandbox
  non vedeva il driver; il controllo fuori sandbox è riuscito.
- Ollama 0.32.14; nessun modello caricato al controllo. Non conosciamo ancora
  la ripartizione CPU/GPU durante una generazione rappresentativa.

## Priorità dei metodi

| Priorità | Metodo | Motivazione e limite |
| --- | --- | --- |
| 1 | Profilo firmware balanced | È disponibile sul PC e governa politiche di potenza/raffreddamento. Prima prova proposta; la temperatura va misurata perché può cambiare anche la ventilazione. |
| 2 | EPP balance_power | Preferenza di efficienza del processore, più pertinente di una semplice quota di tempo CPU. Non è un tetto in watt né una garanzia di temperatura. |
| 3 | Tetto moderato di frequenza CPU | Limita i picchi di boost; scegliere il valore dopo il profiling. Disabilitare completamente il boost è un'alternativa più drastica, da misurare separatamente. |
| 4 | Ridurre lavoro LLM e memoria necessaria | Riuso degli schemi, contesto proporzionato e meno generazioni possono ridurre sia durata sia energia. Verificare qualità e reale collocazione GPU. |
| 5 | Limite di potenza GPU | Interessante solo se supportato e se i dati mostrano un contributo rilevante della GPU. Il supporto in scrittura su questo laptop resta da accertare. |
| Sempre | Pause con isteresi e notifiche | Conservare la protezione esistente anche durante le prove. Una politica preventiva dovrebbe ridurre le pause, non sostituire la protezione. |

Lenovo documenta il cambio delle modalità con Fn+Q; il kernel espone il profilo
ACPI. I nomi non garantiscono da soli un risultato termico: firmware, ventole,
ambiente e carico interagiscono. Non scegliere automaticamente low-power/quiet
come modalità più fredda. Fonti: [Lenovo, guida del modello](https://download.lenovo.com/pccbbs/pubs/legion_7_16_6/html_en/EN/performance_mode.html)
e [kernel, platform profile](https://docs.kernel.org/userspace-api/sysfs-platform_profile.html).

AMD P-State usa EPP come indicazione al firmware sul compromesso fra prestazioni
ed efficienza. Il controllo delle frequenze costituisce una leva diversa dalla
quota Docker, che limita il tempo CPU disponibile senza fissare frequenza o
potenza istantanea. Fonti: [AMD P-State nel kernel](https://www.kernel.org/doc/html/latest/admin-guide/pm/amd-pstate.html),
[CPUFreq](https://cdn.kernel.org/doc/html/latest/admin-guide/pm/cpufreq.html),
[risorse Docker](https://docs.docker.com/engine/containers/resource_constraints/).

TLP già gestisce impostazioni per alimentazione e batteria: un futuro controllo
deve coordinarsi con esso, registrare il valore originale e rispettare cambi
manuali o di alimentazione. Non aggiungere un secondo gestore che riscriva gli
stessi valori. Fonti: [TLP processore](https://linrunner.de/tlp/settings/processor.html)
e [TLP piattaforma](https://linrunner.de/tlp/settings/platform.html).

Nel codice `src/phd_searcher/pipeline/schema_gen.py` la richiesta imposta
`num_ctx=65536`: modificare solo il default del server non correggerebbe questa
richiesta. Prima misurare token effettivi e collocazione con `ollama ps` durante
lavoro utile. Contesto più piccolo, Flash Attention e cache KV q8 sono opzioni
separate: risparmiare memoria non dimostra automaticamente minori temperature;
la quantizzazione richiede controllo della qualità. Non ridurre arbitrariamente
la riserva GPU di circa 3 GiB usata anche per il desktop. Fonte:
[FAQ ufficiale Ollama](https://docs.ollama.com/faq).

NVIDIA permette limiti in watt solo sui dispositivi supportati. N/A sul limite
corrente impone una verifica di capacità prima di progettare un controller;
non prendere il minimo dichiarato di 1 W come valore pratico. Fonte:
[NVIDIA SMI](https://docs.nvidia.com/deploy/nvidia-smi/index.html).

## Metodi secondari e alternative non scelte ora

Non partire da undervolt, scritture dirette al controller delle ventole o
limiti SMU tramite utility non già integrate: aumentano dipendenze e complessità
di recupero prima di aver valutato i controlli firmware disponibili.
Un ulteriore acquisto di basi ventilate non è motivato dai dati raccolti.
Verificare o pulire fisicamente prese e ventole resta un controllo manuale
utile, ma non abbiamo evidenza di polvere o difetti. Non cambiare contemporaneamente
ventilazione esterna e impostazioni software durante il confronto.

Un controller preventivo può in seguito ridurre gradualmente il carico dopo
calore persistente e ripristinarlo solo dopo raffreddamento stabile. Servono
isteresi, durata minima della regolazione, scadenza recuperabile e verifica del
ripristino reale. È una proposta: non è stato installato un controller host.

## Prossima prova circoscritta

1. Preparare pochi input HTML già salvati e rappresentativi (corti, lunghi,
   schemi riutilizzabili), senza ripetere run concluse o scrivere nuovi bandi.
2. Salvare profilo/EPP/frequenze iniziali e definire ripristino verificabile,
   timeout e interazione con TLP. Confrontare inizialmente solo performance
   contro balanced, mantenendo invariati modello, prompt e parallelismo.
3. Alternare l'ordine delle condizioni con temperatura iniziale comparabile;
   separare caricamento a freddo e inferenza. Stima del test da ricavare dai
   tempi delle richieste selezionate, prima di accodarlo.
4. Misurare tempo totale incluse pause, p95 e picco CPU/GPU, tempo sopra soglia,
   watt GPU disponibili, token/s, errori ed equivalenza delle estrazioni.
   Senza energia CPU misurabile, non chiamare i watt GPU consumo dell'intero PC.
5. Scegliere il compromesso che riduce calore sostenuto preservando risultati
   e velocità utile; solo dopo valutare EPP, frequenza o contesto, una variabile
   per volta. Nessuna promessa numerica di miglioramento prima dei dati.

Nessuna nuova wave o benchmark accodato durante questa ricerca: il set comparabile
e il ripristino dei controlli host vanno ancora preparati. Coda osservata vuota;
le run terminate restano intatte. La release essenziale resta distinta da queste
ottimizzazioni facoltative.
