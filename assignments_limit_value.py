import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')
# Page configuration
st.set_page_config(
    page_title="Sistema Assegnazione Pallet",
    page_icon="📦",
    layout="wide"
)
st.title("📦 Sistema di Assegnazione Pallet (con limite a valore)")
st.markdown("Sistema automatico per l'assegnazione ottimale dei pallet ai negozi")
st.markdown("---")
# Initialize session state
if 'df_results' not in st.session_state:
    st.session_state.df_results = None
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False
# Sidebar for file uploads
st.sidebar.header("📁 Caricamento File")
# File upload sections
uploaded_st = st.sidebar.file_uploader(
    "Carica tabella ST (Excel)",
    type=['xlsx', 'xls'],
    help="File contenente i dati dei negozi con Total Delivered, Total Sales e ST value"
)
uploaded_avanzamenti = st.sidebar.file_uploader(
    "Carica tabella AVANZAMENTI (Excel)",
    type=['xlsx', 'xls'],
    help="File contenente i dati degli avanzamenti per negozio"
)
uploaded_prelievi = st.sidebar.file_uploader(
    "Carica file PRELIEVI (Excel)",
    type=['xlsx', 'xls'],
    help="File contenente gli ID_PRELIEVO e le funzioni"
)
uploaded_stock = st.sidebar.file_uploader(
    "Carica file STOCK (Excel)",
    type=['xlsx', 'xls'],
    help="File contenente i dati dello stock per negozio"
)
# Parameters section in sidebar
st.sidebar.header("⚙️ Parametri del Sistema")
I1 = st.sidebar.slider(
    "I1 - Peso media ponderata (%)",
    min_value=0,
    max_value=100,
    value=70,
    help="Importanza della media ponderata nel calcolo finale"
)
I2 = 100 - I1
st.sidebar.write(f"I2 - Peso media avanzamenti (%): {I2}")
alpha = st.sidebar.slider(
    "Alpha (α)",
    min_value=0.0,
    max_value=1.0,
    value=0.7,
    step=0.05,
    help="Parametro per il calcolo del punteggio P"
)
soglia_delivered = st.sidebar.number_input(
    "Soglia Total Delivered",
    min_value=0.0,
    value=100000.0,
    step=1000.0,
    help="Soglia minima per il totale delivered dei negozi"
)
soglia_assegnato_per_negozio = st.sidebar.number_input(
    "Soglia massima per negozio",
    min_value=0.0,
    value=5000.0,
    step=100.0,
    help="Valore massimo assegnabile per negozio nella prima fase"
)
moltiplicatore_soglia = st.sidebar.number_input(
    "Moltiplicatore soglia riassegnazione",
    min_value=1.0,
    max_value=10.0,
    value=1.5,
    step=0.1,
    help="Moltiplicatore per calcolare la soglia massima nella riassegnazione automatica"
)
# Main content area
if all([uploaded_st, uploaded_avanzamenti, uploaded_prelievi, uploaded_stock]):
    
    # Process files
    with st.spinner("Caricamento e processamento dei file..."):
        
        try:
            # Pulizia e normalizzazione del DataFrame ST - ESATTO COME ORIGINALE
            df = pd.read_excel(uploaded_st, header=0)
            
            # Prendi la riga con i numeri sopra le colonne
            numeri_colonne = df.iloc[0, 1::3].values
            # Crea un elenco per le nuove intestazioni
            nuove_intestazioni = ['Des Negozio']
            # Aggiungi le intestazioni modificate con il numero
            for i, numero in enumerate(numeri_colonne):
                nuove_intestazioni.append(f"{numero} Somma di Total Delivered")
                nuove_intestazioni.append(f"{numero} Somma di Total Sales")
                nuove_intestazioni.append(f"{numero} Media di ST value")
            
            # Sostituisci le intestazioni nel dataframe
            df.columns = nuove_intestazioni
            # Elimina la riga con i numeri
            df = df.drop(index=0)
            df = df.drop(index=1).reset_index(drop=True)
            # Rimuovo eventuali righe con valori NaN nella colonna 'Des negozio'
            df = df.dropna(subset=["Des Negozio"])
            df = df.fillna(0)
            
            # Caricamento del file contenente gli AVANZAMENTI
            df_avanzamenti = pd.read_excel(uploaded_avanzamenti)
            df_avanzamenti = df_avanzamenti.fillna(0)
            
            # Trova i codici mancanti nel df_avanzamenti
            codici_mancanti_AV = set(df['Des Negozio']) - set(df_avanzamenti['Des Negozio'])
            for codice in codici_mancanti_AV:
                nuova_riga_AV = pd.DataFrame({'Des Negozio': [codice], 'Valore': [0]})
                df_avanzamenti = pd.concat([df_avanzamenti, nuova_riga_AV], ignore_index=True)
            df_avanzamenti = df_avanzamenti.fillna(0)
            
            # Caricamento del file contenente i PRELIEVI
            df_prelievi = pd.read_excel(uploaded_prelievi)
            df_prelievi = df_prelievi.fillna(0)
            
            # Caricamento del file contenente lo STOCK
            df_stock = pd.read_excel(uploaded_stock)
            df_stock = df_stock.fillna(0)
            
            # Trova i codici mancanti nel df_stock
            codici_mancanti = set(df['Des Negozio']) - set(df_stock['Des Negozio'])
            for codice in codici_mancanti:
                nuova_riga = pd.DataFrame({'Des Negozio': [codice], 'Valore': [0]})
                df_stock = pd.concat([df_stock, nuova_riga], ignore_index=True)
            df_stock = df_stock.fillna(0)
            
            st.success("✅ File caricati e processati con successo!")
            
        except Exception as e:
            st.error(f"Errore nel processamento dei file: {str(e)}")
            st.stop()
    
    # Show data preview
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Anteprima Dati Negozi")
        st.dataframe(df.head(), use_container_width=True)
        
    with col2:
        st.subheader("📦 Anteprima Prelievi")
        st.dataframe(df_prelievi.head(), use_container_width=True)
    
    # Process button
    if st.button("🚀 Avvia Assegnazione Pallet", type="primary", use_container_width=True):
        
        with st.spinner("Processamento in corso..."):
            
            # ALGORITMO ORIGINALE COMPLETO
            df_negozi = df
            df_prelievi['Valore Totale'] = df_prelievi.drop(columns=['ID_PRELIEVO']).sum(axis=1)
            
            if I1 + I2 != 100:
                st.error("I1 + I2 deve essere uguale a 100.")
                st.stop()
                
            if not (0 <= alpha <= 1):
                st.error("Alpha deve essere un valore compreso tra 0 e 1.")
                st.stop()
            
            negozi_disponibili = set(df_negozi['Des Negozio'])
            
            # Calcola il totale delivered per negozio
            def calcola_totale_delivered(row):
                return sum([row[col] for col in row.index if "Total Delivered" in col])
            
            negozi_validi = {
                negozio: calcola_totale_delivered(df_negozi[df_negozi['Des Negozio'] == negozio].iloc[0])
                for negozio in negozi_disponibili
                if calcola_totale_delivered(df_negozi[df_negozi['Des Negozio'] == negozio].iloc[0]) >= soglia_delivered
            }
            
            negozi_map = {negozio: df_negozi[df_negozi['Des Negozio'] == negozio].iloc[0] for negozio in negozi_validi}
            
            # Funzioni per calcolo media ponderata e avanzamenti
            def calcola_media_avanzamenti(codici_funzione, negozio):
                avanzamenti = [
                    df_avanzamenti.loc[df_avanzamenti['Des Negozio'] == negozio, codice].mean() if codice in df_avanzamenti.columns else 0
                    for codice in codici_funzione
                ]
                return sum(avanzamenti) / len(avanzamenti) if avanzamenti else 0
            
            def calcola_media_ponderata_con_controllo(codici_funzione, negozio_row):
                total_weighted_st = 0
                total_delivered = 0
                for codice in codici_funzione:
                    col_delivered = f"{codice} Somma di Total Delivered"
                    col_st = f"{codice} Media di ST value"
                    if col_delivered in negozio_row.index and col_st in negozio_row.index:
                        delivered_value = negozio_row[col_delivered]
                        st_value = negozio_row[col_st]
                        if delivered_value > 0:
                            total_weighted_st += st_value * delivered_value
                            total_delivered += delivered_value
                return total_weighted_st / total_delivered if total_delivered > 0 else 0
            
            def calcola_media_ponderata_combinata(codici_funzione, negozio):
                media_ponderata = calcola_media_ponderata_con_controllo(codici_funzione, negozi_map[negozio])
                media_avanzamenti = calcola_media_avanzamenti(codici_funzione, negozio)
                return (I1 * media_ponderata + I2 * media_avanzamenti) / 100, media_ponderata, media_avanzamenti
            
            # Calcola il totale dello stock dal dataframe df_stock
            def calcola_stock_totale(codici_funzione):
                return df_stock[[codice for codice in codici_funzione if codice in df_stock.columns]].sum().sum()
            
            # Calcola lo stock per un singolo negozio
            def calcola_stock_negozio(codici_funzione, negozio):
                return df_stock.loc[df_stock['Des Negozio'] == negozio, [
                    codice for codice in codici_funzione if codice in df_stock.columns
                ]].sum().sum()
            
            # Funzione per calcolare il punteggio P
            def calcola_punteggio_P(media_ponderata_combinata, codici_funzione, negozio):
                stock_totale_funzioni = calcola_stock_totale(codici_funzione)
                stock_funzioni_negozio = calcola_stock_negozio(codici_funzione, negozio)
                ps = stock_funzioni_negozio / stock_totale_funzioni if stock_totale_funzioni > 0 else 0
                if media_ponderata_combinata < 0:
                    media_ponderata_combinata = 0
                return (media_ponderata_combinata**alpha) / (1 + ps**(1 - alpha))
            
            # Assegnazione pallet
            results = []
            valori_assegnati = {negozio: 0 for negozio in negozi_validi}
            
            progress_bar = st.progress(0)
            total_rows = len(df_prelievi)
            
            for idx, (index, row) in enumerate(df_prelievi.iterrows()):
                progress_bar.progress((idx + 1) / total_rows)
                
                id_prelievo = row['ID_PRELIEVO']
                valore_totale = row['Valore Totale']
                codici_funzione = [col for col in row.index if col != 'ID_PRELIEVO' and col != "Valore Totale" and row[col] > 0]
                
                # Controlla funzioni non presenti in df_negozi
                funzioni_non_presenti = [codice for codice in codici_funzione if f"{codice} Somma di Total Delivered" not in df_negozi.columns]
                if len(funzioni_non_presenti) == len(codici_funzione):  # Tutte le funzioni sono mancanti
                    results.append([
                        str(id_prelievo), 
                        "Nessun negozio disponibile (TUTTE FUNZIONI NON PRESENTI)", 
                        0,
                        0, 
                        0,
                        0, 
                        0, 
                        ",".join(map(str, funzioni_non_presenti)), 
                        valore_totale
                    ])
                    continue
                
                # Ignora funzioni non presenti
                codici_funzione = [
                    codice for codice in codici_funzione 
                    if f"{codice} Somma di Total Delivered" in df_negozi.columns
                ]
                
                negozi_e_ponderate = []
                for negozio in negozi_validi:
                    # Controlla che il negozio abbia un valore di "Total Delivered" maggiore di zero per tutte le funzioni
                    negozio_row = negozi_map[negozio]
                    if all(negozio_row.get(f"{codice} Somma di Total Delivered", 0) > 0 for codice in codici_funzione):
                        if valori_assegnati[negozio] + valore_totale <= soglia_assegnato_per_negozio:
                            ponderata_combinata, media_ponderata, media_avanzamenti = calcola_media_ponderata_combinata(codici_funzione, negozio)
                            punteggio = calcola_punteggio_P(ponderata_combinata, codici_funzione, negozio)
                            stock_totale_funzioni = calcola_stock_totale(codici_funzione)
                            stock_funzioni_negozio = calcola_stock_negozio(codici_funzione, negozio)
                            ps = stock_funzioni_negozio / stock_totale_funzioni if stock_totale_funzioni > 0 else 0
                            negozi_e_ponderate.append((negozio, punteggio, ps, ponderata_combinata, media_ponderata, media_avanzamenti))
                
                negozi_e_ponderate.sort(key=lambda x: x[1], reverse=True)
                
                if negozi_e_ponderate:
                    negozio_assegnato, punteggio, ps, ponderata_combinata, media_ponderata, media_avanzamenti = negozi_e_ponderate[0]
                    valori_assegnati[negozio_assegnato] += valore_totale
                    results.append([
                        str(id_prelievo), negozio_assegnato, punteggio, ps, ponderata_combinata, 
                        media_ponderata, media_avanzamenti, ",".join(map(str, codici_funzione)), valore_totale
                    ])
                else:
                    results.append([str(id_prelievo), "Nessun negozio disponibile", 0, 0, 0, 0, 0, ",".join(map(str, codici_funzione)), valore_totale])
            
            progress_bar.empty()
            
            # Crea DataFrame risultati
            df_results = pd.DataFrame(results, columns=["ID_PRELIEVO", "Negozio Assegnato", "Punteggio", "Percentuale Stock", "Media Ponderata Combinata", "Media Ponderata", "Media Avanzamenti", "Funzioni presenti", "Valore Totale"])
            df_results['ID_PRELIEVO'] = df_results['ID_PRELIEVO'].apply(lambda x: str(x).split('.')[0] if '.' in str(x) else str(x))
            
            # RIASSEGNAZIONE AUTOMATICA DEI PALLET MANCANTI
            pallet_non_assegnati = df_results[df_results["Negozio Assegnato"] == "Nessun negozio disponibile"]
            
            if not pallet_non_assegnati.empty:
                st.info("🔄 Avvio riassegnazione automatica dei pallet mancanti...")
                
                # Calcola il valore totale massimo assegnato a ciascun negozio
                max_valore_assegnato_per_negozio = max(valori_assegnati.values()) if valori_assegnati.values() else 0
                
                # Calcola la soglia massima automaticamente usando il moltiplicatore configurabile
                max_pallet_valore = df_prelievi['Valore Totale'].max()
                soglia_massima = max(max_valore_assegnato_per_negozio, max_pallet_valore * moltiplicatore_soglia)
                
                st.info(f"Soglia massima per riassegnazione: {soglia_massima:.2f} (moltiplicatore: {moltiplicatore_soglia})")
                
                with st.spinner("Riassegnazione automatica in corso..."):
                    progress_bar2 = st.progress(0)
                    total_unassigned = len(pallet_non_assegnati)
                    
                    for idx, (index, row) in enumerate(pallet_non_assegnati.iterrows()):
                        progress_bar2.progress((idx + 1) / total_unassigned)
                        
                        id_prelievo = row['ID_PRELIEVO']
                        valore_totale = row['Valore Totale']
                        codici_funzione_str = row['Funzioni presenti'].split(',')
                        # Convertiamo ogni elemento della lista in int
                        codici_funzione = [int(codice) for codice in codici_funzione_str if codice.strip().isdigit()]
                        
                        negozi_e_ponderate = []
                        for negozio in negozi_validi:
                            negozio_row = negozi_map[negozio]
                            if all(negozio_row.get(f"{codice} Somma di Total Delivered", 0) > 0 for codice in codici_funzione):
                                ponderata_combinata, media_ponderata, media_avanzamenti = calcola_media_ponderata_combinata(codici_funzione, negozio)
                                punteggio = calcola_punteggio_P(ponderata_combinata, codici_funzione, negozio)
                                stock_totale_funzioni = calcola_stock_totale(codici_funzione)
                                stock_funzioni_negozio = calcola_stock_negozio(codici_funzione, negozio)
                                ps = stock_funzioni_negozio / stock_totale_funzioni if stock_totale_funzioni > 0 else 0
                                negozi_e_ponderate.append((negozio, punteggio, ps, ponderata_combinata, media_ponderata, media_avanzamenti))
                        
                        negozi_e_ponderate.sort(key=lambda x: x[1], reverse=True)
                        
                        negozio_assegnato = None
                        for candidato, punteggio, ps, ponderata_combinata, media_ponderata, media_avanzamenti in negozi_e_ponderate:
                            if valori_assegnati[candidato] + valore_totale <= soglia_massima:
                                negozio_assegnato = candidato
                                valori_assegnati[negozio_assegnato] += valore_totale
                                # Aggiorna il risultato nel dataframe
                                df_results.loc[df_results['ID_PRELIEVO'] == id_prelievo, 
                                             ['Negozio Assegnato', 'Punteggio', 'Percentuale Stock', 
                                              'Media Ponderata Combinata', 'Media Ponderata', 'Media Avanzamenti']] = [
                                    negozio_assegnato, punteggio, ps, ponderata_combinata, media_ponderata, media_avanzamenti
                                ]
                                break
                    
                    progress_bar2.empty()
                    st.success("✅ Riassegnazione automatica completata!")
            
            # Store in session state
            st.session_state.df_results = df_results
            st.session_state.processing_complete = True
        
        # Display results
        st.success("✅ Assegnazione completata!")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_pallets = len(st.session_state.df_results)
            st.metric("Totale Pallet", total_pallets)
        
        with col2:
            pallet_non_assegnati_final = st.session_state.df_results[
                (st.session_state.df_results["Negozio Assegnato"] == "Nessun negozio disponibile") |
                (st.session_state.df_results["Negozio Assegnato"] == "Nessun negozio disponibile (TUTTE FUNZIONI NON PRESENTI)")
            ]
            assigned_pallets = total_pallets - len(pallet_non_assegnati_final)
            st.metric("Pallet Assegnati", assigned_pallets)
        
        with col3:
            unassigned_pallets = len(pallet_non_assegnati_final)
            st.metric("Pallet Non Assegnati", unassigned_pallets)
        
        with col4:
            assignment_rate = (assigned_pallets / total_pallets) * 100 if total_pallets > 0 else 0
            st.metric("Tasso di Assegnazione", f"{assignment_rate:.1f}%")
        
        # Results table
        st.subheader("📋 Risultati Assegnazione")
        st.dataframe(st.session_state.df_results, use_container_width=True)
        
        # Download button
        def convert_df_to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Risultati')
            return output.getvalue()
        
        excel_data = convert_df_to_excel(st.session_state.df_results)
        
        st.download_button(
            label="📥 Scarica Risultati (Excel)",
            data=excel_data,
            file_name="risultati_assegnazione.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        # Final checks
        pallet_ancora_non_assegnati = st.session_state.df_results[st.session_state.df_results["Negozio Assegnato"] == "Nessun negozio disponibile"]
        if not pallet_ancora_non_assegnati.empty:
            st.warning("⚠️ Alcuni pallet rimangono ancora non assegnati dopo la riassegnazione automatica")
            with st.expander("Visualizza pallet ancora non assegnati"):
                st.dataframe(pallet_ancora_non_assegnati, use_container_width=True)
        
        pallet_senza_funzioni = st.session_state.df_results[st.session_state.df_results["Negozio Assegnato"] == "Nessun negozio disponibile (TUTTE FUNZIONI NON PRESENTI)"]
        if not pallet_senza_funzioni.empty:
            st.error("⚠️ Presenti pallet non assegnati (tutte funzioni non presenti)")
            with st.expander("Visualizza pallet con funzioni non presenti"):
                st.dataframe(pallet_senza_funzioni, use_container_width=True)
else:
    st.info("👆 Carica tutti i file richiesti nella barra laterale per iniziare")
    
    # Show file requirements
    st.subheader("📋 File Richiesti")
    
    file_requirements = {
        "Tabella ST": "Contiene dati dei negozi con colonne Total Delivered, Total Sales e ST value",
        "Tabella AVANZAMENTI": "Contiene dati degli avanzamenti per ogni negozio", 
        "File PRELIEVI": "Contiene ID_PRELIEVO e codici funzione per ogni pallet",
        "File STOCK": "Contiene dati dello stock disponibile per negozio"
    }
    
    for file_name, description in file_requirements.items():
        st.write(f"**{file_name}**: {description}")
# Footer
st.markdown("---")
st.markdown("*Sistema di Assegnazione Pallet - Versione Web App con Riassegnazione Automatica*")



