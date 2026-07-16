import streamlit as st
from database import init_db, register_user, verify_user, check_email_exists, check_username_exists

init_db()
st.set_page_config(page_title="Bütçe Paneli", layout="centered")

if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    with tab1:
        u = st.text_input("Kullanıcı Adı", key="l_u")
        p = st.text_input("Şifre", type="password", key="l_p")
        if st.button("Giriş Yap"):
            user = verify_user(u, p)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_info = dict(user)
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")
    with tab2:
        reg_u = st.text_input("Kullanıcı Adı", key="r_u")
        reg_n = st.text_input("Ad Soyad", key="r_n")
        reg_e = st.text_input("E-posta", key="r_e")
        reg_ph = st.text_input("Telefon", key="r_ph")
        reg_p = st.text_input("Şifre", type="password", key="r_p")
        if st.button("Kaydı Tamamla"):
            if check_username_exists(reg_u):
                st.error("Bu kullanıcı adı zaten alınmış!")
            elif check_email_exists(reg_e):
                st.error("Bu e-posta zaten kullanımda!")
            elif register_user(reg_u, reg_n, reg_p, reg_e, reg_ph):
                st.success("Kayıt başarılı! Giriş yapabilirsiniz.")
            else:
                st.error("Bilinmeyen bir veritabanı hatası oluştu.")
else:
    st.title("💰 Bütçe Takip Paneli")
    st.write(f"Hoş geldin, {st.session_state.user_info['full_name']}")
    if st.button("Çıkış Yap"):
        st.session_state.logged_in = False
        st.rerun()
