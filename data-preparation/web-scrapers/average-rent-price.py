import csv
import os
import time
from datetime import datetime, timedelta, timezone
from typing import List

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

    # 間取り名
    MADORI_NAMES = [
        "1R",
        "1K",
        "1DK",
        "1LDK",
        "2K",
        "2DK",
        "2LDK",
        "3K",
        "3DK",
        "3LDK",
        "4K",
        "4DK",
    ]
    # CSV カラム名
    COLUMN_NAMES = ["station"] + MADORI_NAMES
    output_rows: list[list] = []
    output_rows.append(COLUMN_NAMES)

    line_list_raw_html = requests.get(url, headers=headers)
    line_list_raw_html.encoding = line_list_raw_html.apparent_encoding
    line_list_parsed_html = BeautifulSoup(line_list_raw_html.text, "lxml")
    # print(line_parsed_html)
    line_list = line_list_parsed_html.select(
        ".rosenType > ul > li > a"
        # "#lower-left > article > section > section:nth-child(1) > div > ul > li > ul > li"
    )
    line_link_dict = {}
    station_link_dict = {}
    market_price_dict = {}
    for line in line_list:
        line_link_dict[line.text] = line.get("href")

    # print(line_link_dict)
    i = 0
    print("Getting station list from lines...")
    for line_name, line_url in line_link_dict.items():
        i += 1
        print("[" + str(i) + "/" + str(len(line_link_dict)) + "]")
        station_list_raw_html = requests.get(line_url, headers=headers)
        station_list_raw_html.encoding = station_list_raw_html.apparent_encoding
        station_list_parsed_html = BeautifulSoup(station_list_raw_html.text, "lxml")
        station_list = station_list_parsed_html.select(
            "#prg-aggregate-graph > tr > td.station > a"
            # "#lower-left > article > section > section:nth-child(1) > div > ul > li > ul > li"
        )
        for station in station_list:
            station_link_dict[station.text] = station.get("href")
        # リクエスト間隔調整
        time.sleep(0.7)

    i = 0
    print("Getting market price for each station...")
    for station_name, station_url in station_link_dict.items():
        i += 1
        print("[" + str(i) + "/" + str(len(station_link_dict)) + "]")
        market_price_dict[station_name] = {}

        market_price_raw_html = requests.get(station_url, headers=headers)
        market_price_raw_html.encoding = market_price_raw_html.apparent_encoding
        market_price_parsed_html = BeautifulSoup(market_price_raw_html.text, "lxml")
        market_price_list = market_price_parsed_html.select(
            "#prg-aggregate-graph > tr > td"
            # "#lower-left > article > section > section:nth-child(1) > div > ul > li > ul > li"
        )
        madori = ""
        for market_price in market_price_list:
            html_class = market_price.get("class")[0]
            if html_class == "madori":
                raw_madori = market_price.text
                if raw_madori == "ワンルーム":
                    madori = "1R"
                else:
                    madori = raw_madori
                if madori not in MADORI_NAMES:
                    print("WARNING: " + madori + " is not in MADORI_LIST!")
            elif html_class == "price":
                price_span = market_price.select_one("td > div.money > span")
                if price_span:
                    market_price_dict[station_name][madori] = price_span.text

        # リクエスト間隔調整
        time.sleep(0.7)

    # create output rows
    for station_name, market_price in market_price_dict.items():
        output_row = [station_name]
        for madori in MADORI_NAMES:
            price = market_price.get(madori, "")
            output_row.append(price)
        output_rows.append(output_row)

    # for 公園 in 東京23区内の公園リスト:
    #     公園の名称 = 公園.select_one("a").contents[0]
    #     住所 = 公園.select_one("span").text
    #     output_rows.append([公園の名称, 住所])

    # 東京23区外の公園リスト = line_parsed_html.select(
    #     "#lower-left > article > section > section:nth-child(5) > div > ul > li > ul > li"
    # )

    # for 公園 in 東京23区外の公園リスト:
    #     公園の名称 = 公園.select_one("a").contents[0]
    #     住所 = 公園.select_one("span").text
    #     output_rows.append([公園の名称, 住所])

    # CSV ファイル出力
    csv_file_name = __write_csv(
        output_rows,
        OUTPUT_DIR_NAME,
        CSV_BASE_FILE_NAME.format(CURRENT_DATETIME_STR),
    )

    print("クローリングが完了しました。")
    print("CSV出力先: " + csv_file_name)


def __write_csv(output_rows: List[List], output_dir_name: str, file_name: str) -> str:
    """CSV 出力関数
    Args:
        output_rows (List[List[str]]): CSV 出力用データ
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
