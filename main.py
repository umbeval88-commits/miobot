import requests
import feedparser
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- TRUCCO PER HUGGING FACE: MINI SERVER DI VITA ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot attivato e funzionante in background!")

def avvia_server_controllo():
    server_address = ('', 7860)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    httpd.serve_forever()

# --- CONFIGURAZIONE BOT ---
TOKEN = "8845798324:AAGAoFnMGLwrvLO-qJa6gT2moFBzHg2CWT8"
CHAT_ID = "-1001798648198"
TAG = "scontierisp0d-21"
FILE_MEMORIA = "pubblicati.txt"

# --- LISTA FONTI AD ALTO VOLUME ---
FONTI_SCONTI = [
    "https://www.tariffando.it/feed/",
    "https://www.smartworld.it/feed",
    "https://www.spaziogames.it/feed/",
    "https://www.tomshw.it/feed/"
]

def ora_consentita():
    fuso_italia = timezone(timedelta(hours=2)) 
    ora_italiana = datetime.now(fuso_italia)
    minuti_attuali = (ora_italiana.hour * 60) + ora_italiana.minute
    inizio_lavoro = (8 * 60) + 30  
    fine_lavoro = 21 * 60          
    return inizio_lavoro <= minuti_attuali <= fine_lavoro

def gia_pubblicato(link_id):
    try:
        with open(FILE_MEMORIA, "r") as f:
            return link_id in f.read().splitlines()
    except FileNotFoundError:
        return False

def salva_in_memoria(link_id):
    with open(FILE_MEMORIA, "a") as f:
        f.write(link_id + "\n")

def pulisci_e_trasforma_link(url):
    try:
        if "amzn.to" in url or "t.me" in url:
            res = requests.head(url, allow_redirects=True, timeout=10)
            url = res.url
        match = re.search(r'/(dp|gp/product)/([A-Z0-9]{10})', url)
        if match:
            asin = match.group(2)
            return f"https://www.amazon.it/dp/{asin}?tag={TAG}", asin
    except:
        pass
    return None, None
    
def invia_telegram(foto, testo):
    # Usiamo il metodo sendPhoto dell'API Telegram
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    dati = {
        "chat_id": CHAT_ID,
        "photo": foto,
        "caption": testo,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, data=dati, timeout=60)
        if res.status_code == 200:
            print(f"✅ Messaggio con foto inviato!", flush=True)
        else:
            print(f"⚠️ Errore Telegram {res.status_code}: {res.text}", flush=True)
    except Exception as e:
        print(f"❌ Errore connessione: {e}", flush=True)

# --- AVVIO BOT ---
threading.Thread(target=avvia_server_controllo, daemon=True).start()

while True:
    print("DEBUG: Avvio un nuovo ciclo completo di controllo...", flush=True)
    if ora_consentita():
        print("DEBUG: L'orario è consentito. Inizio a controllare i siti...", flush=True)
        for fonte in FONTI_SCONTI:
            print(f"DEBUG: Sto scaricando il feed da: {fonte}", flush=True)
            feed = feedparser.parse(fonte)
            print(f"DEBUG: Trovati {len(feed.entries)} articoli in questo feed.", flush=True)
            
            for entry in feed.entries:
                contenuto = entry.get('content', [{'value': ''}])[0]['value'] or entry.get('summary', '')
                soup = BeautifulSoup(contenuto, 'html.parser')
                link_amazon = next((a['href'] for a in soup.find_all('a', href=True) if "amazon.it" in a['href'] or "amzn.to" in a['href']), None)
                
                if link_amazon:
                    print(f"DEBUG: Trovato link Amazon nell'articolo: {entry.title}", flush=True)
                    link_pulito, asin = pulisci_e_trasforma_link(link_amazon)
                    id_univoco = asin if asin else link_amazon
                    
                    if not gia_pubblicato(id_univoco):
                        print(f"DEBUG: Nuova offerta mai pubblicata! Procedo con l'invio...", flush=True)
                        img_tag = soup.find('img', src=True)
                        foto_url = img_tag['src'] if img_tag else "https://images.unsplash.com/photo-1523474253046-8cd2748b5fd2?w=600"
                        titolo = entry.title.replace("<", "").replace(">", "")
                        messaggio = f"🛍️ <b>{titolo}</b>\n\n🔥 Super occasione!\n\n👉 <b>Acquista qui</b>: {link_pulito}"
                        invia_telegram(foto_url, messaggio)
                        salva_in_memoria(id_univoco)
                        time.sleep(5)
                    else:
                        print(f"DEBUG: Articolo già pubblicato in passato ({id_univoco}), lo salto.", flush=True)
                
            time.sleep(5)
    else:
        print("DEBUG: Ora non consentita dalle impostazioni. Il bot riproverà tra 5 minuti.", flush=True)
        time.sleep(300)
