import os
from utils import load_json, save_json, make_dir, download_image, scantree
from scraper import ProductList, ProductDetails
from excel_exporter import export_excel
from multiprocessing import Pool
import requests

# from selenium import webdriver

make_dir('output')
make_dir('output/excel')
make_dir('output/data')
make_dir('output/products')
make_dir('output/images')


def download_images():
    image_meta_list = []
    for entry in scantree('output/products'):
        if entry.name.endswith('.json'):
            data = load_json(entry.path)
            if data['image_url'] == '':
                continue
            image_meta_list.append({
                'url': data['image_url'],
                'path': 'output/images/',
                'file_name': entry.name.replace('.json', '')
            })
    print('===', len(image_meta_list), '===')
    pool = Pool(50)
    pool.map(download_image, image_meta_list)


if __name__ == '__main__':
    product_list = ProductList()
    # product_list.fetch_meta_list()
    # product_list.scrape()

    product_details = ProductDetails()
    # product_details.scrape()

    export_excel()

    # export_compatibility_list()
    #
    # download_images()
