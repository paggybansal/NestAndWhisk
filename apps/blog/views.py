from django.views.generic import DetailView, ListView

from apps.blog.models import BlogPost
from apps.core.views import CoreContextMixin


class BlogPostListView(CoreContextMixin, ListView):
    template_name = "blog/list.html"
    model = BlogPost
    context_object_name = "posts"
    paginate_by = 9

    def get_queryset(self):
        return BlogPost.objects.filter(is_published=True).select_related("category")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["featured_post"] = BlogPost.objects.filter(is_published=True, is_featured=True).select_related("category").first()
        return context


class BlogPostDetailView(CoreContextMixin, DetailView):
    template_name = "blog/detail.html"
    model = BlogPost
    context_object_name = "post"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return BlogPost.objects.filter(is_published=True).select_related("category")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["related_posts"] = (
            BlogPost.objects.filter(is_published=True)
            .exclude(pk=self.object.pk)
            .select_related("category")[:3]
        )
        return context

