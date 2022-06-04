from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовое название',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст'
        )

    def test_object_name_is_text_fild(self):
        """В поле __str__  объекта post записано значение поля post.text."""
        self.assertEqual(self.post.text, str(self.post))

    def test_group_label(self):
        """verbose_name поля group совпадает с ожидаемым."""
        verbose = self.post._meta.get_field('group').verbose_name
        self.assertEqual(verbose, 'группа')

    def test_text_help_text(self):
        """help_text поля text совпадает с ожидаемым."""
        help_text = self.post._meta.get_field('text').help_text
        self.assertEqual(help_text, 'Введите текст поста')
