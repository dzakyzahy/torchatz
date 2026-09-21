# TorChatZ 🧅💬

> **Anonymous Peer-to-Peer Terminal Chat over Tor Onion Services (v3)**  
> Terinspirasi dari konsep [TorChat](https://github.com/prof7bit/TorChat), dimodernisasi untuk **Python 3**, **Tor v3 (ed25519)**, dan antarmuka **Terminal (CLI/TUI)** yang kompatibel secara cross-platform di **Kali Linux** dan **Windows CMD / PowerShell**.

---

## 🌟 Fitur Utama (Key Features)

- 🔒 **100% Anonim & Zero-Knowledge Identity**:
  - **Tidak ada kebocoran IP**: Semua koneksi dipaksa melalui jaringan sirkuit Tor SOCKS5 proxy.
  - **Rahasia OS & Jaringan**: Tidak ada fingerprint sistem operasi, versi kernel, atau nama komputer dalam payload protokol.
  - **Hanya Username & Onion**: Lawan bicara hanya mengetahui alamat `.onion` (v3 56-karakter) dan nama panggilan/username pseudonim Anda.
  - **Enkripsi Bawaan**: Sirkuit multi-hop Tor (ed25519 & curve25519) mengenkripsi seluruh pertukaran pesan secara end-to-end tanpa memerlukan server perantara (serverless P2P).
- 💻 **Terminal-Native & Copy-Paste Friendly**:
  - Berjalan langsung di Terminal (Bash/Zsh di Kali Linux) dan Command Prompt / PowerShell / Windows Terminal di Windows.
  - Mendukung **Copy** dan **Paste** teks langsung (Ctrl+V / Klik Kanan) tanpa merusak layout terminal.
  - Auto-completion perintah dengan tombol `Tab` dan navigasi riwayat dengan tombol panah `Up`/`Down`.
- 📁 **Transfer File Multimedia (Gambar, Video, Dokumen)**:
  - Mengirim dan menerima gambar (`.jpg`, `.png`), video (`.mp4`, `.mkv`), audio, dokumen (`.pdf`, `.txt`), maupun arsip (`.zip`).
  - Pengiriman berbasis streaming chunk biner dengan validasi integritas **SHA-256 Checksum**.
  - Perlindungan sanitasi nama file untuk mencegah celah *Directory Traversal*.
- ⚡ **Otomasi Tor**:
  - Secara otomatis mendeteksi port Tor SOCKS5 (`9050` pada Linux/Tor daemon atau `9150` pada Tor Browser di Windows).
  - Terintegrasi dengan Tor Control Port (`9051`/`9151`) untuk membuat **Ephemeral Hidden Service** v3 secara otomatis tanpa perlu konfigurasi manual.

---

## 🚀 Panduan Cepat (Quick Start)

### 🐧 1. Penggunaan di Kali Linux

1. **Clone repository**:
   ```bash
   git clone https://github.com/dzakyzahy/torchatz.git
   cd torchatz
   ```

2. **Jalankan service Tor**:
   ```bash
   sudo apt update
   sudo apt install -y tor python3 python3-pip
   sudo systemctl start tor
   ```

3. **Install dependensi & jalankan**:
   ```bash
   chmod +x scripts/start_kali.sh
   ./scripts/start_kali.sh
   ```
   *Atau jalankan manual:*
   ```bash
   pip install -r requirements.txt
   python3 torchatz.py
   ```

---

### 🪟 2. Penggunaan di Windows (CMD / PowerShell)

1. **Pastikan Tor berjalan di Windows**:
   - Opsi termudah: Buka **Tor Browser** dan biarkan berjalan di latar belakang (secara default menyediakan SOCKS5 proxy di `127.0.0.1:9150`).
   - Atau jalankan **Tor Expert Bundle** (`tor.exe`).

2. **Clone & Masuk ke Folder**:
   ```cmd
   git clone https://github.com/dzakyzahy/torchatz.git
   cd torchatz
   ```

3. **Jalankan via Script Batch atau Python**:
   ```cmd
   scripts\start_windows.bat
   ```
   *Atau secara manual:*
   ```cmd
   python -m pip install -r requirements.txt
   python torchatz.py
   ```

---

## ⌨️ Daftar Perintah Terminal (Commands)

| Perintah | Deskripsi |
| :--- | :--- |
| `/help` | Menampilkan panduan dan daftar seluruh perintah yang tersedia. |
| `/myid` | Menampilkan alamat `.onion` v3 Anda, username, dan port koneksi saat ini. |
| `/nick <nama>` | Mengubah nama tampilan/username pseudonim Anda saat ini. |
| `/add <onion> [alias]` | Menambahkan teman ke daftar kontak dengan nama alias opsional. |
| `/del <alias/onion>` | Menghapus teman dari daftar kontak. |
| `/contacts` atau `/list` | Menampilkan tabel seluruh kontak beserta status online/offline. |
| `/connect <alias/onion>` | Membuka sirkuit koneksi Tor ke alamat teman. |
| `/chat <alias/onion>` | Memilih lawan bicara aktif untuk sesi chat langsung. |
| `/send <path_file>` | Mengirim file (gambar, video, dokumen) ke kontak yang sedang aktif di `/chat`. |
| `/files` | Melihat daftar file yang berhasil diunduh di folder `downloads/`. |
| `/clear` | Membersihkan layar terminal. |
| `/quit` atau `/exit` | Menutup aplikasi dan melepaskan sirkuit Tor secara bersih. |

> 💡 **Tips Mengetik Chat**: Setelah Anda memilih lawan bicara dengan `/chat <alias>`, Anda bisa langsung mengetik pesan dan menekan `Enter` untuk mengirim, atau `Ctrl+V` untuk mem-paste teks.

---

## 🛡️ Arsitektur Anonimitas & Keamanan

```
[Peer A: Kali/Windows]
        │
        ▼ (Localhost only: 127.0.0.1:11009)
 [Tor v3 Onion Service]
        │
        ▼ (Tor Multi-hop Circuit: 6 Hops Rendezvous)
 [Tor Network Rendezvous Point]
        │
        ▲ (Tor Multi-hop Circuit: 6 Hops Rendezvous)
 [Tor v3 Onion Service]
        │
        ▲ (Localhost only: 127.0.0.1:11009)
[Peer B: Windows/Kali]
```

1. **Rute Zero-Leak**: Tidak ada socket yang dibind ke IP publik `0.0.0.0`. Listener hanya mengikat interface loopback `127.0.0.1`.
2. **Tanpa Perantara**: Tidak ada server cloud / database pusat yang menyimpan riwayat percakapan Anda. Pesan berpindah langsung antar peer via rendezvous circuit.
3. **Data Sanitization**: Path direktori lokal pengirim (seperti `C:\Users\name\Desktop` atau `/home/kali/`) dipotong habis (`basename`), hanya nama file yang dikirimkan ke penerima.

---

## 📂 Struktur Direktori

```
TorChatZ/
├── torchatz.py            # Entry point utama aplikasi CLI
├── torchatz/              # Modul inti aplikasi
│   ├── __init__.py
│   ├── config.py          # Pengaturan, identitas & kontak lokal
│   ├── tor_manager.py     # Kontroler Tor daemon & Onion v3 service
│   ├── protocol.py        # Frame serialization & packet definition
│   ├── network.py         # SOCKS5 client & loopback listener
│   ├── file_transfer.py   # Engine transfer chunk file & hash SHA-256
│   └── ui.py              # Antarmuka terminal Rich & prompt_toolkit
├── scripts/
│   ├── start_kali.sh      # Script runner untuk Kali Linux
│   └── start_windows.bat  # Script runner untuk Windows CMD
├── torrc.template         # Template konfigurasi torrc
├── requirements.txt       # Dependensi Python
├── .gitignore
├── LICENSE                # MIT License
└── README.md
```

---

## 📜 Lisensi (License)

Didistribusikan di bawah lisensi **MIT License**. Lihat [LICENSE](LICENSE) untuk informasi lebih lanjut.
