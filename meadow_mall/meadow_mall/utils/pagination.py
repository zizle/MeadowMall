# _*_ coding:utf-8 _*_
# 自定义全局分类配置
from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 2  # 默认每页的显示条数
    page_query_param = 'page_size'
    max_page_size = 20  # 每页最大的可设置条数