# _*_ coding:utf-8 _*_
from django.conf.urls import url
from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register('areas', views.AreasViewSet, base_name='')
urlpatterns = router.urls
