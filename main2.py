import streamlit as st
import pandas as pd
import os
from database import init_db, register_user, verify_user, check_email_exists, check_username_exists

# Başlatma
init_db()

st.set_page_config(page_title="Finansal Asistan", layout="centered")

# --- ANA BÜTÇE İŞLEVLERİ ---
def ana_butce_uygulamasi(user_id):
    VERI_DOSYASI = f"akilli_butce_verileri_{user_id}.csv"
    
    def verileri_yukle():
        if os.path.exists(VERI_DOSYASI):
            return pd.read_csv(VERI_DOSYASI)
        return pd.DataFrame(columns=["Tarih", "Kategori", "Tür", "Tutar", "Açıklama"])

    df = verileri_yukle()

    st.title("🏦 Finansal Asistan")
    
    # Basit bir dashboard
    toplam_gelir = df[df["Tür"]=="Gelir"]["Tutar"].sum()
    toplam_gider = df[df["Tür"]=="Gider"]["Tutar"].sum()
    st.metric("Güncel Bakiye", f"₺{toplam_gelir - toplam_gider:,.2f}")

    if st.button("İşlem Ekle"):
        st.session_state.sayfa = "ekle"
        st.rerun()

    if "sayfa" not in st.session_state: st.session_state.sayfa = "liste"
    
    if st.session_state.sayfa == "ekle":
        with st.form("yeni_islem_formu"):
            tur = st.radio("Tür", ["Gelir", "Gider"], key="form_tur")
            tut = st.number_input("Tutar", min_value=0.0, key="form_tutar")
            kat = st.selectbox("Kategori", ["Maaş", "Market", "Diğer"], key="form_kat")
            if st.form_submit_button("Kaydet"):
                yeni = pd.DataFrame([{"Tarih": str(datetime.now().date()), "Kategori": kat, "Tür": tur, "Tutar": tut, "Açıklama": ""}])
                pd.concat([df, yeni]).to_csv(VERI_DOSYASI, index=False)
                st.success("İşlem eklendi!")
                st.session_state.sayfa = "liste"
                st.rerun()
    else:
        st.dataframe(df)

# --- OTURUM YÖNETİMİ (Keyler ile çakışma önlendi) ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        u = st.text_input("Kullanıcı Adı", key="login_u")
        p = st.text_input("Şifre", type="password", key="login_p")
        if st.button("Giriş Yap", key="btn_login"):
            user = verify_user(u, p)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_info = dict(user)
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")

    with tab2:
        reg_u = st.text_input("Kullanıcı Adı", key="reg_u")
        reg_name = st.text_input("Ad Soyad", key="reg_name")
        reg_email = st.text_input("E-posta", key="reg_email")
        reg_phone = st.text_input("Telefon", key="reg_phone")
        reg_p = st.text_input("Şifre", type="password", key="reg_p")
        
        if st.button("Kaydı Tamamla", key="btn_reg"):
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
    ana_butce_uygulamasi(st.session_state.user_info['id'])
    if st.sidebar.button("Çıkış Yap", key="btn_logout"):
        st.session_state.logged_in = False
        st.rerun()
