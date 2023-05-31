"""
Serializers from book APIs.
"""
from rest_framework import serializers
from core.models import (Book, Tag, Author)


class AuthorSerializer(serializers.ModelSerializer):
    """Serializer for authors"""

    class Meta:
        model = Author
        fields = ['id', 'name']
        read_only_fields = ['id']


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tags"""

    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']


class BookSerializer(serializers.ModelSerializer):
    """Serializer for books."""
    tags = TagSerializer(many=True, required=False)
    authors = AuthorSerializer(many=True, required=False)

    class Meta:
        model = Book
        fields = ['id', 'title', 'price', 'link', 'tags', 'authors']
        read_only_fields = ['id']

    def _get_or_create_tags(self, tags, book):
        """Handle getting or creating tags as needed"""
        auth_user = self.context['request'].user
        for tag in tags:
            tag_obj, created = Tag.objects.get_or_create(
                user=auth_user,
                **tag
            )
            book.tags.add(tag_obj)

    def _get_or_create_authors(self, authors, book):
        """Handle getting or creating authors as needed."""
        auth_user = self.context['request'].user
        for author in authors:
            author_obj, create = Author.objects.get_or_create(
                user=auth_user,
                **author,
            )
            book.authors.add(author_obj)

    def create(self, validated_data):
        """Create a book"""
        tags = validated_data.pop('tags', [])
        authors = validated_data.pop('authors', [])
        book = Book.objects.create(**validated_data)
        self._get_or_create_tags(tags, book)
        self._get_or_create_authors(authors, book)
        return book

    def update(self, instance, validated_data):
        """Update book."""
        tags = validated_data.pop('tags', None)
        authors = validated_data.pop('authors', None)

        if tags is not None:
            instance.tags.clear()
            self._get_or_create_tags(tags, instance)
        if authors is not None:
            instance.authors.clear()
            self._get_or_create_authors(authors, instance)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class BookDetailSerializer(BookSerializer):
    """Serializer for book detail"""

    class Meta(BookSerializer.Meta):
        fields = BookSerializer.Meta.fields + ['description', 'image']


class BookImageSerializer(serializers.ModelSerializer):
    """Serializer for uploading images and books"""

    class Meta:
        model = Book
        fields = ['id', 'image']
        read_only_fields = ['id']
        extra_kwargs = {'image': {'required': 'True'}}
