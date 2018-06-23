# _*_ coding:utf-8 _*_
# QQ登录辅助
from django.conf import settings
from urllib.parse import urlencode


class OAuthQQ(object):
    """QQ认证登录辅助"""
    def __init__(self, status):
        self.status = status

    def get_qq_login_url(self):
        """获取QQ登录的url"""
        params = {
            'response_type': 'code',
            'client_id': settings.QQ_CLIENT_ID,
            'redirect_uri': settings.QQ_REDIRECT_URI,
            'state': self.status,
            'scope': 'get_user_info',
        }
        url = 'https://graph.qq.com/oauth2.0/authorize?' + urlencode(params)
        return url
