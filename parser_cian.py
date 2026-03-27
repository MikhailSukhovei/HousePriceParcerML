import os
import time
import random
from urllib.parse import urlparse, parse_qs
import pandas as pd
import numpy as np
from tqdm import tqdm
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


init_url = 'https://kemerovo.cian.ru/'
urls_file_name = 'cian_urls.csv'


def get_max_page(driver):
    pagination = driver.find_elements(By.CSS_SELECTOR, '[data-name="PaginationItem"]')
    nums = [int(p.text) for p in pagination if p.text.isdigit()]
    return max(nums) if nums else 1


def get_urls():
    base_url = 'https://kemerovo.cian.ru'
    url = 'https://kemerovo.cian.ru/cat.php?deal_type=sale&engine_version=2&offer_type=flat&region=4580'

    driver = uc.Chrome(headless=False, use_subprocess=False, version_main=145)
    wait = WebDriverWait(driver, 20)

    name_list = []
    url_list = []
    try:
        driver.get(url)
        time.sleep(3)

        seen_urls = set()

        while True:
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[data-mark="OfferTitle"]')))

            offers = driver.find_elements(By.CSS_SELECTOR, '[data-mark="OfferTitle"]')
            for item in offers:
                try:
                    parent = item.find_element(By.XPATH, './ancestor::a[1]')
                    offer_url = parent.get_attribute('href')
                    offer_name = item.text.strip()

                    if offer_url and offer_url not in seen_urls:
                        seen_urls.add(offer_url)
                        name_list.append(offer_name)
                        url_list.append(offer_url)
                except Exception:
                    pass

            # Ищем именно ссылку "Дальше"
            next_links = driver.find_elements(
                By.XPATH,
                '//a[.//span[normalize-space()="Дальше"]]'
            )

            if not next_links:
                print('Кнопка "Дальше" не найдена. Похоже, последняя страница.')
                break

            href = next_links[0].get_attribute("href")

            if not href or not isinstance(href, str):
                print(f'Некорректный href у кнопки "Дальше": {href}')
                break

            print('Переход на:', href)
            driver.get(href)
            time.sleep(2)

        pd.DataFrame({'name': name_list, 'url': url_list}).to_csv(urls_file_name, index=False, encoding='utf-8-sig')

    finally:
        pd.DataFrame({'name': name_list, 'url': url_list}).to_csv(urls_file_name, index=False, encoding='utf-8-sig')
        driver.quit()


def build_price_url(base_search_url: str, price_from: int, price_to: int | None = None) -> str:
    parts = [base_search_url]

    if 'minprice=' not in base_search_url:
        parts.append(f'minprice={price_from}')

    if price_to is not None and 'maxprice=' not in base_search_url:
        parts.append(f'maxprice={price_to}')

    return '&'.join(parts)


def collect_urls_from_current_range(driver, wait, seen_urls: set[str]):
    name_list = []
    url_list = []

    while True:
        wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[data-mark="OfferTitle"]'))
        )

        offers = driver.find_elements(By.CSS_SELECTOR, '[data-mark="OfferTitle"]')

        if not offers:
            break

        for item in offers:
            try:
                parent = item.find_element(By.XPATH, './ancestor::a[1]')
                offer_url = parent.get_attribute('href')
                offer_name = item.text.strip()

                if offer_url and offer_url not in seen_urls:
                    seen_urls.add(offer_url)
                    name_list.append(offer_name)
                    url_list.append(offer_url)
            except Exception:
                pass

        next_links = driver.find_elements(
            By.XPATH,
            '//a[.//span[normalize-space()="Дальше"]]'
        )

        if not next_links:
            break

        href = next_links[0].get_attribute("href")
        if not href or not isinstance(href, str):
            break

        print('Переход на следующую страницу:', href)
        driver.get(href)
        time.sleep(2)

    return name_list, url_list


