from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import View
from utils.mixin import LoginRequiredMixin
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.conf import settings
from user.models import User, Address
from goods.models import GoodsSKU
from order.models import OrderInfo, OrderGoods
from celery_tasks.tasks import send_register_active_email
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django_redis import get_redis_connection
import re


# Create your views here.


def register(request):
    """用户注册"""
    if request.method == 'POST':
        # 1. 获取用户数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        cpassword = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 2. 数据校验

        # 判断用户是否正确输入数据
        if not all([username, password, cpassword, email]):
            return render(request, 'dailyfresh/register.html', {"errormsg": "数据格式不正确！！！"})
        # 判断用户输入的邮箱是否合法
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'dailyfresh/register.html', {"errormsg", "邮箱格式不正确！！！"})
        # 判断用户两次输入的密码是否一样
        if password != cpassword:
            return render(request, 'dailyfresh/register.html', {"errormsg": "两次输入的密码不一样！！！"})
        # 判断用户是否同意用户协议
        if allow != 'on':
            return render(request, 'dailyfresh/register.html', {"errormsg": "请同意用户协议！！！"})

        # 3. 数据处理

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None

        if user:
            return render(request, 'dailyfresh/register.html', {"errormsg": "用户已存在，请重新输入！！！"})

        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()
        # 4. 返回应答

        return redirect(reverse('goods:index'))
    if request.method == 'GET':
        return render(request, 'dailyfresh/register.html')


def register_handle(request):
    """用户注册处理"""
    # 1. 获取用户数据
    username = request.POST.get('user_name')
    password = request.POST.get('pwd')
    cpassword = request.POST.get('cpwd')
    email = request.POST.get('email')
    allow = request.POST.get('allow')

    # 2. 数据校验

    # 判断用户是否正确输入数据
    if not all([username, password, cpassword, email]):
        return render(request, 'dailyfresh/register.html', {"errormsg": "数据格式不正确！！！"})
    # 判断用户输入的邮箱是否合法
    if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
        return render(request, 'dailyfresh/register.html', {"errormsg", "邮箱格式不正确！！！"})
    # 判断用户两次输入的密码是否一样
    if password != cpassword:
        return render(request, 'dailyfresh/register.html', {"errormsg": "两次输入的密码不一样！！！"})
    # 判断用户是否同意用户协议
    if allow != 'on':
        return render(request, 'dailyfresh/register.html', {"errormsg": "请同意用户协议！！！"})

    # 3. 数据处理

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = None

    if user:
        return render(request, 'dailyfresh/register.html', {"errormsg": "用户已存在，请重新输入！！！"})

    user = User.objects.create_user(username, email, password)
    user.is_active = 0
    user.save()
    # 4. 返回应答

    return redirect(reverse('goods:index'))


class RegisterView(View):
    """注册类"""

    def get(self, request):
        """显示注册页面"""
        return render(request, 'dailyfresh/register.html')

    def post(self, request):
        """注册处理页"""
        # 1. 获取用户数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        cpassword = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 2. 数据校验

        # 判断用户是否正确输入数据
        if not all([username, password, cpassword, email]):
            return render(request, 'dailyfresh/register.html', {"errormsg": "数据不完整！！！"})
        # 判断用户输入的邮箱是否合法
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'dailyfresh/register.html', {"errormsg", "邮箱格式不正确！！！"})
        # 判断用户两次输入的密码是否一样
        if password != cpassword:
            return render(request, 'dailyfresh/register.html', {"errormsg": "两次输入的密码不一样！！！"})
        # 判断用户是否同意用户协议
        if allow != 'on':
            return render(request, 'dailyfresh/register.html', {"errormsg": "请同意用户协议！！！"})

        # 3. 业务处理:数据校验

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None

        if user:
            return render(request, 'dailyfresh/register.html', {"errormsg": "用户已存在，请重新输入！！！"})

        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()

        # 发送激活邮件，包含激活链接：http://127.0.0.1:8000/user/active/3
        # 激活链接中需要包含用户的身份信息,并且要把身份信息进行加密
        # 加密用户的身份信息， 生成激活token
        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {'confirm': user.id}
        token = serializer.dumps(info)
        token = token.decode()

        # 发邮件
        send_register_active_email.delay(email, username, token)
        # 4. 返回应答

        return redirect(reverse('goods:index'))


class ActiveView(View):
    def get(self, request, token):
        """进行用户激活"""
        # 进行解密，获取激活的用户信息
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            # 获取待激活的用户id
            user_id = info['confirm']

            # 根据id获取用户信息
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()

            # 跳转至登录页面
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            # 激活链接已过期
            return HttpResponse('激活链接已过期')


