"""
http请求方法常量
"""

METHOD_HEAD = 'HEAD'
METHOD_GET = 'GET'
METHOD_DELETE = 'DELETE'
METHOD_OPTIONS = 'OPTIONS'
METHOD_PATCH = 'PATCH'
METHOD_POST = 'POST'
METHOD_PUT = 'PUT'
METHOD_ALL = {METHOD_HEAD, METHOD_GET, METHOD_DELETE, METHOD_OPTIONS, METHOD_PATCH, METHOD_POST, METHOD_PUT}

"""
http 请求码常量
"""
from http import HTTPStatus

STATUS_CODES = HTTPStatus.__dict__.get('_value2member_map_')


if __name__ == '__main__':
    print(100 in STATUS_CODES.keys())