import csv
import enum
import os
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import chromedriver_binary  # Adds chromedriver binary to path # noqa
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.select import Select

OUTPUT_DIR_NAME = "output"
CSV_BASE_FILE_NAME = "標識設置データ（建設工事情報）"

# 標識設置データ（建設工事情報）物件検索ページの URL
url: str = "https://www.kensetsu-databank.co.jp/kensaku/"


class CssSelector(enum.Enum):
    届出日_から_年 = "#container01 > form > table > tbody > tr:nth-child(2) > td > select:nth-child(2)"
    届出日_から_月 = "#container01 > form > table > tbody > tr:nth-child(2) > td > select:nth-child(3)"
    届出日_から_日 = "#container01 > form > table > tbody > tr:nth-child(2) > td > select:nth-child(4)"
    届出日_まで_年 = "#container01 > form > table > tbody > tr:nth-child(2) > td > select:nth-child(6)"
    届出日_まで_月 = "#container01 > form > table > tbody > tr:nth-child(2) > td > select:nth-child(7)"
    届出日_まで_日 = "#container01 > form > table > tbody > tr:nth-child(2) > td > select:nth-child(8)"
    建設地_東京２３区すべてを選択 = "#s-tokyo23"
    検索開始ボタン = "#container01 > form > p:nth-child(4) > input[type=submit]"
    次の〇〇件を表示ボタン = "input[name='goNext']"
    検索結果テーブルの件名列 = "#container01 > form > table > tbody > tr > td:nth-child(2) > a"
    詳細ページのテーブル = "#container01 > table:nth-child(6) > tr"


# 標識設置データ（建設工事情報）物件検索ページで検索する
# NOTE: Headless Chrome を使用するとなぜか実行速度が遅くなるので、今回は使用しない
# options = webdriver.ChromeOptions()
# options.add_argument("--headless")
# driver: webdriver.Chrome = webdriver.Chrome(options=options)

driver: webdriver.Chrome = webdriver.Chrome()
driver.get(url)
time.sleep(1)
Select(driver.find_element_by_css_selector(CssSelector.届出日_から_年.value)).select_by_value(
    "2017"
)
Select(driver.find_element_by_css_selector(CssSelector.届出日_から_月.value)).select_by_value(
    "01"
)
Select(driver.find_element_by_css_selector(CssSelector.届出日_から_日.value)).select_by_value(
    "01"
)
Select(driver.find_element_by_css_selector(CssSelector.届出日_まで_年.value)).select_by_value(
    "2020"
)
Select(driver.find_element_by_css_selector(CssSelector.届出日_まで_月.value)).select_by_value(
    "12"
)
Select(driver.find_element_by_css_selector(CssSelector.届出日_まで_日.value)).select_by_value(
    "31"
)

checkbox_建設地_東京２３区すべてを選択 = driver.find_element_by_css_selector(
    CssSelector.建設地_東京２３区すべてを選択.value
)
if checkbox_建設地_東京２３区すべてを選択.is_selected():
    pass
else:
    checkbox_建設地_東京２３区すべてを選択.click()
driver.find_element_by_css_selector(CssSelector.検索開始ボタン.value).click()

# 検索結果ページで詳細ページのURLを取得する
url_list: list = []
while True:
    raw_html_result_list_page = driver.page_source.encode("utf-8")
    parsed_html_result_list_page: BeautifulSoup = BeautifulSoup(
        raw_html_result_list_page, "lxml"
    )
    a_list: list = parsed_html_result_list_page.select(CssSelector.検索結果テーブルの件名列.value)
    current_page_url: str = driver.current_url
    for a in a_list:
        url_list.append(urljoin(current_page_url, a.get("href")))
    # リクエスト間隔調整
    time.sleep(1)
    try:
        driver.find_element_by_css_selector(CssSelector.次の〇〇件を表示ボタン.value).click()
    except NoSuchElementException:
        # 検索結果の最終ページに達したのでURL取得処理を終了する
        break
driver.quit()

# 検索結果ページで取得した詳細ページのURLに1ページずつアクセスし、詳細情報を取得する
output_rows = []
total = len(url_list)
for i, url in enumerate(url_list):
    # 処理時間が長くなるので、プログレスを表示する
    print(("[ {0} / {1} ] {2}".format(i + 1, total, url)))
    # リクエスト間隔調整
    time.sleep(0.8)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
    }
    raw_html_detail_page = requests.get(url, headers=headers)
    parsed_html_detail_page = BeautifulSoup(raw_html_detail_page.text, "lxml")
    detail_table_tr_list = parsed_html_detail_page.select(CssSelector.詳細ページのテーブル.value)

    # 詳細データのヘッダ情報をセット
    column_names = []
    if i == 0:
        for table_tr in detail_table_tr_list:
            column_name = table_tr.select_one("td:nth-child(1)")
            # <tr>タグ内に<td>タグが2つない行は空行なのでスキップ
            if not table_tr.select_one("td:nth-child(2)"):
                continue
            column_names.append(column_name.text)
        output_rows.append(column_names)

    # 詳細データを取得する
    output_row = []
    for table_tr in detail_table_tr_list:
        cell = table_tr.select_one("td:nth-child(2)")
        # <tr>タグ内に<td>タグが2つない行は空行なのでスキップ
        if not table_tr.select_one("td:nth-child(2)"):
            continue
        output_row.append(cell.text)
    output_rows.append(output_row)

# ===================================================================================================
#  CSV 出力
# ===================================================================================================

JST = timezone(timedelta(hours=+9), "JST")
now = datetime.now(JST)
current_path = os.path.dirname(__file__)
file_name = os.path.normpath(
    os.path.join(
        current_path,
        OUTPUT_DIR_NAME,
        CSV_BASE_FILE_NAME + "_" + now.strftime("%Y%m%d_%H%M%S") + ".csv",
    )
)
if not os.path.exists(os.path.dirname(file_name)):
    os.makedirs(os.path.dirname(file_name))
with open(file_name, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(output_rows)
print("クローリングが完了しました。 CSV出力先: " + file_name)
