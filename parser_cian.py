import os
import time
import random
import pandas as pd
from tqdm import tqdm
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By


init_url = 'https://kemerovo.cian.ru/'
urls_file_name = 'cian_urls.csv'


def get_urls():
    url = 'https://kemerovo.cian.ru/cat.php?deal_type=sale&engine_version=2&location%5B0%5D=4944&offer_type=flat'
    driver = uc.Chrome(headless=False, use_subprocess=False, version_main=133)

    driver.get(init_url)
    time.sleep(3)

    driver.get(url)

    max_page = 18

    name_list = []
    url_list = []
    for i in range(1, max_page + 1):
        offers = driver.find_elements(By.CSS_SELECTOR, '[data-mark="OfferTitle"]')
        for item in offers:
            parent = item.find_element(By.XPATH, '..')
            name_list.append(item.text)
            url_list.append(parent.get_attribute('href'))
        time.sleep(1)
        driver.get(url + '&p=%i' % (i + 1))

    pd.DataFrame({'name': name_list, 'url': url_list}).to_csv(urls_file_name)

    time.sleep(10)

    driver.quit()


def get_data():
    driver = uc.Chrome(headless=False, use_subprocess=False, version_main=133)

    driver.get(init_url)
    time.sleep(3)

    metadata = pd.read_csv(urls_file_name)

    rows = []
    for i, row in tqdm(metadata.iterrows(), total=len(metadata)):
        try:
            name = row['name']
            url = row['url']

            driver.get(url)

            price = driver.find_element(By.CSS_SELECTOR, '[data-name="PriceInfo"]').text

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

            rows.append({
                **{'Имя': name, 'Ссылка': url, 'Цена': price, 'Адрес': address, 'Описание': description},
                **object_factoids_item_dict,
                **offer_summary_info_item_dict,
                **name_value_list_item_dict
            })

            random.uniform(1, 2)

            # if i > 10:
            # break
        except Exception as e:
            print(e)

    pd.DataFrame(rows).to_csv('cian_train.csv')

    time.sleep(10)

    driver.quit()


if __name__ == '__main__':
    if not os.path.isfile(urls_file_name):
        print('Start url parsing...')
        get_urls()
        print('Url parsing complete!')
    else:
        print('Url parsing skipping')

    get_data()
