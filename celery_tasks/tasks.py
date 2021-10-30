# 使用celery
from celery import Celery, shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template import loader, RequestContext

# 创建一个Celery类的实例对象
app = Celery('celery_tasks.tasks', broker='redis://192.168.31.24:6379/8')

import os
# import django
#
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
# django.setup()
from goods.models import GoodsType, GoodsSKU, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
from django_redis import get_redis_connection


@app.task
def send_register_active_email(to_email, username, token):
    """发送激活邮件"""
    # 组织邮件信息
    subject = '天天生鲜欢迎信息'  # 邮件标题
    message = ''  # 邮件正文
    sender = settings.EMAIL_FROM  # 邮件发送者
    receiver = [to_email]  # 邮件接收者, 可以是多个, 所以这是个列表
    html_message = '<h3>亲爱的用户%s,感谢您注册天天生鲜</h3>' \
                   '<p>请点击<a href="http://127.0.0.1:8000/user/active/%s">激活</a>以进行用户激活</p>' % (username, token)
    send_mail(subject, message, sender, receiver, html_message=html_message)


@app.task
def generate_static_index_html():
    
    types = GoodsType.objects.all()

    # 获取首页轮播商品信息
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')

    # 获取首页促销活动信息
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品展示信息
    for type in types:  # GoodsType
        # 获取type种类首页分类商品的图片展示信息
        image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
        # 获取type种类首页分类商品的文字展示信息
        title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

        # 动态给type增加属性，分别保存首页分类商品的图片展示信息和文字展示信息
        type.image_banners = image_banners
        type.title_banners = title_banners

    context = {'types': types,
               'goods_banners': goods_banners,
               'promotion_banners': promotion_banners}



    # 使用模板
    # 1. 加载模板文件
    temp = loader.get_template('dailyfresh/static_index.html')
    # 2. 定义模板上下文
    # context = RequestContext(request, context)
    # 3. 模板渲染
    static_index_html = temp.render(context)

    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w') as f:
        f.write(static_index_html)

