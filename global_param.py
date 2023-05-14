import os


TIMEOUT = int(os.environ.get('TIMEOUT', 600))    #таймаут для возврата результата из потоков
DJANGO_HOST = str(os.environ.get('DJANGO_HOST', 'http://127.0.0.1:8000'))
GETCWD = str(os.environ.get('GETCWD', ''))

#количество информации подаваемой на вход
COUNT_GET_URL = int(os.environ.get('COUNT_GET_URL', 20))
COUNT_URL_PAGE_TYPE = int(os.environ.get('COUNT_URL_PAGE_TYPE', 20))
COUNT_FACTORY = int(os.environ.get('COUNT_FACTORY', 20))
COUNT_GET_URL_PICTURE = int(os.environ.get('COUNT_GET_URL_PICTURE', 20))
COUNT_GET_PICTURE_IN_DECODE = int(os.environ.get('COUNT_GET_PICTURE_IN_DECODE', 1))

#количество процессов в которой работает программа
POOLCOUNT_GET_URL = int(os.environ.get('POOLCOUNT_GET_URL', 3))
POOLCOUNT_URL_PAGE_TYPE = int(os.environ.get('POOLCOUNT_URL_PAGE_TYPE', 3))
POOLCOUNT_FACTORY = int(os.environ.get('POOLCOUNT_FACTORY', 1))
POOLCOUNT_GET_URL_PICTURE = int(os.environ.get('POOLCOUNT_GET_URL_PICTURE', 3))
POOLCOUNT_GET_PICTURE_IN_DECODE = int(os.environ.get('POOLCOUNT_GET_PICTURE_IN_DECODE', 1))