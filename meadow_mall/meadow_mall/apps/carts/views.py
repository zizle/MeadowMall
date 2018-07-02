from django.shortcuts import render
from rest_framework.generics import GenericAPIView
from django_redis import get_redis_connection
from rest_framework.response import Response
import pickle
import base64
from rest_framework import status

from . import serializers
from . import constants
from goods.models import SKU


class CartView(GenericAPIView):
    serializer_class = serializers.CartSerializer

    def perform_authentication(self, request):
        pass

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sku_id = serializer.validated_data.get('sku_id')
        count = serializer.validated_data.get('count')
        selected = serializer.validated_data.get('selected')
        # 判断用户登录状态
        try:
            user = request.user
        except Exception:
            user = None

        if user and user.is_authenticated:
            # 保存数据到数据库
            # 连接redis
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            # 构造hash数据
            # 用户购物车数据 redis hash
            """
            redis数据类型：
            哈希：
            {cart_用户1: {商品1：count}, {商品2：count}, ...}
            集合：
            {selected_用户1:商品1， 商品2， ...}
            
            存储：
                哈希：
                    hincrby(key, field, increment)  key 的 filed 属性 增加 increment
                集合：
                    sadd(key, member)  key增加成员，可以增加多个[member1, member2, ...]
            """

            pl.hincrby('cart_%s' % user.id, sku_id, count)
            if selected:
                # 是否勾选  redis  set
                pl.sadd('cart_selected_%s' % user.id, sku_id)
            pl.execute()
            return Response(serializer.data)

        else:
            # 查看当前cookie中的购物车数据
            cart = request.COOKIES.get('cart')

            if cart:
                # 解析cookie数据
                cart_bytes = base64.b64decode(cart.encode())
                cart_dict = pickle.loads(cart_bytes)
            # 如果不存在进行设置
            else:
                cart_dict = {}
            if sku_id in cart_dict:
                # 如果存在就累加
                cart_dict[sku_id]['count'] += count
                cart_dict[sku_id]['selected'] = selected
            else:
                # 不存在就设置cookie
                cart_dict[sku_id] = {
                    'count': count,
                    'selected': selected,
                }
            # 设置cookie
            cart_cookie = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response = Response(serializer.data)
            response.set_cookie('cart', cart_cookie, max_age=constants.CART_COOKIE_EXPIRES)
            # 返回数据
            return response

    def get(self, request):
        """购物车数据"""
        # 获取用户的登录状态
        try:
            user = request.user
        except Exception:
            user = None
        # 登录的用户从redis中获取数据
        if user and user.is_authenticated:
            # 从redis中获取数据
            """
            
            cart_1: {
                sku_id: 2,
                count: 3
            }
            selected_1:{selected_1: True}
            
            构造为：
            sku_id:{count: count, selected: selected}
            
            """
            redis_conn = get_redis_connection('carts')
            redis_cart = redis_conn.hgetall('cart_%s' % user.id)
            redis_selected = redis_conn.smembers('cart_selected_%s' % user.id)
            # 调整数据
            cart_dict = {}
            for sku_id, count in redis_cart.items():
                cart_dict[int(sku_id)] = {
                    'count': count,
                    'selected': sku_id in redis_selected
                }
        # 未登录的用户从cookie中获取数据
        else:
            cookie_cart = request.COOKIES.get('cart')
            if cookie_cart:
                # 解析cookie
                """
                cart_dict = {
                    sku_id : 1,
                    selected: True
                }
                """
                cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))
            else:
                cart_dict = {}

        # 查出所有的购物车数据
        skus = SKU.objects.filter(id__in=cart_dict.keys())
        # 遍历商品
        for sku in skus:
            sku.count = cart_dict[sku.id]['count']
            sku.selected = cart_dict[sku.id]['selected']
        # 序列化
        # 创建序列化器
        serializer = serializers.CartSKUSerializer(skus, many=True)
        return Response(serializer.data)

    def put(self, request):
        """购物车修改"""
        # 接收参数和校验
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 校验成功的数据
        sku_id = serializer.validated_data['sku_id']
        count = serializer.validated_data['count']
        selected = serializer.validated_data['selected']
        # 判断用户的登录状态
        try:
            user = request.user
        except Exception:
            user = None
        if user and user.is_authenticated:
            # 已登录用户操作redis
            redis_conn = get_redis_connection('carts')
            # 获取redis中的数据
            pl = redis_conn.pipeline()
            pl.hset('cart_%s' % user.id, sku_id, count)
            if selected:
                pl.sadd('cart_selected_%s' % user.id, sku_id)
            else:
                pl.srem('cart_selected_%s' % user.id, sku_id)
            pl.execute()
            return Response(serializer.data)
        # 未登录用户操作cookie
        else:
            # 获取cookie
            cart_cookies = request.COOKIES.get('cart')

            if cart_cookies:
                # 解析cookie
               cart_dict = pickle.loads(base64.b64decode(cart_cookies.encode()))
            else:
                cart_dict = {}
            # 修改cookie值
            for sku_id in cart_dict:
                cart_dict[sku_id] = {
                    'count': count,
                    'selected': selected
                }
            # 设置响应对象
            response = Response(serializer.data)
            # 设置cookie返回
            cart_cookie = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('cart', cart_cookie, max_age=constants.CART_COOKIE_EXPIRES)
            return response

    def delete(self, request):
        """删除购物车数据"""
        # 获取参数，校验
        serializer = serializers.CartDeleteSerializer(data=request.data)
        serializer.is_valid()
        sku_id = serializer.validated_data['sku_id']
        try:
            user = request.user
        except Exception:
            user = None
        # 已登录用户删除redis
        if user and user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            # 修改redis中的数据
            pl = redis_conn.pipeline()
            pl.hdel('cart_%s' % user.id, sku_id)
            pl.srem('cart_selected_%s' % user.id, sku_id)
            pl.execute()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            response = Response(status=status.HTTP_204_NO_CONTENT)
            # 未登录用户删除cookie
            cart_cookie = request.COOKIES.get('cart')
            if cart_cookie:
                # 解析
                cart_dict = pickle.loads(base64.b64decode(cart_cookie.encode()))
                if sku_id in cart_dict:
                    # 修改
                    del cart_dict[sku_id]
                # 设置cookie
                    cookie_cart = base64.b64encode(pickle.dumps(cart_dict)).decode()
                response.set_cookie('cart', cookie_cart, max_age=constants.CART_COOKIE_EXPIRES)
                return response
