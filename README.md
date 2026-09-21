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

### 🐧 1. Penggunaan di Kali Linux (100% CLI)

1. **Clone repository & masuk ke folder**:
   ```bash
   git clone https://github.com/dzakyzahy/torchatz.git
   cd torchatz
   ```

2. **Jalankan TorChatZ (Otomatis start Tor & Onion)**:
   ```bash
   chmod +x *.sh scripts/*.sh
   ./start.sh
   ```
   *Atau jalankan via Python:*
   ```bash
   python3 torchatz.py
   ```

---

### 🪟 2. Penggunaan di Windows Terminal / CMD / PowerShell (100% CLI - No GUI)

1. **Clone & Masuk ke Folder**:
   ```powershell
   git clone https://github.com/dzakyzahy/torchatz.git
   cd torchatz
   ```

2. **Jalankan TorChatZ (Otomatis start Tor & Onion)**:
   - Di **PowerShell / Windows Terminal**:
     ```powershell
     .\start.bat
     ```
   - Atau di **CMD**:
     ```cmd
     start.bat
     ```
   - Atau langsung via **Python**:
     ```powershell
     python torchatz.py
     ```
   *Script ini otomatis mengunduh Tor Expert Bundle jika belum ada, menyalakan background daemon Tor, dan langsung membuka antarmuka terminal TorChatZ.*

---

## ⌨️ Daftar Perintah Terminal (Commands)

| Perintah | Deskripsi |
| :--- | :--- |
| `/help` | Menampilkan panduan dan daftar seluruh perintah yang tersedia. |
| `/myid` | Menampilkan alamat `.onion` v3 Anda, username, dan port koneksi saat ini. |
| `/nick <nama>` | Mengubah nama tampilan/username pseudonim Anda saat ini. |
| `/add <onion> [alias]` | Menambahkan teman ke daftar kontak dengan validasi ketat 56 karakter. |
| `/alias <lama> <baru>` | Mengganti alias nama kontak tersimpan (atau `/rename`). |
| `/del <alias/onion>` | Menghapus teman dari daftar kontak. |
| `/contacts` atau `/list` | Menampilkan tabel seluruh kontak beserta status online/offline. |
| `/connect <alias/onion>` | Membuka sirkuit koneksi Tor ke alamat teman. |
| `/chat <alias/onion>` | Memilih lawan bicara aktif untuk sesi chat langsung. |
| `/home` atau `/leave` | Keluar dari obrolan aktif dan kembali ke prompt menu utama. |
| `/disconnect [alias]` | Memutuskan koneksi aktif ke kontak tertentu. |
| `/copy` atau `/c` | **Menyalin chat/skrip kode terakhir ke clipboard OS** (format, spasi, & indentasi 100% utuh tanpa rusak). Dukung juga `/c <1..N>` atau `/c me`. |
| `/paste` atau `/p` | **Mem-paste & mengirim teks/skrip multiline dari clipboard** langsung tanpa terpotong atau rusak oleh terminal. |
| `/send <path_file>` | Mengirim file (gambar, video, dokumen) ke kontak yang sedang aktif di `/chat`. |
| `/files` | Melihat daftar file yang berhasil diunduh di folder `downloads/`. |
| `/update` atau `/pull` | Menarik pembaruan dari GitHub (`git pull`) dan otomatis memuat ulang (*in-place reload*) tanpa keluar terminal. Dukung `/update force`. |
| `/restart` | Me-restart TorChatZ secara langsung tanpa menutup jendela terminal. |
| `/tor [restart]` | Melihat status daemon Tor atau merestart sirkuit onion service. |
| `/clear` | Membersihkan layar terminal. |
| `/quit` atau `/exit` | Menutup aplikasi dan melepaskan sirkuit Tor secara bersih. |

> 💡 **Tips Mengetik Chat & Skrip**:
> - Gunakan `/p` untuk mengirim skrip kode multi-baris dari clipboard tanpa baris baru yang berantakan.
> - Gunakan `/c` untuk langsung menyalin skrip/pesan yang baru saja dikirimkan teman ke clipboard sistem laptop Anda tanpa perlu seleksi mouse yang merusak indentasi.

---

