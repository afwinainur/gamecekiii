import streamlit as st
import pandas as pd
import io
import json
import os

# Konfigurasi halaman
st.set_page_config(page_title="Papan Skor Pro", page_icon="🏆", layout="wide")

# File untuk menyimpan data agar tidak hilang saat refresh
DB_FILE = "game_state.json"

def save_data():
    """Simpan data session_state ke file JSON."""
    data = {
        "game_name": st.session_state.game_name,
        "players": st.session_state.players,
        "history": st.session_state.history,
        "game_active": st.session_state.game_active
    }
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

def load_data():
    """Muat data dari file JSON jika ada."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return None
    return None

def main():
    # 1. Inisialisasi Session State
    # Kita cek apakah data sudah ada di disk untuk mencegah reset saat refresh (F5)
    disk_data = load_data()

    if 'initialized' not in st.session_state:
        if disk_data:
            st.session_state.game_name = disk_data.get('game_name', "Turnamen Seru")
            st.session_state.players = disk_data.get('players', [])
            st.session_state.history = disk_data.get('history', [])
            st.session_state.game_active = disk_data.get('game_active', False)
        else:
            st.session_state.game_name = "Turnamen Seru"
            st.session_state.players = []
            st.session_state.history = []
            st.session_state.game_active = False
        st.session_state.initialized = True

    # Judul Dinamis berdasarkan Nama Permainan
    if st.session_state.game_active:
        st.title(f"🏆 {st.session_state.game_name}")
    else:
        st.title("🏆 Aplikasi Penghitung Skor Pro")
    
    st.write("Kelola pemain, catat skor tiap ronde, dan ekspor hasilnya. (Data tersimpan otomatis)")

    # --- SIDEBAR: PENGATURAN PERMAINAN ---
    st.sidebar.header("⚙️ Pengaturan Permainan")
    
    if not st.session_state.game_active:
        # Input Nama Permainan
        game_name_input = st.sidebar.text_input("Nama Permainan", value=st.session_state.game_name)
        
        num_players = st.sidebar.number_input("Jumlah Pemain", min_value=2, max_value=10, value=2)
        player_names = []
        for i in range(num_players):
            name = st.sidebar.text_input(f"Nama Pemain {i+1}", f"Pemain {i+1}", key=f"name_{i}")
            player_names.append(name)
        
        if st.sidebar.button("Mulai Permainan Baru", type="primary"):
            st.session_state.game_name = game_name_input
            st.session_state.players = player_names
            st.session_state.history = []
            st.session_state.game_active = True
            save_data() # Simpan ke disk
            st.rerun()
    else:
        st.sidebar.subheader(f"Sedang Bermain: {st.session_state.game_name}")
        if st.sidebar.button("Reset / Permainan Baru", type="secondary"):
            st.session_state.game_active = False
            st.session_state.players = []
            st.session_state.history = []
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE) # Hapus file cadangan saat reset total
            st.rerun()

    # --- KONTEN UTAMA ---
    if st.session_state.game_active:
        players = st.session_state.players
        
        # Form Input Skor Ronde Baru
        with st.expander("➕ Masukkan Skor Ronde Baru", expanded=True):
            with st.form("round_form"):
                cols = st.columns(len(players))
                current_round_scores = {}
                for idx, p_name in enumerate(players):
                    # Input hanya angka (number_input)
                    score = cols[idx].number_input(f"Skor {p_name}", step=1, value=0, key=f"input_{p_name}_{len(st.session_state.history)}")
                    current_round_scores[p_name] = score
                
                submit = st.form_submit_button("Simpan Skor Ronde")
                if submit:
                    round_num = len(st.session_state.history) + 1
                    entry = {"Ronde": round_num}
                    entry.update(current_round_scores)
                    st.session_state.history.append(entry)
                    save_data() # Simpan setiap ada perubahan skor
                    st.rerun()

        # Menampilkan Data & Statistik
        if st.session_state.history:
            df = pd.DataFrame(st.session_state.history)
            
            # Hitung Total Skor
            totals = df.drop(columns=["Ronde"]).sum().sort_values(ascending=False)
            
            # Tampilkan Leaderboard
            st.subheader("📊 Papan Peringkat (Total)")
            cols_stats = st.columns(len(players))
            
            highest_score = totals.max()
            lowest_score = totals.min()

            for i, (name, total) in enumerate(totals.items()):
                with cols_stats[i]:
                    if total == highest_score and total != lowest_score:
                        st.success(f"👑 {name}")
                        st.metric("Skor Total", total)
                        st.caption("🔥 Luar biasa! Terus pertahankan!")
                    elif total == lowest_score and total != highest_score:
                        st.error(f"💀 {name}")
                        st.metric("Skor Total", total)
                        st.caption("👎 Payah sekali, ayo latihan lagi!")
                    else:
                        st.info(f"👤 {name}")
                        st.metric("Skor Total", total)
                        st.caption("Lumayan, berusahalah!")

            # Tabel Riwayat
            st.divider()
            st.subheader(f"📝 Riwayat {st.session_state.game_name}")
            st.dataframe(df, use_container_width=True, hide_index=True)

            # --- FITUR EKSPOR ---
            st.subheader("💾 Ekspor Data")
            c1, c2 = st.columns(2)
            
            safe_filename = st.session_state.game_name.replace(" ", "_").lower()

            # Export CSV
            csv = df.to_csv(index=False).encode('utf-8')
            c1.download_button(
                label=f"Unduh {st.session_state.game_name} (CSV)",
                data=csv,
                file_name=f"skor_{safe_filename}.csv",
                mime="text/csv",
                use_container_width=True
            )

            # Export Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Skor')
            
            c2.download_button(
                label=f"Unduh {st.session_state.game_name} (XLSX)",
                data=buffer.getvalue(),
                file_name=f"skor_{safe_filename}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.info(f"Belum ada skor yang dicatat untuk '{st.session_state.game_name}'.")
    else:
        st.info("Silakan atur Nama Permainan dan Pemain di sidebar, lalu klik 'Mulai Permainan Baru'.")

if __name__ == "__main__":
    main()