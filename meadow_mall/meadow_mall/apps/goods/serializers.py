# _*_ coding:utf-8 _*_

from rest_framework import serializers
from drf_haystack.serializers import HaystackSerializer

from .models import SKU
from .search_indexes import SKUIndex


class SKUSerializer(serializers.ModelSerializer):
    """历史记录数据返回序列化器"""
    class Meta:
        model = SKU
        fields = ('id', 'name', 'price', 'default_image_url', 'comments')


class SKUIndexSerializer(HaystackSerializer):
    """
    SKU索引结果数据序列化器
    """
    class Meta:
        index_classes = [SKUIndex]
        fields = ('text', 'id', 'name', 'price', 'default_image_url', 'comments')
