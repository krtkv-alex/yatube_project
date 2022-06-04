from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from posts.models import Group, Post

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовое название',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст'
        )

    def setUp(self):
        self.guest_client = Client()

        self.author_client = Client()
        self.author_client.force_login(self.user)

        self.user_without_post = User.objects.create_user(username='auth')
        self.auth_client = Client()
        self.auth_client.force_login(self.user_without_post)

        cache.clear()

    def test_all_url_available_to_guest(self):
        """Проверка на доступность страниц для гостя."""
        url_available_to_guest = [
            '/',
            f'/group/{self.group.slug}/',
            f'/posts/{self.post.id}/',
            f'/profile/{self.post.author}/'
        ]
        for address in url_available_to_guest:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_page_create_not_auth_user(self):
        """
        Со страницы 'Новая запись' гость должен быть перенаправлен на
        страницу авторизации.
        """
        response = self.guest_client.get('/create/')
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_page_create_auth_user(self):
        """Проверка доступа пользователя к странице 'Новая запись'."""
        response = self.auth_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_page_edit_author_user(self):
        """Проверка доступа автора к странице 'Редактирования поста'."""
        response = self.author_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_page_edit_not_author_user(self):
        """
        Со страницы 'Редактировать пост' пользователь, не являющийся автором
        поста, должен быть перенаправлен на страницу поста.
        """
        response = self.auth_client.get(f'/posts/{self.post.id}/edit/')
        self.assertRedirects(response, f'/posts/{self.post.id}/')

    def test_page_not_found(self):
        """Проверка вызова несуществующей страницы."""
        response = self.guest_client.get('/page_not_found/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/create/': 'posts/post_form.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/profile/{self.post.author}/': 'posts/profile.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.auth_client.get(address)
                self.assertTemplateUsed(response, template)
