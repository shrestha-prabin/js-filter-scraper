import requests
from bs4 import BeautifulSoup
from utils import save_json, make_dir, mock_response, load_json, divide_chunks, make_soup, scantree
from multiprocessing import Pool
import os
import re
# from selenium import webdriver
from time import sleep
import json
from functools import reduce

base_url = ''

user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) ' \
             'Chrome/83.0.4103.116 Safari/537.36 '


class ProductList:

    def fetch_meta_list(self):
        meta_list = []
        brand_list = self.fetch_brand_list()
        print(len(brand_list), brand_list)
        for brand_item in brand_list:
            class_list = self.fetch_class_list(brand_item)
            if len(class_list) == 0:
                class_list = [{'app_class_id': '', 'app_class_name': ''}]
            print(len(class_list), brand_item, class_list)
            for class_item in class_list:
                meta_list.append({
                    'brand_item': brand_item,
                    'class_item': class_item
                })

        save_json(meta_list, 'meta_list.json')

    def scrape(self):
        meta_list = load_json('meta_list.json')
        pool = Pool(50)
        pool.map(self.export, meta_list)

    def export(self, meta_item):
        brand_item = meta_item['brand_item']
        class_item = meta_item['class_item']
        output_file_name = 'output/data/' + brand_item['name'].replace('/', '#') + '_' + class_item[
            'app_class_name'].replace('/', '#') + '.json'
        if os.path.exists(output_file_name):
            return

        model_list = self.fetch_model_list(brand_item, class_item)
        model_ids = reduce(lambda x, y: x + y['app_model_id'] + ',', model_list, '')
        product_list = self.fetch_product_list(brand_item, model_ids[0:len(model_ids) - 1], class_item)
        save_json(product_list, output_file_name)
        print(output_file_name)

    def fetch_brand_list(self):
        url = 'http://www.jsfilter.jp/catalogue'
        response = requests.get(url)
        soup = make_soup(response.text)

        result = []
        for option in soup.find('select', attrs={'id': 'selBrand'}).findAll('option'):
            result.append({
                'name': option.text.strip(),
                'value': option['value']
            })
        return result

    def fetch_class_list(self, brand_item):
        url = 'http://www.jsfilter.jp/application/get_application_class/' + brand_item['value']
        response = requests.get(url, headers={
            'X-Requested-With': 'XMLHttpRequest',
        })
        response = json.loads(response.text)
        return response

    def fetch_model_list(self, brand_item, class_item):
        url = 'http://www.jsfilter.jp/application/get_application_models/'
        response = requests.post(url, data={
            'classId': class_item['app_class_id'],
            'brandId': brand_item['value']
        }, headers={
            'X-Requested-With': 'XMLHttpRequest',
        })
        response = json.loads(response.text)
        return response

    def fetch_product_list(self, brand_item, model_id, class_item):
        url = 'http://www.jsfilter.jp/application/get_applications/'
        response = requests.post(url, data={
            'modelId': model_id,
            'classId': class_item['app_class_id'],
            'year': '',
            'eng_vol': ''
        })
        soup = make_soup(response.text)
        skip = True
        model = ''
        result = []
        for child in soup.find('table').findAll(recursive=False):
            if skip:
                skip = False
                continue
            if child.get('class') == ['model-title']:
                model = child.text.split('»')[-1].strip()
                continue

            result.append({
                'brand': brand_item['name'],
                'class': class_item['app_class_name'],
                'model': model,
                'year': child.find('td', attrs={'data-title': 'YEAR'}).text.strip(),
                'engine_vol': child.find('td', attrs={'data-title': 'ENG VOL'}).text.strip(),
                'engine_no': child.find('td', attrs={'data-title': 'ENG NO'}).text.strip(),
                'body_no': child.find('td', attrs={'data-title': 'BODY NO'}).text.strip(),
                'oil': self.get_filter_data(child, 'OIL'),
                'air': self.get_filter_data(child, 'AIR'),
                'fuel': self.get_filter_data(child, 'FUEL'),
                'cabin': self.get_filter_data(child, 'CABIN'),
                'trans': self.get_filter_data(child, 'TRANS'),
            })

        return result

    def get_filter_data(self, soup, data_title):
        container = soup.find('td', attrs={'data-title': data_title})
        result = []
        for item in container.findAll('a'):
            result.append({
                'code': item.text.strip(),
                'url': item.get('href')
            })
        return result


class ProductDetails:

    def scrape(self):
        meta_list = []
        product_url_list = []
        for entry in scantree('output/data'):
            if entry.name.endswith('.json'):
                data = load_json(entry.path)
                for data_item in data:
                    category_list = ['oil', 'air', 'fuel', 'cabin', 'trans']
                    for category_item in category_list:
                        for product_item in data_item[category_item]:
                            output_file_name = 'output/products/' + category_item + '/' + product_item['code'] + '.json'
                            if os.path.exists(output_file_name):
                                # print('Skipping:', output_file_name)
                                continue

                            if product_item['url'] in product_url_list:
                                continue

                            product_url_list.append(product_item['url'])
                            meta_list.append({
                                'category': category_item,
                                'product_code': product_item['code'],
                                'product_url': product_item['url']
                            })

            print('\r', len(meta_list), end='')
        print()

        pool = Pool(50)
        pool.map(self.export, meta_list)


    def export(self, meta_item):
        url = meta_item['product_url']
        output_dir = 'output/products/' + meta_item['category']
        make_dir(output_dir)

        if url is None:
            return

        output_file_name = output_dir + '/' + meta_item['product_code'] + '.json'

        response = requests.get(url)
        soup = make_soup(response.text)

        if self.get_image_url(soup, url) is None:
            return

        details = {
            'url': url,
            'image_url': self.get_image_url(soup, url),
            'specifications': self.get_specifications(soup),
            'cross_reference': self.get_cross_reference(soup),
            'applications': self.get_applications(soup)
        }

        save_json(details, output_file_name)
        print(output_file_name)

    def get_image_url(self, soup, url):
        container = soup.find('div', attrs={'class': 'detail__gallery'})
        if container.find('a', attrs={'id': 'achrColorBox'}) is None:
            return ''
        return container.find('a', attrs={'id': 'achrColorBox'})['href']

    def get_specifications(self, soup):
        container = soup.find('div', attrs={'class': 'detail__specification'})
        result = []
        for item in container.findAll('div', attrs={'class': 'str'}):
            result.append(
                item.find('div', attrs={'class': 'param-title'}).text
                + '|' +
                item.find('div', attrs={'class': 'param-field'}).text
            )
        return result

    def get_cross_reference(self, soup):
        container = None
        for c in soup.findAll('div', attrs={'class': 'detail__plate'}):
            if c.find('p', attrs={'class': 'box-title'}).text == 'Cross reference':
                container = c
                break
        result = []
        for item in container.findAll('div', attrs={'class': 'str'}):
            result.append(
                item.find('div', attrs={'class': 'owner'}).text
                + '|' +
                item.find('div', attrs={'class': 'field'}).text
            )
        return result

    def get_applications(self, soup):
        container = soup.find('div', attrs={'class': 'table-grid'})

        result = []
        skip = True
        for child in container.findAll(recursive=False):
            if skip:
                skip = False
                continue
            if 'model-title' in child.get('class'):
                result.append(child.text.strip())
            elif 'model-body' in child.get('class'):
                table = child.find('table', attrs={'class': 'search-result-table'})
                for row in table.findAll('tr'):
                    row_children = row.findAll('td')
                    row_data = reduce(lambda x,y: x + y.text.strip() +  '|' , row_children, '')
                    result.append(row_data[0:len(row_data)-1])
        return result
