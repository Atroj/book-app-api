"""
Test for authors API.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework.test import APIClient
from rest_framework import status

from core.models import (
    Author,
    Book
)

from book.serializers import AuthorSerializer

AUTHORS_URL = reverse('book:author-list')


def detail_url(author_id):
    """Create and return author detail URL."""
    return reverse('book:author-detail', args=[author_id])


def create_user(email='user@example.com', password="testpass123"):
    """Create and return user."""
    return get_user_model().objects.create_user(email=email, password=password)


class PublicAuthorsApiTests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving authors."""
        res = self.client.get(AUTHORS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateAuthorsApiTests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_authors(self):
        """Test retrieving a list of authors"""
        Author.objects.create(user=self.user, name='Author 1')
        Author.objects.create(user=self.user, name='Author 2')

        res = self.client.get(AUTHORS_URL)

        authors = Author.objects.all().order_by('-name')
        serializer = AuthorSerializer(authors, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_authors_limited_to_user(self):
        """Test list of authors is limited to authenticated user."""
        user2 = create_user(email="user2@example.com")
        Author.objects.create(user=user2, name='Author 3')
        author = Author.objects.create(user=self.user, name='Author 4')

        res = self.client.get(AUTHORS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], author.name)
        self.assertEqual(res.data[0]['id'], author.id)

    def test_update_author(self):
        """Test updating an author"""
        author = Author.objects.create(user=self.user, name='Author 5')

        payload = {'name': 'Author 6'}
        url = detail_url(author.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        author.refresh_from_db()
        self.assertEqual(author.name, payload['name'])

    def test_delete_author(self):
        """Test deleting an author."""
        author = Author.objects.create(user=self.user, name='Author 7')

        url = detail_url(author.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        authors = Author.objects.filter(user=self.user)
        self.assertFalse(authors.exists())

    def test_filter_authors_assigned_to_books(self):
        """Test listing authors by those assigned to books"""
        author1 = Author.objects.create(user=self.user, name='Author 8')
        author2 = Author.objects.create(user=self.user, name='Author 9')
        book = Book.objects.create(
            title="Title",
            price=Decimal('4.50'),
            user=self.user
        )
        book.authors.add(author1)
        res = self.client.get(AUTHORS_URL, {'assigned_only': 1})

        s1 = AuthorSerializer(author1)
        s2 = AuthorSerializer(author2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_authors_unique(self):
        """Test filtered authors returns a unique list."""
        author1 = Author.objects.create(user=self.user, name='Author 10')
        Author.objects.create(user=self.user, name='Author 11')
        book1 = Book.objects.create(
            title='Title 1',
            price=Decimal('7.00'),
            user=self.user,
        )
        book2 = Book.objects.create(
            title='Title 2',
            price=Decimal('4.00'),
            user=self.user
        )
        book1.authors.add(author1)
        book2.authors.add(author1)

        res = self.client.get(AUTHORS_URL, {'assigned_only': 1})
        self.assertEqual(len(res.data), 1)