def get_urls_by_price_step():
    base_search_url = (
        #'https://kemerovo.cian.ru/cat.php?deal_type=sale&engine_version=2&offer_type=flat&region=4580'
        'https://tomsk.cian.ru/kupit-kvartiru-vtorichka/'
    )

    step = 50_000
    start_price = 0
    max_price = 15_000_000

    # Сколько пустых диапазонов подряд считаем признаком конца рынка
    max_empty_ranges_in_row = 3
    empty_ranges_in_row = 0

    driver = uc.Chrome(headless=False, use_subprocess=False, version_main=145)
    wait = WebDriverWait(driver, 20)

    all_names = []
    all_urls = []
    seen_urls = set()

    try:
        while start_price < max_price:
            end_price = start_price + step
            range_url = build_price_url(base_search_url, start_price, end_price)

            print(f'\nДиапазон: {start_price:,} .. {end_price:,}'.replace(',', ' '))
            print('URL:', range_url)

            driver.get(range_url)
            time.sleep(3)

            # Проверяем, есть ли объявления вообще
            offers = driver.find_elements(By.CSS_SELECTOR, '[data-mark="OfferTitle"]')
            if not offers:
                print('В диапазоне объявлений нет.')
                empty_ranges_in_row += 1
                start_price += step
                continue

            empty_ranges_in_row = 0

            names, urls = collect_urls_from_current_range(driver, wait, seen_urls)

            print(f'Собрано новых объявлений в диапазоне: {len(urls)}')

            all_names.extend(names)
            all_urls.extend(urls)

            pd.DataFrame({'name': all_names, 'url': all_urls}).to_csv(
                urls_file_name, index=False, encoding='utf-8-sig'
            )

            start_price += step

    finally:
        pd.DataFrame({'name': all_names, 'url': all_urls}).to_csv(
            urls_file_name, index=False, encoding='utf-8-sig'
        )
        driver.quit()


def get_data():
    driver = uc.Chrome(headless=False, use_subprocess=False, version_main=145)

    driver.get(init_url)
    time.sleep(3)

    metadata = pd.read_csv(urls_file_name)
    metadata["id"] = metadata["url"].apply(lambda x: x.split("/")[5])
    metadata = metadata.drop_duplicates("id")

    rows = []
    for i, row in tqdm(metadata.iterrows(), total=len(metadata)):
        try:
            name = row['name']
            url = row['url']

            driver.get(url)

            map_block = driver.find_element(By.ID, "mapsSection")
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", map_block)

            wait = WebDriverWait(driver, 15)

            price = wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, '[data-testid="price-amount"] span')
                )
            ).text
            #price = driver.find_element(By.CSS_SELECTOR, '[data-testid="price-amount"] span').text

            address = driver.find_element(By.CSS_SELECTOR, '[data-name="AddressContainer"]').text

            object_factoids_item = driver.find_elements(By.CSS_SELECTOR, '[data-name="ObjectFactoidsItem"]')
            object_factoids_item_dict = dict()
            for item in object_factoids_item:
                object_factoids_item_dict[item.text.split('\n')[0]] = item.text.split('\n')[1]

            description = driver.find_element(By.CSS_SELECTOR, '[data-name="Description"]').text

            offer_summary_info_item = driver.find_elements(By.CSS_SELECTOR, '[data-name="OfferSummaryInfoItem"]')
            offer_summary_info_item_dict = dict()
            for item in offer_summary_info_item:
                offer_summary_info_item_dict[item.text.split('\n')[0]] = item.text.split('\n')[1]

            name_value_list_item = driver.find_elements(By.CSS_SELECTOR, '[data-name="NameValueListItem"]')
            name_value_list_item_dict = dict()
            for item in name_value_list_item:
                name_value_list_item_dict[item.text.split('\n')[0]] = item.text.split('\n')[1]

            # logo_link = wait.until(
            #     EC.presence_of_element_located(
            #         (By.CLASS_NAME, "ymaps-2-1-79-copyright__logo")
            #     )
            # )
            #
            # wait.until(lambda d: logo_link.get_attribute("href") != "")
            #
            # href = logo_link.get_attribute("href")
            # print("href:", href)
            #
            # qs = parse_qs(urlparse(href).query)
            # ll = qs.get("ll", [None])[0]
            #
            # if ll:
            #     lon, lat = map(float, ll.split(","))
            #     # print("longitude =", lon)
            #     # print("latitude  =", lat)
            # else:
            #     print("Параметр ll не найден")
            #     lon, lat = np.nan, np.nan

            rows.append({
                **{
                    'Имя': name,
                    'Ссылка': url,
                    'Цена': price,
                    'Адрес': address,
                    'Описание': description,
                    # 'Долгота': lon,
                    # 'Широта': lat
                },
                **object_factoids_item_dict,
                **offer_summary_info_item_dict,
                **name_value_list_item_dict
            })
        except Exception as e:
            print(e)

    pd.DataFrame(rows).to_csv('cian_train.csv')

    time.sleep(10)

    driver.quit()


if __name__ == '__main__':
    if not os.path.isfile(urls_file_name):
        print('Start url parsing...')
        get_urls_by_price_step()
        print('Url parsing complete!')
    else:
        print('Url parsing skipping')

    get_data()
