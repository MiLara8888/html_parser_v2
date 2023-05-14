#!/usr/bin/env python
# -- coding: utf-8 --
"""
определяет тип страницы в зависимости от метаданных сайта, в метаданных могут быть:
- регулярные выражения для определения типа страницы по url <type_page_regular_url>
- регулярные выражения для определения типа страницы по html <type_page_regular_html>
- регулярные выражения по вложенности url <type_page_include_url>
отправляет  put запрос  dictfield {id:тип страницы}
"""
import re
import json
import logging
from time import sleep
from multiprocessing import Pool
from logging import  INFO, WARNING, ERROR, CRITICAL, FileHandler
from requests.exceptions import ConnectionError

import requests

from global_param import DJANGO_HOST, TIMEOUT, COUNT_URL_PAGE_TYPE, POOLCOUNT_URL_PAGE_TYPE

log_format = '%(asctime)s   - %(name)s - %(levelname)s - %(message)s'

logger = logging.getLogger('type_page_url')
logger.setLevel(logging.INFO)    #уровень на уровне всего логирования файла


class DebugFileHandler(FileHandler):
    """
    переопределение класса, чтобы warning и info падали в другой файл
    """
    def __init__(self, filename :str, mode='a', encoding=None, delay=False):
        super().__init__(filename, mode, encoding, delay)

    def emit(self, record):
        if record.levelno == CRITICAL or record.levelno == ERROR or record.levelno == WARNING:
            return
        super().emit(record)


info_handler = DebugFileHandler('log/type-page-info.log')
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(info_handler)

error_handler = logging.FileHandler('log/type-page-error.log')
error_handler.setLevel(logging.WARNING)
error_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(error_handler)

POOL_COUNT = POOLCOUNT_URL_PAGE_TYPE
logger.info(f'программа запущена в {POOL_COUNT} процесса(ов)')


class TypeUrl:

    _id: int = None
    _url: str = None
    _meta_url: dict = None
    _type_page: int = 0
    _format: list = None


    def __init__(self, *args, **kwargs) -> None:
        self._format = []    #список форматов


    def set_data(self, *args, **kwargs):
        self._id = kwargs.get('id', None)
        self._url = kwargs.get('url', None)
        self._meta_url = kwargs.get('meta_url', None)
        self._type_page = 32


    @property
    def state(self):
        return self._state


    @state.setter
    def state(self, value):
        self._state = value


    def get_format(self):
        """вернёт список форматов сериалайзера"""
        if list(self._meta_url.keys()):
            self._format = list(self._meta_url.keys())
            return self._get_serializer()
        else:
            logger.error(f'для страницы {self._url} не удалось определить формат')


    def _get_serializer(self):
        """метод определяющий, какой способ обрабатывания метаданных использовать"""
        if "type_page_regular_url" in self._format:    #когда тип страницы можно определить по url
            return self._serialize_by_url()
        elif f"type_page_regular_html" in self._format:    #когда тип страницы можно определять по html
            return self._serialize_by_html()
        elif "type_page_include_url" in self._format:    #когда можно определить тип по вложенности url
            return self._serialize_by_include_url()
        else:
            logger.error(f'для страницы {self._url} не удалось определить формат')


    def _serialize_by_include_url(self):
        """определение типа страницы по вложенности url"""
        pass


    def _serialize_by_html(self):
        """определение типа страницы по html"""
        pass


    def _serialize_by_url(self):
        """определение типа страницы по url и регулярному выражению"""
        type_keys={'brand':10,'collection':30,'product':20}    #типы из джанги
        regular=self._meta_url['type_page_regular_url']
        for key, arr in regular.items():
            for pattern in arr:
                if re.match(pattern, self._url):
                    return int(self._id), type_keys[key]
        return int(self._id), 50


def worker(cls: TypeUrl):
    return cls.get_format()



def main():
    while True:
        try:
            request_data=requests.get(f'{DJANGO_HOST}/api/parser/get-category-url/{COUNT_URL_PAGE_TYPE}/')
            if request_data.status_code==201:    #если успех
                result_list=json.loads(request_data.content)    #преобразовывает  b '' в list
                if result_list:

                    list_workers = []

                    for obj in (result_list):
                        cls_obj = TypeUrl()
                        cls_obj.set_data(**obj)
                        list_workers.append(cls_obj)


                    if len(list_workers) > 0:
                        with Pool(processes=POOL_COUNT) as poll:
                            result = poll.map_async(worker, list_workers)
                            n = result.get(timeout=TIMEOUT)
                            resp = requests.post(f'{DJANGO_HOST}/api/parser/postcategory/',json={'result_list':n})
                            if resp.status_code==201:
                                logger.info(f'успешно обработаны {n}')
                            elif resp.status_code!=201:
                                logger.error(f'{resp.text} не удалось отправить post запрос в django {n}')
                                sleep(200)
                else:
                    logger.info('путой список к исполнению, спим минуту')
                    sleep(60)

            elif request_data.status_code==500:
                logger.error(request_data.text)
                sleep(100)

            else:
                logger.error('из django вернулся не 201 и не 500 статус')
                sleep(100)

        except ConnectionError as e:
            logger.error('Проблема с соединением')
            sleep(100)

        except ValueError as e:
            logger.error(f'Проблема в форматировании {e}')
            sleep(100)

        except Exception as e:
            logger.error(f'Ошибка {e}')
            sleep(100)


if __name__ == "__main__":
    main()