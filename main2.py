#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Akıllı Bütçe Paneli - Yeni Modern Mobil UI, Tam Sürüm
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import random
import re
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

from database import init_db, register_user, verify_user, check_email_exists, update_password, cleanup_inactive_accounts, check_username_exists
from billing import check_and_update_subscription, process_fake_payment

st.set_page_config(page_title="Akıllı Bütçe Paneli (V3)", page_icon="📱", layout="centered")

# --- ÖZEL CSS (GÖRSELDEKİ TASARIM İÇİN) ---
st.markdown("""
<style>
    /* Streamlit varsayılan padding'leri küçült */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 600px; }
    
    /* Bakiye Kartı (Hero Card) */
    .hero-card {
        background: linear-gradient(135deg, #1A2A40 0%, #205E6D 50%, #2C8C9E 100%);
        border-radius: 15px;
        padding: 25px 20px;
        color: white;
        text-align: center;
        box-shadow: 0px 8px 15px rgba(0,0,0,0.15);
        margin-bottom: 20px;
    }
    .hero-title { font-size: 14px; opacity: 0.9; margin-bottom: 5px; }
    .hero-balance { font-size: 38px; font-weight: 700; margin: 0; letter-spacing: -1px; }
    .hero-subtitle { font-size: 14px; opacity: 0.8; margin-top: 5px; }
    
    /* İşlem Listesi (Son İşlemler) */
    .islem-satiri {
        display: flex; align-items: center; justify-content: space-between;
        padding: 12px 0; border-bottom: 1px solid #f0f0f0;
    }
    .islem-sol { display: flex; align-items: center; }
    .islem-ikon {
        width: 45px; height: 45px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        margin-right: 15px; font-size: 20px; color: white;
    }
    .bg-market { background-color: #274472; }
    .bg-kahve { background-color: #A67B5B; }
    .bg-maas { background-color: #2C8C9E; }
    .bg-diger { background-color: #7D7D7D; }
    
    .islem-detay p { margin: 0; padding: 0; line-height: 1.2; }
    .islem-baslik { font-weight: 600; font-size: 16px; color: #333; }
    .islem-tarih { font-size: 12px; color: #888; margin-top: 3px !important; }
    
    .islem-tutar { font-weight: 600; font-size: 16px; }
    .tutar-eksi { color: #333; }
    .tutar-arti { color: #4CAF50; }
    
    /* Streamlit radyo butonlarını yatay menüye benzetme */
    div.row-widget.stRadio > div{flex-direction:row; justify-content: space-around; background: #f8f9fa; padding: 10px; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

init_db()
cleanup_inactive_accounts()

# --- ANA BÜTÇE PANELİ ---
def ana_butce_uygulamasi(user_id):
    VERI_DOSYASI = f"akilli_butce_verileri_{user_id}.csv"

    def verileri_yukle():
        if os.path.exists(VERI_DOSYASI):
            df = pd.read_csv(VERI_DOSYASI)
            df["Tarih"] = pd.to_datetime(df["Tarih"]).dt.date
            return df
        else:
            bos_df = pd.DataFrame(columns=["Tarih", "Kategori", "Tür", "Tutar", "Açıklama"])
            bos_df.to_csv(VERI_DOSYASI, index=False)
            return bos_df

    giderler_df = verileri_yukle()
    
    if "aktif_sayfa" not in st.session_state:
        st.session_state.aktif_sayfa = "Ana Sayfa"

    sayfa = st.radio("Menü", ["Ana Sayfa", "İşlemler", "Banka Entegrasyonu", "Profil"], 
                     horizontal=True, label_visibility="collapsed")

    if sayfa == "Ana Sayfa":
        toplam_gelir = giderler_df[giderler_df["Tür"] == "Gelir"]["Tutar"].sum()
        toplam_gider = giderler_df[giderler_df["Tür"] == "Gider"]["Tutar"].sum()
        kalan_bakiye = toplam_gelir - toplam_gider
        
        bugun = datetime.now().date()
        bu_ay_df = giderler_df[pd.to_datetime(giderler_df["Tarih"]).dt.month == bugun.month]
        bu_ay_gider = bu_ay_df[bu_ay_df["Tür"] == "Gider"]["Tutar"].sum()
        bu_ay_gelir = bu_ay_df[bu_ay_df["Tür"] == "Gelir"]["Tutar"].sum()
        bu_ay_net = bu_ay_gelir - bu_ay_gider
        
        st.markdown(f"""
            <div class="hero-card">
                <div class="hero-title">Toplam Bakiye</div>
                <div class="hero-balance">₺{kalan_bakiye:,.2f}</div>
                <div class="hero-subtitle">Bu Ay {('+₺' if bu_ay_net >= 0 else '-₺')}{abs(bu_ay_net):,.2f}</div>
            </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🟢 Gelir Ekle", use_container_width=True):
                st.info("Üst menüden 'İşlemler' sekmesine gidiniz.")
        with c2:
            if st.button("🔴 Gider Ekle", use_container_width=True):
                st.info("Üst menüden 'İşlemler' sekmesine gidiniz.")
        with c3:
            if st.button("🔵 Transfer", use_container_width=True):
                st.info("Yakında Eklenecek")

        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                <h3 style="margin:0; font-size:20px;">Aylık Genel Bakış</h3>
                <span style="color:#666; font-size:14px;">Bu ay harcama: ₺{bu_ay_gider:,.0f}</span>
            </div>
        """, unsafe_allow_html=True)
        
        sadece_giderler = giderler_df[giderler_df["Tür"] == "Gider"]
        if not sadece_giderler.empty:
            gunluk_toplam = sadece_giderler.groupby("Tarih")["Tutar"].sum().reset_index()
            fig = px.area(gunluk_toplam, x="Tarih", y="Tutar")
            
            fig.update_traces(line_shape='spline', fillcolor='rgba(44, 140, 158, 0.2)', line_color='#2C8C9E')
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(showgrid=False, visible=False),
                yaxis=dict(showgrid=False, visible=False),
                height=150
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Grafik oluşturulabilmesi için gider işlemi ekleyin.")

        st.markdown("<h3 style='margin-bottom:10px; font-size:20px;'>Son İşlemler</h3>", unsafe_allow_html=True)
        
        if giderler_df.empty:
            st.write("Henüz işlem yok.")
        else:
            son_5 = giderler_df.tail(5).iloc[::-1]
            
            html_islem_listesi = ""
            for _, row in son_5.iterrows():
                kat = str(row['Kategori']).lower()
                ikon, bg_class = "🏷️", "bg-diger"
                if "market" in kat or "gıda" in kat: ikon, bg_class = "🛒", "bg-market"
                elif "kahve" in kat or "yemek" in kat: ikon, bg_class = "☕", "bg-kahve"
                elif "maaş" in kat or row['Tür'] == "Gelir": ikon, bg_class = "💵", "bg-maas"
                
                tutar_str = f"₺{row['Tutar']:,.2f}"
                if row['Tür'] == 'Gider':
                    tutar_html = f"<div class='islem-tutar tutar-eksi'>-{tutar_str}</div>"
                else:
                    tutar_html = f"<div class='islem-tutar tutar-arti'>+{tutar_str}</div>"
                    
                html_islem_listesi += f"""
                <div class="islem-satiri">
                    <div class="islem-sol">
                        <div class="islem-ikon {bg_class}">{ikon}</div>
                        <div class="islem-detay">
                            <p class="islem-baslik">{row['Kategori']}</p>
                            <p class="islem-tarih">{row['Tarih']}</p>
                        </div>
                    </div>
                    {tutar_html}
                </div>
                """
            st.markdown(html_islem_listesi, unsafe_allow_html=True)

    elif sayfa == "İşlemler":
        st.header("➕ Yeni İşlem Ekle")
        with st.form("islem_formu"):
            tarih = st.date_input("Tarih")
            tur = st.radio("İşlem Türü", ["Gider", "Gelir"], horizontal=True)
            
            if tur == "Gider":
                kategori = st.selectbox("Kategori", ["Market", "Kahve", "Yemek", "Ulaşım", "Faturalar", "Eğlence", "Diğer"])
            else:
                kategori = st.selectbox("Kategori", ["Maaş", "Harçlık", "Yatırım Getirisi", "Diğer"])
                
            tutar = st.number_input("Tutar (TL)", min_value=0.0, format="%.2f")
            aciklama = st.text_input("Açıklama (İsteğe Bağlı)")
            kaydet_butonu = st.form_submit_button("Kaydet")
            
            if kaydet_butonu:
                yeni_islem = pd.DataFrame([{"Tarih": tarih, "Kategori": kategori, "Tür": tur, "Tutar": tutar, "Açıklama": aciklama}])
                guncel_df = pd.concat([giderler_df, yeni_islem], ignore_index=True)
                guncel_df.to_csv(VERI_DOSYASI, index=False)
                st.success("İşlem başarıyla eklendi! Ana Sayfadan görebilirsiniz.")

    elif sayfa == "Banka Entegrasyonu":
        st.header("🔄 Dosya Yükle")
        islem_turu = st.radio("İşlem Türü", ["Gider (Kredi Kartı)", "Gelir (Hesap Dökümü)"], horizontal=True)
        yuklenen_dosya = st.file_uploader("CSV veya Excel dosyası seçin", type=["csv", "xlsx"])

        if yuklenen_dosya is not None:
            try:
                ekstre = pd.read_csv(yuklenen_dosya) if yuklenen_dosya.name.endswith('.csv') else pd.read_excel(yuklenen_dosya)
                c1, c2, c3 = st.columns(3)
                tarih_kol = c1.selectbox("Tarih", ekstre.columns)
                aciklama_kol = c2.selectbox("Açıklama", ekstre.columns)
                tutar_kol = c3.selectbox("Tutar", ekstre.columns)

                if st.button("Veriyi Sisteme İşle"):
                    yeni_veriler = pd.DataFrame()
                    yeni_veriler["Tarih"] = pd.to_datetime(ekstre[tarih_kol]).dt.date
                    yeni_veriler["Açıklama"] = ekstre[aciklama_kol].astype(str)
                    yeni_veriler["Tutar"] = ekstre[tutar_kol].astype(float).abs()
                    yeni_veriler["Tür"] = "Gider" if "Gider" in islem_turu else "Gelir"
                    yeni_veriler["Kategori"] = "Diğer"
                    
                    guncel_df = pd.concat([verileri_yukle(), yeni_veriler], ignore_index=True)
                    guncel_df.to_csv(VERI_DOSYASI, index=False)
                    st.success(f"Başarılı! {len(yeni_veriler)} işlem eklendi.")
            except Exception as e:
                st.error(f"Hata: {e}")

    elif sayfa == "Profil":
        user = st.session_state.user_info
        st.header("👤 Profiliniz")
        st.write(f"**Ad Soyad:** {user['full_name']}")
        st.write(f"**Kullanıcı Adı:** {user['username']}")
        st.write(f"**E-posta:** {user['email']}")
        
        status, message = check_and_update_subscription(user["id"])
        if status == "active": st.success(message)
        elif status == "warning": st.warning(message)
        
        st.markdown("---")
        if st.button("🚪 Güvenli Çıkış Yap", type="primary"):
            st.session_state.logged_in = False
            st.session_state.user_info = None
            st.rerun()

# --- OTURUM VE YÖNETİM SİSTEMİ ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_info" not in st.session_state: st.session_state.user_info = None
if "otp_sent" not in st.session_state: st.session_state.otp_sent = False
if "generated_otp" not in st.session_state: st.session_state.generated_otp = None
if "forgot_password_mode" not in st.session_state: st.session_state.forgot_password_mode = False
if "reset_otp_sent" not in st.session_state: st.session_state.reset_otp_sent = False
if "reset_otp" not in st.session_state: st.session_state.reset_otp = None
if "reset_email" not in st.session_state: st.session_state.reset_email = None
if "reset_otp_verified" not in st.session_state: st.session_state.reset_otp_verified = False

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        if not st.session_state.forgot_password_mode:
            st.subheader("Üye Girişi")
            login_user = st.text_input("Kullanıcı Adı", key="login_user")
            show_pass_login = st.checkbox("Parolayı Göster", key="show_login")
            login_pass = st.text_input("Şifre", type="default" if show_pass_login else "password", key="login_pass")
            
            if st.button("Giriş Yap"):
                user = verify_user(login_user, login_pass)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_info = dict(user)
                    st.success("Giriş başarılı!")
                    st.rerun()
                else: st.error("Kullanıcı adı veya şifre hatalı!")
            
            st.markdown("---")
            if st.button("🔑 Şifremi Unuttum"):
                st.session_state.forgot_password_mode = True
                st.rerun()
        else:
            st.subheader("Şifre Sıfırlama")
            if st.button("⬅️ Geri Dön"):
                st.session_state.forgot_password_mode = False
                st.session_state.reset_otp_sent = False
                st.session_state.reset_otp_verified = False
                st.rerun()
            
            if not st.session_state.reset_otp_verified:
                st.info("Lütfen sisteme kayıtlı e-posta adresinizi girin.")
                reset_email = st.text_input("E-posta Adresi", key="fp_email")
                
                if st.button("Sıfırlama Kodu Gönder"):
                    if check_email_exists(reset_email):
                        st.session_state.reset_otp = str(random.randint(100000, 999999))
                        st.session_state.reset_email = reset_email
                        try:
                            gonderici_mail = st.secrets["email"]["gonderici"]
                            gonderici_sifre = st.secrets["email"]["sifre"]
                            msg = MIMEText(f"Akıllı Bütçe Paneli şifre sıfırlama kodunuz: {st.session_state.reset_otp}")
                            msg['Subject'] = 'Şifre Sıfırlama Talebi'
                            msg['From'] = gonderici_mail
                            msg['To'] = reset_email
                            server = smtplib.SMTP('smtp.gmail.com', 587)
                            server.starttls()
                            server.login(gonderici_mail, gonderici_sifre)
                            server.send_message(msg)
                            server.quit()
                            st.session_state.reset_otp_sent = True
                            st.success("📧 Sıfırlama kodu gönderildi!")
                        except Exception as e: st.error(f"E-posta gönderilemedi. Hata: {e}")
                    else: st.error("Hesap bulunamadı!")
                
                if st.session_state.reset_otp_sent:
                    st.markdown("---")
                    entered_otp = st.text_input("E-postanıza Gelen 6 Haneli Kodu Girin")
                    if st.button("Kodu Doğrula"):
                        if entered_otp == st.session_state.reset_otp:
                            st.session_state.reset_otp_verified = True
                            st.rerun()
                        else: st.error("❌ Hatalı doğrulama kodu!")
            else:
                st.success("✅ Kod doğrulandı! Şimdi yeni şifrenizi oluşturabilirsiniz.")
                show_pass_reset = st.checkbox("Yeni Şifreyi Göster", key="show_reset")
                new_pass = st.text_input("Yeni Şifre", type="default" if show_pass_reset else "password")
                new_pass_confirm = st.text_input("Yeni Şifre Tekrar", type="default" if show_pass_reset else "password")
                
                if st.button("Şifreyi Güncelle"):
                    if new_pass != new_pass_confirm: st.error("❌ Şifreler eşleşmiyor!")
                    elif len(new_pass) < 8 or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_pass):
                        st.error("🔒 Şifreniz en az 8 karakter ve 1 özel karakter içermelidir.")
                    else:
                        update_password(st.session_state.reset_email, new_pass)
                        st.success("🎉 Şifreniz başarıyla güncellendi!")
                        st.session_state.reset_otp_sent = False
                        st.session_state.reset_otp_verified = False
                        st.session_state.reset_otp = None
                
    with tab2:
        st.subheader("Yeni Hesap Oluştur (7 Gün Ücretsiz)")
        reg_username = st.text_input("Kullanıcı Adı", key="reg_user")
        reg_name = st.text_input("Ad Soyad", key="reg_name")
        reg_email = st.text_input("E-posta Adresi", key="reg_email")
        reg_phone = st.text_input("Cep Telefonu", placeholder="05xxxxxxxxx", key="reg_phone")
        
        show_pass_reg = st.checkbox("Şifreyi Göster", key="show_reg")
        reg_pass = st.text_input(
            "Şifre Belirleyin", 
            type="default" if show_pass_reg else "password", 
            key="reg_pass"
        )
        reg_pass_confirm = st.text_input(
            "Şifre Tekrarı", 
            type="default" if show_pass_reg else "password", 
            key="reg_pass_confirm"
        )
        
        if "captcha_num1" not in st.session_state:
            st.session_state.captcha_num1 = random.randint(1, 10)
            st.session_state.captcha_num2 = random.randint(1, 10)
            
        captcha_answer = st.number_input(
            f"Ben Robot Değilim: {st.session_state.captcha_num1} + {st.session_state.captcha_num2} = ?",
            step=1, value=0, key="captcha_answer"
        )
        
        if st.button("Doğrulama Kodu Gönder"):
            if check_username_exists(reg_username):
                st.error("❌ Bu kullanıcı adı başkası tarafından alınmış! Lütfen farklı bir kullanıcı adı belirleyin.")
            elif check_email_exists(reg_email):
                st.error("❌ Bu e-posta adresi zaten kullanılıyor! Lütfen 'Giriş Yap' sekmesini kullanın veya başka bir e-posta deneyin.")
            elif reg_pass != reg_pass_confirm:
                st.error("🔒 Hata: Girdiğiniz şifreler birbiriyle eşleşmiyor!")
            elif len(reg_pass) < 8:
                st.error(f"🔒 Hata: Şifreniz çok kısa! En az 8 karakter olmalıdır. (Şu an {len(reg_pass)} karakter girdiniz)")
            elif not re.search(r"[!@#$%^&*(),.?\":{}|<>]", reg_pass):
                st.error("🔒 Hata: Şifreniz en az bir adet özel karakter içermelidir! (Örnek: ! @ # $ % ^ & *)")
            elif reg_username and reg_name and reg_email and reg_phone and reg_pass:
                if captcha_answer == (st.session_state.captcha_num1 + st.session_state.captcha_num2):
                    st.session_state.generated_otp = str(random.randint(100000, 999999))
                    
                    try:
                        gonderici_mail = st.secrets["email"]["gonderici"]
                        gonderici_sifre = st.secrets["email"]["sifre"]
                        
                        msg = MIMEText(f"Doğrulama kodunuz: {st.session_state.generated_otp}")
                        msg['Subject'] = 'Hesap Doğrulama Kodunuz'
                        msg['From'] = gonderici_mail
                        msg['To'] = reg_email

                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        server.login(gonderici_mail, gonderici_sifre)
                        server.send_message(msg)
                        server.quit()
                        
                        st.session_state.otp_sent = True
                        st.success(f"📧 Doğrulama kodu gönderildi!")
                    except Exception as e:
                        st.error(f"E-posta gönderilemedi. Hata detayları: {e}")
                else:
                    st.error("❌ Robot testi başarısız! Toplama işlemini doğru yaptığınızdan emin olun.")
            else:
                st.error("⚠️ Lütfen formu eksiksiz doldurun.")
                
        if st.session_state.otp_sent:
            user_otp = st.text_input("Doğrulama Kodunu Girin", key="user_otp")
            if st.button("Kaydı Tamamla"):
                if user_otp == st.session_state.generated_otp:
                    success = register_user(
                        st.session_state.reg_user, 
                        st.session_state.reg_name, 
                        st.session_state.reg_pass, 
                        st.session_state.reg_email, 
                        st.session_state.reg_phone
                    )
                    if success:
                        st.success("🎉 Kaydınız başarıyla tamamlandı! 7 günlük ücretsiz denemeniz başladı.")
                        st.session_state.otp_sent = False
                        st.session_state.generated_otp = None
                    else:
                        st.error("❌ Kayıt Başarısız: Bu telefon numarası sistemde zaten kayıtlı!")
                else:
                    st.error("❌ Hatalı doğrulama kodu girdiniz.")

else:
    user = st.session_state.user_info
    status, message = check_and_update_subscription(user["id"])
    
    if status == "suspended":
        st.error(message)
        st.warning("Verilerinize erişiminiz duraklatılmıştır. Lütfen aboneliğinizi başlatın.")
        st.subheader("💳 Güvenli Kart Ödeme Ekranı (Aylık 20 TL)")
        with st.form("payment_form"):
            card_name = st.text_input("Kart Üzerindeki İsim")
            card_no = st.text_input("Kart Numarası", max_chars=16)
            col1, col2 = st.columns(2)
            with col1: 
                card_exp = st.text_input("Son Kullanma (AA/YY)")
            with col2: 
                card_cvv = st.text_input("CVV", type="password", max_chars=3)
            pay_submit = st.form_submit_button("Güvenli Ödeme Yap ve Verilerimi Aç")
            if pay_submit:
                if card_name and len(card_no) == 16 and card_exp and len(card_cvv) == 3:
                    process_fake_payment(user["id"])
                    st.success("Ödemeniz başarıyla alındı! Aboneliğiniz aktif edildi.")
                    st.rerun()
                else: 
                    st.error("Lütfen kart bilgilerini doğru girin.")
    else:
        if status == "warning":
            st.warning(message)
            if st.button("💳 Şimdi Ödeme Yap (20 TL)"):
                process_fake_payment(user["id"])
                st.success("Ödemeniz alındı!")
                st.rerun()
        
        ana_butce_uygulamasi(user["id"])
