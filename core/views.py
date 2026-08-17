from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Count, Q, Avg
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from courses.models import Course, Category, Enrollment, Article, ArticleComment


def home(request):
    categories = Category.objects.annotate(
        course_count=Count('tagged_courses', filter=Q(tagged_courses__is_published=True))
    ).order_by('order', 'name')

    featured_courses = Course.objects.filter(
        is_featured=True, is_published=True
    ).prefetch_related('categories').annotate(
        avg_rating=Avg('reviews__rating'),
        enrollment_count=Count('enrollments'),
    ).order_by('-created_at')[:6]

    stats = {
        'courses_count':     Course.objects.filter(is_published=True).count(),
        'students_count':    User.objects.filter(is_active=True, is_staff=False).count(),
        'instructors_count': User.objects.filter(is_active=True, courses_taught__is_published=True).distinct().count(),
        'enrollments_count': Enrollment.objects.count(),
    }

    from accounts.models import PlatformRating
    happy_ratings = (PlatformRating.objects
                     .filter(rating='happy')
                     .select_related('user')
                     .order_by('-created_at')[:60])

    return render(request, 'core/home.html', {
        'categories':       categories,
        'featured_courses': featured_courses,
        'stats':            stats,
        'happy_ratings':    happy_ratings,
    })


def talent_list(request):
    """Listado público de currículums marcados como públicos."""
    from accounts.models import UserProfile
    q = request.GET.get('q', '').strip()
    profiles = UserProfile.objects.filter(
        cv_public=True
    ).exclude(
        cv_headline='', cv_summary='', cv_experience='', cv_education='', cv_skills=''
    ).select_related('user', 'company').order_by('user__first_name', 'user__last_name')
    if q:
        from django.db.models import Q
        profiles = profiles.filter(
            Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) |
            Q(cv_headline__icontains=q) | Q(cv_skills__icontains=q) |
            Q(company__name__icontains=q)
        )
    return render(request, 'core/talent_list.html', {'profiles': profiles, 'q': q})


@require_http_methods(['POST'])
def contact_view(request):
    first_name = request.POST.get('first_name', '').strip()
    last_name  = request.POST.get('last_name', '').strip()
    email      = request.POST.get('email', '').strip()
    phone      = request.POST.get('phone', '').strip()
    company    = request.POST.get('company', '').strip()
    position   = request.POST.get('position', '').strip()
    message    = request.POST.get('message', '').strip()

    if not first_name or not email:
        messages.error(request, 'El nombre y el email son obligatorios.')
        return redirect('core:home' + '#contacto')

    # Guardar en BD
    from accounts.models import Contact
    contact = Contact.objects.create(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        company=company,
        position=position,
        message=message,
    )

    # Enviar email de confirmación al contacto
    from accounts.views import _get_email_connection
    from accounts.models import SiteConfig
    from django.core.mail import EmailMessage
    conn, from_email = _get_email_connection()
    cfg = SiteConfig.get()
    if conn is not None:
        subject = f'Hemos recibido tu mensaje – {cfg.site_name}'
        body = (
            f'Hola {contact.full_name},\n\n'
            f'Gracias por ponerte en contacto con nosotros. Hemos recibido tu mensaje y te '
            f'responderemos lo antes posible.\n\n'
            f'{'—' * 40}\n'
            f'{message}\n'
            f'{'—' * 40}\n\n'
            f'Un saludo,\n'
            f'El equipo de {cfg.site_name}'
        )
        try:
            EmailMessage(subject, body, from_email, [email], connection=conn).send()
        except Exception:
            pass

    messages.success(request, '¡Mensaje enviado! Te contactaremos pronto.')
    return redirect('core:home')



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

