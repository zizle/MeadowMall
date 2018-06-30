from django.shortcuts import render
from rest_framework.generics import ListAPIView




# Create your views here.
class SKUListView(ListAPIView):
    """sku列表数据"""
    pass

    def get_queryset(self):
        pass
