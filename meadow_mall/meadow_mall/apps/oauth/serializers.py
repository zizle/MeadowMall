# _*_ coding:utf-8 _*_

from rest_framework import serializers
from django_redis import get_redis_connection

from .utils import OAuthQQ
from users.models import User
from oauth.models import OAuthQQUser


class OAuthQQUserSerializer(serializers.Serializer):
    """自定义QQ登录用户的序列化器"""
    mobile = serializers.RegexField(label='手机号', regex=r'^1[3-9]\d{9}$')
    password = serializers.CharField(label='密码', max_length=20, min_length=8)
    access_token = serializers.CharField(label='操作凭证')
    sms_code = serializers.CharField(label='短信验证码')

    def validate(self, attrs):
        """检验access_token"""
        access_token = attrs['access_token']
        openid = OAuthQQ.check_save_user_token(access_token)
        if not openid:
            raise serializers.ValidationError('无效的access_token')
        attrs['openid'] = openid

        # 检验短信验证码
        mobile = attrs['mobile']
        sms_code = attrs['sms_code']
        redis_conn = get_redis_connection('verify_codes')
        real_sms_code = redis_conn.get('sms_%s' % mobile)
        if sms_code != real_sms_code.decode():
            return serializers.ValidationError('短信验证码错误')

        # 检查当前用户是否存在
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            pass
        else:
            # 用户存在，检验密码
            password = attrs['password']
            if not user.check_password(password):
                raise serializers.ValidationError('手机号或密码错误')
            attrs['user'] = user

        return attrs

    def create(self, validated_data):
        user = validated_data.get('user')
        if not user:
            # 用户不存在，创建用户
            user = User.objects.create_user(
                username=validated_data['mobile'],
                password=validated_data['password'],
                mobile=validated_data['mobile']
            )
        # 创建与qq绑定的信息
        OAuthQQUser.objects.create(
            user=user,
            openid=validated_data['openid']
        )
        return user


