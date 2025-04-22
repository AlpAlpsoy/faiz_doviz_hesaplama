import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import datetime as dt

st.set_page_config(page_title="Faiz ve Döviz Simülasyonu", layout="centered")

# TCMB'den XML verisini getiren fonksiyonlar
def create_tcmb_url(date):
    return f"https://www.tcmb.gov.tr/kurlar/{date.strftime('%Y%m')}/{date.strftime('%d%m%Y')}.xml"

def get_valid_tcmb_rates(date):
    max_attempts = 10
    attempts = 0
    while attempts < max_attempts:
        try:
            url = create_tcmb_url(date)
            response = requests.get(url)
            if response.status_code == 200:
                response.encoding = 'utf-8'
                tree = ET.fromstring(response.text)
                usd = tree.find(".//Currency[@Kod='USD']/BanknoteSelling").text
                eur = tree.find(".//Currency[@Kod='EUR']/BanknoteSelling").text
                return float(usd.replace(",", ".")), float(eur.replace(",", ".")), date
        except:
            pass
        date -= timedelta(days=1)
        attempts += 1
    return None, None, None

def get_exchange_rates_from_tcmb():
    url = "http://www.tcmb.gov.tr/kurlar/today.xml"
    response = requests.get(url)
    response.encoding = 'utf-8'
    tree = ET.fromstring(response.text)
    usd = tree.find(".//Currency[@Kod='USD']/BanknoteSelling").text
    eur = tree.find(".//Currency[@Kod='EUR']/BanknoteSelling").text
    return float(usd.replace(",", ".")), float(eur.replace(",", "."))

# Faiz hesaplama fonksiyonları
def bilesik_faiz_simulasyonu(anapara, gunluk_faiz_orani, gun_sayisi):
    bakiye = anapara
    for _ in range(gun_sayisi):
        bakiye += bakiye * gunluk_faiz_orani
    toplam_faiz = bakiye - anapara
    return bakiye, toplam_faiz

def basit_faiz_simulasyonu(anapara, faiz_orani, gun_sayisi):
    faiz_orani = faiz_orani / 100
    toplam_faiz = anapara * faiz_orani * (gun_sayisi / 365)
    toplam_bakiye = anapara + toplam_faiz
    return toplam_bakiye, toplam_faiz

# Uygulama arayüzü

today = dt.date.today()
yesterday = today - dt.timedelta(days=1)
max_past_date = today - dt.timedelta(days=10*365)

st.title("Faiz ve Döviz Getiri Karşılaştırma Aracı")

with st.form("faiz_formu"):
    anapara = st.number_input("Başlangıç anapara (TL)", min_value=0.0, value=0.0)
    faiz_turu = st.selectbox("Faiz türü", options=["Basit", "Bileşik"])
    faiz_orani = st.number_input("Faiz oranı", help="Basit faiz hesabı için yıllık faiz oranı, Bileşik faiz hesabı için günlük faiz oranı girin.", value=0.0)
    stopaj_orani = st.number_input("Stopaj oranı (%)", value=0.0)
    baslangic = st.date_input("Başlangıç tarihi", value= yesterday, min_value= max_past_date, max_value= yesterday)
    bitis = st.date_input("Bitiş tarihi", value= today, min_value= max_past_date, max_value= today)
    submit = st.form_submit_button("Hesapla")

