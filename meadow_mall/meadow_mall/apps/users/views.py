from django.shortcuts import render

# Create your views here.

from rest_framework.views import APIView
from .models import User
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .serializers import CreateUserSerializer, UserDetailSerializer, EmailSerializer


# url(r'^usernames/(?P<username>\w{5,20})/count/$', views.UsernameCountView.as_view()),
class UsernameCountView(APIView):
    def get(self, request, username):
        count = User.objects.filter(username=username).count()
        data = {
            'username': username,
            'count': count
        }
        return Response(data)


# url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', views.MobileCountView.as_view()),
class MobileCountView(APIView):
    """
    手机号数量
    """
    def get(self, request, mobile):
        """
        获取指定手机号数量
        """
        count = User.objects.filter(mobile=mobile).count()

        data = {
            'mobile': mobile,
            'count': count
        }

        return Response(data)


# url(r'^users/$', views.UserView.as_view()),
class UserView(CreateAPIView):
    """
    用户注册
    传入参数：
        username, password, password2, sms_code, mobile, allow
    """
    serializer_class = CreateUserSerializer


class UserDetailView(RetrieveAPIView):
    """用户中心详情"""
    serializer_class = UserDetailSerializer
    # 增加访问视图的权限
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class EmailView(UpdateAPIView):
    """保存邮箱"""
    permission_classes = [IsAuthenticated]
    serializer_class = EmailSerializer

    def get_object(self):
        return self.request.user


class VerifyEmailView(APIView):
    """邮箱验证视图"""
    def get(self, request):
        """验证邮箱"""
        # 接收token
        token = request.query_params.get('token')
        if not token:
            return Response({"message": '缺少token'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.check_verify_email_token(token)
        if not user:
            return Response({'message': '链接信息无效'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            user.email_active = True
            user.save()
            return Response({'message': 'OK'})




