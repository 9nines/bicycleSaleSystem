"""dailyfresh URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    # url(r'^tinymce/', include('tinymce.urls')),  # 富文本编辑器
    url(r'^ckeditor/', include('ckeditor_uploader.urls'), name='ckeditor'),  # 富文本编辑器
    url(r'search/', include('haystack.urls'), name='haystack'),  # 全文检索框架
    url(r'^user/', include('user.urls'), name='user'),  # 用户模块
    url(r'^cart/', include('cart.urls'), name='cart'),  # 购物车模块
    url(r'^order/', include('order.urls'), name='order'),  # 订单模块
    url(r'^', include('goods.urls'), name='goods'),  # 商品模块
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # 没有这一句无法显示上传的图片
