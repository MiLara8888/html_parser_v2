#!/usr/bin/env python
# -- coding: utf-8 --
"""
фабрика по извлечению информации из html - страницы
factory/give-html/<int:cnt>   get
factory/post-item/     post
"""
import re
import os
import json
import logging
from time import sleep
from multiprocessing import Pool
from logging import INFO, WARNING, ERROR, CRITICAL, FileHandler

import requests

from global_param import DJANGO_HOST, TIMEOUT, COUNT_FACTORY, POOLCOUNT_FACTORY


POOL_COUNT = POOLCOUNT_FACTORY
list_workers = []


log_format = '%(asctime)s   - %(name)s - %(levelname)s - %(message)s'


logger = logging.getLogger('factory')
logger.setLevel(logging.INFO)  # уровень на уровне всего логирования файла


class DebugFileHandler(FileHandler):
    """
    переопределение класса, чтобы warning и info падали в другой файл
    """

    def __init__(self, filename: str, mode='a', encoding=None, delay=False):
        super().__init__(filename, mode, encoding, delay)

    def emit(self, record):
        if record.levelno == CRITICAL or record.levelno == ERROR or record.levelno == WARNING:
            return
        super().emit(record)


info_handler = DebugFileHandler('log/factory-page-info.log')
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(info_handler)


error_handler = logging.FileHandler('log/factory-page-error.log')
error_handler.setLevel(logging.WARNING)
error_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(error_handler)


logger.info(f'программа запущена в {POOL_COUNT} процесса(oв)')


class BaseSiteClass:
    """для обработки ответа, валидации и отправки на обработку в нужную фабрику"""
    html_page: str = None    # основные данные для обработки
    id: int = None    # для отправки обратно в краулер
    url: str = None    # в url может-быть полезная информация
    domain_name: str = None    # с этой информацией будет определяться фабрика переработки
    site_id: int = None


    def __init__(self):
        self.name: str = None  # наименование
        self.unit: str = None  # единица измерения
        self.wholesale_price: float = None  # Оптовая стоимость товара
        self.sales_price: float = None  # розничная стоимость товара
        self.site_code: str = None  # уникальный идентификатор на сайте
        self.brand: str = None  # бренд
        self.vendor_code: str = None  # артикул
        self.json_data: dict = {'characteristics': {}}  # инфо для базы


    def set_data(self, *args, **kwargs):
        self.html_page = kwargs.get('html_page', None)
        self.id = kwargs.get('id', None)
        self.url = kwargs.get('url', None)
        self.domain_name = kwargs.get('domain_name', None)
        self.site_id = kwargs.get('site_id', None)


    def validate(self):  # проверит на вхождение всех полей
        if self.html_page and self.id and self.url and self.domain_name and self.site_id:
            if self.domain_name == 'santehnika-online.ru':
                SantehnikaOnlineFactory(self.html_page, self.id, self.url, self.domain_name, self.site_id)
        else:
            logger.error(f"на странице {self.url} не все данные необходимые для корректной обработки информации")


    def post_response(self):
        """отправка post запроса"""

        try:
            sleep(0.5)

            json_result = {'name': self.name, 'unit': self.unit, 'wholesale_price': self.wholesale_price, 'sales_price':self.sales_price,
                        'vendor_code':self.vendor_code, 'site_code':self.site_code, 'json_data':self.json_data, 'brand':self.brand}

            resp = requests.post(f'{DJANGO_HOST}/api/factory/post-item/{self.site_id}/{self.id}/', json=json_result)

            if resp.status_code!=201:
                logger.error(f'{resp.text} {self.url} Django часть не приняла этот post запрос ')
                # sleep(200)
            elif resp.status_code==201:
                logger.info(f'{os.getpid()} товар со страницы id - {self.id} успешно извлечён')

        except Exception as e:
            logger.error(f'{e} ошибка отправки post запроса в django')



    def attempt_plus(self):
        """специальный метод для отправки put запроса с изменением статуса и добавлением +1 attempt к странице"""

        resp = requests.put(f'{DJANGO_HOST}/api/change-status/{self.id}/', json = {'status':20})    #снова извлекаем html

        if resp.status_code==201:
            logger.info(f'{self.id} Django часть добавила attempt')
        elif resp.status_code==500:
            logger.error(f'{resp.text}  {self.id}  django часть не приняла запрос на обновление attempта')




