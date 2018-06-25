from django.shortcuts import render
from rest_framework.views import APIView
from django_redis import get_redis_connection
from django.http import HttpResponse
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
import random
import logging

from meadow_mall.libs.captcha.captcha import captcha
from meadow_mall.utils.yuntongxun.sms import CCP
from . import constants
from .serializers import ImageCodeCheckSerializer
from celery_tasks.sms.tasks import send_sms_code
# Create your views here.
# 记录日志者
logger = logging.getLogger('django')


# url(r'/image_codes/(?P<image_code_id>[\w-]+)/')
class ImageCodeView(APIView):
    """图片验证码"""
    def get(self, request, image_code_id):
        """生成图片验证码返回"""
        # url完成接收uuid，校验uuid
        # 生成图片验证码
        text, image = captcha.generate_captcha()
        # 保存到redis
        redis_conn = get_redis_connection('verify_codes')
        redis_conn.setex('img_%s' % image_code_id, constants.IMAGE_CODE_REDIS_EXPIRES, text)
        # 返回给前端
        print('图片验证码:', text)
        return HttpResponse(image, content_type="image/jpg")  # 返回类型如果是images浏览器会直接下载


# url(/sms_codes/(?P<mobile>1[3-9]\d{9})/?image_code_id=xxx&text=xxx)
class SMSCodeView(GenericAPIView):
    """短信验证码"""
    # 实例化序列化器
    serializer_class = ImageCodeCheckSerializer

    def get(self, request, mobile):
        """发送短信验证码"""
        # 接收参数， 视图自己完成了
        # 校验参数
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        # 生成短信验码
        sms_code = '%06d' % random.randint(0, 999999)
        # 保存短信验证码与发送的记录
        redis_conn = get_redis_connection('verify_codes')
        # 以下与redis网络通信过于频繁，引入管道
        # redis_conn.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        # redis_conn.setex('send_flag_%s' % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)  # 随意保存一个值，我们并不关心它是什么

        pl = redis_conn.pipeline()  # 连接对象中取出管道
        pl.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        pl.setex('send_flag_%s' % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)  # 随意保存一个值，我们并不关心它是什么
        # 将保存在管道中的任务一次执行完
        pl.execute()
        # try:
        #     # 发送短信
        #     expires = constants.SMS_CODE_REDIS_EXPIRES // 60  # 短信有效期
        #     result = CCP().send_template_sms(mobile, [sms_code, expires], 1)
        # except Exception as e:
        #     logger.error("发送验证码短信[异常][ mobile: %s, message: %s ]" % (mobile, e))
        #     return Response({'message': 'failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # else:
        #     if result == 0:
        #         logger.info("发送验证码短信[正常][ mobile: %s ]" % mobile)
        #         print(sms_code)
        #         return Response({'message': 'OK'})
        #     else:
        #         logger.warning("发送验证码短信[失败][ mobile: %s ]" % mobile)
        #         return Response({'message': 'failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 使用celery异步任务发送短信
        expires = constants.SMS_CODE_REDIS_EXPIRES // 60  # 短信有效期
        temp_id = constants.SMS_CODE_TEMP_ID  # 短信模板
        send_sms_code.delay(mobile, sms_code, expires, temp_id)  ##  程序直接死在这，不知道为什么
        return Response({'message': 'OK'})

