# _*_ coding:utf-8 _*_
# QQ登录辅助
from django.conf import settings
from urllib.parse import urlencode, parse_qs
from urllib.request import urlopen
from itsdangerous import TimedJSONWebSignatureSerializer as TJWSSerializer, BadData
import logging
import json

from .exceptions import OAuthQQAPIError
from . import constants

logger = logging.getLogger('django')


class OAuthQQ(object):
    """QQ认证登录辅助"""
    def __init__(self, client_id=None, client_secret=None, redirect_uri=None, state=None):
        self.state = state or settings.QQ_STATE
        self.client_id = client_id if client_id else settings.QQ_CLIENT_ID
        self.client_secret = client_secret if client_secret else settings.QQ_CLIENT_SECRET
        self.redirect_uri = redirect_uri if redirect_uri else settings.QQ_REDIRECT_URI

    def get_qq_login_url(self):
        """获取QQ登录的url"""
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'state': self.state,
            'scope': 'get_user_info',
        }
        url = 'https://graph.qq.com/oauth2.0/authorize?' + urlencode(params)
        return url

    def get_access_token(self, code):
        """获取access_token"""
        params = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
        }
        url = 'https://graph.qq.com/oauth2.0/token?' + urlencode(params)
        try:
            # 向qq服务器发起获取access_token的请求
            response = urlopen(url)
            response_data = response.read().decode()
            # access_token = FE04 ** ** ** ** CCE2 & expires_in = 7776000 & refresh_token = 88E4 *** ** ** ** BE14
            # 解析出来的数据是{access_token: [xxx], }
            response_dict = parse_qs(response_data)
        except Exception as e:
            logger.error('获取access_token异常：%s' %e)
            # 抛出错误
            raise OAuthQQAPIError
        else:
            access_token = response_dict.get('access_token')

            return access_token[0]

    def get_openid(self, access_token):
        """
        获取openid
        :param access_token: 向QQ服务器获取openid必须参数
        :return: openid
        """
        url = 'https://graph.qq.com/oauth2.0/me?access_token=' + access_token
        response = urlopen(url)
        response_data = response.read().decode()
        # callback({"client_id": "YOUR_APPID", "openid": "YOUR_OPENID"})\n;
        try:
            # 解析数据
            response_dict = json.loads(response_data[10:-4])
            print('获取openid时response_dict:',response_dict)
        except Exception as e:
            data = parse_qs(response_data)
            logger.error('code=%s msg=%s' % ((data.get('code'), data.get('msg'))))
            raise OAuthQQAPIError
        # 获取openid
        openid = response_dict.get('openid', None)
        return openid

    @staticmethod
    def generate_access_token(openid):
        """
        生成access_token
        :return: token
        """
        serializer = TJWSSerializer(settings.SECRET_KEY, expires_in=constants.SAVE_QQ_USER_TOKEN_EXPIRES)
        token = serializer.dumps({"openid": openid})
        return token.decode()

    @staticmethod
    def check_save_user_token(token):
        """
        检验我们生成的access_token
        :param token:
        :return:
        """
        serializer = TJWSSerializer(settings.SECRET_KEY, expires_in=constants.SAVE_QQ_USER_TOKEN_EXPIRES)
        try:
            data = serializer.loads(token)
        except BadData:
            return None
        else:
            return data.get('openid')