from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.decorators import login_required

@login_required
def profile_view(request):
    # Временная заглушка для профиля
    return render(request, 'profile.html')

def home(request):
    # Стартовая страница — приветствие
    if request.user.is_authenticated:
        return redirect('index')  # Если пользователь авторизован, перенаправляем на главную
    return render(request, 'home.html')

def index(request):
    # Главная страница магазина с каталогом
    return render(request, 'index.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Проверка, что поля не пустые
        if not username or not password:
            messages.error(request, 'Имя пользователя и пароль не могут быть пустыми')
            return render(request, 'login.html')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('index')  # Редирект на главную страницу (index.html)
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    return render(request, 'login.html')

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('index')  # Перенаправление после выхода

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Проверка на пустые поля
        if not username or not email or not password:
            messages.error(request, 'Все поля должны быть заполнены')
            return render(request, 'register.html')

        # Проверка на наличие пользователя с таким именем
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь с таким именем уже существует')
            return render(request, 'register.html')

        # Проверка на корректность email
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Некорректный email')
            return render(request, 'register.html')

        # Создание нового пользователя
        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)  # Авторизация сразу после регистрации
        return redirect('home')  # Перенаправление на страницу приветствия (home)
    return render(request, 'register.html')
