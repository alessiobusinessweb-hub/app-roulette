from datetime import datetime
import hashlib
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st

# Configurazione Pagina Streamlit per Smartphone/PC
st.set_page_config(
    page_title="Roulette Analytics Pro", page_icon="🎯", layout="centered"
)

# CHIAVE SEGRETA AMMINISTRATORE (Deve essere uguale a quella del tuo generatore!)
SECRET_KEY = "MIA_CHIAVE_SUPER_SEGRETA_ROULETTE"


# ==========================================
# VERIFICA LICENZA A SCADENZA
# ==========================================
def verifica_licenza(codice_licenza):
  try:
    parti = codice_licenza.strip().split("-")
    if len(parti) != 3:
      return False, "Formato codice non valido.", None

    nome_utente, data_str, firma_ricevuta = parti
    payload = f"{nome_utente.upper()}-{data_str}"

    # Verifichiamo l'autenticità della firma
    firma_calcolata = hashlib.sha256(
        f"{payload}{SECRET_KEY}".encode()
    ).hexdigest()[:8]
    if firma_ricevuta.lower() != firma_calcolata.lower():
      return False, "Codice di licenza contraffatto o errato.", None

    # Verifichiamo la data di scadenza
    data_scadenza = datetime.strptime(data_str, "%Y%m%d")
    data_oggi = datetime.now()

    if data_oggi > data_scadenza:
      return (
          False,
          f"Licenza per {nome_utente} SCADUTA il"
          f" {data_scadenza.strftime('%d/%m/%Y')}!",
          data_scadenza,
      )

    return (
        True,
        f"Licenza per {nome_utente} ATTIVA fino al"
        f" {data_scadenza.strftime('%d/%m/%Y')}",
        data_scadenza,
    )
  except Exception:
    return False, "Errore durante la verifica del codice.", None


# ==========================================
# PARSER HTML
# ==========================================
def estrai_numeri_da_html(contenuto_html):
  soup = BeautifulSoup(contenuto_html, "html.parser")
  numeri = []
  elementi = soup.find_all(
      lambda tag: tag.has_attr("data-role")
      and tag["data-role"].startswith("number-")
  )
  for el in elementi:
    valore_str = el["data-role"].replace("number-", "").strip()
    if valore_str.isdigit() and 0 <= int(valore_str) <= 36:
      numeri.append(int(valore_str))

  if not numeri:
    spans = soup.find_all("span", class_="YLMNPL")
    for s in spans:
      txt = s.get_text().strip()
      if txt.isdigit() and 0 <= int(txt) <= 36:
        numeri.append(int(txt))

  return numeri[::-1]


# ==========================================
# STATO DELLA SESSIONE (MEMORIA APP)
# ==========================================
VALORE_UNITA_BASE = 0.10
MAX_COLPI_CICLO = 5
ROSSI = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

if "bankroll_iniziale" not in st.session_state:
  st.session_state.bankroll_iniziale = 50.0
if "bankroll" not in st.session_state:
  st.session_state.bankroll = 50.0
if "peak_bankroll" not in st.session_state:
  st.session_state.peak_bankroll = 50.0
if "cronologia" not in st.session_state:
  st.session_state.cronologia = []
if "ciclo_attivo" not in st.session_state:
  st.session_state.ciclo_attivo = False
if "terna_corrente" not in st.session_state:
  st.session_state.terna_corrente = []
if "colpo_attuale_ciclo" not in st.session_state:
  st.session_state.colpo_attuale_ciclo = 0
if "pezzi_per_numero" not in st.session_state:
  st.session_state.pezzi_per_numero = 2
if "terne_escluse" not in st.session_state:
  st.session_state.terne_escluse = set()
if "storico_stati" not in st.session_state:
  st.session_state.storico_stati = []
if "autenticato" not in st.session_state:
  st.session_state.autenticato = False


# ==========================================
# LOGIN CON LICENZA A SCADENZA
# ==========================================
st.sidebar.title("🔑 Attivazione Licenza")
licenza_input = st.sidebar.text_input(
    "Inserisci Codice Licenza:", type="password"
)

