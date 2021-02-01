import contextlib
from urllib.request import urlopen


def make_tiny(url):
    request_url = ('https://tinyurl.com/api-create.php?url=' +
                   url)
    with contextlib.closing(urlopen(request_url)) as response:
        return response.read().decode('utf-8')
