# ProgettoFinaleGit  
## Portale Web ProxMox – M340

## Descrizione
Questo progetto realizza un portale web per la richiesta e creazione automatica di macchine virtuali (container LXC) su ProxMox VE.
Gli utenti possono richiedere una macchina standardizzata, che viene approvata da un amministratore e creata tramite le API di ProxMox.

---

## Requisiti di sistema

### Lato ProxMox
- ProxMox VE funzionante
- Almeno:
  - 1 template LXC Debian
  - 1 VM dedicata per ospitare il portale web
- Token API ProxMox abilitato
- Accesso SSH al nodo ProxMox
- Eseguire comando per evitare problemi di quorum: pvect expected 1

### Lato VM del portale
- Debian 12
- Python 3.10+
- Connessione di rete verso il nodo ProxMox
- Utente: root
- Password: Password&1

---

## Installazione del portale web

Clonare il repository:
git clone https://github.com/<username>/<repository>.git  
cd <repository>

Creare ambiente virtuale Python:
python3 -m venv .venv  
source .venv/bin/activate

Installare le dipendenze:
pip install -r requirements.txt

Creare un file `.env` nella root del progetto con il seguente contenuto:

SECRET_KEY=supersecretkey

PROXMOX_HOST=https://IP_PROXMOX:8006/api2/json  
PROXMOX_NODE=px1  
PROXMOX_USER=root@pam  
PROXMOX_TOKEN_NAME=token-name  
PROXMOX_TOKEN_VALUE=token-value  

PROXMOX_SSH_HOST=IP_PROXMOX  
PROXMOX_SSH_USER=root  
PROXMOX_SSH_KEY=/percorso/chiave/id_rsa  

PROXMOX_LXC_TEMPLATE_ID=ID_TEMPLATE  

ADMIN_PASSWORD=admin  

Avvio dell’applicazione:
python app.py

Il portale sarà disponibile su:
http://IP_VM:5000

---

## Utilizzo

### Utente
- Registrazione e login
- Richiesta di una macchina (Bronze / Silver / Gold)
- Visualizzazione stato e credenziali nella pagina “My Requests”

### Amministratore
- Login come admin
- Approvazione o rifiuto delle richieste
- Creazione automatica della macchina su ProxMox

---

## Tipi di macchina disponibili

Bronze: 1 CPU core, 512 MB RAM, 2 GB disco  
Silver: 1 CPU core, 1 GB RAM, 4 GB disco  
Gold: 2 CPU core, 2 GB RAM, 6 GB disco  

---

## Funzionamento tecnico
- Clonazione container tramite API REST ProxMox
- Configurazione delle risorse hardware
- Avvio del container
- Impostazione automatica della password root via SSH
- Recupero automatico dell’indirizzo IP
- Salvataggio delle credenziali nel database
- Visualizzazione delle informazioni tramite interfaccia web

---

## Hosting del portale
Il portale web è ospitato su una VM dedicata su ProxMox, creata e dimensionata appositamente per il servizio, come richiesto dalla consegna.

---

## Consegna
- Repository GitHub con codice e README
- Cluster ProxMox completo (template + VM servizio)
- Video dimostrativo con demo

---


## Nota sull'hosting
Nota sull’hosting del portale nella VM

Durante la fase finale del progetto sono stati riscontrati problemi di configurazione di rete e accesso SSH all’interno della VM dedicata all’hosting del portale web, legati alla gestione delle chiavi SSH e alla configurazione del percorso della chiave sul sistema.

Per questo motivo il progetto viene consegnato completamente funzionante a livello di codice e logica applicativa, mentre l’esecuzione del portale sulla VM richiede i seguenti passaggi aggiuntivi:

Generazione manuale di una chiave SSH sulla VM del portale:

  ssh-keygen

Copia della chiave pubblica sul nodo ProxMox:

  ssh-copy-id root@IP_PROXMOX

Aggiornamento del percorso della chiave privata nel file .env:

  PROXMOX_SSH_KEY=/percorso/corretto/id_rsa

Una volta completati questi passaggi, il portale può essere avviato correttamente anche dalla VM dedicata, mantenendo invariato il codice dell’applicazione.

---

## Fonti utilizzate
https://pve.proxmox.com/wiki/Proxmox_VE_API  
https://flask.palletsprojects.com/  
https://www.debian.org/
https://chatgpt.com