if licenza_input:
  valido, messaggio, scadenza = verifica_licenza(licenza_input)
  if valido:
    st.session_state.autenticato = True
    st.sidebar.success(messaggio)
  else:
    st.session_state.autenticato = False
    st.sidebar.error(messaggio)
else:
  st.session_state.autenticato = False
  st.sidebar.info("👋 Inserisci la tua licenza personale per accedere.")


# ==========================================
# LOGICA DI CALCOLO E STAKING
# ==========================================
def calcola_pezzi_aggressivi(bankroll_attuale, bankroll_iniziale):
  profitto = bankroll_attuale - bankroll_iniziale
  if bankroll_attuale >= bankroll_iniziale * 1.8:
    return 5
  elif bankroll_attuale >= bankroll_iniziale * 1.4:
    return 4
  elif bankroll_attuale >= bankroll_iniziale * 1.1:
    return 3
  elif profitto >= -3.0:
    return 2
  elif bankroll_attuale < bankroll_iniziale - 10.0:
    return 1
  else:
    return 2


def salva_snapshot():
  snapshot = {
      "bankroll": st.session_state.bankroll,
      "peak_bankroll": st.session_state.peak_bankroll,
      "cronologia": list(st.session_state.cronologia),
      "ciclo_attivo": st.session_state.ciclo_attivo,
      "terna_corrente": list(st.session_state.terna_corrente),
      "colpo_attuale_ciclo": st.session_state.colpo_attuale_ciclo,
      "pezzi_per_numero": st.session_state.pezzi_per_numero,
      "terne_escluse": set(st.session_state.terne_escluse),
  }
  st.session_state.storico_stati.append(snapshot)


def annulla_ultimo_tiro():
  if st.session_state.storico_stati:
    snap = st.session_state.storico_stati.pop()
    st.session_state.bankroll = snap["bankroll"]
    st.session_state.peak_bankroll = snap["peak_bankroll"]
    st.session_state.cronologia = snap["cronologia"]
    st.session_state.ciclo_attivo = snap["ciclo_attivo"]
    st.session_state.terna_corrente = snap["terna_corrente"]
    st.session_state.colpo_attuale_ciclo = snap["colpo_attuale_ciclo"]
    st.session_state.pezzi_per_numero = snap["pezzi_per_numero"]
    st.session_state.terne_escluse = snap["terne_escluse"]


def elabora_tiro(nuovo_numero):
  salva_snapshot()
  st.session_state.cronologia.append(nuovo_numero)
  crono = st.session_state.cronologia

  if st.session_state.ciclo_attivo:
    pezzi = st.session_state.pezzi_per_numero
    costo_fiches = pezzi * VALORE_UNITA_BASE
    spesa = 3 * costo_fiches
    st.session_state.bankroll -= spesa
    st.session_state.colpo_attuale_ciclo += 1

    if nuovo_numero in st.session_state.terna_corrente:
      vincita = (costo_fiches * 35) + costo_fiches
      st.session_state.bankroll += vincita
      st.session_state.ciclo_attivo = False
      st.session_state.terne_escluse = set(st.session_state.terna_corrente)
      st.session_state.pezzi_per_numero = calcola_pezzi_aggressivi(
          st.session_state.bankroll, st.session_state.bankroll_iniziale
      )
    else:
      if st.session_state.colpo_attuale_ciclo >= MAX_COLPI_CICLO or (
          st.session_state.bankroll < (3 * VALORE_UNITA_BASE)
      ):
        st.session_state.ciclo_attivo = False
        st.session_state.terne_escluse = set(st.session_state.terna_corrente)
        st.session_state.pezzi_per_numero = calcola_pezzi_aggressivi(
            st.session_state.bankroll, st.session_state.bankroll_iniziale
        )

  if not st.session_state.ciclo_attivo and st.session_state.bankroll >= (
      3 * VALORE_UNITA_BASE
  ):
    if len(crono) >= 5:
      ultimi_dati = pd.Series(crono[-120:])
      frequenze = ultimi_dati.value_counts()
      candidati = [
          num
          for num in frequenze.index
          if num not in st.session_state.terne_escluse
      ]
      top3 = candidati[:3]
      if len(top3) < 3:
        for n in range(37):
          if (
              n not in top3
              and n not in st.session_state.terne_escluse
          ):
            top3.append(n)
          if len(top3) == 3:
            break
    else:
      top3 = [0, 1, 2]

    top3.sort()
    st.session_state.terna_corrente = top3
    st.session_state.ciclo_attivo = True
    st.session_state.colpo_attuale_ciclo = 0

  if st.session_state.bankroll > st.session_state.peak_bankroll:
    st.session_state.peak_bankroll = st.session_state.bankroll


