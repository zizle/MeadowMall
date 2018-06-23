# _*_ coding:utf-8 _*_
import re
from django_redis import get_redis_connection
from rest_framework_jwt.settings import api_settings

from rest_framework import serializers
from .models import User


class CreateUserSerializer(serializers.ModelSerializer):
    """用户模型序列化器"""
    password2 = serializers.CharField(label='确认密码', write_only=True)  # ready_only是在返回数据是用的（序列化时输入）
    sms_code = serializers.CharField(label='短信验证码', write_only=True)  # write_only是在校验的时候用的（反序列化时输入）
    allow = serializers.CharField(label='同意协议', write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'password2', 'sms_code', 'mobile', 'allow']
        extra_kwargs = {
            'username': {
                'min_length': 5,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许5-20个字符的用户名',
                    'max_length': '仅允许5-20个字符的用户名',
                    }
            },

        'password': {
            'write_only': True,
            'min_length': 8,
            'max_length': 20,
            'error_messages': {
                'min_length': '仅允许8-20个字符的密码',
                'max_length': '仅允许8-20个字符的密码',
                }
            }
        }

    def validate_mobile(self, value):
        """验证手机号"""
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式有误!')
        return value

    def validate_allow(self, value):
        """检验是否勾选用户协议"""
        if value != 'true':
            raise serializers.ValidationError('请同意用户协议!')
        return value

    def validate(self, data):
        """检验两次密码"""
        if data['password'] != data['password2']:
            raise serializers.ValidationError('两次密码不一致!')

        # 判断短信验证码
        # 获取真实验证码
        redis_conn = get_redis_connection('verify_codes')
        mobile = data['mobile']
        real_sms_code = redis_conn.get('sms_%s' % mobile)
        # 对比验证码
        if not real_sms_code:
            raise serializers.ValidationError('无效的短信验证码')
        if data['sms_code'] != real_sms_code.decode():
            raise serializers.ValidationError('短信验证码错误')
        return data

    def create(self, validated_data):
        """创建用户"""
        # 移除数据库模型不存在的属性
        del validated_data['password2']
        del validated_data['allow']
        del validated_data['sms_code']
        # 创建模型对象
        user = User.objects.create(**validated_data)
        user.set_password(validated_data['password'])
        user.save()

        # 创建完用户签发JWT
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)
        user.token = token
        return user
