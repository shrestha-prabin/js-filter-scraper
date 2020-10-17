import xlsxwriter
import os
from utils import load_json, flatten_list
from functools import reduce


def get_product_details(category, code):
    file_name = 'output/products/' + category + '/' + code + '.json'

    if os.path.exists(file_name):
        return load_json(file_name)
    else:
        # print('\nFile not found', file_name)
        return None


def export(brand):
    workbook = xlsxwriter.Workbook('output/excel/' + brand.replace('/', '#') + '.xlsx', {'strings_to_urls': False})
    worksheet = workbook.add_worksheet('jsfilter')

    worksheet.write('A1', 'Brand')
    worksheet.write('B1', 'Class')
    worksheet.write('C1', 'Model')
    worksheet.write('D1', 'Year')
    worksheet.write('E1', 'Engine Vol')
    worksheet.write('F1', 'Engine No')
    worksheet.write('G1', 'Body No')
    worksheet.write('H1', 'Filter Type')
    worksheet.write('I1', 'Product Name')
    worksheet.write('J1', 'Product Code')
    worksheet.write('K1', 'Specifications')
    worksheet.write('L1', 'Cross Reference')
    worksheet.write('M1', 'Applications')
    worksheet.write('N1', 'Image URL')
    worksheet.write('O1', 'Product URL')

    worksheet.set_column('A:H', 15)
    worksheet.set_column('I:I', 30)
    worksheet.set_column('J:J', 15)
    worksheet.set_column('K:O', 30)

    row, col = 1, 0

    with os.scandir('output/data') as it:
        for file_entry in it:
            if file_entry.name.endswith('.json'):
                if file_entry.name.split('_')[0] != brand:
                    continue
                data_file = load_json(file_entry.path)

                for item in data_file:

                    category_list = ['oil', 'air', 'fuel', 'cabin', 'trans']
                    for category_item in category_list:
                        for product_item in item[category_item]:
                            details = get_product_details(category_item, product_item['code'])

                            worksheet.write(row, col, item['brand'])
                            worksheet.write(row, col + 1, item['class'])
                            worksheet.write(row, col + 2, item['model'])
                            worksheet.write(row, col + 3, item['year'])
                            worksheet.write(row, col + 4, item['engine_vol'])
                            worksheet.write(row, col + 5, item['engine_no'])
                            worksheet.write(row, col + 6, item['body_no'])
                            worksheet.write(row, col + 7, category_item.upper())

                            worksheet.write(row, col + 9, product_item['code'])

                            if details is not None:
                                worksheet.write(row, col + 8,  details['name'])
                                worksheet.write(row, col + 10, flatten_list(details['specifications']))
                                worksheet.write(row, col + 11, flatten_list(details['cross_reference']))
                                worksheet.write(row, col + 12, flatten_list(details['applications']))
                                worksheet.write(row, col + 13,  details['image_url'])
                                worksheet.write(row, col + 14,  details['url'])

                            print('\r', brand, row, end='')
                            row += 1

    workbook.close()


def export_excel():
    meta_list = load_json('meta_list.json')
    brand_list = []
    for meta_item in meta_list:
        brand = meta_item['brand_item']['name']
        if brand not in brand_list:
            brand_list.append(brand)

    for brand in brand_list:
        export(brand)
