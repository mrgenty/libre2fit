# libre2fit
Script in Python per importare i dati della glicemia esportati da FreeStyle Libre (LibreLink) direttamente su Google Fit.

### 1\. Esportazione CSV da LibreView

1.  Accedi a [LibreView.com](https://www.libreview.com/) con le tue credenziali, verifica che sia impostata la lingua su "Italiano"

2.  Clicca sul tasto **Scarica dati glicemia** in alto a destra.

3.  Clicca su **Scarica**.

4.  Otterrai un file `.csv` che contiene lo storico completo delle registrazioni degli ultimi 18 mesi.

* * * * *

### 2\. Configurazione Google OAuth

1.  Vai sulla [Google Cloud Console](https://console.cloud.google.com/).

2.  Crea un **Nuovo Progetto** chiamato "libre2fit".

3.  Cerca **Fitness API** nella barra di ricerca e clicca su **Abilita**.

4.  Configura la **Schermata consenso OAuth**:

    -   Scegli **External**.

    -   Inserisci i dati richiesti.

    -   Se richiesto, in **Scopes**, aggiungi: `.../auth/fitness.blood_glucose.read` e `.../auth/fitness.blood_glucose.write`.

    -   **Fondamentale:** In "Test users", aggiungi l'indirizzo del tuo account Google (spesso @gmail.com) sul quale vuoi caricare i dati.

5.  Vai su **Credenziali**:

    -   Clicca **Crea credenziali** > **ID client OAuth**.

    -   Seleziona **Applicazione desktop**.

    -   Scarica il file JSON, rinominalo in `credentials.json` e mettilo nella cartella dello script.

* * * * *

### 3\. Utilizzo

1.  Installa i pacchetti: `pip install pandas requests google-auth-oauthlib`.

2.  Avvia lo script: `python nome_script.py`.

3.  Autorizza l'app nel browser.

4.  Se l'autorizzazione fa a buon fine, seleziona il file scaricato da LibreView e attendi il completamento della sincronizzazione.


**Attenzione**
Non eliminare il file *last_sync.txt*, in quanto viene utilizzato per evitare che eventuali sincronizzazioni future riscrivano dati già precedente inviati a Fit.

**Problemi noti**
Se LibreView è impostato in una lingua diversa dall'italiano, anche il CSV sarà in quella lingua. In questo caso lo script fallirà in quanto non sarà in grado di trovare l'intestazione del CSV.
