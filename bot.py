import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
from groq import Groq
import pandas as pd
import json

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "YOUR_GROQ_API_KEY_HERE")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
PORT = int(os.getenv("PORT", 8000))

groq_client = Groq(api_key=GROQ_API_KEY)

# Menyimpan admin yang sudah login
logged_in_admins = set()

def load_products():
    df = pd.read_excel('Book1.xlsx')
    products = {}
    for idx, row in df.iterrows():
        products[row['Kode Produk']] = {
            'code': row['Kode Produk'],
            'name': row['Nama Produk'],
            'category': row['Kategori'],
            'price': float(row['Harga (Rp)']),
            'stock': int(row['Stok']),
            'description': row['Deskripsi Singkat']
        }
    return products

def save_products():
    """Simpan perubahan stok ke Excel"""
    df = pd.read_excel('Book1.xlsx')
    
    for idx, row in df.iterrows():
        code = row['Kode Produk']
        if code in PRODUCTS:
            df.at[idx, 'Stok'] = PRODUCTS[code]['stock']
    
    df.to_excel('Book1.xlsx', index=False)

def update_stock(product_code, quantity):
    """Kurangi stok produk"""
    if product_code in PRODUCTS:
        PRODUCTS[product_code]['stock'] -= quantity
        save_products()

