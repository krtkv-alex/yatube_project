from django import forms
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import get_object_or_404
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Follow, Group, Post

User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small_gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовое название',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
            image=cls.uploaded
        )
        cls.templates_pages_names = {
            reverse('posts:index'): (
                'posts/index.html'
            ),
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}): (
                'posts/group_list.html'
            ),
            reverse(
                'posts:profile',
                kwargs={'username': cls.user.username}
            ): 'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': cls.post.id}): (
                'posts/post_detail.html'
            ),
            reverse('posts:post_create'): (
                'posts/post_form.html'
            ),
            reverse('posts:post_edit', kwargs={'post_id': cls.post.id}): (
                'posts/post_form.html'
            )
        }

    def page_obj(self, response):
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, self.post.text)
        self.assertEqual(first_object.group, self.post.group)
        self.assertEqual(first_object.author, self.post.author)
        self.assertEqual(first_object.image, self.post.image)

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.user)

        self.user_without_post = User.objects.create_user(
            username='auth_follower'
        )
        self.auth_follower_client = Client()
        self.auth_follower_client.force_login(self.user_without_post)

        self.user_not_follower = User.objects.create_user(
            username='auth_not_follower'
        )
        self.auth_not_follower_client = Client()
        self.auth_not_follower_client.force_login(self.user_not_follower)

        cache.clear()

    def test_pages_urls_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for reverse_name, template in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index.html сформирован с правильным контекстом."""
        response = self.author_client.get(reverse('posts:index'))
        self.page_obj(response)

    def test_index_page_work_cache(self):
        """Проверим, что кеш работает на главной странице."""
        post_count = Post.objects.count()
        response_before = self.author_client.get(reverse('posts:index'))
        Post.objects.get(id=self.post.id).delete()
        self.page_obj(response_before)
        self.assertEqual(Post.objects.count(), post_count - 1)

        cache.clear()
        response_after = self.author_client.get(reverse('posts:index'))
        self.assertNotEqual(response_before, response_after)

    def test_post_create_page_show_correct_context(self):
        """Шаблон create_post.html сформирован с правильным контекстом."""
        response = self.author_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                from_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(from_field, expected)

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list.html сформирован с правильным контекстом."""
        response = self.author_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertEqual(response.context.get('group').title, self.group.title)
        self.page_obj(response)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail.html сформирован с правильным контекстом."""
        response = self.author_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.context.get('post'), self.post)

    def test_post_edit_page_show_correct_context(self):
        """
        Шаблон create_post.html при редактировании сформирован
        с правильным контекстом.
        """
        response = self.author_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        post = get_object_or_404(Post, id=1)
        self.assertContains(response, post.text)
        self.assertContains(response, post.group)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile.html сформирован с правильным контекстом."""
        response = self.author_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        self.assertEqual(response.context.get('post').author, self.post.author)
        self.page_obj(response)

    def test_follow(self):
        """Пользователь может подписаться на автора контента."""
        follow_count = Follow.objects.count()
        self.auth_follower_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.post.author.username}
            )
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)

    def test_unfollow(self):
        """Пользователь может отписываться от авторов контента."""
        self.auth_follower_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.post.author.username}
            )
        )
        follow_count = Follow.objects.count()
        self.auth_follower_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.post.author.username}
            )
        )
        self.assertEqual(Follow.objects.count(), follow_count - 1)

    def test_for_the_visibility_of_a_post_by_subscribers_and_not(self):
        """Проверка на видимость поста подписчикам и не подписчикам."""
        self.auth_follower_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.post.author.username}
            )
        )
        response_follower = self.auth_follower_client.get(
            reverse('posts:follow_index')
        )
        self.page_obj(response_follower)
        response_not_follower = self.auth_not_follower_client.get(
            reverse('posts:follow_index')
        )
        self.assertNotEqual(response_follower, response_not_follower)


class PaginatorViewsTest(TestCase):
    """Создадим 11 постов и проверим paginator."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовое название',
            slug='test-slug',
            description='Тестовое описание',
        )
        Post.objects.bulk_create(
            Post(
                text=f'Тестовый текст {i}.',
                author=cls.user
            ) for i in range(1, 12)
        )

    def setUp(self):
        cache.clear()

    def test_first_page_contains_ten_records(self):
        """На первой странице отображено 10 постов из 11."""
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_one_records(self):
        """На второй странице отображены оставшиеся страницы."""
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 1)
