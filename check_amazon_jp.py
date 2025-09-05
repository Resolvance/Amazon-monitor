import os
import smtplib
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.sync_api import sync_playwright

SEARCH_URL = (
    "https://www.amazon.co.jp/s?"
    "k=LG+Samsung+MSI+curved+OLED+monitor&i=electronics&rh=p_n_condition-type%3A2224375051"
)

MAX_PRICE = 800000

def get_used_monitors():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(SEARCH_URL, timeout=60000)
        page.wait_for_timeout(5000)  # wait for dynamic content

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    for item in soup.select("div.s-main-slot div[data-asin]"):
        title = item.select_one("h2 a span")
        price = item.select_one("span.a-price-whole")
        link = item.select_one("h2 a")

        if not title or not price or not link:
            continue

        title_text = title.get_text(strip=True)
        price_text = price.get_text(strip=True).replace(",", "")

        try:
            price_val = int(price_text)
        except ValueError:
            continue

        if (
            any(brand in title_text for brand in ["LG", "Samsung", "MSI"])
            and ("曲面" in title_text or "Curved" in title_text)
            and "OLED" in title_text
            and price_val <= MAX_PRICE
        ):
            results.append(
                {
                    "title": title_text,
                    "price": price_val,
                    "url": "https://www.amazon.co.jp" + link["href"],
                }
            )

    return results

def send_email(monitors):
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    recipient = os.getenv("EMAIL_TO")

    subject = f"[Amazon JP Alert] {len(monitors)} Curved OLED Monitors Found!"
    body = "\n\n".join(
        [f"{m['title']} - ¥{m['price']}\n{m['url']}" for m in monitors]
    )

    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, password)
        server.send_message(msg)

def main():
    monitors = get_used_monitors()
    if monitors:
        print(f"Found {len(monitors)} monitor(s) under {MAX_PRICE} yen")
        for m in monitors:
            print(f"- {m['title']} ¥{m['price']} {m['url']}")
        send_email(monitors)
        print("✅ Email sent!")
    else:
        print("No monitors found under threshold.")

if __name__ == "__main__":
    main()