if submit:
    gun_sayisi = (bitis - baslangic).days
    if gun_sayisi <= 0:
        st.warning("Bitiş tarihi, başlangıç tarihinden sonra olmalı.")
        st.stop()

    if faiz_turu == "Bileşik":
        toplam_bakiye, toplam_faiz = bilesik_faiz_simulasyonu(anapara, faiz_orani / 100, gun_sayisi)
    else:
        toplam_bakiye, toplam_faiz = basit_faiz_simulasyonu(anapara, faiz_orani, gun_sayisi)

    stopaj_tutari = toplam_faiz * (stopaj_orani / 100)
    net_kazanc = toplam_faiz - stopaj_tutari
    net_toplam_bakiye = anapara + net_kazanc

    usd_kuru, eur_kuru = get_exchange_rates_from_tcmb()
    net_bakiye_usd = net_toplam_bakiye / usd_kuru
    net_bakiye_eur = net_toplam_bakiye / eur_kuru

    usd_baslangic, eur_baslangic, baslangic_kur_tarihi = get_valid_tcmb_rates(baslangic)
    usd_bitis, eur_bitis, bitis_kur_tarihi = get_valid_tcmb_rates(bitis)

    tl_dolar_bitis = (anapara / usd_baslangic) * usd_bitis
    tl_euro_bitis = (anapara / eur_baslangic) * eur_bitis

    maksimum_getiri = max(net_toplam_bakiye, tl_dolar_bitis, tl_euro_bitis)
    en_yuksek_getiri = (
        "FAİZ 💰" if maksimum_getiri == net_toplam_bakiye else
        "DOLAR 💵" if maksimum_getiri == tl_dolar_bitis else
        "EURO 💶"
    )

    # st.subheader("📊 Sonuçlar")
    # st.markdown(f"**Tarih Aralığı:** {baslangic} - {bitis} ({gun_sayisi} gün)")
    # st.markdown(f"**Toplam net faiz kazancı:** {net_kazanc:.2f} TL")
    # st.markdown(f"**Stopaj sonrası bakiye:** {net_toplam_bakiye:.2f} TL")
    # st.markdown(f"**Net bakiye USD karşılığı:** {net_bakiye_usd:.2f} USD")
    # st.markdown(f"**Net bakiye EUR karşılığı:** {net_bakiye_eur:.2f} EUR")
    # st.markdown(f"**Dolarla işlem sonucu:** {tl_dolar_bitis:.2f} TL")
    # st.markdown(f"**Euroyla işlem sonucu:** {tl_euro_bitis:.2f} TL")

    # METRİK GÖRÜNÜMÜ – Faiz Getirisi Özeti
    st.subheader("💰 Faiz Getirisi Özeti")
    col1, col2, col3 = st.columns(3)
    col1.metric("Brüt Faiz", f"{toplam_faiz:,.2f} TL")
    col2.metric("Stopaj Kesintisi", f"{stopaj_tutari:,.2f} TL")
    col3.metric("Net Kazanç", f"{net_kazanc:,.2f} TL")
    
    col4, col5 = st.columns(2)
    col4.metric("Toplam Net Bakiye (TL)", f"{net_toplam_bakiye:,.2f} TL")
    col5.metric("Vade Süresi", f"{gun_sayisi} gün")
    
    st.markdown("---")
    
    # DÖVİZ KARŞILIĞI
    st.markdown("📌 TCMB Güncel Döviz Kurları:")
    col8, col9 = st.columns(2)
    col8.metric("Güncel USD/TL", f"{usd_bitis:.2f} TL")
    col9.metric("Güncel EUR/TL", f"{eur_bitis:.2f} TL")
    st.subheader("💱 Net Bakiye Döviz Karşılıkları")
    col6, col7 = st.columns(2)
    col6.metric("USD Karşılığı", f"{net_bakiye_usd:,.2f} USD")
    col7.metric("EUR Karşılığı", f"{net_bakiye_eur:,.2f} EUR")
    
    st.markdown("---")
    
    # DÖVİZ ALINSAYDI SENARYOSU
    st.subheader("📉 Döviz Alınsaydı Ne Olurdu?")
    st.write(f"**USD:** {baslangic_kur_tarihi.strftime('%Y-%m-%d')} → {usd_baslangic:.2f} TL  |  "
             f"{bitis_kur_tarihi.strftime('%Y-%m-%d')} → {usd_bitis:.2f} TL")
    st.write(f"➡️ TL karşılığı: **{tl_dolar_bitis:,.2f} TL**")
    
    st.write(f"**EUR:** {baslangic_kur_tarihi.strftime('%Y-%m-%d')} → {eur_baslangic:.2f} TL  |  "
             f"{bitis_kur_tarihi.strftime('%Y-%m-%d')} → {eur_bitis:.2f} TL")
    st.write(f"➡️ TL karşılığı: **{tl_euro_bitis:,.2f} TL**")

    st.success(f"{gun_sayisi} gün sonunda net kazancınız {net_kazanc:,.2f} TL, toplam net bakiyeniz {net_toplam_bakiye:,.2f} TL oldu.")
    st.info(f"🏆 En yüksek getiriyi **{en_yuksek_getiri}** kazandırdı.")

    # Grafik çizimi
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = ['Faiz', 'USD', 'EUR']
    values = [net_toplam_bakiye, tl_dolar_bitis, tl_euro_bitis]
    colors = ['gold', 'green', 'blue']

    bars = ax.bar(labels, values, color=colors)
    ax.set_title("Faiz ve Döviz Getiri Karşılaştırması")
    ax.set_ylabel("Anapara (TL)")
    ax.set_xlabel(f"Tarih Aralığı: {baslangic} - {bitis}")

    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height + 0.5, f'{height:.2f} TL',
                ha='center', va='bottom', fontsize=10)

    # Zoom ayarı (dinamik boşluk bırak)
    min_deger = min(values)
    max_deger = max(values)
    fark = max_deger - min_deger
    ax.set_ylim(min_deger - fark * 0.2, max_deger + fark * 0.2)  # %20 zoom yapacak.
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    st.pyplot(fig)
