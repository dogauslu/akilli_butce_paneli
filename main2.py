#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Akıllı Bütçe Paneli - Tam Sürüm (KVKK Silme Kuralı Ekli)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
import random
import re
import smtplib
from email.mime.text import MIMEText

# Temizlik robotunu da import ettik
from database import init_db, register_user, verify_user, check_email_exists, update_password, cleanup_inactive_accounts
from billing import check_and_update_subscription, process_fake_payment

st.set_page_config(page_title="Akıllı Bütçe Paneli (V2)", page_icon="🧠", layout="wide")

# Veritabanını başlat ve 1 yılı dolan ödemesiz hesapları arka planda temizle
init_db()
cleanup_inactive_accounts()

# --- ANA BÜTÇE PANELİ ---
def ana_butce_uygulamasi(user_id):
    st.title("💰 Akıllı Bütçe Yönetim Paneli")
    st.info("Hesabınız aktif. Verileriniz kişiye özel olarak güvenli şekilde saklanmaktadır.")

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

    st.sidebar.title("Akıllı Menü V2")
    sayfa = st.sidebar.selectbox("Sayfa Seçin", ["Genel Bakış", "İşlem Ekle", "Raporlar", "Banka Entegrasyonu"])

    if sayfa == "Genel Bakış":
        st.header("📊 Genel Bakış")
        
        toplam_gelir = giderler_df[giderler_df["Tür"] == "Gelir"]["Tutar"].sum()
        toplam_gider = giderler_df[giderler_df["Tür"] == "Gider"]["Tutar"].sum()
        kalan_bakiye = toplam_gelir - toplam_gider
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Toplam Gelir", f"{toplam_gelir:,.2f} TL")
        col2.metric("Toplam Gider", f"{toplam_gider:,.2f} TL")
        col3.metric("Kalan Bakiye", f"{kalan_bakiye:,.2f} TL")
        
        st.subheader("Son İşlemler")
        st.dataframe(giderler_df.tail(5))

    elif sayfa == "İşlem Ekle":
        st.header("➕ Yeni İşlem Ekle")
        
        with st.form("islem_formu"):
            tarih = st.date_input("Tarih")
            tur = st.radio("İşlem Türü", ["Gider", "Gelir"])
            
            if tur == "Gider":
                kategori = st.selectbox("Kategori", ["Market", "Giyim", "Eğlence", "Yemek", "Ulaşım", "Faturalar", "Diğer"])
            else:
                kategori = st.selectbox("Kategori", ["Maaş", "Harçlık", "Yatırım Getirisi", "Diğer"])
                
            tutar = st.number_input("Tutar (TL)", min_value=0.0, format="%.2f")
            aciklama = st.text_input("Açıklama")
            
            kaydet_butonu = st.form_submit_button("Kaydet")
            
            if kaydet_butonu:
                yeni_islem = pd.DataFrame([{
                    "Tarih": tarih,
                    "Kategori": kategori,
                    "Tür": tur,
                    "Tutar": tutar,
                    "Açıklama": aciklama
                }])
                guncel_df = pd.concat([giderler_df, yeni_islem], ignore_index=True)
                guncel_df.to_csv(VERI_DOSYASI, index=False)
                st.success("İşlem başarıyla eklendi!")

    elif sayfa == "Raporlar":
        st.header("📈 Raporlar ve Analizler")
        
        if giderler_df.empty:
            st.info("Henüz raporlanacak bir veri yok. Önce birkaç işlem ekleyin.")
        else:
            col_grafik1, col_grafik2 = st.columns(2)
            
            with col_grafik1:
                st.subheader("Gider Dağılımı")
                sadece_giderler = giderler_df[giderler_df["Tür"] == "Gider"]
                if not sadece_giderler.empty:
                    kategori_toplam = sadece_giderler.groupby("Kategori")["Tutar"].sum().reset_index()
                    fig_pie = px.pie(kategori_toplam, values="Tutar", names="Kategori", hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.write("Henüz gider verisi yok.")
                    
            with col_grafik2:
                st.subheader("Günlük Harcama Trendi")
                sadece_giderler = giderler_df[giderler_df["Tür"] == "Gider"]
                if not sadece_giderler.empty:
                    gunluk_toplam = sadece_giderler.groupby("Tarih")["Tutar"].sum().reset_index()
                    fig_bar = px.bar(gunluk_toplam, x='Tarih', y='Tutar', 
                                     color='Tutar', color_continuous_scale='Reds',
                                     text_auto='.0f')
                    fig_bar.update_layout(xaxis_tickangle=-45, margin=dict(b=80), xaxis_title="", yaxis_title="")
                    fig_bar.update_xaxes(type='category')
                    fig_bar.update_traces(textposition='outside') 
                    st.plotly_chart(fig_bar, use_container_width=True)
                    
    elif sayfa == "Banka Entegrasyonu":
        st.header("🔄 Veri Entegrasyonu")
        islem_turu = st.radio("Hangi tür veriyi yüklüyorsunuz?", ["Kredi Kartı Harcamaları (Gider)", "Maaş/Transfer (Gelir)"])

        yuklenen_dosya = st.file_uploader("Dosyanızı seçin", type=["csv", "xlsx"])

        if yuklenen_dosya is not None:
            try:
                ekstre = pd.read_csv(yuklenen_dosya) if yuklenen_dosya.name.endswith('.csv') else pd.read_excel(yuklenen_dosya)
                
                st.subheader("⚙️ Kolon Eşleştirme")
                c1, c2, c3 = st.columns(3)
                tarih_kol = c1.selectbox("Tarih Sütunu", ekstre.columns)
                aciklama_kol = c2.selectbox("Açıklama Sütunu", ekstre.columns)
                tutar_kol = c3.selectbox("Tutar Sütunu", ekstre.columns)

                if st.button("Veriyi Sisteme İşle"):
                    yeni_veriler = pd.DataFrame()
                    yeni_veriler["Tarih"] = pd.to_datetime(ekstre[tarih_kol]).dt.date
                    yeni_veriler["Açıklama"] = ekstre[aciklama_kol].astype(str)
                    yeni_veriler["Tutar"] = ekstre[tutar_kol].astype(float).abs()
                    
                    yeni_veriler["Tür"] = "Gider" if "Gider" in islem_turu else "Gelir"

                    try:
                        with open("kategoriler.json", "r", encoding="utf-8") as f:
                            kategori_haritasi = json.load(f)
                    except: 
                        kategori_haritasi = {}

                    kategoriler = []
                    for aciklama in yeni_veriler["Açıklama"]:
                        metin = str(aciklama).upper()
                        bulundu = False
                        for kat, markalar in kategori_haritasi.items():
                            if any(m in metin for m in markalar):
                                kategoriler.append(kat)
                                bulundu = True
                                break
                        if not bulundu: 
                            kategoriler.append("Diğer")
                    
                    yeni_veriler["Kategori"] = kategoriler

                    guncel_df = pd.concat([verileri_yukle(), yeni_veriler], ignore_index=True)
                    guncel_df.to_csv(VERI_DOSYASI, index=False)
                    st.success(f"Başarılı! {len(yeni_veriler)} işlem eklendi.")
            except Exception as e:
                st.error(f"Hata: {e}")

# --- OTURUM VE YÖNETİM ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "otp_sent" not in st.session_state:
    st.session_state.otp_sent = False
if "generated_otp" not in st.session_state:
    st.session_state.generated_otp = None

if "forgot_password_mode" not in st.session_state:
    st.session_state.forgot_password_mode = False
if "reset_otp_sent" not in st.session_state:
    st.session_state.reset_otp_sent = False
if "reset_otp" not in st.session_state:
    st.session_state.reset_otp = None
if "reset_email" not in st.session_state:
    st.session_state.reset_email = None
# YENİ: Kodun doğrulanıp doğrulanmadığını tutan durum
if "reset_otp_verified" not in st.session_state:
    st.session_state.reset_otp_verified = False

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        if not st.session_state.forgot_password_mode:
            st.subheader("Üye Girişi")
            login_user = st.text_input("Kullanıcı Adı", key="login_user")
            
            show_pass_login = st.checkbox("Parolayı Göster", key="show_login")
            login_pass = st.text_input(
                "Şifre", 
                type="default" if show_pass_login else "password", 
                key="login_pass"
            )
            
            if st.button("Giriş Yap"):
                user = verify_user(login_user, login_pass)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_info = dict(user)
                    st.success("Giriş başarılı!")
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı!")
            
            st.markdown("---")
            if st.button("🔑 Şifremi Unuttum"):
                st.session_state.forgot_password_mode = True
                st.rerun()
                
        else:
            # --- ŞİFREMİ UNUTTUM AŞAMALARI ---
            st.subheader("Şifre Sıfırlama")
            
            if st.button("⬅️ Geri Dön"):
                # Geri dönüldüğünde tüm sıfırlama aşamalarını temizle
                st.session_state.forgot_password_mode = False
                st.session_state.reset_otp_sent = False
                st.session_state.reset_otp_verified = False
                st.rerun()
            
            # AŞAMA 1 ve 2: Kod gönderimi ve Doğrulama (Henüz doğrulanmadıysa)
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
                        except Exception as e:
                            st.error(f"E-posta gönderilemedi. Hata: {e}")
                    else:
                        st.error("Bu e-posta adresiyle kayıtlı bir hesap bulunamadı!")
                
                # AŞAMA 2: Kod gönderildiyse doğrulama kutusunu göster
                if st.session_state.reset_otp_sent:
                    st.markdown("---")
                    entered_otp = st.text_input("E-postanıza Gelen 6 Haneli Kodu Girin")
                    
                    if st.button("Kodu Doğrula"):
                        if entered_otp == st.session_state.reset_otp:
                            st.session_state.reset_otp_verified = True
                            st.rerun()
                        else:
                            st.error("❌ Hatalı doğrulama kodu girdiniz!")
            
            # AŞAMA 3: Kod DOĞRULANDIYSA sadece şifre yenileme ekranını göster
            else:
                st.success("✅ Kod doğrulandı! Şimdi yeni şifrenizi oluşturabilirsiniz.")
                
                show_pass_reset = st.checkbox("Yeni Şifreyi Göster", key="show_reset")
                new_pass = st.text_input("Yeni Şifre", type="default" if show_pass_reset else "password")
                new_pass_confirm = st.text_input("Yeni Şifre Tekrar", type="default" if show_pass_reset else "password")
                
                if st.button("Şifreyi Güncelle"):
                    if new_pass != new_pass_confirm:
                        st.error("❌ Şifreler birbiriyle eşleşmiyor!")
                    elif len(new_pass) < 8 or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_pass):
                        st.error("🔒 Şifreniz en az 8 karakter olmalı ve en az bir özel karakter içermelidir.")
                    else:
                        update_password(st.session_state.reset_email, new_pass)
                        st.success("🎉 Şifreniz başarıyla güncellendi! 'Geri Dön' butonuna basarak giriş yapabilirsiniz.")
                        # İşlem bitince durumları sıfırla ki tekrar giriş yapılabilsin
                        st.session_state.reset_otp_sent = False
                        st.session_state.reset_otp_verified = False
                        st.session_state.reset_otp = None
                
    with tab2:
        st.subheader("Yeni Hesap Oluştur (7 Gün Ücretsiz)")
        # TÜM KUTUCUKLARA 'KEY' EKLENDİ Kİ VERİLER SİLİNMESİN
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
            if reg_pass != reg_pass_confirm:
                st.error("🔒 Şifreler birbiriyle eşleşmiyor!")
            elif len(reg_pass) < 8 or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", reg_pass):
                st.error("🔒 Şifreniz en az 8 karakter olmalı ve en az bir özel karakter (!, @, #, $, vb.) içermelidir.")
            elif reg_username and reg_name and reg_email and reg_phone and reg_pass:
                if captcha_answer == (st.session_state.captcha_num1 + st.session_state.captcha_num2):
                    st.session_state.generated_otp = str(random.randint(100000, 999999))
                    
                    try:
                        gonderici_mail = st.secrets["email"]["gonderici"]
                        gonderici_sifre = st.secrets["email"]["sifre"]
                        
                        msg = MIMEText(f"Akıllı Bütçe Paneli hesabınızı oluşturmak için doğrulama kodunuz: {st.session_state.generated_otp}")
                        msg['Subject'] = 'Hesap Doğrulama Kodunuz'
                        msg['From'] = gonderici_mail
                        msg['To'] = reg_email

                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        server.login(gonderici_mail, gonderici_sifre)
                        server.send_message(msg)
                        server.quit()
                        
                        st.session_state.otp_sent = True
                        st.success(f"📧 Doğrulama kodu {reg_email} adresine gönderildi!")
                    except Exception as e:
                        st.error(f"E-posta gönderilemedi. Hata detayları: {e}")
                else:
                    st.error("Robot testi başarısız!")
            else:
                st.error("Lütfen tüm alanları doldurun.")
                
        if st.session_state.otp_sent:
            user_otp = st.text_input("Doğrulama Kodunu Girin", key="user_otp")
            if st.button("Kaydı Tamamla"):
                if user_otp == st.session_state.generated_otp:
                    # Session state'teki verileri çekerek kaydetmeyi garantiliyoruz
                    success = register_user(
                        st.session_state.reg_user, 
                        st.session_state.reg_name, 
                        st.session_state.reg_pass, 
                        st.session_state.reg_email, 
                        st.session_state.reg_phone
                    )
                    if success:
                        st.success("Kaydınız başarıyla tamamlandı! 7 günlük ücretsiz denemeniz başladı.")
                        st.session_state.otp_sent = False
                        st.session_state.generated_otp = None
                    else:
                        st.error("❌ Kayıt Başarısız: Bu kullanıcı adı, e-posta adresi veya telefon numarası sistemde zaten kayıtlı!")
                else:
                    st.error("Hatalı doğrulama kodu.")
else:
    user = st.session_state.user_info
    status, message = check_and_update_subscription(user["id"])
    
    st.sidebar.title(f"Hoş Geldiniz, {user['full_name']}")
    if st.sidebar.button("Güvenli Çıkış"):
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.rerun()

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
                    st.error("Lütfen kart bilgilerini eksiksiz ve doğru girin.")

    else:
        if status == "warning":
            st.warning(message)
            if st.sidebar.button("💳 Şimdi Ödeme Yap (20 TL)"):
                process_fake_payment(user["id"])
                st.success("Ödemeniz alındı!")
                st.rerun()
        elif status == "active":
            st.sidebar.info(message)
        
        ana_butce_uygulamasi(user["id"])
