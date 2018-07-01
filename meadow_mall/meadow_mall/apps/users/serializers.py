# _*_ coding:utf-8 _*_
import re
from django_redis import get_redis_connection
from rest_framework_jwt.settings import api_settings

from rest_framework import serializers
from .models import User, Address
from celery_tasks.email.tasks import send_verify_email
from goods.models import SKU
from . import constants


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


class UserDetailSerializer(serializers.ModelSerializer):
    """用户详情序列化器"""
    class Meta:
        model = User
        fields = ('id', 'username', 'mobile', 'email', 'email_active')


class EmailSerializer(serializers.ModelSerializer):
    """验证用户邮箱"""
    class Meta:
        model = User
        fields = ('id', 'email')
        extra_kwargs = {
            'email': {
                'required': True,
            }
        }

    def update(self, instance, validated_data):
        instance.email = validated_data['email']
        instance.save()

        # 生成验证链接
        verify_url = instance.generate_verify_email_url()
        # 发送邮件
        send_verify_email.delay(instance.email, verify_url)
        return instance


class UserAddressSerializer(serializers.ModelSerializer):
    province = serializers.StringRelatedField(read_only=True)
    city = serializers.StringRelatedField(read_only=True)
    district = serializers.StringRelatedField(read_only=True)
    province_id = serializers.IntegerField(label='省ID', required=True)
    city_id = serializers.IntegerField(label='市ID', required=True)
    district_id = serializers.IntegerField(label='区ID', required=True)

    class Meta:
        model = Address
        exclude = ('user', 'is_deleted', 'create_time', 'update_time')

    def validate_mobile(self, value):
        """
        验证手机号
        """
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class AddressTitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ('title',)


class AddUserBrowsingHistorySerializer(serializers.Serializer):
    """用户浏览历史"""
    sku_id = serializers.IntegerField(label='商品sku编号', min_value=1)

    def validated_sku_id(self, value):
        try:
            SKU.objects.get(id=value)
        except SKU.DoesNotExist:
            raise serializers.ValidationError('该商品不存在')
        return value

    def create(self, validated_data):
        user_id = self.context['request'].user.id
        sku_id = validated_data['sku_id']
        redis_conn = get_redis_connection('history')
        pl = redis_conn.pipeline()

        pl.lrem('history_%s' % user_id, 0, sku_id)  # 从表头搜索，移除与sku_id相同的元素
        pl.lpush('history_%s' % user_id, sku_id)
        pl.ltrim('history_%s' % user_id, 0, constants.USER_BROWSING_HISTORY_COUNTS_LIMIT-1)

        # redis管道执行命令
        pl.execute()

        return validated_data


class SKUSerializer(serializers.ModelSerializer):
    """历史记录数据返回序列化器"""
    class Meta:
        model = SKU
        fields = ('id', 'name', 'price', 'default_image_url', 'comments')


