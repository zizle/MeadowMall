from django.shortcuts import render
from rest_framework.generics import ListAPIView
from rest_framework.filters import OrderingFilter
from drf_haystack.viewsets import HaystackViewSet

from . import serializers
from .models import SKU


# Create your views here.
class SKUListView(ListAPIView):
    """sku列表数据"""
    serializer_class = serializers.SKUSerializer
    # 排序
    filter_backends = (OrderingFilter,)
    ordering_fields = ('create_time', 'price', 'sales')
    #分页

    def get_queryset(self):
        """获取查询集"""
        category_id = self.kwargs['category_id']
        return SKU.objects.filter(category_id=category_id, is_launched=True)


class SKUSearchViewSet(HaystackViewSet):
    """sku搜引"""
    index_models = [SKU]
    serializer_class = serializers.SKUIndexSerializer