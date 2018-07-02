# _*_ coding:utf-8 _*_
from rest_framework import serializers

from goods.models import SKU


class CartSerializer(serializers.Serializer):
    sku_id = serializers.IntegerField(label='sku id ', min_value=1)
    count = serializers.IntegerField(label='数量', min_value=1)
    selected = serializers.BooleanField(label='是否勾选', default=True)

    def validate(self, attrs):
        try:
            sku = SKU.objects.get(id=attrs['sku_id'])
        except SKU.DoesNotExist:
            raise serializers.ValidationError('商品不存在')
        if attrs['count'] > sku.stock:
            raise serializers.ValidationError('库存不足')
        return attrs


class CartSKUSerializer(serializers.ModelSerializer):
    count = serializers.IntegerField(label='数量')
    selected = serializers.BooleanField(label='是否勾选')
    class Meta:
        model = SKU
        fields = ('id', 'count', 'selected', 'name', 'default_image_url', 'price')


class CartDeleteSerializer(serializers.Serializer):
    """删除购物车校验数据序列化器"""
    sku_id = serializers.IntegerField(label='商品的id')

    def validate_sku_id(self, value):
        # 获取商品数据
        try:
            sku = SKU.objects.get(id=value)
        except SKU.DoesNotExist:
            raise serializers.ValidationError('商品不存在')
        return value


