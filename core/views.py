from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Count, Q, Avg
from django.contrib.auth.models import User
from courses.models import Course, Category, Enrollment, Article, ArticleComment


def home(request):
    categories = Category.objects.annotate(
        course_count=Count('tagged_courses', filter=Q(tagged_courses__is_published=True))
    ).order_by('order', 'name')

    featured_courses = Course.objects.filter(
        is_featured=True, is_published=True
    ).prefetch_related('categories').annotate(avg_rating=Avg('reviews__rating')).order_by('-created_at')[:6]

    stats = {
        'courses_count':     Course.objects.filter(is_published=True).count(),
        'students_count':    User.objects.filter(is_active=True, is_staff=False).count(),
        'instructors_count': User.objects.filter(is_active=True, courses_taught__is_published=True).distinct().count(),
        'enrollments_count': Enrollment.objects.count(),
    }

    return render(request, 'core/home.html', {
        'categories':       categories,
        'featured_courses': featured_courses,
        'stats':            stats,
    })


def blog_list(request):
    articles = Article.objects.filter(is_published=True).select_related('author').order_by('-created_at')
    return render(request, 'core/blog_list.html', {'articles': articles})


def blog_detail(request, slug):
    article  = get_object_or_404(Article, slug=slug, is_published=True)
    related  = Article.objects.filter(is_published=True).exclude(pk=article.pk).order_by('-created_at')[:3]
    comments = article.comments.select_related('author', 'author__profile').all()
    return render(request, 'core/blog_detail.html', {
        'article':  article,
        'related':  related,
        'comments': comments,
    })


@login_required
@require_POST
def blog_comment(request, slug):
    article = get_object_or_404(Article, slug=slug, is_published=True)
    content = request.POST.get('content', '').strip()
    if content:
        ArticleComment.objects.create(article=article, author=request.user, content=content)
    return redirect(f'/blog/{slug}/#comentarios')

