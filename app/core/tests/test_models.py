"""
Tests for modules
"""
from unittest.mock import patch
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from core import models


def create_user(email="user@exasmple.com", password="testpass123"):
    """Create and return a new user."""
    return get_user_model().objects.create_user(email, password)


class ModelTest(TestCase):
    """Test models"""

    def test_create_user_with_email_successful(self):
        """Test creating a user with and email is successful."""
        email = 'test@examplle.com'
        password = 'testpass123'
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )
        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email(self):
        """Test email is normalized for new users."""
        sample_emails = [
            ['test1@EXAMPLE.COM', 'test1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com'],
            ['test4@example.COM', 'test4@example.com']
        ]
        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email, 'sample123')
            self.assertEqual(user.email, expected)

    def test_new_user_without_user_raises_error(self):
        """Test that creating a user without an email raises a ValueError."""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', 'test123')

    def test_create_super_user(self):
        """Test creating superuser"""
        user = get_user_model().objects.create_superuser(
            'test@example.com',
            'test123',
        )
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_book(self):
        """Test creating a book is successful."""
        user = get_user_model().objects.create_user(
            'test@example.com',
            'test123'
        )

        book = models.Book.objects.create(
            user=user,
            title='Sample book title',
            price=Decimal('5.50'),
            description="Sample book description"
        )

        self.assertEqual(str(book), book.title)

    def test_create_tag(self):
        """Test creating a tag is successfully."""
        user = create_user()
        tag = models.Tag.objects.create(user=user, name='Tag1')
        self.assertEqual(str(tag), tag.name)

    def test_create_authors(self):
        """Test creating an authors is successful."""
        user = create_user()
        author = models.Author.objects.create(
            user=user,
            name='Author1'
        )

        self.assertEqual((str(author)), author.name)

    @patch('core.models.uuid.uuid4')
    def test_book_file_name_uuid(self, mock_uuid):
        """Test generating image path"""
        uuid = 'test-uuid'
        mock_uuid.return_value = uuid
        file_path = models.book_image_file_path(None, 'example.jpg')

        self.assertEqual(file_path, f'uploads/book/{uuid}.jpg')
