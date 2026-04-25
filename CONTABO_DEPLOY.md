# Panduan Deploy Bot di Contabo VPS (Step by Step)

## Step 1 — Beli VPS di Contabo

1. Buka https://contabo.com
2. Pilih **Cloud VPS S** (paling murah, cukup untuk bot)
   - RAM: 4 GB
   - Storage: 50 GB NVMe
   - Harga: ~$5.50/bulan
3. Pilih OS: **Ubuntu 22.04**
4. Pilih region: **Singapore** (agar cepat dari Indonesia)
5. Buat password root, simpan baik-baik
6. Checkout & bayar

Setelah 30–60 menit, kamu dapat email berisi:
- IP Address VPS (contoh: 123.45.67.89)
- Username: root
- Password: yang kamu buat tadi

---

## Step 2 — Masuk ke VPS (SSH)

### Windows (pakai PowerShell atau CMD):
```
ssh root@123.45.67.89
```
Ganti `123.45.67.89` dengan IP VPS kamu.

Ketik password (tidak terlihat saat diketik, itu normal), tekan Enter.

Selamat, kamu sudah masuk ke VPS!

---

## Step 3 — Setup Server

Copy-paste semua perintah ini satu per satu:

```bash
# Update sistem
apt update && apt upgrade -y

# Install Python 3.11 dan tools yang dibutuhkan
apt install python3 python3-pip git nano screen -y

# Cek versi Python (harus 3.10+)
python3 --version
```

---

## Step 4 — Upload Kode Bot ke VPS

Ada 2 cara:

### Cara A — Pakai GitHub (Disarankan)

Kamu perlu push kode ke GitHub dulu (dari PC kamu):
```
cd d:\bottele
git init
git add .
git commit -m "bot sambung kata"
git branch -M main
git remote add origin https://github.com/USERNAME/sambungkata-bot.git
git push -u origin main
```

Lalu di VPS:
```bash
git clone https://github.com/USERNAME/sambungkata-bot.git
cd sambungkata-bot
```

### Cara B — Upload Langsung Pakai SCP (tanpa GitHub)

Dari PC Windows kamu, buka PowerShell:
```
scp -r d:\bottele root@123.45.67.89:/root/sambungkata-bot
```
Masukkan password VPS. Semua file akan terupload.

Lalu masuk VPS dan:
```bash
cd /root/sambungkata-bot
```

---

## Step 5 — Install Dependencies & Konfigurasi

```bash
# Masuk ke folder bot
cd /root/sambungkata-bot

# Install semua library Python
pip3 install -r requirements.txt

# Download kamus KBBI (otomatis ~120rb kata)
python3 -X utf8 kbbi/data/build_kbbi.py

# Buat file .env dengan token bot
nano .env
```

Di dalam nano, ketik:
```
BOT_TOKEN=isi_token_bot_kamu_disini
```
Tekan **Ctrl+X → Y → Enter** untuk simpan dan keluar.

---

## Step 6 — Test Jalankan Bot

```bash
python3 -X utf8 bot.py
```

Lihat outputnya. Kalau muncul:
```
Bot Sambung Kata KBBI mulai berjalan...
Bot aktif. Tekan Ctrl+C untuk berhenti.
```

Berarti bot berhasil! Tekan **Ctrl+C** untuk stop dulu.

---

## Step 7 — Setup systemd (Auto-start & Auto-restart)

Ini agar bot otomatis jalan saat VPS reboot, dan restart sendiri kalau crash.

```bash
nano /etc/systemd/system/sambungkata.service
```

Copy-paste isi berikut:
```ini
[Unit]
Description=Bot Sambung Kata KBBI
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/sambungkata-bot
ExecStart=/usr/bin/python3 -X utf8 bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Tekan **Ctrl+X → Y → Enter** untuk simpan.

Lalu aktifkan:
```bash
# Reload systemd
systemctl daemon-reload

# Aktifkan agar auto-start saat reboot
systemctl enable sambungkata

# Jalankan sekarang
systemctl start sambungkata

# Cek status (harus Active: running)
systemctl status sambungkata
```

---

## Perintah Berguna Setelah Deploy

```bash
# Cek status bot
systemctl status sambungkata

# Lihat log real-time
journalctl -u sambungkata -f

# Stop bot
systemctl stop sambungkata

# Restart bot (misal setelah update kode)
systemctl restart sambungkata
```

---

## Step 8 — Update Kode Bot (Kalau Ada Perubahan)

### Jika pakai GitHub:
```bash
cd /root/sambungkata-bot
git pull origin main
systemctl restart sambungkata
```

### Jika upload manual (SCP):
Dari PC Windows:
```
scp -r d:\bottele\* root@123.45.67.89:/root/sambungkata-bot/
```
Lalu di VPS:
```bash
systemctl restart sambungkata
```

---

## Troubleshooting

**Bot tidak jalan / error:**
```bash
journalctl -u sambungkata -n 50
```
Lihat pesan error di bagian bawah.

**Token salah:**
```bash
nano /root/sambungkata-bot/.env
# Edit token, simpan
systemctl restart sambungkata
```

**Kamus KBBI kosong:**
```bash
cd /root/sambungkata-bot
python3 -X utf8 kbbi/data/build_kbbi.py
systemctl restart sambungkata
```

**VPS tidak bisa diakses:**
- Login ke panel Contabo
- Klik Rescue Mode untuk reset password
