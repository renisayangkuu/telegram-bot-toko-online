# 🛍️ Telegram Bot Toko Online dengan AI

Bot Telegram untuk toko online dengan fitur AI menggunakan Groq, sistem pembayaran, dan manajemen stok otomatis.

## ✨ Fitur

### Untuk Customer:
- 🤖 Chat dengan AI untuk belanja natural
- 🛒 Keranjang belanja otomatis
- 💳 Multiple payment methods (Transfer, E-wallet, COD)
- 📱 Upload bukti pembayaran
- 📦 Tracking pesanan
- 🔢 Pesan dengan jumlah custom

### Untuk Admin:
- 🔐 Login system dengan password
- 📊 Dashboard pesanan
- ✅ Konfirmasi pembayaran
- 📈 Manajemen stok otomatis
- 📧 Notifikasi otomatis ke customer

## 🚀 Deploy ke Railway

### 1. Persiapan
1. Fork/clone repository ini
2. Buat bot di @BotFather Telegram
3. Dapatkan API key dari Groq
4. Siapkan file Excel dengan produk

### 2. Deploy
1. Buka [Railway.app](https://railway.app)
2. Login dengan GitHub
3. Klik "New Project" → "Deploy from GitHub repo"
4. Pilih repository ini
5. Set environment variables:
   - `BOT_TOKEN`: Token bot dari @BotFather
   - `GROQ_API_KEY`: API key dari Groq
   - `ADMIN_PASSWORD`: Password admin (opsional)

### 3. Environment Variables
```
BOT_TOKEN=your_bot_token_here
GROQ_API_KEY=your_groq_api_key_here
ADMIN_PASSWORD=your_admin_password
```

## 📋 Requirements

- Python 3.11+
- python-telegram-bot>=21.0
- openpyxl>=3.1.0
- pandas>=2.0.0
- groq>=0.4.0

## 🛠️ Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables atau edit langsung di bot.py

3. Jalankan bot:
```bash
python bot.py
```

## 📊 Format Excel Produk

File `Book1.xlsx` harus memiliki kolom:
- Kode Produk (PRD001, PRD002, dst)
- Nama Produk
- Kategori
- Harga (Rp)
- Stok
- Deskripsi Singkat

## 🎯 Cara Penggunaan

### Customer:
1. `/start` - Mulai belanja
2. Chat: "Mau beli 3 keripik pisang"
3. `/keranjang` - Lihat keranjang
4. `/checkout` - Bayar
5. Upload bukti transfer (jika perlu)

### Admin:
1. `/admin` - Login admin
2. `/orders` - Lihat pesanan
3. `/konfirmasi #001` - Konfirmasi bayar
4. `/selesai #001` - Selesaikan pesanan

## 🔧 Konfigurasi

Bot akan otomatis detect environment:
- **Local**: Menggunakan polling
- **Railway**: Menggunakan webhook

## 📝 License

MIT License