# _*_ coding:utf-8 _*_
from rest_framework import serializers
from django_redis import get_redis_connection
import logging

logger = logging.getLogger('django')


class ImageCodeCheckSerializer(serializers.Serializer):
    """图片验证序列化器，用于发送短信前校验"""
    image_code_id = serializers.UUIDField()
    text = serializers.CharField(min_length=4, max_length=4)

    def validate(self, attrs):
        """校验多个字段"""
        # 获取当前传入的验证码
        image_code_id = attrs['image_code_id']
        text = attrs['text']

        # 获取保存在redis中的验证码
        redis_conn = get_redis_connection('verify_codes')
        real_image_code_text = redis_conn.get('img_%s' % image_code_id)
        if not real_image_code_text:
            raise serializers.ValidationError('图片验证码无效!')

        # 防止用户直接请求发短信验证码可以二次使用，我们要删除验证码
        try:
            redis_conn.delete('img_%s' % image_code_id)
        except Exception as e:
            logger.error(e)

        # 进行比较是否输入正确
        real_image_code_text = real_image_code_text.decode()  # 从redis取出的是bytes类型
        if text.lower() != real_image_code_text.lower():
            raise serializers.ValidationError('输入的图片验证码有误!')
        # 防止发送过于频繁
        # 获取手机号
        # 在创建序列化器的时候会创建一个context属性， 传入3个参数request， format， view
        # 在视图类kwargs存放着url解析出来的参数
        mobile = self.context['view'].kwargs['mobile']
        # 定义发送的标记
        send_flag = redis_conn.get('send_flag_%s' % mobile)
        if send_flag:
            raise serializers.ValidationError('操作过于频繁！')
        return attrs



