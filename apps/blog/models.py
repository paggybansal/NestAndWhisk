from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


class BlogCategory(TimeStampedModel):
	name = models.CharField(max_length=120, unique=True)
	slug = models.SlugField(max_length=140, unique=True)
	description = models.TextField(blank=True)
	is_active = models.BooleanField(default=True)
	sort_order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["sort_order", "name"]
		verbose_name = "blog category"
		verbose_name_plural = "blog categories"

	def __str__(self) -> str:
		return self.name

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.name)
		super().save(*args, **kwargs)


class BlogPost(TimeStampedModel):
	category = models.ForeignKey(
		BlogCategory,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="posts",
	)
	title = models.CharField(max_length=180)
	slug = models.SlugField(max_length=200, unique=True)
	excerpt = models.CharField(max_length=280)
	body = models.TextField()
	hero_kicker = models.CharField(max_length=120, blank=True)
	reading_time_minutes = models.PositiveSmallIntegerField(default=4)
	is_published = models.BooleanField(default=True)
	is_featured = models.BooleanField(default=False)
	published_at = models.DateTimeField(null=True, blank=True)
	seo_title = models.CharField(max_length=160, blank=True)
	seo_description = models.CharField(max_length=255, blank=True)

	class Meta:
		ordering = ["-published_at", "-created_at"]
		indexes = [
			models.Index(fields=["is_published", "published_at"]),
			models.Index(fields=["slug"]),
		]
		verbose_name = "blog post"
		verbose_name_plural = "blog posts"

	def __str__(self) -> str:
		return self.title

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.title)
		super().save(*args, **kwargs)

	def get_absolute_url(self):
		return reverse("blog:detail", kwargs={"slug": self.slug})
