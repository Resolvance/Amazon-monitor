import os
import smtplib
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.sync_api import sync_playwright

# Amazon Japan search URL for LG, Samsung, MSI Curved OLED monitors
SEARCH_URL = (
    "https://www.amazon.co.jp/s?"
    "k=LG+Samsung+MSI+curved+OLED+monitor&i=electronics&rh=p_n_condition-type%3A2224375051"
)

# Maximum price filter (in yen)
MAX_PRICE = 80000

def get_product_used_price(page, url):
    """Given a product page URL, return the used price if available, else None."""
    try:
        page.goto(url, timeout=60000)
        page.wait_for_timeout(3000)
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        # Try to find "Used from" price
        used_price_el = soup.select_one(
            "#usedBuySection .a-color-price, #olpOfferListColumn .a-color-price"
        )
        if used_price_el:
            price_text = used_price_el.get_text(strip=True).replace("￥", "").replace(",", "").strip()
            return int(price_text)
    except Exception as e:
        print(f"Error fetching product page {url}: {e}")
    return None

def get_used_monitors():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(SEARCH_URL, timeout=60000)
        page.wait_for_timeout(5000)  # wait for JS content

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        for item in soup.select("div.s-main-slot div[data-asin]"):
            title_el = item.select_one("h2 a span")
            link_el = item.select_one("h2 a")

            if not title_el or not link_el:
                continue

            title_text = title_el.get_text(strip=True)
            product_url = "https://www.amazon.co.jp" + link_el["href"]

            # Check brand / curved / OLED before loading page to save time
            if not any(brand in title_text for brand in ["LG", "Samsung", "MSI"]):
                continue
            if "OLED" not in title_text or ("曲面" not in title_text and "Curved" not in title_text):
                continue

            # Get used price from product page
            price_val = get_product_used_price(page, product_url)
            if price_val is None:
                continue

            print(f"DEBUG: {title_text} | used price: ¥{price_val} | {product_url}")

            if price_val <= MAX_PRICE:
                results.append({
                    "title": title_text,
                    "price": price_val,
                    "url": product_url
                })

        browser.close()
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
        print("poopy")

if __name__ == "__main__":
    main()
