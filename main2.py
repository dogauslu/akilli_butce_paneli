import streamlit as st
from database import init_db, register_user, verify_user, check_email_exists, check_username_exists

# Başlangıç Ayarları
init_db()
st.set_page_config(page_title="Finansal Asistan", layout="centered")

# Oturum Yönetimi
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        u = st.text_input("Kullanıcı Adı")
        p = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap"):
            user = verify_user(u, p)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_info = dict(user)
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")

    with tab2:
        reg_u = st.text_input("Kullanıcı Adı (Kayıt)")
        reg_name = st.text_input("Ad Soyad")
        reg_email = st.text_input("E-posta")
        reg_phone = st.text_input("Telefon")
        reg_p = st.text_input("Şifre", type="password")
        
        if st.button("Kaydı Tamamla"):
            if check_username_exists(reg_u):
                st.error("Bu kullanıcı adı alınmış!")
            elif check_email_exists(reg_email):
                st.error("Bu e-posta zaten kullanımda!")
            else:
                if register_user(reg_u, reg_name, reg_p, reg_email, reg_phone):
                    st.success("Kayıt başarılı! Giriş yapabilirsiniz.")
                else:
                    st.error("Bir hata oluştu.")
else:
    st.title(f"Hoş geldin {st.session_state.user_info['full_name']}")
    st.write("Panelin başarıyla çalışıyor!")
    if st.button("Çıkış Yap"):
        st.session_state.logged_in = False
        st.rerun()
