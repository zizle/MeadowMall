from django.shortcuts import render
from rest_framework.generics import GenericAPIView
from django_redis import get_redis_connection
from rest_framework.response import Response
import pickle
import base64

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
                pl.sadd('cart_%s' % user.id, sku_id)
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
            redis_conn = get_redis_connection('cart')
            redis_cart = redis_conn.hgetall('cart_%s' % user.id)
            redis_selected = redis_conn.smember('cart_selected_%s' % user.id)
            # 调整数据
            cart_dict = {}
            for sku_id, count in redis_cart:
                cart_dict[sku_id] = {
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

