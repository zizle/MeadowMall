# _*_ coding:utf-8 _*_
import re
from django.contrib.auth.backends import ModelBackend
from .models import User


def jwt_response_payload_handler(token, user=None, request=None):
    """自定义jwt验证成功返回的数据"""
    return {
        'token': token,
        'user_id': user.id,
        'username': user.username
    }


def get_user_by_account(account):
    """
    根据账号获取user对象
    :param:账号，可以是用户名也可以是手机号
    :return:user对象或者None
    """
    try:
        if re.match(r'1[3-9]\d{9}$', account):
            # 匹配成功就是账号是手机号
            user = User.objects.get(mobile=account)
        else:
            # 账号是用户名
            user = User.objects.get(username=account)
    except User.DoesNotExist:
        return None
    else:
        return user


class UsernameMobileAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = get_user_by_account(username)
        if user and user.check_password(password):
            return user
        print(user.username, user.check_password(password))
        # 不做返回是返回None
