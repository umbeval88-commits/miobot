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
    "https://www.amazon.it/gp/deals/feed/", # Il feed ufficiale Amazon (se funzionante)
    "https://www.hdblog.it/feed/",
    "https://feeds.feedburner.com/scontiamolo", # Storico per le offerte Amazon
    "https://www.tecnocino.it/feed/",
    "https://www.offerte-amazon.it/feed/",
    "https://www.idealo.it/feed/blog.xml"
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
    # Invece di inviare una foto, inviamo solo il testo (più leggero e veloce)
    messaggio_finale = f"{testo}\n\n[Immagine: {foto}]"
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    dati = {"chat_id": CHAT_ID, "text": messaggio_finale, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=dati, timeout=60)
        if res.status_code == 200:
            print(f"✅ Messaggio inviato!", flush=True)
        else:
            print(f"⚠️ Errore Telegram {res.status_code}: {res.text}", flush=True)
    except Exception as e:
        print(f"❌ Errore connessione: {e}", flush=True)

# --- AVVIO BOT ---
threading.Thread(target=avvia_server_controllo, daemon=True).start()

while True:
    if ora_consentita():
        for fonte in FONTI_SCONTI:
            feed = feedparser.parse(fonte)
            for entry in feed.entries:
                contenuto = entry.get('content', [{'value': ''}])[0]['value'] or entry.get('summary', '')
                soup = BeautifulSoup(contenuto, 'html.parser')
                link_amazon = next((a['href'] for a in soup.find_all('a', href=True) if "amazon.it" in a['href'] or "amzn.to" in a['href']), None)
                
                if link_amazon:
                    link_pulito, asin = pulisci_e_trasforma_link(link_amazon)
                    if asin and not gia_pubblicato(asin):
                        img_tag = soup.find('img', src=True)
                        foto_url = img_tag['src'] if img_tag else "https://images.unsplash.com/photo-1523474253046-8cd2748b5fd2?w=600"
                        titolo = entry.title.replace("<", "").replace(">", "")
                        messaggio = f"🛍️ <b>{titolo}</b>\n\n🔥 Super occasione!\n\n👉 <b>Acquista qui</b>: {link_pulito}"
                        invia_telegram(foto_url, messaggio)
                        salva_in_memoria(asin)
                        time.sleep(60) 
        time.sleep(180)
    else:
        time.sleep(300)
