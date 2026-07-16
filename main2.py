import streamlit as st
import pandas as pd
import os
from database import init_db, register_user, verify_user

# Uygulamayı Başlat
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
                st.error("Kullanıcı adı veya şifre hatalı!")
    with tab2:
        reg_u = st.text_input("Kullanıcı Adı", key="r_u")
        reg_n = st.text_input("Ad Soyad", key="r_n")
        reg_e = st.text_input("E-posta", key="r_e")
        reg_ph = st.text_input("Telefon", key="r_ph")
        reg_p = st.text_input("Şifre", type="password", key="r_p")
        if st.button("Kaydı Tamamla"):
            if register_user(reg_u, reg_n, reg_p, reg_e, reg_ph):
                st.success("Kayıt başarılı, giriş yapabilirsin.")
            else:
                st.error("Kayıt başarısız!")
else:
    st.title("💰 Bütçe Takip Paneli")
    st.write(f"Hoş geldin, {st.session_state.user_info['full_name']}")
    
    # Çok basit veri girişi
    st.subheader("İşlem Ekle")
    tutar = st.number_input("Tutar", min_value=0.0)
    tur = st.radio("Tür", ["Gelir", "Gider"])
    if st.button("Kaydet"):
        st.write(f"{tur} kaydedildi: {tutar} TL")
        
    if st.button("Çıkış Yap"):
        st.session_state.logged_in = False
        st.rerun()
