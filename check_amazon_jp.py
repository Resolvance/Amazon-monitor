import os
import smtplib
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SEARCH_URL = "https://www.amazon.co.jp/s?k=LG+Samsung+MSI+curved+OLED+monitor&i=electronics&rh=p_n_condition-type%3A2224375051"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7"
}

MAX_PRICE = 80000

def get_used_monitors():
    r = requests.get(SEARCH_URL, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")
    results = []

    for item in soup.select("div.s-main-slot div[data-asin]"):
        title = item.select_one("h2 a span")
        price = item.select_one("span.a-price-whole")
        link = item.select_one("h2 a")

        if not title or not price or not link:
            continue

        title_text = title.get_text(strip=True)
        price_text = price.get_text(strip=True).
