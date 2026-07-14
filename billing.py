from datetime import datetime, timedelta
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
    
    # Kural 1: 1 Haftalık Deneme Süresi Devam Ediyorsa
    if now <= trial_end:
        cursor.execute("UPDATE users SET status = 'active' WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return "active", f"🎁 Ücretsiz deneme sürümündesiniz. Kalan: {(trial_end - now).days} gün."

    # Kural 2: Deneme Süresi BİTTİYSE ve Hiç Ödeme Yapılmadıysa (is_premium == 0)
    if user["is_premium"] == 0:
        status = "suspended"
        message = "⏳ 7 günlük ücretsiz deneme süreniz sona erdi! Uygulamayı kullanmaya devam etmek ve verilerinize ulaşmak için aylık 20 TL abonelik işlemini tamamlayın."
        cursor.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
        conn.commit()
        conn.close()
        return status, message

    # Kural 3: Zaten Premium Üye İse (Ayın 15'i ve 20'si kuralları)
    current_day = now.day
    last_pay_str = user["last_payment_date"]
    
    has_paid_this_month = False
    if last_pay_str:
        last_pay = datetime.strptime(last_pay_str, "%Y-%m-%d")
        if last_pay.month == now.month and last_pay.year == now.year:
            has_paid_this_month = True

    status = "active"
    message = "Aboneliğiniz aktif."

    if current_day >= 15 and not has_paid_this_month:
        if 15 <= current_day <= 20:
            status = "warning"
            message = "⚠️ Dikkat! Aylık 20 TL ödemeniz alınamadı. Son ödeme tarihi ayın 20'sidir."
        else:
            status = "suspended"
            message = "🛑 Ödeme süreniz dolmuştur! Aylık 20 TL ödeme yaparak verilerinize ulaşabilirsiniz."
    
    cursor.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
    conn.commit()
    conn.close()
    return status, message

def process_fake_payment(user_id):
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
