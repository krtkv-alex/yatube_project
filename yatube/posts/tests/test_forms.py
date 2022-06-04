import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.forms import PostForm
from posts.models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовое название',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст'
        )
        cls.form = PostForm()
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()

        self.author_client = Client()
        self.author_client.force_login(self.user)

        self.user_without_post = User.objects.create_user(username='auth')
        self.auth_client = Client()
        self.auth_client.force_login(self.user_without_post)

    def test_post_create(self):
        """Проверяем, что создается новая запись."""
        post_count = Post.objects.count()
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=self.small_gif,
            content_type='image/gif'
        )
        response = self.author_client.post(
            reverse('posts:post_create'),
            data={
                'text': 'Проверка на создание поста',
                'image': uploaded
            },
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        self.assertTrue(
            Post.objects.filter(
                text='Проверка на создание поста',
                image='posts/small.gif'
            ).exists()
        )

    def test_post_create_form_is_not_valid(self):
        """Проверяем, что запись не создается, если форма не валидна."""
        post_count = Post.objects.count()
        response = self.author_client.post(
            reverse('posts:post_create'),
            data={'text': ' '},
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count)
        self.assertFormError(
            response,
            'form',
            'text',
            'Обязательное поле.'
        )
        self.assertEqual(response.status_code, 200)

    def test_post_edit_author(self):
        """Проверим, может ли автор поста его редактировать."""
        post_count = Post.objects.count()
        response = self.author_client.post(
            reverse('posts:post_edit', kwargs={'post_id': 1}),
            data={'text': 'Изменим тестовый текст.'},
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count)
        self.assertContains(response, 'Изменим тестовый текст.')

    def test_post_create_not_author(self):
        """Проверим, может ли не автор поста его редактировать."""
        response = self.auth_client.post(
            reverse('posts:post_edit', kwargs={'post_id': 1}),
            data={'text': 'Изменим тестовый текст.'},
            follow=True
        )
        self.assertContains(response, 'Тестовый текст')

    def test_add_comment_autn_user(self):
        """Проверим, может ли пользователь оставлять комментарии."""
        comment_count = Comment.objects.count()
        response = self.auth_client.post(
            reverse('posts:add_comment', kwargs={'post_id': 1}),
            data={
                'author': self.user,
                'post': self.post,
                'text': 'Тестовый комментарий.'
            },
            follow=True
        )
        self.assertContains(response, 'Тестовый комментарий.')
        self.assertEqual(Comment.objects.count(), comment_count + 1)

    def test_add_comment_guest(self):
        """Проверим, может ли гость оставлять комментарии."""
        comment_count = Comment.objects.count()
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': 1}),
            data={
                'author': self.user,
                'post': self.post,
                'text': 'Тестовый комментарий.'
            },
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comment_count)
