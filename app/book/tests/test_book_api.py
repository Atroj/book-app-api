"""
Tests for book APIs.
"""

from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Book,
    Tag,
    Author)

from book.serializers import (
    BookSerializer,
    BookDetailSerializer)

BOOKS_URL = reverse('book:book-list')


def detail_url(book_id):
    """Create and return a book detail URL."""
    return reverse('book:book-detail', args=[book_id])


def image_upload_url(book_id):
    """Create and return and image upload URL."""
    return reverse('book:book-upload-image', args=[book_id])


def create_book(user, **params):
    """Create and return sample book."""
    defaults = {
        'title': 'Title 1',
        'price': Decimal('5.25'),
        'description': 'Sample description',
        'link': 'http://example.com/book.pdf'
    }
    book = Book.objects.create(user=user, **defaults)
    return book


def create_user(**params):
    """Create and return new user."""
    return get_user_model().objects.create_user(**params)


class PublicBookAPITests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(BOOKS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateBookAPITests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='user@example.com',
            password='password123',
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_books(self):
        """Test retrieving a list of books."""
        create_book(user=self.user)
        create_book(user=self.user)

        res = self.client.get(BOOKS_URL)

        books = Book.objects.all().order_by('-id')
        serializer = BookSerializer(books, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_book_list_limited_to_user(self):
        """Test list of books is limited to authenticated user"""
        other_user = create_user(
            email='other@example.com',
            password='password123'
        )

        create_book(other_user)
        create_book(user=self.user)

        res = self.client.get(BOOKS_URL)
        books = Book.objects.filter(user=self.user)
        serializer = BookSerializer(books, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_book_detail(self):
        """Test get book detail."""
        book = create_book(user=self.user)

        url = detail_url(book.id)
        res = self.client.get(url)

        serializer = BookDetailSerializer(book)

        self.assertEqual(res.data, serializer.data)

    def test_create_book(self):
        """Test creating a book"""
        payload = {
            'title': 'Book 2',
            'price': Decimal('5.99')
        }
        res = self.client.post(BOOKS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        book = Book.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(book, k), v)
        self.assertEqual(book.user, self.user)

    def test_partial_update(self):
        """Test partial update for a book"""
        original_link = 'http://example.com/book.pdf'
        book = create_book(
            user=self.user,
            title='title',
            link=original_link
        )
        payload = {'title': 'Book 3'}
        url = detail_url(book.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        book.refresh_from_db()
        self.assertEqual(book.title, payload['title'])
        self.assertEqual(book.link, original_link)
        self.assertEqual(book.user, self.user)

    def test_full_update(self):
        """Test full update for book."""
        book = create_book(
            user=self.user,
            title='Book 4',
            link='http://example.com/book.pdf',
            description='Sample book description'
        )

        payload = {
            'title': 'Book 5',
            'link': 'http://example.com/new-book.pdf',
            'description': 'New book descripton',
            'price': Decimal('2.50')

        }
        url = detail_url(book.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        book.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(book, k), v)
        self.assertEqual(book.user, self.user)

    def test_update_user_returns_error(self):
        """Test changing the book user results in error"""
        new_user = create_user(email='user2@example.com', password='test123')
        book = create_book(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(book.id)
        self.client.get(url, payload)

        book.refresh_from_db()
        self.assertEqual(book.user, self.user)

    def test_delete_book(self):
        """Test deleting a book"""
        book = create_book(user=self.user)

        url = detail_url(book.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Book.objects.filter(id=book.id).exists())

    def test_book_other_users_book_error(self):
        """Test trying to delete another users book gives error."""
        new_user = create_user(email='user2@example.com', password='test123')
        book = create_book(user=new_user)

        url = detail_url(book.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Book.objects.filter(id=book.id).exists())

    def test_create_book_with_new_tags(self):
        """Test creating a book with new tags."""
        payload = {
            'title': 'Book 6',
            'price': Decimal('2.50'),
            'tags': [{'name': 'Tag 1'}, {'name': 'Tag 2'}]
        }
        res = self.client.post(BOOKS_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        books = Book.objects.filter(user=self.user)
        book = books[0]

        self.assertEqual(book.tags.count(), 2)
        for tag in payload['tags']:
            exists = book.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_book_with_existing_tags(self):
        """Test creating book with existing tag."""
        tag_indian = Tag.objects.create(user=self.user, name='Tag 3')
        payload = {
            'title': 'Book 7',
            'price': Decimal(4.50),
            'tags': [{'name': 'Tag 3'}, {'name': 'Tag 4'}]

        }
        res = self.client.post(BOOKS_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        books = Book.objects.filter(user=self.user)
        self.assertEqual(books.count(), 1)
        book = books[0]
        self.assertEqual(book.tags.count(), 2)
        self.assertIn(tag_indian, book.tags.all())
        for tag in payload['tags']:
            exists = book.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """Test creating tag when updating a book"""
        book = create_book(user=self.user)

        payload = {'tags': [{'name': 'Tag 6'}]}
        url = detail_url(book.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Tag 6')
        self.assertIn(new_tag, book.tags.all())

    def test_update_book_assign_tag(self):
        """Test assigning an existing tag when updating a book"""
        tag_1 = Tag.objects.create(user=self.user, name='Tag 8')
        book = create_book(user=self.user)
        book.tags.add(tag_1)

        tag_2 = Tag.objects.create(user=self.user, name='Tag 9')
        payload = {'tags': [{'name': 'Tag 8'}]}
        url = detail_url(book.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_1, book.tags.all())
        self.assertNotIn(tag_2, book.tags.all())

    def test_clear_book_tags(self):
        """Test clearing books"""
        tag = Tag.objects.create(user=self.user, name='tag 11')
        book = create_book(user=self.user)
        book.tags.add(tag)

        payload = {'tags': []}
        url = detail_url(book.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(book.tags.count(), 0)

    def test_create_book_with_new_authors(self):
        """Test creating new book with new authors."""
        payload = {
            'title': 'Book 8',
            'price': Decimal('4.30'),
            'authors': [{'name': 'Author 1'}, {'name': 'Author 2'}],

        }
        res = self.client.post(BOOKS_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        books = Book.objects.filter(user=self.user)
        self.assertEqual(books.count(), 1)
        book = books[0]
        self.assertEqual(book.authors.count(), 2)
        for author in payload['authors']:
            exists = book.authors.filter(
                name=author['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_book_with_existing_author(self):
        """Test creating a new book with existing author"""
        author = Author.objects.create(user=self.user, name='Author 3')
        payload = {
            'title': 'Vietnamese Soup',
            'price': '2.55',
            'authors': [{'name': 'Author 3'}, {'name': 'Author 4'}],
        }
        res = self.client.post(BOOKS_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        books = Book.objects.filter(user=self.user)
        self.assertEqual(books.count(), 1)
        book = books[0]
        self.assertEqual(book.authors.count(), 2)
        self.assertIn(author, book.authors.all())
        for author in payload['authors']:
            exists = book.authors.filter(
                name=author['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_author_on_update(self):
        """Test creating an author when updating the book"""
        book = create_book(user=self.user)
        payload = {'authors': [{'name': 'Author 5'}]}
        url = detail_url(book.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_author = Author.objects.get(user=self.user, name='Author 5')
        self.assertIn(new_author, book.authors.all())

    def test_update_book_assign_author(self):
        """Test assigning an existing author when updating a book"""
        author1 = Author.objects.create(user=self.user, name="Author 6")
        book = create_book(user=self.user)
        book.authors.add(author1)

        author2 = Author.objects.create(user=self.user, name='Author 7')
        payload = {'authors': [{'name': 'Author 7'}]}
        url = detail_url(book.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(author2, book.authors.all())
        self.assertNotIn(author1, book.authors.all())

    def test_clear_book_authors(self):
        """Test clearing a books authors"""
        author = Author.objects.create(user=self.user, name='Author 8')
        book = create_book(user=self.user)
        book.authors.add(author)

        payload = {'authors': []}
        url = detail_url(book.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(book.authors.count(), 0)

    def test_filter_by_tags(self):
        """Test filtering by tags."""
        r1 = create_book(user=self.user, title='Book 9')
        r2 = create_book(user=self.user, title='Book 10')
        tag1 = Tag.objects.create(user=self.user, name='Tag 12')
        tag2 = Tag.objects.create(user=self.user, name='Tag 13')
        r1.tags.add(tag1)
        r2.tags.add(tag2)
        r3 = create_book(user=self.user, title='Fish and chips')

        params = {'tags': f'{tag1.id},{tag2.id}'}
        res = self.client.get(BOOKS_URL, params)

        s1 = BookSerializer(r1)
        s2 = BookSerializer(r2)
        s3 = BookSerializer(r3)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_authors(self):
        """Test filtering books by authors."""
        r1 = create_book(user=self.user, title='Book 9')
        r2 = create_book(user=self.user, title='Book 10')
        in1 = Author.objects.create(user=self.user, name='Author 12')
        in2 = Author.objects.create(user=self.user, name='Author 13')
        r1.authors.add(in1)
        r2.authors.add(in2)
        r3 = create_book(user=self.user, title='Book 11')

        params = {'authors': f'{in1.id},{in2.id}'}
        res = self.client.get(BOOKS_URL, params)

        s1 = BookSerializer(r1)
        s2 = BookSerializer(r2)
        s3 = BookSerializer(r3)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTests(TestCase):
    """Tests for the image upload API."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'password123',
        )
        self.client.force_authenticate(self.user)
        self.book = create_book(user=self.user)

    def tearDown(self):
        self.book.image.delete()

    def test_upload_image(self):
        """Test uploading an image to a book."""
        url = image_upload_url(self.book.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.book.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.book.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image."""
        url = image_upload_url(self.book.id)
        payload = {'image': 'notanimage'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
