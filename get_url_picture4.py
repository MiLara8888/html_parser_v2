# -*- coding: utf-8 -*-
# !/usr/bin/env python
"""

фабрика извлечения url-ok картинок из html страницы

"""
import os
import json
import logging
import requests
from time import sleep
from multiprocessing import Pool
from logging import INFO, WARNING, ERROR, CRITICAL, FileHandler

from global_param import DJANGO_HOST, TIMEOUT, COUNT_GET_URL_PICTURE, POOLCOUNT_GET_URL_PICTURE



poll = None
request_data = None
POOL_COUNT = POOLCOUNT_GET_URL_PICTURE
log_format = '%(asctime)s   - %(name)s - %(levelname)s - %(message)s'


logger = logging.getLogger('get_url_picture')
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


info_handler = DebugFileHandler('log/get-url-picture-info.log')
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(info_handler)

error_handler = logging.FileHandler('log/get-url-picture-error.log')
error_handler.setLevel(logging.WARNING)
error_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(error_handler)


logger.info(f'Программа запущена, и будет работать в {POOL_COUNT} процесса(ов)!')



class BasePictureGet:
    """
    для обработки ответа, валидации и отправки на обработку в нужную фабрику
    """
    html_page: str = None    # основные данные для обработки
    id: int = None    #айди страницы
    domain_name: str = None    #для определения фабрики
    site_id: int = None    #id сайта


    def __init__(self):
        self.picture_list: list = []


    def set_data(self, *args, **kwargs):
        self.html_page = kwargs.get("html_page", None)
        self.id = kwargs.get("id", None)
        self.domain_name = kwargs.get("domain_name", None)
        self.site_id = kwargs.get("site_id", None)



    def validate(self):  # проверит на вхождение всех полей
        if self.html_page and self.id and self.domain_name and self.site_id:
            if self.domain_name == 'santehnika-online.ru':
                SantehnikaPictures(self.html_page, self.id, self.site_id)
        else:
            logger.error(f"на странице {self.id} не все данные необходимые для корректной обработки информации")


    def post_resp(self):
        """
        отправляет post запрос
        """
        # parser/post-picture-url/<int:site_pk>/<int:page_pk>/
        resp = requests.post(f'{DJANGO_HOST}/api/parser/post-picture-url/{self.site_id}/{self.id}/', json={ 'picture_list': self.picture_list})
        if resp.status_code!=201:
            logger.error(f' {resp.text} не удалось отправить post запрос в django со страницы id - {self.id} со списком url-ок')
        elif resp.status_code==201:
            logger.info(f'{os.getpid()} url-ки со страницы id - {self.id} успешно отправлены')


    def attempt_method(self):
        resp = requests.put(f'{DJANGO_HOST}/api/change-status/{self.id}/', json = {'status':20})    #снова извлекаем html
        if resp.status_code==201:
            logger.info(f'{self.id} Django часть добавила attempt')
        elif resp.status_code==500:
            logger.error(f'{resp.text}  {self.id}  django часть не приняла запрос на обновление attempта')



class SantehnikaPictures(BasePictureGet):
    """фабрика для извлечения картинок из сайта сантехника онлайн"""

    def __init__(self, html_page, id, site_id) -> None:
        super().__init__()
        self.html_page: str = html_page
        self.id:int = id
        self.picture_list:list = []
        self.site_id = site_id
        self.get_json()


    def get_json(self):
        """Достаём json"""
        try:
            self.json_product = json.loads(self.html_page[self.html_page.find('{"Location'):self.html_page.find(';</script>')])
            self.json_product = json.loads(self.html_page[self.html_page.find('{"Location'):self.html_page.find(';</script>')])
            data = self.json_product.get('CardMedia', None).get('data', None)
            self.get_dict_picture(data)
        except:
            self.attempt_method()
            logger.error(f'{self.id} Не удалось из страницы извлечь json отправлена обратно со статусом 20')



    def get_dict_picture(self, data):
        """
        извлекает дикты картинок
        """

        for i in data:
            if i in ['pictures', 'shema']:
                for j in data[i]:
                    self.get_picture_url(j)


        if self.picture_list:
            self.post_resp()
        elif not self.picture_list:
            self.post_resp()
            logger.error(f'{self.id} На странице нет картинок')


    def get_picture_url(self, info):
        """ извлечение url картинок из dicta """
        for i in info:
            try:
                picture_url = info[i].get('src')    #url
                self.picture_list.append(picture_url)
            except AttributeError as e:
                continue
            except IndexError as e:
                continue


def worker(cls: BasePictureGet):
    cls.validate()
    return None


def main():
    while True:
        try:  # отлов глобальной ошибки в соединении
            request_data = requests.get(f'{DJANGO_HOST}/api/parser/get-picture-url/{COUNT_GET_URL_PICTURE}/')
            if request_data.status_code == 201:
                url_objects = json.loads(request_data.content)

                if url_objects:
                    list_workers = []

                    for obj in url_objects:
                        cls_obj=BasePictureGet()
                        cls_obj.set_data(**obj)
                        list_workers.append(cls_obj)

                    if len(list_workers) > 0:
                        with Pool(processes=POOLCOUNT_GET_URL_PICTURE) as poll:
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