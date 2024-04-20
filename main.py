import csv
import datetime
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException


# LINE Notify用のアクセストークン
LINE_TOKEN = "YOUR_ACCESS_TOKEN"


def send_line_notify(message):
    """LINEに通知を送る関数"""
    headers = {"Authorization": f"Bearer {LINE_TOKEN}"}
    data = {"message": message}
    response = requests.post(
        "https://notify-api.line.me/api/notify", headers=headers, data=data
    )
    if response.status_code != 200:
        raise RuntimeError("LINE通知に失敗しました。")


def get_product_details(driver, url):
    """指定されたURLの商品ページから現在の価格とタイトルを取得する関数"""
    try:
        driver.get(url)
        price_element = driver.find_element("css selector", "span.a-price-whole")
        title_element = driver.find_element("css selector", "#productTitle")
        price = int(re.sub(r"\D", "", price_element.text))
        title = title_element.text.strip()
        return price, title
    except NoSuchElementException:
        raise RuntimeError(f"価格またはタイトルの取得に失敗しました。URL: {url}")


def update_csv(file, rows):
    """CSVファイルを更新"""
    file.seek(0)
    file.truncate()
    writer = csv.DictWriter(
        file, fieldnames=["url", "last_checked_price", "last_checked_time"]
    )
    writer.writeheader()
    writer.writerows(rows)


def check_price_change(file_path):
    """CSVファイルを読み込み、価格変更をチェックし、LINE通知を送る"""
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    try:
        with open(file_path, mode="r+", newline="") as file:
            reader = csv.DictReader(file)
            updated_rows = []

            for row in reader:
                current_price, title = get_product_details(driver, row["url"])
                last_price = row["last_checked_price"]

                if last_price == "" or int(last_price) != current_price:
                    row["last_checked_price"] = current_price
                    row["last_checked_time"] = datetime.datetime.now().isoformat()

                    if last_price == "":
                        message = (
                            f"新しい商品が追加されました: 「{title}」の初期価格は {current_price} 円です。\n"
                            f"詳細はこちら: {row['url']}"
                        )
                    else:
                        price_diff = current_price - int(last_price)
                        change_type = "値上がり" if price_diff > 0 else "値下がり"
                        message = (
                            f"価格更新通知: 「{title}」の新価格は {current_price} 円です。\n"
                            f"{abs(price_diff)} 円の {change_type}です。\n"
                            f"詳細はこちら: {row['url']}"
                        )

                    send_line_notify(message)

                updated_rows.append(row)

            # CSVファイルを更新
            update_csv(file, updated_rows)

    finally:
        driver.quit()


if __name__ == "__main__":
    check_price_change("prices.csv")
