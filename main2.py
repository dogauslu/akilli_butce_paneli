import streamlit as st
import random
import smtplib
from email.mime.text import MIMEText
from database import init_db, register_user, verify_user, check_email_exists, update_password

init_db()
st.set_page_config(page_title="Finansal Asistan", layout="centered")

# Oturum Durumlarını Başlat
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "forgot_mode" not in st.session_state: st.session_state.forgot_mode = False
if "otp" not in st.session_state: st.session_state.otp = None

def send_email(to_email, code):
    try:
        # Kendi mail bilgilerini buraya gir veya st.secrets kullan
        sender = "senin_mailin@gmail.com" 
        password = "senin_uygulama_sifren" 
        msg = MIMEText(f"Doğrulama kodunuz: {code}")
        msg['Subject'] = "Şifre Sıfırlama Kodu"
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, to_email, msg.as_string())
        server.quit()
        return True
    except:
        return False

if not st.session_state.logged_in:
    if not st.session_state.forgot_mode:
        tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
        with tab1:
            u = st.text_input("Kullanıcı Adı", key="l_u")
            p = st.text_input("Şifre", type="password", key="l_p")
            if st.button("Giriş Yap", key="btn_login"):
                user = verify_user(u, p)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_info = dict(user)
                    st.rerun()
                else: st.error("Hatalı giriş!")
            
            if st.button("Şifremi Unuttum", key="btn_forgot"):
                st.session_state.forgot_mode = True
                st.rerun()
        with tab2:
            reg_u = st.text_input("Kullanıcı Adı", key="r_u")
            reg_name = st.text_input("Ad Soyad", key="r_n")
            reg_email = st.text_input("E-posta", key="r_e")
            reg_phone = st.text_input("Telefon", key="r_ph")
            reg_p = st.text_input("Şifre", type="password", key="r_p")
            if st.button("Kaydı Tamamla", key="btn_reg"):
                if register_user(reg_u, reg_name, reg_p, reg_email, reg_phone):
                    st.success("Kayıt başarılı!")
                else: st.error("Hata!")
    else:
        # Şifremi Unuttum Akışı
        st.subheader("Şifre Sıfırlama")
        f_email = st.text_input("E-posta Adresin", key="f_e")
        if st.button("Kod Gönder", key="btn_send"):
            if check_email_exists(f_email):
                st.session_state.otp = str(random.randint(100000, 999999))
                if send_email(f_email, st.session_state.otp):
                    st.success("Kod mailine gönderildi!")
                else: st.error("Mail gönderilemedi!")
            else: st.error("Bu mail kayıtlı değil!")
            
        code = st.text_input("Doğrulama Kodu", key="f_code")
        new_p = st.text_input("Yeni Şifre", type="password", key="f_newp")
        
        if st.button("Şifreyi Güncelle", key="btn_update"):
            if code == st.session_state.otp:
                update_password(f_email, new_p)
                st.success("Şifren güncellendi!")
                st.session_state.forgot_mode = False
                st.rerun()
            else: st.error("Hatalı kod!")
        
        if st.button("Geri Dön", key="btn_back"):
            st.session_state.forgot_mode = False
            st.rerun()
else:
    st.title("Hoş geldin!")
    if st.button("Çıkış", key="btn_logout"):
        st.session_state.logged_in = False
        st.rerun()