def load_orders():
    if os.path.exists('orders.json'):
        with open('orders.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_orders(orders):
    with open('orders.json', 'w', encoding='utf-8') as f:
        json.dump(orders, f, indent=2, ensure_ascii=False)

PRODUCTS = load_products()
user_carts = {}
awaiting_admin_password = {}  # Menyimpan user yang sedang proses login admin
awaiting_payment_method = {}  # Menyimpan user yang sedang pilih metode pembayaran
awaiting_payment_proof = {}  # Menyimpan user yang sedang upload bukti bayar
pending_orders = {}  # Menyimpan order sementara sebelum pilih pembayaran

def is_admin(user_id):
    return user_id in logged_in_admins

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    user_id = update.effective_user.id
    
    print(f"[DEBUG] /start dari user: {user_name} (ID: {user_id})")
    
    try:
        help_text = f"""
╔═══════════════════════╗
║  🌟 TOKO SERBA ADA 🌟  ║
╚═══════════════════════╝

*Selamat Datang di Toko Kami!* 👋

Halo *{user_name}*, terima kasih sudah berkunjung!

Kami menjual berbagai produk berkualitas:

🍪 *Makanan & Minuman*
Keripik, brownies, sambal, minuman segar

👕 *Fashion & Aksesoris*  
Kaos custom, tote bag kanvas

🏠 *Produk Rumah Tangga*
Pewangi laundry dan lainnya

━━━━━━━━━━━━━━━━━━━━━

📍 Jl. Raya Contoh 123, Jakarta
📞 WA: 0812-3456-7890
🕐 Senin-Sabtu 08.00-20.00

━━━━━━━━━━━━━━━━━━━━━

💬 *Ada yang bisa kami bantu?*

Contoh chat:
• "Lihat semua produk"
• "Mau beli keripik pisang"
• "Ada brownies?"

🤖 AI kami siap membantu!
"""

        await update.message.reply_text(help_text, parse_mode='Markdown')
        print(f"[DEBUG] Berhasil kirim pesan ke {user_name}")
        
    except Exception as e:
        print(f"[ERROR] Gagal kirim pesan: {e}")
        # Kirim pesan sederhana jika markdown gagal
        await update.message.reply_text(f"Halo {user_name}! Selamat datang di toko kami. Ketik 'help' untuk bantuan.")

async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    awaiting_admin_password[user_id] = True
    await update.message.reply_text("🔐 Masukkan password admin:")

async def admin_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in logged_in_admins:
        logged_in_admins.remove(user_id)
        await update.message.reply_text("✅ Logout berhasil!")
    else:
        await update.message.reply_text("❌ Anda belum login sebagai admin")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    user_message = update.message.text
    
    print(f"[DEBUG] Pesan dari {user_name} (ID: {user_id}): {user_message}")
    
    # Cek apakah user sedang proses login admin
    if user_id in awaiting_admin_password:
        if user_message == ADMIN_PASSWORD:
            logged_in_admins.add(user_id)
            del awaiting_admin_password[user_id]
            await update.message.reply_text("✅ Login admin berhasil!\n\nGunakan:\n/orders - Lihat semua pesanan\n/selesai ORD0001 - Tandai selesai\n/logout - Keluar dari admin")
        else:
            del awaiting_admin_password[user_id]
            await update.message.reply_text("❌ Password salah!")
        return
    
    # Cek apakah user sedang pilih metode pembayaran
    if user_id in awaiting_payment_method:
        payment_method = user_message.upper()
        
        if payment_method in ['TRANSFER', 'EWALLET', 'COD']:
            order = pending_orders[user_id]
            order['payment_method'] = payment_method
            
            if payment_method == 'COD':
                # COD langsung selesai, simpan order dan kurangi stok
                order['status'] = 'Menunggu Konfirmasi'
                order['payment_status'] = 'COD'
                
                # Kurangi stok produk
                for item in order['items']:
                    update_stock(item['product_code'], item['quantity'])
                
                orders = load_orders()
                orders.append(order)
                save_orders(orders)
                
                del pending_orders[user_id]
                del awaiting_payment_method[user_id]
                user_carts[user_id] = {}
                
                text = f"""
✅ *Pesanan Berhasil!*

📋 No. Pesanan: *{order['order_id']}*
💵 Total: Rp {order['total']:,.0f}
💳 Pembayaran: *COD (Bayar di Tempat)*

Pesanan Anda akan segera diproses.
Silakan siapkan uang pas saat barang tiba.

Terima kasih! 🙏
"""
                await update.message.reply_text(text, parse_mode='Markdown')
                
            elif payment_method == 'TRANSFER':
                awaiting_payment_proof[user_id] = True
                del awaiting_payment_method[user_id]
                
                text = f"""
💳 *Transfer Bank*

Silakan transfer ke:
🏦 *BCA: 1234567890*
📝 a.n. Toko Serba Ada

💵 Total: *Rp {order['total']:,.0f}*

Setelah transfer, kirim bukti transfer (foto/screenshot) ke chat ini.
"""
                await update.message.reply_text(text, parse_mode='Markdown')
                
            elif payment_method == 'EWALLET':
                awaiting_payment_proof[user_id] = True
                del awaiting_payment_method[user_id]
                
                text = f"""
📱 *E-Wallet*

Silakan transfer ke:
💳 *GoPay/OVO/Dana: 0812-3456-7890*
📝 a.n. Toko Serba Ada

💵 Total: *Rp {order['total']:,.0f}*

Setelah transfer, kirim bukti transfer (foto/screenshot) ke chat ini.
"""
                await update.message.reply_text(text, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Pilihan tidak valid!\n\nKetik: TRANSFER, EWALLET, atau COD")
        return
    
    user_message = user_message.lower()
    
    # Buat konteks produk untuk AI
    products_list = ""
    for prod in PRODUCTS.values():
        products_list += f"- {prod['name']} ({prod['code']}): Rp {prod['price']:,.0f}, Stok: {prod['stock']}, Kategori: {prod['category']}\n"
    
    # Cek keranjang user
    cart_info = ""
    if user_id in user_carts and user_carts[user_id]:
        cart_info = "\n\nKeranjang customer saat ini:\n"
        for code, qty in user_carts[user_id].items():
            prod = PRODUCTS[code]
            cart_info += f"- {prod['name']} × {qty}\n"
    
    system_prompt = f"""Anda adalah asisten toko online yang ramah. Tugas Anda:

1. Membantu customer menemukan dan membeli produk
2. Jika customer ingin beli, WAJIB jawab dengan format:
   BELI: KODE_PRODUK JUMLAH
   Contoh: BELI: PRD001 2 (untuk beli 2 item)
   Contoh: BELI: PRD001 1 (untuk beli 1 item)

3. Jika customer tanya produk/rekomendasi, jelaskan dan tawarkan untuk beli

Produk tersedia:
{products_list}
{cart_info}

PENTING: 
- Jika customer bilang "beli", "mau", "pesan", dll, jawab dengan "BELI: KODE_PRODUK JUMLAH"
- Deteksi jumlah dari kata customer (contoh: "2 keripik" = 2, "keripik 3" = 3)
- Jika tidak disebutkan jumlah, default 1
- Gunakan kode produk yang tepat
- Cek stok sebelum menyarankan
- Jika tidak yakin, tanyakan dulu"""

    try:
        await update.message.chat.send_action("typing")
        
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        
        # Cek apakah AI menyuruh beli
        if "BELI:" in ai_response:
            # Extract kode produk dan jumlah
            parts = ai_response.split("BELI:")
            if len(parts) > 1:
                items = parts[1].strip().split()
                product_code = items[0].strip()
                quantity = 1  # Default 1
                
                # Cek apakah ada jumlah
                if len(items) > 1:
                    try:
                        quantity = int(items[1])
                    except:
                        quantity = 1
                
                if product_code in PRODUCTS:
                    prod = PRODUCTS[product_code]
                    
                    # Cek stok
                    current_cart_qty = user_carts.get(user_id, {}).get(product_code, 0)
                    total_qty = current_cart_qty + quantity
                    
                    if total_qty > prod['stock']:
                        await update.message.reply_text(f"❌ Stok tidak cukup!\n\n📦 {prod['name']}\n📊 Stok tersedia: {prod['stock']}\n🛒 Di keranjang: {current_cart_qty}\n\nMaksimal bisa tambah: {prod['stock'] - current_cart_qty}")
                        return
                    
                    # Tambah ke keranjang
                    if user_id not in user_carts:
                        user_carts[user_id] = {}
                    
                    user_carts[user_id][product_code] = total_qty
                    
                    response_text = f"✅ *Ditambahkan ke keranjang!*\n\n📦 {prod['name']}\n🔢 Jumlah: {quantity}\n💰 Rp {prod['price']:,.0f} × {quantity} = Rp {prod['price'] * quantity:,.0f}\n\n🛒 Total di keranjang: {total_qty}\n\nKetik /keranjang untuk lihat keranjang\nKetik /checkout untuk bayar"
                    
                    await update.message.reply_text(response_text, parse_mode='Markdown')
                    return
        
        # Kirim respons AI biasa
        await update.message.reply_text(ai_response)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_carts or not user_carts[user_id]:
        await update.message.reply_text("🛒 Keranjang kosong\n\nChat dengan bot untuk belanja!")
        return
    
    text = "🛒 *Keranjang Belanja*\n\n"
    total = 0
    
    for product_code, qty in user_carts[user_id].items():
        prod = PRODUCTS[product_code]
        subtotal = prod['price'] * qty
        total += subtotal
        text += f"📦 {prod['name']}\n   Rp {prod['price']:,.0f} × {qty} = Rp {subtotal:,.0f}\n\n"
    
    text += f"━━━━━━━━━━━━━━━━\n💵 *Total: Rp {total:,.0f}*\n\nKetik /checkout untuk bayar\nKetik /batal untuk kosongkan keranjang"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    if user_id not in user_carts or not user_carts[user_id]:
        await update.message.reply_text("🛒 Keranjang kosong!")
        return
    
    # Cek stok dulu sebelum checkout
    for product_code, qty in user_carts[user_id].items():
        prod = PRODUCTS[product_code]
        if prod['stock'] < qty:
            await update.message.reply_text(f"❌ Stok {prod['name']} tidak cukup!\n\nStok tersedia: {prod['stock']}\nYang Anda pesan: {qty}")
            return
    
    order_items = []
    total = 0
    
    for product_code, qty in user_carts[user_id].items():
        prod = PRODUCTS[product_code]
        subtotal = prod['price'] * qty
        total += subtotal
        
        order_items.append({
            'product_code': product_code,
            'product_name': prod['name'],
            'quantity': qty,
            'price': prod['price'],
            'subtotal': subtotal
        })
    
    # Buat nomor pesanan simple
    orders = load_orders()
    order_number = len(orders) + 1
    order_id = f"#{order_number:03d}"  # Format: #001, #002, dst
    
    pending_orders[user_id] = {
        'order_id': order_id,
        'user_id': user_id,
        'user_name': user_name,
        'items': order_items,
        'total': total,
        'date': datetime.now().isoformat()
    }
    
    awaiting_payment_method[user_id] = True
    
    # Tampilkan ringkasan dan pilihan pembayaran
    items_text = ""
    for item in order_items:
        items_text += f"• {item['product_name']} × {item['quantity']} = Rp {item['subtotal']:,.0f}\n"
    
    text = f"""
📋 *Ringkasan Pesanan*

{items_text}
━━━━━━━━━━━━━━━━
💵 *Total: Rp {total:,.0f}*

━━━━━━━━━━━━━━━━

💳 *Pilih Metode Pembayaran:*

Ketik salah satu:
1️⃣ *TRANSFER* - Transfer Bank
2️⃣ *EWALLET* - GoPay/OVO/Dana
3️⃣ *COD* - Bayar di Tempat

Contoh: ketik "TRANSFER"
"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    orders = load_orders()
    
    user_orders = [o for o in orders if o['user_id'] == user_id]
    
    if not user_orders:
        await update.message.reply_text("📦 Belum ada pesanan")
        return
    
    text = "📦 *Pesanan Saya*\n\n"
    
    for order in reversed(user_orders[-5:]):
        date = datetime.fromisoformat(order['date']).strftime('%d/%m/%Y %H:%M')
        payment_status = order.get('payment_status', 'N/A')
        payment_method = order.get('payment_method', 'N/A')
        
        text += f"🔖 {order['order_id']}\n"
        text += f"💵 Rp {order['total']:,.0f}\n"
        text += f"💳 {payment_method}\n"
        text += f"💰 {payment_status}\n"
        text += f"📊 {order['status']}\n"
        text += f"📅 {date}\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def cancel_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_carts[user_id] = {}
    await update.message.reply_text("✅ Keranjang dikosongkan")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Cek apakah user sedang upload bukti bayar
    if user_id in awaiting_payment_proof:
        order = pending_orders[user_id]
        
        # Kurangi stok produk
        for item in order['items']:
            update_stock(item['product_code'], item['quantity'])
        
        # Simpan order dengan status menunggu konfirmasi
        order['status'] = 'Menunggu Konfirmasi Pembayaran'
        order['payment_status'] = 'Menunggu Verifikasi'
        order['payment_proof'] = update.message.photo[-1].file_id
        
        orders = load_orders()
        orders.append(order)
        save_orders(orders)
        
        del pending_orders[user_id]
        del awaiting_payment_proof[user_id]
        user_carts[user_id] = {}
        
        text = f"""
✅ *Bukti Pembayaran Diterima!*

📋 No. Pesanan: *{order['order_id']}*
💵 Total: Rp {order['total']:,.0f}
💳 Metode: {order['payment_method']}

Pembayaran Anda sedang diverifikasi oleh admin.
Kami akan menghubungi Anda segera.

Terima kasih! 🙏
"""
        await update.message.reply_text(text, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Anda tidak sedang dalam proses pembayaran.")

async def admin_confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Anda belum login sebagai admin!\n\nGunakan /admin untuk login terlebih dahulu.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Format salah!\n\nGunakan: /konfirmasi #001")
        return
    
    order_id = context.args[0]
    if not order_id.startswith('#'):
        order_id = '#' + order_id
    
    orders = load_orders()
    
    for order in orders:
        if order['order_id'] == order_id:
            order['status'] = 'Pembayaran Dikonfirmasi'
            order['payment_status'] = 'Lunas'
            save_orders(orders)
            
            # Kirim notifikasi ke customer
            customer_text = f"""
✅ *Pembayaran Dikonfirmasi!*

📋 No. Pesanan: *{order_id}*
💵 Total: Rp {order['total']:,.0f}
💰 Status: *LUNAS*

Pesanan Anda sedang diproses dan akan segera dikirim.

Terima kasih! 🙏
"""
            try:
                await context.bot.send_message(
                    chat_id=order['user_id'],
                    text=customer_text,
                    parse_mode='Markdown'
                )
            except:
                pass
            
            await update.message.reply_text(f"✅ Pembayaran {order_id} berhasil dikonfirmasi!\n\nNotifikasi telah dikirim ke customer.")
            return
    
    await update.message.reply_text(f"❌ Pesanan {order_id} tidak ditemukan!\n\nCek kembali nomor pesanan.")

# Admin commands
async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ Hanya admin")
        return

    orders = load_orders()

    if not orders:
        await update.message.reply_text("📦 Belum ada pesanan")
        return

    # Pisahkan pesanan berdasarkan status
    pending_orders = []
    completed_orders = []

    for order in orders:
        if order['status'] == 'Selesai':
            completed_orders.append(order)
        else:
            pending_orders.append(order)

    text = "📦 *Semua Pesanan*\n\n"

    # Tampilkan pesanan yang perlu diproses dulu
    if pending_orders:
        text += "⏳ *PERLU DIPROSES:*\n\n"
        for order in reversed(pending_orders[-10:]):
            date = datetime.fromisoformat(order['date']).strftime('%d/%m %H:%M')
            payment_status = order.get('payment_status', 'N/A')
            payment_method = order.get('payment_method', 'N/A')

            text += f"🔖 {order['order_id']} - {order['user_name']}\n"
            text += f"💵 Rp {order['total']:,.0f}\n"
            text += f"💳 {payment_method} | {payment_status}\n"
            text += f"📊 {order['status']}\n"
            text += f"📅 {date}\n"

            # Tampilkan action yang perlu dilakukan
            if payment_status == 'Menunggu Verifikasi':
                text += f"👉 /konfirmasi {order['order_id']}\n"
            elif payment_status == 'Lunas' or payment_status == 'COD':
                text += f"👉 /selesai {order['order_id']}\n"

            text += "\n"

    # Tampilkan pesanan selesai
    if completed_orders:
        text += "✅ *SELESAI:*\n\n"
        for order in reversed(completed_orders[-5:]):
            date = datetime.fromisoformat(order['date']).strftime('%d/%m %H:%M')
            payment_status = order.get('payment_status', 'N/A')

            text += f"🔖 {order['order_id']} - {order['user_name']}\n"
            text += f"💵 Rp {order['total']:,.0f} | {payment_status}\n"
            text += f"📅 {date}\n\n"

    await update.message.reply_text(text, parse_mode='Markdown')


async def admin_complete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Anda belum login sebagai admin!\n\nGunakan /admin untuk login terlebih dahulu.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Format salah!\n\nGunakan: /selesai #001")
        return
    
    order_id = context.args[0]
    if not order_id.startswith('#'):
        order_id = '#' + order_id
    
    orders = load_orders()
    
    for order in orders:
        if order['order_id'] == order_id:
            order['status'] = 'Selesai'
            save_orders(orders)
            
            # Kirim notifikasi ke customer
            customer_text = f"""
🎉 *Pesanan Selesai!*

📋 No. Pesanan: *{order_id}*
💵 Total: Rp {order['total']:,.0f}

Pesanan Anda telah selesai diproses.
Terima kasih telah berbelanja! 🙏

Jangan lupa belanja lagi ya! 😊
"""
            try:
                await context.bot.send_message(
                    chat_id=order['user_id'],
                    text=customer_text,
                    parse_mode='Markdown'
                )
            except:
                pass
            
            await update.message.reply_text(f"✅ Pesanan {order_id} ditandai selesai!\n\nNotifikasi telah dikirim ke customer.")
            return
    
    await update.message.reply_text(f"❌ Pesanan {order_id} tidak ditemukan!\n\nCek kembali nomor pesanan.")

def main():
    print("🏪 Bot toko dengan AI...")
    print(f"📦 {len(PRODUCTS)} produk")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("keranjang", show_cart))
    app.add_handler(CommandHandler("checkout", checkout))
    app.add_handler(CommandHandler("pesanan", show_orders))
    app.add_handler(CommandHandler("batal", cancel_cart))
    app.add_handler(CommandHandler("admin", admin_login))
    app.add_handler(CommandHandler("logout", admin_logout))
    app.add_handler(CommandHandler("orders", admin_orders))
    app.add_handler(CommandHandler("selesai", admin_complete))
    app.add_handler(CommandHandler("konfirmasi", admin_confirm_payment))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Siap!")
    
    # Untuk Railway, gunakan webhook jika ada PORT environment variable
    if os.getenv("RAILWAY_ENVIRONMENT"):
        print("🚂 Running on Railway with webhook...")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN')}"
        )
    else:
        print("💻 Running locally with polling...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
