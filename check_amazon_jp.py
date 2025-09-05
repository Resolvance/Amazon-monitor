import os
import smtplib
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.sync_api import sync_playwright

# Amazon Japan search URL for LG, Samsung, MSI Curved OLED monitors, used items only
SEARCH_URL = (
    "https://www.amazon.co.jp/s?"
    "k=LG+Samsung+MSI+curved+OLED+monitor&i=electronics&rh=p_n_condition-type%3A2224375051"
)

# Maximum price filter (in yen)
MAX_PRICE = 80000

def get_used_monitors():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(SEARCH_URL, timeout=60000)
        page.wait_for_timeout(5000)  # wait for JS content to load

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    for item in soup.select("div.s-main-slot div[data-asin]"):
        title_el = item.select_one("h2 a span")
        link_el = item.select_one("h2 a")

        if not title_el or not link_el:
            continue

        title_text = title_el.get_text(strip=True)

        # Try normal price first
        price_el = item.select_one("span.a-price-whole")

        # Fallback for used items: look for "中古品 ￥xx より"
        if not price_el:
            price_el = item.select_one("span.a-color-secondary")

        if not price_el:
            continue

        # Clean price text
        price_text = price_el.get_text(strip=True).replace("￥", "").replace(",", "").replace("中古品", "").replace("より", "").strip()

        try:
            price_val = int(price_text)
        except ValueError:
            continue

        # Debug logging
        print(f"DEBUG: {title_text} | raw price: {price_el.get_text(strip=True)} | parsed price: {price_val}")

        # Filter for brand, curved, OLED, and price
        if (
            any(brand in title_text for brand in ["LG", "Samsung", "MSI"])
            and ("曲面" in title_text or "Curved" in title_text)
            and "OLED" in title_text
            and price_val <= MAX_PRICE
        ):
            results.append({
                "title": title_text,
                "price": price_val,
                "url": "https://www.amazon.co.jp" + link_el["href"]
            })

    return results

def send_email(monitors):
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    recipient = os.getenv("EMAIL_TO")

    if not user or not password or not recipient:
        print("❌ Missing email credentials. Check GitHub Secrets.")
        return

    subject = f"[Amazon JP Alert] {len(monitors)} Curved OLED Monitors Found!"
    body = "\n\n".join([f"{m['title']} - ¥{m['price']}\n{m['url']}" for m in monitors])

    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(user, password)
            server.send_message(msg)
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def main():
    monitors = get_used_monitors()
    if monitors:
        print(f"Found {len(monitors)} monitor(s) under {MAX_PRICE} yen")
        for m in monitors:
            print(f"- {m['title']} ¥{m['price']} {m['url']}")
        send_email(monitors)
    else:
        print("No monitors found under threshold.")

if __name__ == "__main__":
    main()
