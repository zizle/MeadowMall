# _*_ coding:utf-8 _*_

# 创建模型基类

from django.db import models


class BaseModel(models.Model):
    """为模型类补充字段"""
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    class Meta:
        abstract = True # 说明是抽象模型类，迁移时不会创建这个表