class LoginView(View):
    """登录页面"""

    def get(self, request):
        """显示登录页面"""
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'dailyfresh/login.html', {"username": username, "checked": checked})

    def post(self, request):
        """登录校验"""
        # 1. 接收数据
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        # 2. 数据校验
        if not all([username, password]):
            return render(request, 'dailyfresh/login.html', {"errormsg": "数据不完整"})
        # 3. 业务处理:数据校验
        user = authenticate(username=username, password=password)
        if user is not None:
            # 用户名密码正确
            if user.is_active:
                # 用户已激活
                login(request, user)
                remember = request.POST.get('remember')
                # 获取登录后所要跳转的网址
                # 默认跳转到首页
                next_url = request.GET.get('next', reverse('goods:index'))
                # 跳转至首页
                response = redirect(next_url)
                # 判断是否需要记住用户名
                if remember == 'on':
                    # 用户需要记住用户名
                    response.set_cookie('username', username, max_age=7 * 24 * 3600)
                else:
                    response.delete_cookie('username')
                # 4. 返回应答
                return response
            else:
                # 用户未激活
                return render(request, 'dailyfresh/login.html', {"errormsg": "用户未激活"})
        else:
            return render(request, 'dailyfresh/login.html', {"errormsg": "用户名或密码错误"})


class LogoutView(View):
    """退出用户登录"""

    def get(self, request):
        """退出登录"""
        # 清除用户的session信息
        logout(request)
        # 跳转到登录页
        return redirect(reverse('user:login'))


class UserInfoView(LoginRequiredMixin, View):
    """用户信息类"""

    def get(self, request):
        """用户中心信息页"""
        # page = 'user'
        # request.user
        # 如果用户未登录->AnonymousUser类的一个实例
        # 如果用户已登录->User类的一个实例
        # request.user.is_authenticated()

        # 获取用户的个人信息
        user = request.user
        address = Address.objects.get_default_address(user)

        # 获取用户的最近浏览信息
        # from redis import StrictRedis
        # sr = StrictRedis(host='192.168.188.119', port='6379', db=9)

        con = get_redis_connection('default')
        history_key = 'history_%d' % user.id

        # 获取用户最新浏览的5个商品的id
        sku_ids = con.lrange(history_key, 0, 4)  # [2, 3, 1]
        # 从数据库中查询用户浏览的商品的具体信息
        # goods_li = GoodsSKU.objects.filter(id__in=sku_ids)
        # goods_res = []
        # for a_id in sku_ids:
        #     for goods in goods_li:
        #         if a_id == goods.id:
        #             goods_res.append(goods)
        # 遍历获取用户浏览的商品信息
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)
        context = {"page": "user", "address": address, "goods_li": goods_li}
        return render(request, 'dailyfresh/user_center_info.html', context)


# /user/order
class UserOrderView(LoginRequiredMixin, View):
    """用户中心-信息页"""

    def get(self, request, page):
        """显示"""
        # 获取用户的订单信息
        user = request.user
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')

        # 便利获取订单商品的信息
        for order in orders:
            # 根据order_id查询订单商品信息
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)

            # 便利order_skus计算商品的小计
            for order_sku in order_skus:
                # 计算小计
                amount = order_sku.count * order_sku.price
                # 动态给order_sku增加属性amount，保存订单商品的小计
                order_sku.amount = amount
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            # 动态给order增加属性，保存订单商品的信息
            order.order_skus = order_skus

        # 分页
        paginator = Paginator(orders, 1)

        # 获取第page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1

        # 获取第page页的Page实例对象
        order_page = paginator.page(page)

        # todo: 进行页码的控制，页面上最多显示5个页码
        # 1.总页数小于5页，页面上显示所有页码
        # 2.如果当前页是前3页，显示1-5页
        # 3.如果当前页是后3页，显示后5页
        # 4.其他情况，显示当前页的前2页，当前页，当前页的后2页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        # print(order_page)
        # 组织上下文
        context = {'order_page': order_page,
                   'pages': pages,
                   'orders': orders}

        return render(request, 'dailyfresh/user_center_order.html', context)


class AddressView(LoginRequiredMixin, View):
    """用户信息类"""

    def get(self, request):
        """用户中心信息页"""
        # page = address

        # 获取登录用户对应的User对象
        user = request.user
        # 获取用户的默认收货地址
        address = Address.objects.get_default_address(user)

        return render(request, 'dailyfresh/user_center_site.html', {"page": "address", "address": address})

    def post(self, request):
        """地址添加"""
        # 接收数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        # 校验数据
        # 数据完整性校验
        if not all([receiver, addr, phone]):
            # 数据不完整
            return render(request, 'dailyfresh/user_center_site.html', {"errormsg": "数据不完整"})
        # 校验手机号
        if not re.match(r"^1[3|4|5|7|8][0-9]{9}$", phone):
            return render(request, 'dailyfresh/user_center_site.html', {"errormsg": "手机号格式不正确"})

        # 业务处理：地址添加
        # 如果用户已存在默认收货地址，添加的地址不作为默认收货地址，否则作为默认收货地址
        # 获取登录用户对应的User对象
        user = request.user

        address = Address.objects.get_default_address(user)

        if address:
            is_default = False
        else:
            is_default = True
        # 添加地址
        Address.objects.create(
            user=user,
            receiver=receiver,
            addr=addr,
            zip_code=zip_code,
            phone=phone,
            is_default=is_default
        )
        # 返回应答
        # 刷新地址页面
        return redirect(reverse('user:address'))  # 刷新收货地址
