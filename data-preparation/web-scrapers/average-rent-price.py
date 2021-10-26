import csv
import os
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

# 共通
CURRENT_DATETIME_STR: str = datetime.now(timezone(timedelta(hours=+9), "JST")).strftime(
    "%Y%m%d_%H%M%S"
)
OUTPUT_DIR_NAME: str = "output"
CSV_BASE_FILE_NAME: str = "avg_rent_price_for_each_station_{0}.csv"

url = "https://www.homes.co.jp/chintai/tokyo/line/price/"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
}


def main():

    # CSV カラム名
    COLUMN_NAMES = ["公園の名称", "住所"]
    output_rows: list[list] = []
    output_rows.append(COLUMN_NAMES)

    raw_html = requests.get(url, headers=headers)
    raw_html.encoding = raw_html.apparent_encoding
    parsed_html = BeautifulSoup(raw_html.text, "lxml")

    東京23区内の公園リスト = parsed_html.select(
        "#lower-left > article > section > section:nth-child(1) > div > ul > li > ul > li"
    )

    for 公園 in 東京23区内の公園リスト:
        公園の名称 = 公園.select_one("a").contents[0]
        住所 = 公園.select_one("span").text
        output_rows.append([公園の名称, 住所])

    東京23区外の公園リスト = parsed_html.select(
        "#lower-left > article > section > section:nth-child(5) > div > ul > li > ul > li"
    )

    for 公園 in 東京23区外の公園リスト:
        公園の名称 = 公園.select_one("a").contents[0]
        住所 = 公園.select_one("span").text
        output_rows.append([公園の名称, 住所])

    # CSV ファイル出力
    csv_file_name = __write_csv(
        output_rows,
        OUTPUT_DIR_NAME,
        CSV_BASE_FILE_NAME.format(CURRENT_DATETIME_STR),
    )

    print("クローリングが完了しました。")
    print("CSV出力先: " + csv_file_name)


def __write_csv(output_rows: list[list], output_dir_name: str, file_name: str) -> str:
    """CSV 出力関数
    Args:
        output_rows (list[list[str]]): CSV 出力用データ
        output_dir_name (str): CSV 出力先ディレクトリ名
        file_name (str):CSV 用ファイル名(拡張子付き)
    Returns:
        str: 出力したCSVファイルのフルパス
    """

    current_path = os.path.dirname(__file__)
    file_name = os.path.normpath(
        os.path.join(
            current_path,
            output_dir_name,
            file_name,
        )
    )
    if not os.path.exists(os.path.dirname(file_name)):
        os.makedirs(os.path.dirname(file_name))
    with open(file_name, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(output_rows)
    return file_name


if __name__ == "__main__":
    main()
