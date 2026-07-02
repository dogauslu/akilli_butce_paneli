#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  2 11:31:11 2026

@author: mac
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json

# --- AYARLAR ---
st.set_page_config(page_title="Akıllı Bütçe Paneli (V2)", page_icon="🧠", layout="wide")
VERI_DOSYASI = "akilli_butce_verileri.csv" # Eski veriyle karışmasın diye yeni isim verdik

# --- VERİ YÜKLEME FONKSİYONU ---
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

# --- YAN MENÜ (ROUTING) ---
st.sidebar.title("Akıllı Menü V2")
sayfa = st.sidebar.selectbox("Sayfa Seçin", ["Genel Bakış", "İşlem Ekle", "Raporlar", "Banka Entegrasyonu"])

# --- 1. GENEL BAKIŞ SAYFASI ---
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

# --- 2. İŞLEM EKLE SAYFASI ---
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

# --- 3. RAPORLAR SAYFASI ---
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
            if not sadece_giderler.empty:
                gunluk_toplam = sadece_giderler.groupby("Tarih")["Tutar"].sum().reset_index()
                fig_bar = px.bar(gunluk_toplam, x='Tarih', y='Tutar', 
                                 color='Tutar', color_continuous_scale='Reds',
                                 text_auto='.0f')
                
                fig_bar.update_layout(xaxis_tickangle=-45, margin=dict(b=80), xaxis_title="", yaxis_title="")
                fig_bar.update_xaxes(type='category')
                fig_bar.update_traces(textposition='outside') 
                st.plotly_chart(fig_bar, use_container_width=True)

# --- 4. BANKA ENTEGRASYONU SAYFASI ---
elif sayfa == "Banka Entegrasyonu":
    st.header("🏦 Banka Ekstresi ile Otomatik Yükleme")
    st.write("Bankanızdan indirdiğiniz CSV veya Excel formatındaki ekstre dosyasını yükleyin.")

    yuklenen_dosya = st.file_uploader("Ekstre Dosyasını Seçin", type=["csv", "xlsx"])

    if yuklenen_dosya is not None:
        try:
            if yuklenen_dosya.name.endswith('.csv'):
                ekstre = pd.read_csv(yuklenen_dosya)
            else:
                ekstre = pd.read_excel(yuklenen_dosya)
            
            st.subheader("Yüklenen Dosya Önizlemesi")
            st.dataframe(ekstre.head(3))

            st.subheader("⚙️ Kolon Eşleştirme Ayarları")
            col1, col2, col3 = st.columns(3)
            with col1:
                tarih_kolonu = st.selectbox("Tarih Sütunu", ekstre.columns)
            with col2:
                aciklama_kolonu = st.selectbox("Açıklama Sütunu", ekstre.columns)
            with col3:
                tutar_kolonu = st.selectbox("Tutar Sütunu", ekstre.columns)

            if st.button("Ekstreyi İşle ve Bütçeye Ekle"):
                yeni_veriler = pd.DataFrame()
                yeni_veriler["Tarih"] = pd.to_datetime(ekstre[tarih_kolonu]).dt.date
                yeni_veriler["Açıklama"] = ekstre[aciklama_kolonu].astype(str)
                yeni_veriler["Tutar"] = ekstre[tutar_kolonu].astype(float).abs()
                yeni_veriler["Tür"] = "Gider"

                # Harici JSON dosyasından dinamik olarak kategorileri okuyoruz
                try:
                    with open("kategoriler.json", "r", encoding="utf-8") as f:
                        kategori_haritasi = json.load(f)
                except Exception:
                    kategori_haritasi = {}

                kategoriler = []
                for aciklama in yeni_veriler["Açıklama"]:
                    metin = str(aciklama).upper()
                    bulundu = False
                    
                    for kategori, markalar in kategori_haritasi.items():
                        if any(marka in metin for marka in markalar):
                            kategoriler.append(kategori)
                            bulundu = True
                            break
                    
                    if not bulundu:
                        kategoriler.append("Diğer")
                
                yeni_veriler["Kategori"] = kategoriler

                mevcut_df = verileri_yukle()
                guncel_df = pd.concat([mevcut_df, yeni_veriler], ignore_index=True)
                guncel_df.to_csv(VERI_DOSYASI, index=False)
                
                st.success(f"🎉 {len(yeni_veriler)} adet işlem başarıyla eklendi!")
                st.balloons()
                
        except Exception as e:
            st.error(f"Dosya işlenirken hata oluştu: {e}")