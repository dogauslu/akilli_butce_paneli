# billing.py
from datetime import datetime
import sqlite3
from database import get_connection

def check_and_update_subscription(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return "suspended", "Kullanıcı bulunamadı."

    now = datetime.now()
    trial_start = datetime.strptime(user["trial_start_date"], "%Y-%m-%d %H:%M:%S")
    trial_end = trial_start + timedelta(days=7)
    
    # Kural 1: 1 Haftalık Ücretsiz Deneme Süresi Aktif mi?
    if now <= trial_end:
        cursor.execute("UPDATE users SET status = 'active' WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        remaining_days = (trial_end - now).days
        return "active", f"Ücretsiz deneme sürümündesiniz. Kalan süre: {remaining_days} gün."

    # Deneme süresi bitmiş, ücretli abonelik durumunu kontrol et
    current_day = now.day
    is_premium = user["is_premium"]
    last_pay_str = user["last_payment_date"]
    
    has_paid_this_month = False
    if last_pay_str:
        last_pay = datetime.strptime(last_pay_str, "%Y-%m-%d")
        if last_pay.month == now.month and last_pay.year == now.year:
            has_paid_this_month = True

    status = "active"
    message = "Aboneliğiniz aktif."

    # Kural 2: Ayın 15'i geldi veya geçti ama bu ay henüz ödeme yapılmadı
    if current_day >= 15 and not has_paid_this_month:
        # Kural 3: Ayın 15'i ile 20'si arası (Uyarı Dönemi)
        if 15 <= current_day <= 20:
            status = "warning"
            message = "⚠️ Dikkat! Aylık 20 TL abonelik ödemeniz tahsil edilemedi. Son ödeme tarihi her ayın 20'sidir. Lütfen kart bilgilerinizi güncelleyerek ödemenizi tamamlayın."
        # Kural 4: Ayın 20'sinden sonrası (Askıya Alma Dönemi)
        else:
            status = "suspended"
            message = "🛑 Ödeme süreniz dolmuştur! Verilerinize erişebilmek için aylık 20 TL olan üyelik ücretini ödemeniz gerekmektedir. Ödeme yapıldığı an verileriniz tekrar açılacaktır."
    
    cursor.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
    conn.commit()
    conn.close()
    return status, message

def process_fake_payment(user_id):
    """Kredi/Banka Kartı simüle eden ödeme fonksiyonu"""
    conn = get_connection()
    cursor = conn.cursor()
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        UPDATE users 
        SET is_premium = 1, last_payment_date = ?, status = 'active' 
        WHERE id = ?
    """, (today_str, user_id))
    conn.commit()
    conn.close()
    return True