## 🛡️ Arsitektur Anonimitas, Privasi, & Keamanan (Security Model)

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

### 1. Zero-Leak Network Model
* **Tidak Ada Port Publik**: Listener socket hanya mengikat interface loopback lokal `127.0.0.1:11009`. Tidak ada port yang dibuka ke IP publik (`0.0.0.0`).
* **Sirkuit Rendezvous Tor v3**: Seluruh aliran TCP berjalan melalui circuit 6-hop Tor rendezvous terenkripsi ed25519. Lawan bicara tidak dapat melihat IP asli, provider internet (ISP), maupun lokasi geografis Anda.

### 2. Perlindungan Eksekusi Kode Berbahaya (Anti-RCE & Data-Only Payload)
* **Pesan Bersifat Murni Data**: Semua teks chat, skrip kode (Bash, Python, PowerShell), atau JSON yang dikirimkan oleh lawan chat diperlakukan murni sebagai teks (*data-only payload*).
* **Zero Shell Execution**: TorChatZ **TIDAK PERNAH** melemparkan teks chat ke `eval()`, `exec()`, `os.system()`, maupun `subprocess`.
* **Clipboard Sanitization**: Saat Anda menggunakan `/c` untuk menyalin skrip dari lawan bicara, teks disalin langsung ke clipboard sistem operasi laptop Anda agar Anda dapat memeriksa atau menjalankannya secara sadar di editor teks.

### 3. Sanitasi File Transfer & Perlindungan Direktori (Anti-Path Traversal)
* Pengirim tidak dapat mengarahkan penulisan file ke luar folder `downloads/`. Karakter traversal seperti `../` atau `..\` disanitasi secara otomatis (`Path(filename).name`).
* Setiap file diverifikasi menggunakan hash **SHA-256 Checksum** sebelum diakui berhasil.
* Path folder sistem pengirim (seperti `C:\Users\username\Desktop` atau `/home/kali/`) dipangkas habis sebelum frame dikirimkan sehingga tidak membocorkan struktur OS pengirim.

### 4. Privasi Kunci Rahasia & Data Lokal
* Kunci privat onion (`ED25519-V3`), alamat kontak tersimpan (`contacts.json`), dan pengaturan (`settings.json`) tersimpan murni di laptop Anda (folder `data/`).
* File data rahasia dilindungi oleh `.gitignore` dan **tidak akan pernah ter-upload ke repositori GitHub**.

---

## 🔧 Troubleshooting

* **Status Kontak Masih OFFLINE setelah `/add`?**
  * **Waktu Propagasi Tor**: Alamat onion v3 baru membutuhkan waktu 30–60 detik untuk mempropagasi descriptor-nya ke direktori terdistribusi Tor (HSDir). Tunggu sebentar lalu ketik `/connect <alias>` atau `/reconnect`.
  * **Sinkronisasi Jam (Clock Sync)**: Onion Services v3 mengandalkan penanggalan berbasis waktu yang ketat. Pastikan jam pada laptop Kali Linux dan laptop Windows Anda tersinkronisasi (*accurate NTP time*).
  * **Validasi 56 Karakter**: Pastikan seluruh 56 karakter alamat `.onion` tersalin lengkap tanpa ada karakter yang terpotong. Gunakan `/add <onion> [alias]`.

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
│   ├── network.py         # SOCKS5 client, loopback listener & RLock
│   ├── file_transfer.py   # Engine transfer chunk file & hash SHA-256
│   └── ui.py              # Antarmuka terminal Rich & prompt_toolkit (/c, /p, /update)
├── scripts/
│   ├── start_kali.sh      # Script runner untuk Kali Linux
│   └── start_windows.bat  # Script runner untuk Windows CMD/PowerShell
├── tests/                 # Test suite unit & integration (10 passing tests)
├── torrc.template         # Template konfigurasi torrc
├── requirements.txt       # Dependensi Python
├── .gitignore             # Pengamanan file rahasia lokal
├── LICENSE                # MIT License
└── README.md
```

---

## 📜 Lisensi (License)

Didistribusikan di bawah lisensi **MIT License**. Lihat [LICENSE](LICENSE) untuk informasi lebih lanjut.
