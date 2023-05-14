#!/usr/bin/env python
# -- coding: utf-8 --
"""
получает текст html страницы по api достаёт url из страницы и отправляет по api в краулер
будет работать для всех видов страниц, регулярка ищет по содержимому href
!!!ВНИМАНИЕ ЕСЛИ КОЛИЧЕСТВО ПРОЦЕССОВ НЕ УКАЗАНО ЯВНО В ПЕРЕМЕННОЙ POOL_COUNT, КОЛЛИЧЕСТВО ПРОЦЕССОВ БУДЕТ ЗАВИСЕТЬ ОТ МАШИНЫ!!!

СТАТУСЫ

    HTML_SUCCESSFULLY = 30, 'HTML успешно извлечён страница готова к извлечению url-ок'
    IN_PROCESS_PARS = 31, 'Страница в процессе извлечения url'
    SUCCESSFULLY_URL = 32, 'Из страницы успешно извлечены url страница готова к определению типа'
"""
import os
import re
import json
import logging
from time import sleep
from urllib.parse import urlparse
from logging import INFO, WARNING, ERROR, CRITICAL, FileHandler
from multiprocessing import Pool

import requests

from global_param import DJANGO_HOST, TIMEOUT, COUNT_GET_URL, POOLCOUNT_GET_URL


poll = None
request_data = None
POOL_COUNT = POOLCOUNT_GET_URL
list_workers = []


log_format = '%(asctime)s   - %(name)s - %(levelname)s - %(message)s'

logger = logging.getLogger('url_get')
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



info_handler = DebugFileHandler('log/get-url-info.log')
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(info_handler)

error_handler = logging.FileHandler('log/get-url-error.log')
error_handler.setLevel(logging.WARNING)
error_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(error_handler)

logger.info(f'программа запущена в {POOL_COUNT} процесса(ов)!')


class GetUrl(object):
    _id: int = None
    _site: int = None
    _html_page: str = ''
    _domain_name: str = ''
    _status: int = None


    def __init__(self, *args, **kwargs) -> None:
        self._list_url = []  # результирующий список


    def set_data(self, *args, **kwargs):
        self._id = kwargs.get('id', None)
        self._domain_name = kwargs.get('domain_name', None)
        self._site = kwargs.get('site', None)
        self._html_page = kwargs.get('html_page', '')
        self._status = 30   # HTML успешно извлечён страница готова к извлечению url-оk


    def validate(self):
        if self._id and self._domain_name and self._site and self._html_page:
            self._get_list_url()

        # значит что нету html-kи поставить статус 20 - 'Html станицы не извлекался'
        elif (not self._html_page) and (self._id and self._domain_name and self._site):
            self._status = 20
            self._html_page = ''
            self._post_reply()
            logger.error(f'{self._id} нету html')
        else:
            logger.error(f'Страница {self.__dict__} Не прошла валидацию ')
            pass


    def _attempt_method(self):
        resp = requests.put(f'{DJANGO_HOST}/api/change-status/{self._id}/', json = {'status':20})    #снова извлекаем html
        if resp.status_code==201:
            logger.info(f'{self._id} Django часть добавила attempt')
        elif resp.status_code==500:
            logger.error(f'{resp.text}  {self._id}  django часть не приняла запрос на обновление attempта')


    def _error_page(self):
        """
        сигналы ошибок в html страницах, которые нам сообщают что можно возвращать статус 20 - 'Html станицы не извлекался'
        """
        error_sign = ["Проверка браузера", "404 Not Found"]
        for i in error_sign:
            if i in self._html_page or (not self._html_page):
                self._status = 20
                self._attempt_method()
                return None
        self._post_reply()


    def _get_list_url(self):
        """
        достаём список url-ok со страницы
        """
        set_url = set(re.findall(r'href\s?=\s?[\'"]?([^\'" >]+)[\'"]?', self._html_page))
        list_url = list(set_url)  # и оставить обратно list
        for i in list_url:
            url = urlparse(i)
            if (url.netloc == self._domain_name or url.netloc == '') and url.scheme in ('http', 'https', ''):
                self._list_url.append(url.path)

        if self._list_url == []:
            self._status = 93  # пустой
        else:
            self._status = 32  # успешный список заполнен
        self._error_page()  # если есть какие-то проблемы поменяет статус на 20


    def _post_reply(self):
        """
        отправляет post запрос
        """
        resp = requests.post(f'{DJANGO_HOST}/api/parser/posturl/{self._site}/{self._id}/', json={'url_list': self._list_url, 'status': self._status, 'site': self._site, 'id': self._id})
        if resp.status_code!=201:
            logger.error(f'не удалось отправить post запрос в django со страницы id - {self._id} со списком url-ок  {resp.text}')
            # sleep(100)
        elif resp.status_code==201:
            logger.info(f'{os.getpid()} url-ки со страницы id - {self._id} успешно отправлены')


def worker(cls: GetUrl):
    cls.validate()
    return None


def main():
    while True:
        try:  # отлов глобальной ошибки в соединении
            request_data = requests.get(f'{DJANGO_HOST}/api/parser/give-html/{COUNT_GET_URL}/')
            if request_data.status_code == 201:
                url_objects = json.loads(request_data.content)
                if url_objects:
                    list_workers = []
                    for obj in (url_objects):
                        cls_obj=GetUrl()
                        cls_obj.set_data(**obj)
                        list_workers.append(cls_obj)

                    if len(list_workers) > 0:
                        with Pool(processes=POOL_COUNT) as poll:
                            res = poll.map_async(worker, list_workers)
                            res.get(timeout=TIMEOUT)    #если не вернёт результат за 10 минут вызовет исключение TimeoutError

                else:
                    logger.info('путой список к исполнению, спим минуту')
                    sleep(60)

            elif request_data.status_code == 500:
                logger.error(request_data.text)
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