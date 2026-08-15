from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from functools import wraps


def staff_required(view_func):
    """Decorator: requiere is_staff, sino redirige al dashboard."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_staff:
            return redirect('courses:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
from django.views.decorators.http import require_http_methods


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('courses:dashboard')

    if request.method == 'POST':
        credential = request.POST.get('username', '').strip()
        password   = request.POST.get('password', '')

        # Buscar por email primero si contiene '@'
        if '@' in credential:
            try:
                user_obj   = User.objects.get(email__iexact=credential)
                username   = user_obj.username
            except User.DoesNotExist:
                username = credential
        else:
            username = credential

        user = authenticate(request, username=username, password=password)

        # Fallback: si authenticate falla intentar directamente con la credencial
        if user is None and '@' in credential:
            user = authenticate(request, username=credential, password=password)

        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'courses:dashboard')
            return redirect(next_url)
        messages.error(request, 'Correo/usuario o contraseña incorrectos.')

    return render(request, 'accounts/login.html')


@require_http_methods(['GET', 'POST'])
def register_view(request):
    if request.user.is_authenticated:
        return redirect('courses:dashboard')

    from accounts.models import SiteConfig
    if not SiteConfig.get().enable_registration:
        return render(request, 'accounts/register_closed.html')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        email      = request.POST.get('email', '').strip()
        username   = request.POST.get('username', '').strip()
        password1  = request.POST.get('password1', '')
        password2  = request.POST.get('password2', '')

        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Ese nombre de usuario ya está en uso.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Ya existe una cuenta con ese correo.')
        elif len(password1) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name,
            )
            login(request, user)
            return redirect('courses:dashboard')

    return render(request, 'accounts/register.html')


def logout_view(request):
    logout(request)
    return redirect('core:home')


@login_required
@require_http_methods(['GET', 'POST'])
def profile_view(request):
    from accounts.models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'profile':
            first_name = request.POST.get('first_name', '').strip()
            last_name  = request.POST.get('last_name', '').strip()
            email      = request.POST.get('email', '').strip()
            username   = request.POST.get('username', '').strip()

            if not username:
                messages.error(request, 'El nombre de usuario no puede estar vacío.')
            elif User.objects.filter(username=username).exclude(pk=request.user.pk).exists():
                messages.error(request, 'Ese nombre de usuario ya está en uso.')
            elif User.objects.filter(email=email).exclude(pk=request.user.pk).exists():
                messages.error(request, 'Ya existe una cuenta con ese correo electrónico.')
            else:
                request.user.first_name = first_name
                request.user.last_name  = last_name
                request.user.email      = email
                request.user.username   = username
                request.user.save()
                messages.success(request, 'Tus datos han sido actualizados correctamente.')

        elif form_type == 'password':
            current  = request.POST.get('current_password', '')
            new_p1   = request.POST.get('new_password1', '')
            new_p2   = request.POST.get('new_password2', '')

            if not request.user.check_password(current):
                messages.error(request, 'La contraseña actual no es correcta.')
            elif new_p1 != new_p2:
                messages.error(request, 'Las nuevas contraseñas no coinciden.')
            elif len(new_p1) < 8:
                messages.error(request, 'La nueva contraseña debe tener al menos 8 caracteres.')
            else:
                request.user.set_password(new_p1)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Contraseña actualizada correctamente.')

        elif form_type == 'signature':
            sig_data = request.POST.get('signature_data', '').strip()
            profile.signature = sig_data
            profile.save()
            messages.success(request, 'Firma guardada correctamente.')

        elif form_type == 'photo':
            new_photo = request.FILES.get('photo')
            if new_photo:
                import os
                if profile.photo and os.path.isfile(profile.photo.path):
                    os.remove(profile.photo.path)
                profile.photo = new_photo
                profile.save()
                messages.success(request, 'Foto de perfil actualizada.')
            else:
                messages.error(request, 'Selecciona una imagen.')

        return redirect('accounts:profile')

    return render(request, 'accounts/profile.html', {
        'active_nav': 'profile',
        'profile':    profile,
    })


# ─── ADMIN: GESTIÓN DE USUARIOS ─────────────────────────────────

@staff_required
def admin_progress(request):
    from courses.models import Course, Enrollment
    from django.db.models import Prefetch

    courses = Course.objects.filter(is_published=True).order_by('title')
    students = User.objects.filter(
        is_active=True, is_staff=False
    ).prefetch_related(
        Prefetch('enrollments',
                 queryset=Enrollment.objects.select_related('course'),
                 to_attr='course_enrollments')
    ).order_by('first_name', 'last_name', 'username')

    # Build matrix: {student_id: {course_id: enrollment_or_None}}
    matrix = []
    for student in students:
        enr_map = {e.course_id: e for e in student.course_enrollments}
        row = {
            'student': student,
            'cells':   [enr_map.get(c.pk) for c in courses],
        }
        matrix.append(row)

    return render(request, 'accounts/admin_progress.html', {
        'active_nav': 'admin_progress',
        'courses':    courses,
        'matrix':     matrix,
    })


@staff_required
def admin_users(request):
    q      = request.GET.get('q', '').strip()
    filter = request.GET.get('filter', 'all')

    qs = User.objects.annotate(course_count=Count('enrollments')).order_by('-date_joined')

    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q) |
                       Q(first_name__icontains=q) | Q(last_name__icontains=q))
    if filter == 'active':
        qs = qs.filter(is_active=True)
    elif filter == 'inactive':
        qs = qs.filter(is_active=False)
    elif filter == 'staff':
        qs = qs.filter(is_staff=True)

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'accounts/admin_users.html', {
        'active_nav': 'admin_users',
        'page_obj':   page,
        'q':          q,
        'filter':     filter,
        'total':      qs.count(),
        'filters': [
            ('all',      'Todos'),
            ('active',   'Activos'),
            ('inactive', 'Inactivos'),
            ('staff',    'Staff'),
        ],
        'stats': {
            'total':    User.objects.count(),
            'active':   User.objects.filter(is_active=True).count(),
            'staff':    User.objects.filter(is_staff=True).count(),
            'new_week': User.objects.filter(
                date_joined__gte=timezone.now() - timedelta(days=7)
            ).count(),
        },
    })


@staff_required
@require_http_methods(['GET', 'POST'])
def admin_user_form(request, user_id=None):
    editing = user_id is not None
    target  = get_object_or_404(User, pk=user_id) if editing else None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'delete' and editing:
            if target == request.user:
                messages.error(request, 'No puedes eliminar tu propio usuario.')
            else:
                name = target.get_full_name() or target.username
                target.delete()
                messages.success(request, f'Usuario "{name}" eliminado.')
            return redirect('accounts:admin_users')

        # ── Save ──
        first_name  = request.POST.get('first_name', '').strip()
        last_name   = request.POST.get('last_name', '').strip()
        email       = request.POST.get('email', '').strip()
        username    = request.POST.get('username', '').strip()
        is_active   = request.POST.get('is_active') == 'on'
        is_staff    = request.POST.get('is_staff') == 'on'
        is_super    = request.POST.get('is_superuser') == 'on'
        password    = request.POST.get('password', '')

        qs_check = User.objects.exclude(pk=user_id) if editing else User.objects
        if not username:
            messages.error(request, 'El nombre de usuario es obligatorio.')
        elif qs_check.filter(username=username).exists():
            messages.error(request, 'Ese nombre de usuario ya está en uso.')
        elif email and qs_check.filter(email=email).exists():
            messages.error(request, 'Ese correo ya pertenece a otro usuario.')
        else:
            if editing:
                target.first_name   = first_name
                target.last_name    = last_name
                target.email        = email
                target.username     = username
                target.is_active    = is_active
                target.is_staff     = is_staff
                target.is_superuser = is_super
                if password:
                    target.set_password(password)
                target.save()
                messages.success(request, 'Usuario actualizado correctamente.')
                return redirect('accounts:admin_user_edit', user_id=target.pk)
            else:
                if not password:
                    messages.error(request, 'La contraseña es obligatoria para usuarios nuevos.')
                    return render(request, 'accounts/admin_user_form.html', {
                        'active_nav': 'admin_users', 'editing': False, 'target': None,
                    })
                new_user = User.objects.create_user(
                    username=username, email=email, password=password,
                    first_name=first_name, last_name=last_name,
                )
                new_user.is_active    = is_active
                new_user.is_staff     = is_staff
                new_user.is_superuser = is_super
                new_user.save()
                messages.success(request, f'Usuario "{new_user.username}" creado correctamente.')
                return redirect('accounts:admin_user_edit', user_id=new_user.pk)

    return render(request, 'accounts/admin_user_form.html', {
        'active_nav': 'admin_users',
        'editing':    editing,
        'target':     target,
    })


# ─── ADMIN: PLANES DE CAPACITACIÓN ──────────────────────────────

from courses.models import TrainingPlan


@staff_required
def admin_plans(request):
    q  = request.GET.get('q', '').strip()
    qs = TrainingPlan.objects.order_by('name')
    if q:
        qs = qs.filter(name__icontains=q)

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'accounts/admin_plans.html', {
        'active_nav': 'admin_plans',
        'page_obj':   page,
        'q':          q,
        'total':      qs.count(),
        'total_all':  TrainingPlan.objects.count(),
        'active_count': TrainingPlan.objects.filter(is_active=True).count(),
    })


@staff_required
@require_http_methods(['GET', 'POST'])
def admin_plan_form(request, plan_id=None):
    editing = plan_id is not None
    target  = get_object_or_404(TrainingPlan, pk=plan_id) if editing else None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'delete' and editing:
            name = target.name
            target.delete()
            messages.success(request, f'Plan "{name}" eliminado.')
            return redirect('accounts:admin_plans')

        name        = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_active   = request.POST.get('is_active') == 'on'

        if not name:
            messages.error(request, 'El nombre es obligatorio.')
        elif TrainingPlan.objects.filter(name=name).exclude(pk=plan_id).exists():
            messages.error(request, 'Ya existe un plan con ese nombre.')
        else:
            if editing:
                target.name        = name
                target.description = description
                target.is_active   = is_active
                target.save()
                messages.success(request, 'Plan actualizado correctamente.')
                return redirect('accounts:admin_plan_edit', plan_id=target.pk)
            else:
                plan = TrainingPlan.objects.create(
                    name=name, description=description, is_active=is_active
                )
                messages.success(request, f'Plan "{plan.name}" creado correctamente.')
                return redirect('accounts:admin_plan_edit', plan_id=plan.pk)

    return render(request, 'accounts/admin_plan_form.html', {
        'active_nav': 'admin_plans',
        'editing':    editing,
        'target':     target,
    })


# ─── ADMIN: CURSOS ─────────────────────────────────────────

from courses.models import Course


@staff_required
def admin_courses(request):
    q  = request.GET.get('q', '').strip()
    qs = Course.objects.select_related('training_plan').order_by('-created_at')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'accounts/admin_courses.html', {
        'active_nav':     'admin_courses',
        'page_obj':       page,
        'q':              q,
        'total':          qs.count(),
        'total_all':      Course.objects.count(),
        'published_count': Course.objects.filter(is_published=True).count(),
        'free_count':     Course.objects.filter(price=0).count(),
    })


@staff_required
@require_http_methods(['GET', 'POST'])
def admin_course_form(request, course_id=None):
    from django.contrib.auth.models import User as AuthUser
    editing = course_id is not None
    target  = get_object_or_404(Course, pk=course_id) if editing else None
    plans      = TrainingPlan.objects.filter(is_active=True).order_by('name')
    categories = Category.objects.order_by('order', 'name')
    users      = AuthUser.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'delete' and editing:
            name = target.title
            target.delete()
            messages.success(request, f'Curso "{name}" eliminado.')
            return redirect('accounts:admin_courses')

        title         = request.POST.get('title', '').strip()
        description   = request.POST.get('description', '').strip()
        price_raw     = request.POST.get('price', '0').strip() or '0'
        plan_id       = request.POST.get('training_plan') or None
        instructor_id = request.POST.get('instructor') or None
        cat_ids       = request.POST.getlist('categories')
        is_published  = request.POST.get('is_published') == 'on'
        is_featured   = request.POST.get('is_featured') == 'on'
        new_image     = request.FILES.get('featured_image')

        try:
            price = float(price_raw.replace(',', '.'))
            if price < 0:
                raise ValueError
        except ValueError:
            messages.error(request, 'El precio debe ser un número positivo.')
            return render(request, 'accounts/admin_course_form.html', {
                'active_nav': 'admin_courses', 'editing': editing,
                'target': target, 'plans': plans,
            })

        if not title:
            messages.error(request, 'El nombre del curso es obligatorio.')
        else:
            from django.contrib.auth.models import User as AuthUser
            plan       = TrainingPlan.objects.filter(pk=plan_id).first() if plan_id else None
            instructor = AuthUser.objects.filter(pk=instructor_id).first() if instructor_id else request.user

            if editing:
                target.title         = title
                target.description   = description
                target.price         = price
                target.training_plan = plan
                target.instructor    = instructor
                target.is_published  = is_published
                target.is_featured   = is_featured
                if new_image:
                    if target.featured_image and os.path.isfile(target.featured_image.path):
                        os.remove(target.featured_image.path)
                    target.featured_image = new_image
                target.save()
                target.categories.set(Category.objects.filter(pk__in=cat_ids))
                messages.success(request, 'Curso actualizado correctamente.')
                return redirect('accounts:admin_course_edit', course_id=target.pk)
            else:
                course = Course.objects.create(
                    title=title,
                    description=description,
                    price=price,
                    training_plan=plan,
                    is_published=is_published,
                    is_featured=is_featured,
                    instructor=instructor,
                    featured_image=new_image,
                )
                course.categories.set(Category.objects.filter(pk__in=cat_ids))
                messages.success(request, f'Curso "{course.title}" creado correctamente.')
                return redirect('accounts:admin_course_edit', course_id=course.pk)

    return render(request, 'accounts/admin_course_form.html', {
        'active_nav':    'admin_courses',
        'editing':       editing,
        'target':        target,
        'plans':         plans,
        'categories':    categories,
        'users':         users,
        'selected_cats': set(target.categories.values_list('pk', flat=True)) if editing else set(),
    })


# ─── ADMIN: TEMAS ────────────────────────────────────────────

from courses.models import Topic


@staff_required
def admin_topics(request):
    q  = request.GET.get('q', '').strip()
    qs = Topic.objects.select_related('course').order_by('course__title', 'name')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'accounts/admin_topics.html', {
        'active_nav':   'admin_topics',
        'page_obj':     page,
        'q':            q,
        'total':        qs.count(),
        'total_all':    Topic.objects.count(),
        'active_count': Topic.objects.filter(is_active=True).count(),
    })


@staff_required
@require_http_methods(['GET', 'POST'])
def admin_topic_form(request, topic_id=None):
    editing = topic_id is not None
    target  = get_object_or_404(Topic, pk=topic_id) if editing else None
    courses = Course.objects.order_by('title')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'delete' and editing:
            name = target.name
            target.delete()
            messages.success(request, f'Tema "{name}" eliminado.')
            return redirect('accounts:admin_topics')

        name        = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        course_id   = request.POST.get('course') or None
        is_active   = request.POST.get('is_active') == 'on'

        if not name:
            messages.error(request, 'El nombre del tema es obligatorio.')
        else:
            course = Course.objects.filter(pk=course_id).first() if course_id else None
            if editing:
                target.name        = name
                target.description = description
                target.course      = course
                target.is_active   = is_active
                target.save()
                messages.success(request, 'Tema actualizado correctamente.')
                return redirect('accounts:admin_topic_edit', topic_id=target.pk)
            else:
                topic = Topic.objects.create(
                    name=name, description=description,
                    course=course, is_active=is_active
                )
                messages.success(request, f'Tema "{topic.name}" creado correctamente.')
                return redirect('accounts:admin_topic_edit', topic_id=topic.pk)

    return render(request, 'accounts/admin_topic_form.html', {
        'active_nav': 'admin_topics',
        'editing':    editing,
        'target':     target,
        'courses':    courses,
    })


# ─── ADMIN: CLASES ───────────────────────────────────────────

import os
from courses.models import Lesson, LessonAttachment


@staff_required
def admin_lessons(request):
    q  = request.GET.get('q', '').strip()
    qs = Lesson.objects.select_related('course', 'topic').order_by('-created_at')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(content__icontains=q))

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'accounts/admin_lessons.html', {
        'active_nav':   'admin_lessons',
        'page_obj':     page,
        'q':            q,
        'total':        qs.count(),
        'total_all':    Lesson.objects.count(),
        'active_count': Lesson.objects.filter(is_active=True).count(),
    })


@staff_required
@require_http_methods(['GET', 'POST'])
def admin_lesson_form(request, lesson_id=None):
    editing = lesson_id is not None
    target  = get_object_or_404(Lesson, pk=lesson_id) if editing else None
    courses = Course.objects.order_by('title')
    topics  = Topic.objects.select_related('course').order_by('course__title', 'name')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'delete' and editing:
            name = target.title
            target.delete()
            messages.success(request, f'Clase "{name}" eliminada.')
            return redirect('accounts:admin_lessons')

        # Delete selected attachments
        del_ids = request.POST.getlist('delete_attachment')
        if del_ids:
            LessonAttachment.objects.filter(pk__in=del_ids, lesson=target).delete()

        title     = request.POST.get('title', '').strip()
        content   = request.POST.get('content', '').strip()
        course_id = request.POST.get('course') or None
        topic_id  = request.POST.get('topic') or None
        is_active = request.POST.get('is_active') == 'on'

        if not title:
            messages.error(request, 'El título de la clase es obligatorio.')
        else:
            course = Course.objects.filter(pk=course_id).first() if course_id else None
            topic  = Topic.objects.filter(pk=topic_id).first() if topic_id else None

            if editing:
                target.title     = title
                target.content   = content
                target.course    = course
                target.topic     = topic
                target.is_active = is_active
                if 'video' in request.FILES:
                    if target.video:  # remove old video
                        if os.path.isfile(target.video.path):
                            os.remove(target.video.path)
                    target.video = request.FILES['video']
                target.save()
            else:
                target = Lesson.objects.create(
                    title=title, content=content, course=course,
                    topic=topic, is_active=is_active,
                    video=request.FILES.get('video'),
                )

            # Save new attachments
            for f in request.FILES.getlist('attachments'):
                LessonAttachment.objects.create(
                    lesson=target,
                    file=f,
                    name=f.name,
                )

            messages.success(request, 'Clase guardada correctamente.')
            return redirect('accounts:admin_lesson_edit', lesson_id=target.pk)

    return render(request, 'accounts/admin_lesson_form.html', {
        'active_nav': 'admin_lessons',
        'editing':    editing,
        'target':     target,
        'courses':    courses,
        'topics':     topics,
        'attachments': target.attachments.all() if editing else [],
    })


# ─── ADMIN: CATEGORÍAS ───────────────────────────────────────

from courses.models import Category


@staff_required
def admin_categories(request):
    q  = request.GET.get('q', '').strip()
    qs = Category.objects.order_by('order', 'name')
    if q:
        qs = qs.filter(name__icontains=q)

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'accounts/admin_categories.html', {
        'active_nav': 'admin_categories',
        'page_obj':   page,
        'q':          q,
        'total':      qs.count(),
        'total_all':  Category.objects.count(),
    })


@staff_required
@require_http_methods(['GET', 'POST'])
def admin_category_form(request, category_id=None):
    editing = category_id is not None
    target  = get_object_or_404(Category, pk=category_id) if editing else None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'delete' and editing:
            name = target.name
            target.delete()
            messages.success(request, f'Categoría "{name}" eliminada.')
            return redirect('accounts:admin_categories')

        name  = request.POST.get('name', '').strip()
        icon  = request.POST.get('icon', '📚').strip() or '📚'
        order = request.POST.get('order', '0').strip() or '0'

        if not name:
            messages.error(request, 'El nombre de la categoría es obligatorio.')
        elif Category.objects.filter(name=name).exclude(pk=category_id).exists():
            messages.error(request, 'Ya existe una categoría con ese nombre.')
        else:
            try:
                order = int(order)
            except ValueError:
                order = 0

            if editing:
                target.name  = name
                target.icon  = icon
                target.order = order
                target.save()
                messages.success(request, 'Categoría actualizada correctamente.')
                return redirect('accounts:admin_category_edit', category_id=target.pk)
            else:
                cat = Category.objects.create(name=name, icon=icon, order=order)
                messages.success(request, f'Categoría "{cat.name}" creada correctamente.')
                return redirect('accounts:admin_category_edit', category_id=cat.pk)

    return render(request, 'accounts/admin_category_form.html', {
        'active_nav': 'admin_categories',
        'editing':    editing,
        'target':     target,
    })



# ─── ADMIN: EXÁMENES ─────────────────────────────────────────

from courses.models import Exam, Question, Choice


@staff_required
def admin_exams(request):
    q  = request.GET.get('q', '').strip()
    qs = Exam.objects.select_related('course').order_by('-created_at')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(course__title__icontains=q))

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'accounts/admin_exams.html', {
        'active_nav': 'admin_exams',
        'page_obj':   page,
        'q':          q,
        'total':      qs.count(),
        'total_all':  Exam.objects.count(),
        'active_count': Exam.objects.filter(is_active=True).count(),
    })


@staff_required
@require_http_methods(['GET', 'POST'])
def admin_exam_form(request, exam_id=None):
    editing = exam_id is not None
    target  = get_object_or_404(Exam, pk=exam_id) if editing else None
    courses = Course.objects.order_by('title')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'delete' and editing:
            name = target.title
            target.delete()
            messages.success(request, f'Examen "{name}" eliminado.')
            return redirect('accounts:admin_exams')

        title         = request.POST.get('title', '').strip()
        course_id     = request.POST.get('course') or None
        description   = request.POST.get('description', '').strip()
        passing_score = int(request.POST.get('passing_score', 80) or 80)
        is_active     = request.POST.get('is_active') == 'on'

        question_texts = request.POST.getlist('question_text[]')
        question_types = request.POST.getlist('question_type[]')
        options_a      = request.POST.getlist('option_a[]')
        options_b      = request.POST.getlist('option_b[]')
        options_c      = request.POST.getlist('option_c[]')
        corrects       = request.POST.getlist('correct[]')

        if not title:
            messages.error(request, 'El título es obligatorio.')
        elif not course_id:
            messages.error(request, 'Debes seleccionar un curso.')
        elif not question_texts or all(t.strip() == '' for t in question_texts):
            messages.error(request, 'El examen debe tener al menos una pregunta.')
        else:
            course = get_object_or_404(Course, pk=course_id)

            if editing:
                target.title         = title
                target.course        = course
                target.description   = description
                target.passing_score = passing_score
                target.is_active     = is_active
                target.save()
                target.questions.all().delete()
                exam = target
            else:
                if Exam.objects.filter(course_id=course_id).exists():
                    messages.error(request, 'Este curso ya tiene un examen asignado.')
                    return render(request, 'accounts/admin_exam_form.html', {
                        'active_nav': 'admin_exams', 'editing': editing,
                        'target': target, 'courses': courses,
                    })
                exam = Exam.objects.create(
                    title=title, course=course, description=description,
                    passing_score=passing_score, is_active=is_active,
                )

            for i, q_text in enumerate(question_texts):
                q_text = q_text.strip()
                if not q_text:
                    continue
                q_type = question_types[i] if i < len(question_types) else 'multiple'
                question = Question.objects.create(
                    exam=exam, text=q_text, order=i + 1, question_type=q_type
                )
                if q_type == 'upload':
                    continue  # las preguntas de adjunto no tienen opciones
                correct  = corrects[i] if i < len(corrects) else 'A'
                opts = [
                    (options_a[i] if i < len(options_a) else '', 'A'),
                    (options_b[i] if i < len(options_b) else '', 'B'),
                    (options_c[i] if i < len(options_c) else '', 'C'),
                ]
                for j, (opt_text, letter) in enumerate(opts):
                    Choice.objects.create(
                        question=question,
                        text=opt_text.strip() or f'Opción {letter}',
                        is_correct=(letter == correct),
                        order=j + 1,
                    )

            messages.success(request, f'Examen "{exam.title}" {"actualizado" if editing else "creado"} correctamente.')
            return redirect('accounts:admin_exam_edit', exam_id=exam.pk)

    questions_data = []
    if editing:
        for q in target.questions.prefetch_related('choices').order_by('order'):
            choices = list(q.choices.order_by('order'))
            correct = 'A'
            for idx, ch in enumerate(choices):
                if ch.is_correct:
                    correct = ['A', 'B', 'C'][idx] if idx < 3 else 'A'
                    break
            questions_data.append({
                'text': q.text,
                'a': choices[0].text if len(choices) > 0 else '',
                'b': choices[1].text if len(choices) > 1 else '',
                'c': choices[2].text if len(choices) > 2 else '',
                'correct': correct,
            })

    return render(request, 'accounts/admin_exam_form.html', {
        'active_nav':     'admin_exams',
        'editing':        editing,
        'target':         target,
        'courses':        courses,
        'questions_data': questions_data,
    })


# ─── SOPORTE ─────────────────────────────────────────────────────

from accounts.models import SupportTicket, SupportMessage as SupportMsg
from django.http import JsonResponse
import json


@login_required
@require_http_methods(['POST'])
def support_send(request):
    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'ok': False})

    # Obtener o crear ticket abierto del usuario
    ticket = SupportTicket.objects.filter(user=request.user, status='open').first()
    if not ticket:
        ticket = SupportTicket.objects.create(user=request.user)

    SupportMsg.objects.create(
        ticket=ticket,
        author=request.user,
        content=content,
        is_staff_reply=False,
    )
    return JsonResponse({'ok': True})


@login_required
def support_messages(request):
    ticket = SupportTicket.objects.filter(user=request.user, status='open').first()
    msgs = []
    if ticket:
        # Marcar como leídos los mensajes de staff
        ticket.messages.filter(is_staff_reply=True, is_read=False).update(is_read=True)
        for m in ticket.messages.all():
            msgs.append({
                'id':      m.pk,
                'content': m.content,
                'is_staff': m.is_staff_reply,
                'time':    m.created_at.strftime('%H:%M'),
            })
    return JsonResponse({'messages': msgs, 'ticket_id': ticket.pk if ticket else None})


# ─── SOPORTE ADMIN ───────────────────────────────────────────────

@staff_required
def admin_support(request):
    tickets = SupportTicket.objects.select_related('user').prefetch_related('messages').order_by('-updated_at')
    open_count   = tickets.filter(status='open').count()
    unread_count = sum(1 for t in tickets if t.unread_by_staff)
    return render(request, 'accounts/admin_support.html', {
        'active_nav':   'admin_support',
        'tickets':      tickets,
        'open_count':   open_count,
        'unread_count': unread_count,
    })


@staff_required
def admin_support_thread(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, pk=ticket_id)
    # Marcar mensajes del usuario como leídos
    ticket.messages.filter(is_staff_reply=False, is_read=False).update(is_read=True)
    return render(request, 'accounts/admin_support_thread.html', {
        'active_nav': 'admin_support',
        'ticket':     ticket,
        'messages':   ticket.messages.all(),
    })


@staff_required
@require_http_methods(['POST'])
def admin_support_reply(request, ticket_id):
    ticket  = get_object_or_404(SupportTicket, pk=ticket_id)
    content = request.POST.get('content', '').strip()
    action  = request.POST.get('action', '')

    if content:
        SupportMsg.objects.create(
            ticket=ticket,
            author=request.user,
            content=content,
            is_staff_reply=True,
        )

    if action == 'close':
        ticket.status = 'closed'
        ticket.save(update_fields=['status'])

    return redirect('accounts:admin_support_thread', ticket_id=ticket.pk)


# ─── ADMIN: TAREAS ────────────────────────────────────────────

from courses.models import Task


@staff_required
def admin_tasks(request):
    q  = request.GET.get('q', '').strip()
    from django.db.models import Count as _Count
    qs = Task.objects.select_related('lesson', 'lesson__course').annotate(
        submissions_count=_Count('submissions')
    ).order_by('lesson__course__title', 'lesson__title', 'order')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(lesson__title__icontains=q))

    paginator = Paginator(qs, 20)
    page      = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'accounts/admin_tasks.html', {
        'active_nav': 'admin_tasks',
        'page_obj':   page,
        'q':          q,
        'total':      qs.count(),
        'total_all':  Task.objects.count(),
    })


@staff_required
@require_http_methods(['GET', 'POST'])
def admin_task_form(request, task_id=None):
    editing = task_id is not None
    target  = get_object_or_404(Task, pk=task_id) if editing else None
    lessons = Lesson.objects.select_related('course').order_by('course__title', 'title')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete' and editing:
            name = target.title
            target.delete()
            messages.success(request, f'Tarea "{name}" eliminada.')
            return redirect('accounts:admin_tasks')

        title               = request.POST.get('title', '').strip()
        description         = request.POST.get('description', '').strip()
        lesson_id           = request.POST.get('lesson') or None
        order               = int(request.POST.get('order', 0) or 0)
        requires_attachment = request.POST.get('requires_attachment') == 'on'
        is_active           = request.POST.get('is_active') == 'on'

        if not title:
            messages.error(request, 'El nombre es obligatorio.')
        elif not lesson_id:
            messages.error(request, 'Debes seleccionar una clase.')
        else:
            lesson = get_object_or_404(Lesson, pk=lesson_id)
            if editing:
                target.title               = title
                target.description         = description
                target.lesson              = lesson
                target.order               = order
                target.requires_attachment = requires_attachment
                target.is_active           = is_active
                target.save()
                messages.success(request, 'Tarea actualizada.')
                return redirect('accounts:admin_task_edit', task_id=target.pk)
            else:
                task = Task.objects.create(
                    title=title, description=description, lesson=lesson,
                    order=order, requires_attachment=requires_attachment, is_active=is_active,
                )
                messages.success(request, f'Tarea "{task.title}" creada.')
                return redirect('accounts:admin_task_edit', task_id=task.pk)

    return render(request, 'accounts/admin_task_form.html', {
        'active_nav': 'admin_tasks',
        'editing':    editing,
        'target':     target,
        'lessons':    lessons,
    })


@staff_required
def admin_task_submissions(request, task_id):
    task        = get_object_or_404(Task, pk=task_id)
    submissions = task.submissions.select_related('student').order_by('-completed_at')
    return render(request, 'accounts/admin_task_submissions.html', {
        'active_nav':  'admin_tasks',
        'task':        task,
        'submissions': submissions,
    })


# ─── ADMIN: BIBLIOTECA ───────────────────────────────────────────

from courses.models import DocFolder, DocFile


@staff_required
def admin_biblioteca(request, folder_id=None):
    current = DocFolder.objects.get(pk=folder_id) if folder_id else None
    subfolders = DocFolder.objects.filter(parent=current).order_by('order', 'name')
    files      = DocFile.objects.filter(folder=current).order_by('name') if current else []

    return render(request, 'accounts/admin_biblioteca.html', {
        'active_nav':  'admin_biblioteca',
        'current':     current,
        'subfolders':  subfolders,
        'files':       files,
        'breadcrumb':  current.breadcrumb() if current else [],
    })


@staff_required
@require_http_methods(['GET', 'POST'])
def admin_folder_form(request, folder_id=None, parent_folder_id=None):
    editing = folder_id is not None
    target  = get_object_or_404(DocFolder, pk=folder_id) if editing else None

    # parent_folder_id comes from URL for creating subfolder
    parent = None
    if not editing:
        # check referer or kwarg
        parent_id = request.GET.get('parent') or None
        if parent_id:
            parent = DocFolder.objects.filter(pk=parent_id).first()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete' and editing:
            back = target.parent
            target.delete()
            messages.success(request, 'Carpeta eliminada.')
            if back:
                return redirect('accounts:admin_folder', folder_id=back.pk)
            return redirect('accounts:admin_biblioteca')

        name      = request.POST.get('name', '').strip()
        parent_id = request.POST.get('parent_id') or None
        order     = int(request.POST.get('order', 0) or 0)
        parent_obj = DocFolder.objects.filter(pk=parent_id).first() if parent_id else None

        if not name:
            messages.error(request, 'El nombre es obligatorio.')
        else:
            if editing:
                target.name   = name
                target.order  = order
                target.parent = parent_obj
                target.save()
                messages.success(request, 'Carpeta actualizada.')
                return redirect('accounts:admin_folder', folder_id=target.pk)
            else:
                folder = DocFolder.objects.create(name=name, parent=parent_obj, order=order)
                messages.success(request, f'Carpeta "{folder.name}" creada.')
                return redirect('accounts:admin_folder', folder_id=folder.pk)

    folders_all = DocFolder.objects.order_by('name')
    return render(request, 'accounts/admin_folder_form.html', {
        'active_nav':  'admin_biblioteca',
        'editing':     editing,
        'target':      target,
        'parent':      parent or (target.parent if editing else None),
        'folders_all': folders_all,
    })


@staff_required
@require_http_methods(['POST'])
def admin_file_upload(request, folder_id):
    folder = get_object_or_404(DocFolder, pk=folder_id)
    files  = request.FILES.getlist('files')
    for f in files:
        name = request.POST.get('name', f.name).strip() or f.name
        DocFile.objects.create(folder=folder, name=name, file=f)
    messages.success(request, f'{len(files)} archivo(s) subido(s).')
    return redirect('accounts:admin_folder', folder_id=folder.pk)


@staff_required
@require_http_methods(['POST'])
def admin_file_delete(request, file_id):
    doc = get_object_or_404(DocFile, pk=file_id)
    folder_id = doc.folder_id
    doc.file.delete(save=False)
    doc.delete()
    messages.success(request, 'Archivo eliminado.')
    return redirect('accounts:admin_folder', folder_id=folder_id)


# ─── ADMIN: ARTÍCULOS ────────────────────────────────────────────

from courses.models import Article


@staff_required
def admin_articles(request):
    q  = request.GET.get('q', '').strip()
    qs = Article.objects.select_related('author').order_by('-created_at')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q))

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'accounts/admin_articles.html', {
        'active_nav':      'admin_articles',
        'page_obj':        page,
        'q':               q,
        'total_all':       Article.objects.count(),
        'published_count': Article.objects.filter(is_published=True).count(),
    })


@staff_required
@require_http_methods(['GET', 'POST'])
def admin_article_form(request, article_id=None):
    editing = article_id is not None
    target  = get_object_or_404(Article, pk=article_id) if editing else None

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete' and editing:
            target.delete()
            messages.success(request, 'Artículo eliminado.')
            return redirect('accounts:admin_articles')

        title        = request.POST.get('title', '').strip()
        summary      = request.POST.get('summary', '').strip()
        content      = request.POST.get('content', '').strip()
        is_published = request.POST.get('is_published') == 'on'
        new_image    = request.FILES.get('cover_image')

        if not title:
            messages.error(request, 'El título es obligatorio.')
        elif not content:
            messages.error(request, 'El contenido es obligatorio.')
        else:
            if editing:
                target.title        = title
                target.summary      = summary
                target.content      = content
                target.is_published = is_published
                if new_image:
                    import os
                    if target.cover_image and os.path.isfile(target.cover_image.path):
                        os.remove(target.cover_image.path)
                    target.cover_image = new_image
                target.save()
                messages.success(request, 'Artículo actualizado.')
                return redirect('accounts:admin_article_edit', article_id=target.pk)
            else:
                art = Article.objects.create(
                    title=title, summary=summary, content=content,
                    author=request.user, is_published=is_published,
                    cover_image=new_image,
                )
                messages.success(request, f'Artículo "{art.title}" creado.')
                return redirect('accounts:admin_article_edit', article_id=art.pk)

    return render(request, 'accounts/admin_article_form.html', {
        'active_nav': 'admin_articles',
        'editing':    editing,
        'target':     target,
    })


# ─── ADMIN: CONFIGURACIÓN GENERAL ───────────────────────────────

from accounts.models import SiteConfig


@staff_required
@require_http_methods(['GET', 'POST'])
def admin_config(request):
    config = SiteConfig.get()

    if request.method == 'POST':
        config.enable_registration = request.POST.get('enable_registration') == 'on'
        config.site_name           = request.POST.get('site_name', 'Nooxial').strip() or 'Nooxial'
        config.maintenance_mode    = request.POST.get('maintenance_mode') == 'on'
        config.save()
        messages.success(request, 'Configuración guardada correctamente.')
        return redirect('accounts:admin_config')

    return render(request, 'accounts/admin_config.html', {
        'active_nav': 'admin_config',
        'config':     config,
    })
