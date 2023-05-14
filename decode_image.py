#!/usr/bin/env python
# -- coding: utf-8 --
"""
статусы

    SUCCESSFULLY_IMAGE = 5, 'Картинка готова к декодированию'
    IN_PROCESS_DECODE = 6, 'Картинка в процессе декодирования'
    SUCCESSFULLY_DECODE_IMG = 7, 'Картинка успешно извлечена в папку'
    ERROR_DECODE_IMAGE = 105, "Ошибка декодирования картинки"
    'decode/post_image_url/<int:site_pk>/<int:page_pk>/'
"""
import os
import base64
import json
import logging
from time import sleep
from logging import INFO, WARNING, ERROR, CRITICAL, FileHandler
from multiprocessing import Pool
import requests
from global_param import DJANGO_HOST, TIMEOUT, COUNT_GET_PICTURE_IN_DECODE, POOLCOUNT_GET_PICTURE_IN_DECODE, GETCWD


# GETCWD = (urllib.parse.quote_plus(GETCWD, safe='/', encoding=None, errors=None))
# print(GETCWD)


poll = None
request_data = None
POOL_COUNT = POOLCOUNT_GET_PICTURE_IN_DECODE
list_workers = []

#Настройки логгирования
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

info_handler = DebugFileHandler('log/decode-image-info.log')
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(info_handler)

error_handler = logging.FileHandler('log/decode-image-error.log')
error_handler.setLevel(logging.WARNING)
error_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(error_handler)

logger.info(f'программа запущена в {POOL_COUNT} процесса(ов)!')


# ('id', 'html_page', 'image_type', 'image_counter', 'domain_name', 'site_id',  'brand', 'vendor_code', 'image_item_id')
class DecodeImage(object):
    _id: int = None
    _html_page: str = ''
    _image_type: str = ''
    _image_counter: int = None
    _domain_name: str = ''
    _site_id: int = None
    _brand: str = ''
    _vendor_code: str = ''
    _image_item_id: int = None
    _status = None
    _image_path: str = ''    #относительный путь для сохранения в базу
    _pattern_path: str = ''   #паттерн создания пути
    path = None    #будет хранить рабочую директорию получаемую из env
    _image_name: str = ''   #имя файла


    def __init__(self, path='', *args, **kwargs) -> None:
        self.path = f'{GETCWD}/'   #текущая робочая директория
        self._status = 7
        self._image_path = ''    #относительная директория картинки


    def set_data(self, *args, **kwargs):
        self._id = kwargs.get('id', None)
        self._html_page = kwargs.get('html_page', '')
        self._image_type = kwargs.get('image_type', '').lower().strip()
        self._image_counter = kwargs.get('image_counter', None)
        self._domain_name = kwargs.get('domain_name', '').lower().strip()
        self._site_id = kwargs.get('site_id', None)
        self._brand = kwargs.get('brand', '').lower().replace(' ', '_').strip()
        self._vendor_code = kwargs.get('vendor_code', '').replace('/', '_').replace('\\', '_').replace(' ', '_').replace('.', '_').strip()
        self._image_item_id = kwargs.get('image_item_id', None)
        self._pattern_path = kwargs.get('pattern_path', None)


    def validate(self):
        if self._id and self._html_page and self._domain_name and self._site_id and self._image_counter and self._brand and self._vendor_code and self._image_item_id and self._pattern_path:
            self.constructor_path()
        else:
            logger.error(f'{self._id} Страница не прошла валидацию')
            self._status = 105
            self._post_reply()


    def _decode(self):
        try:
            base64_img_bytes = self._html_page.encode('utf-8')
            with open(self._image_name, 'wb') as file_to_save:
                decoded_image_data = base64.decodebytes(base64_img_bytes)
                file_to_save.write(decoded_image_data)
                self._status = 7
        except Exception as e:
            logger.error(f'Проблема декодирования картинки {self._id} {e}')
            self._status = 105
        finally:
            self._post_reply()


    def constructor_path(self):
        """формирование директории для сохранения картинки"""
        try:
            os.chdir(self.path)    #тут директория переданая в env становится рабочей
            self._image_path = self._pattern_path.format(brand=self._brand, vendor_code=self._vendor_code, image_counter=self._image_counter , image_type=self._image_type)   #формирует path картинки по формат строке, в обозримом будующем можно добавить большее количество значений
            path_str, separator, self._image_name = self._image_path.rpartition('/')    #деление строки на три части путь, разделитель и название файла
            os.makedirs(path_str, mode=0o777, exist_ok=True)   #создание этой директории без возбуждения ошибки в случае если она уже присутствует
            os.chdir(self.path+path_str)    #тут же становится рабочей
            self._decode()
        except Exception as e:
            logger.error(f'Проблемы в конструкции путей для сохранения кратинки {self._id} {e}')
            self._status  = 105
            self._post_reply()

    def _post_reply(self):
        """
        отправляет post запрос
        """
        # 'decode/post_image_url/<int:page_pk>/'
        resp = requests.post(f'{DJANGO_HOST}/api/decode/post_image_url/{self._id}/', json={'status': self._status, 'image_path':self._image_path})
        if resp.status_code!=201:
            logger.error(f'не удалось отправить post запрос в django со страницы id - {self._id}')
            # sleep(100)
        elif resp.status_code==201:
            logger.info(f'{os.getpid()} картинка со страницы id - {self._id} успешно декодирована')



def worker(cls: DecodeImage):
    cls.validate()
    return None


def main():
    while True:
        try:  # отлов глобальной ошибки в соединении
            request_data = requests.get(f'{DJANGO_HOST}/api/decode/image_url/{COUNT_GET_PICTURE_IN_DECODE}/')
            if request_data.status_code == 201:
                url_objects = json.loads(request_data.content)
                if url_objects:
                    list_workers = []
                    for obj in (url_objects):
                        cls_obj=DecodeImage()
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