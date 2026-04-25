# 🚀 Panduan Menjalankan Bot 24/7

## Perbandingan Opsi Hosting

| Opsi | Biaya | Kemudahan | Rekomendasi |
|---|---|---|---|
| Railway.app | Gratis $5 kredit/bln | Sangat Mudah | ✅ Terbaik untuk pemula |
| Render.com | Gratis permanen | Mudah | ✅ Gratis selamanya |
| VPS (Contabo/DO) | ~$4–6/bln | Sedang | ✅ Terbaik untuk produksi |
| PC sendiri 24/7 | Listrik saja | Mudah | ⚠️ Tidak disarankan |

---

## Opsi 1 — Railway.app (PALING MUDAH)

### Langkah:

1. Buat akun di https://railway.app (login pakai GitHub)

2. Push kode ke GitHub dulu:
```bash
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/USERNAME/nama-repo.git
git push -u origin main
```

3. Deploy di Railway:
   - Klik New Project -> Deploy from GitHub Repo
   - Pilih repo bot kamu
   - Add Variables -> isi BOT_TOKEN = token bot kamu

4. Railway otomatis deploy dan bot langsung jalan 24/7!

Catatan: Railway gratis $5 kredit/bulan. Bot ini memakai ~$0.50–1/bulan.

---

## Opsi 2 — Render.com (GRATIS PERMANEN)

1. Buat akun di https://render.com
2. New -> Background Worker (bukan Web Service!)
3. Hubungkan repo GitHub
4. Set:
   - Build Command: pip install -r requirements.txt && python -X utf8 kbbi/data/build_kbbi.py
   - Start Command: python -X utf8 bot.py
5. Tambah Environment Variable: BOT_TOKEN = token kamu
6. Deploy!

---

## Opsi 3 — VPS (PALING STABIL, ~Rp60rb/bln)

Gunakan Contabo atau DigitalOcean.

Setelah dapat VPS Ubuntu:
```bash
# Install Python
sudo apt update && sudo apt install python3 python3-pip git -y

# Clone repo
git clone https://github.com/USERNAME/nama-repo.git
cd nama-repo

# Install dependencies
pip3 install -r requirements.txt
python3 kbbi/data/build_kbbi.py

# Buat file .env
echo "BOT_TOKEN=isi_token_kamu" > .env

# Jalankan pakai screen
screen -S sambungkata
python3 -X utf8 bot.py
# Tekan Ctrl+A lalu D untuk detach, bot tetap jalan!
```

### Auto-restart dengan systemd:
```bash
sudo nano /etc/systemd/system/sambungkata.service
```
Isi:
```ini
[Unit]
Description=Bot Sambung Kata KBBI
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/nama-repo
ExecStart=/usr/bin/python3 -X utf8 bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
Lalu:
```bash
sudo systemctl enable sambungkata
sudo systemctl start sambungkata
```

---

## File yang Perlu Disiapkan Sebelum Deploy

### .gitignore
```
.env
data/
__pycache__/
*.pyc
kbbi/__pycache__/
```

JANGAN upload .env ke GitHub! Token bot bisa dicuri.

### Procfile (untuk Railway)
```
worker: python -X utf8 bot.py
```

### runtime.txt (opsional)
```
python-3.11.0
```

---

## Rekomendasi

| Situasi | Rekomendasi |
|---|---|
| Baru mulai, mau gratis | Railway.app |
| Mau gratis selamanya | Render.com (Background Worker) |
| Bot untuk banyak grup | VPS Contabo ~$4/bln |
