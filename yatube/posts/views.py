from django.http import HttpResponse

def index(request):
    return HttpResponse('Главная страница проекта Yatube')

def group_posts(request, slug):
    return HttpResponse(f'Все посты группы {slug}')