class SantehnikaOnlineFactory(BaseSiteClass):
    """ФАБРИКА сайта santehnika-online.ru"""

    # _json_data: dict = None    #Какие-то важные данные о товаре

    def __init__(self, html_page, id, url, domain_name, site_id) -> None:
        super().__init__()
        self.html_page = html_page
        self.id = id
        self.url = url.strip()
        self.domain_name = domain_name
        self.site_id = site_id
        self.json_product = None
        self.get_json()


    def get_json(self):
        """Достаём json"""
        try:
            self.json_product = json.loads(self.html_page[self.html_page.find('{"Location'):self.html_page.find(';</script>')])
            self.json_product = json.loads(self.html_page[self.html_page.find('{"Location'):self.html_page.find(';</script>')])
            self.json_product = json.loads(self.html_page[self.html_page.find('{"Location'):self.html_page.find(';</script>')])
            self.json_product = json.loads(self.html_page[self.html_page.find('{"Location'):self.html_page.find(';</script>')])
            self.get_name()
        except:
            logger.error(f'{self.url} Не удалось из страницы извлечь json отправлена обратно со статусом 20')
            self.attempt_plus()


    def get_name(self):
        """имя товара"""
        try:
            self.name = self.json_product.get('cardDelivery', None).get('data', None).get('item', None).get('title', None).strip()
            if self.name:
                self.get_unit()
        except AttributeError:
            logger.error(f'{self.url}- из страницы не удалось извлечь имя отправлена обратно со статусом 20')
            self.attempt_plus()


    def get_unit(self):
        """ единица измерения """
        try:
            self.unit = self.json_product.get('CardPrice', '').get('data', '').get('unitSize', '')
        except AttributeError:
            logger.info(f'{self.url} Не удалось извлечь единицу измерения')
        finally:
            self.get_sales_price()


    def get_sales_price(self):
        """цена"""
        try:
            self.sales_price = self.json_product.get('CardPrice', None).get('data', None).get('price', None)
        except AttributeError:
            logger.info(f'из страницы {self.url} не удалось извлечь цену')
        finally:
            self.get_site_code()


    def get_site_code(self):
        """код на сайте"""
        try:
            self.site_code = self.json_product.get('CardPrice', '').get('data', '').get('code', '')
        except AttributeError:
            logger.info(
                f'{self.url} не удалось извлечь уникальный идектификатор')
        finally:
            self.get_brand()


    def get_brand(self):
        """бренд"""
        try:
            self.brand = self.json_product.get('brandInfo', '').get('name', '')
        except AttributeError:
            logger.info(f'{self.url} не удалось извлечь бренд')
        finally:
            self.get_article()


    def get_article(self):
        """артикул и json_data"""
        try:
            # артикул
            for i in self.json_product.get('CardImportantProperties', '').get('data', '').get('properties', ''):
                if i.get('code') == 'ART_FABRIC':
                    self.vendor_code = i.get('value', '')
                if i.get('code') == 'BRAND' and (self.brand == '' or self.brand==None):
                    self.brand = i.get('value', '')
                value = (re.sub(r'\<[^>]*\>', '', i.get('value', ''))).replace('&nbsp;', '')
                name = i.get('name', '')
                if name:
                    self.json_data['characteristics'][name] = value
        except AttributeError:
            logger.info(f'{self.url} не удалось извлечь информацию для извлечения артикула и характеристик')
        finally:
            self.post_response()



def worker(cls: BaseSiteClass):
    cls.validate()
    return None


def main():
    while True:
        try:  # отлов глобальной ошибки в соединении
            response_data = requests.get(f'{DJANGO_HOST}/api/factory/give-html/{COUNT_FACTORY}/')
            if response_data.status_code == 201:
                url_objects = json.loads(response_data.content)
                if url_objects:

                    list_workers = []

                    for obj in (url_objects):
                        n = BaseSiteClass()
                        n.set_data(**obj)
                        list_workers.append(n)


                    if len(list_workers) > 0:
                        with Pool(processes=POOL_COUNT) as poll:
                            res = poll.map_async(worker, list_workers)
                            res.get(timeout=TIMEOUT)
                else:
                    logger.info('Пустой список к исполнению, спим минуту')
                    sleep(60)

            elif response_data.status_code==500:
                logger.error(response_data.text)
                sleep(100)

            else:
                logger.error('из django вернулся не 201 и не 500 статус')
                sleep(100)

        except TimeoutError as e:
            logger.error('Результат не вернулся за 10 минут')
            sleep(100)

        except ConnectionError as e:
            logger.error('Проблема с соединением')
            sleep(100)

        except Exception as e:
            logger.error(f'Ошибка {e}')
            sleep(100)


if __name__ == "__main__":
    main()