# ==========================================
# DASHBOARD UTENTE
# ==========================================
st.title("🎯 Roulette Analytics Pro")

if not st.session_state.autenticato:
  st.warning(
      "🔒 Accesso bloccato. Inserisci un **codice licenza valido e in corso di"
      " validità** per sbloccare l'applicazione."
  )
else:
  with st.expander("⚙️ Setup Iniziale e Caricamento Dati", expanded=False):
    saldo_in = st.number_input(
        "Saldo Iniziale (€):",
        value=st.session_state.bankroll_iniziale,
        step=5.0,
    )
    html_in = st.text_area("Incolla codice HTML dei 500 numeri:")
    if st.button("🚀 Carica & Avvia Sessione"):
      st.session_state.bankroll_iniziale = saldo_in
      st.session_state.bankroll = saldo_in
      st.session_state.peak_bankroll = saldo_in
      st.session_state.ciclo_attivo = False
      st.session_state.storico_stati = []
      if html_in.strip():
        st.session_state.cronologia = estrai_numeri_da_html(html_in)
        st.success(
            f"Caricati {len(st.session_state.cronologia)} numeri dallo storico!"
        )
      else:
        st.session_state.cronologia = []
      elabora_tiro(
          st.session_state.cronologia[-1] if st.session_state.cronologia else 0
      )
      st.rerun()

  col1, col2, col3 = st.columns(3)
  col1.metric("💰 Cassa Attuale", f"{st.session_state.bankroll:.2f} €")
  pnl = st.session_state.bankroll - st.session_state.bankroll_iniziale
  col2.metric(
      "⚖️ Profit/Loss",
      f"{pnl:+.2f} €",
      delta_color="normal" if pnl >= 0 else "inverse",
  )
  col3.metric("📈 Picco Massimo", f"{st.session_state.peak_bankroll:.2f} €")

  if st.session_state.ciclo_attivo:
    t = st.session_state.terna_corrente
    st.markdown(
        f"""
        <div style="background-color: #27AE60; color: #FFFFFF; padding: 15px; border-radius: 10px; font-size: 22px; font-weight: bold; text-align: center; margin: 15px 0;">
            🎯 TERNA DA PUNTARE: {t[0]} - {t[1]} - {t[2]}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        f"Tentativo in corso: Colpo {st.session_state.colpo_attuale_ciclo + 1} di"
        f" {MAX_COLPI_CICLO} | Puntata consigliata:"
        f" {st.session_state.pezzi_per_numero * VALORE_UNITA_BASE:.2f}€ per"
        " numero"
    )

  col_undo, col_reset = st.columns([2, 1])
  if col_undo.button("↩️ Annulla Ultimo Tiro (Undo)"):
    annulla_ultimo_tiro()
    st.rerun()
  if col_reset.button("🔄 Reset Totale"):
    st.session_state.cronologia = []
    st.session_state.bankroll = st.session_state.bankroll_iniziale
    st.session_state.ciclo_attivo = False
    st.rerun()

  ultimi = (
      st.session_state.cronologia[-10:]
      if len(st.session_state.cronologia) >= 10
      else st.session_state.cronologia
  )
  st.write(f"🕒 **Ultime estrazioni registrate:** `{ultimi}`")

  st.divider()
  st.subheader("🎲 Tappeto Roulette (Clicca per inserire il numero)")

  if st.button("0", key="num_0", use_container_width=True):
    elabora_tiro(0)
    st.rerun()

  riga_3 = [3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36]
  riga_2 = [2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35]
  riga_1 = [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34]

  for riga in [riga_3, riga_2, riga_1]:
    cols = st.columns(12)
    for idx, n in enumerate(riga):
      if cols[idx].button(str(n), key=f"num_{n}"):
        elabora_tiro(n)
        st.rerun()
