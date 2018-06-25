from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_jwt.settings import api_settings
from rest_framework.generics import GenericAPIView

from .utils import OAuthQQ
from .exceptions import OAuthQQAPIError
from .models import OAuthQQUser
from .serializers import OAuthQQUserSerializer


class QQAuthURLView(APIView):
    """获取QQ登录的url"""
    def get(self, request):
        """提供qq登录的url"""
        next = request.query_params.get('next')
        oauth = OAuthQQ(state=next)
        login_url = oauth.get_qq_login_url()
        return Response({"login_url": login_url})


# GET /oauth/qq/user/?code=xxx
class QQAuthUserView(GenericAPIView):
    """QQ登录成功的用户"""
    serializer_class = OAuthQQUserSerializer

    def get(self, request):
        code = request.query_params.get('code')
        if not code:
            return Response({"message": '缺少code'}, status=status.HTTP_400_BAD_REQUEST)
        oauth = OAuthQQ()
        try:
            access_token = oauth.get_access_token(code)
            openid = oauth.get_openid(access_token)
        except OAuthQQAPIError:
            return Response({"message": "QQ服务异常"}, status.HTTP_503_SERVICE_UNAVAILABLE)
        try:
            # 判断用户是否存在
            qq_user = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            # 第一次使用qq登录，签发一个access_token
            token = oauth.generate_access_token(openid)
            return Response({"access_token": token})
        else:
            # 用户存在, 即不是第一次使用QQ登录
            # 找到用户，生成jwt——token，返回数据
            user = qq_user.user
            jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
            jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
            payload = jwt_payload_handler(user)
            token = jwt_encode_handler(payload)
            return Response({
                "token": token,
                "user_id": user.id,
                "user_name": user.username
            })

    def post(self, request):
        """
        保存QQ登录的用户
        :param request:
        :return:
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()  # 调用create方法

        # 签发jwt验证
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)

        response = Response({
            'token': token,
            'user_id': user.id,
            'username': user.username
        })

        return response









