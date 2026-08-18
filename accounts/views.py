from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Max as _Max
from django.core.paginator import Paginator
from django.http import JsonResponse
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
from django.views.decorators.http import require_http_methods, require_POST


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('courses:dashboard')

    saved_username = request.COOKIES.get('nooxial_remember_user', '')
    remember_me    = bool(saved_username)

    if request.method == 'POST':
        credential  = request.POST.get('username', '').strip()
        password    = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me') == 'on'

        # Buscar por email primero si contiene '@'
        if '@' in credential:
            try:
                user_obj = User.objects.get(email__iexact=credential)
                username = user_obj.username
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
            if remember_me:
                # Sesión dura 30 días
                request.session.set_expiry(30 * 24 * 60 * 60)
            else:
                # Sesión expira al cerrar el navegador
                request.session.set_expiry(0)
            next_url = request.GET.get('next', 'courses:dashboard')
            response = redirect(next_url)
            if remember_me:
                # Guardar usuario en cookie (30 días)
                response.set_cookie(
                    'nooxial_remember_user', credential,
                    max_age=30 * 24 * 60 * 60,
                    httponly=True, samesite='Lax',
                )
            else:
                response.delete_cookie('nooxial_remember_user')
            return response
        messages.error(request, 'Correo/usuario o contraseña incorrectos.')

    return render(request, 'accounts/login.html', {
        'saved_username': saved_username,
        'remember_me':    remember_me,
    })


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
            # Enviar email de bienvenida si está activado
            _send_welcome_email(user)
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

        elif form_type == 'cv':
            profile.cv_headline   = request.POST.get('cv_headline', '').strip()
            profile.cv_phone      = request.POST.get('cv_phone', '').strip()
            profile.cv_linkedin   = request.POST.get('cv_linkedin', '').strip()
            profile.cv_instagram  = request.POST.get('cv_instagram', '').strip()
            profile.cv_facebook   = request.POST.get('cv_facebook', '').strip()
            profile.cv_tiktok     = request.POST.get('cv_tiktok', '').strip()
            profile.cv_github     = request.POST.get('cv_github', '').strip()
            profile.cv_summary    = request.POST.get('cv_summary', '').strip()
            profile.cv_experience = request.POST.get('cv_experience', '').strip()
            profile.cv_education  = request.POST.get('cv_education', '').strip()
            profile.cv_skills     = request.POST.get('cv_skills', '').strip()
            profile.cv_public     = request.POST.get('cv_public') == '1'
            profile.save(update_fields=['cv_headline','cv_phone','cv_linkedin','cv_instagram',
                                        'cv_facebook','cv_tiktok','cv_github','cv_summary','cv_experience',
                                        'cv_education','cv_skills','cv_public'])
            messages.success(request, 'Currículum actualizado.')

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

    qs = User.objects.annotate(course_count=Count('enrollments')).select_related('profile__company').order_by('-date_joined')

    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q) |
                       Q(first_name__icontains=q) | Q(last_name__icontains=q))
    if filter == 'active':
        qs = qs.filter(is_active=True)
    elif filter == 'inactive':
        qs = qs.filter(is_active=False)
    elif filter == 'staff':
        qs = qs.filter(is_staff=True)

    paginator = Paginator(qs, 10)
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
    from accounts.models import Company
    editing  = user_id is not None
    target   = get_object_or_404(User, pk=user_id) if editing else None
    companies = Company.objects.order_by('name')

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
                # Empresa
                company_id = request.POST.get('company') or None
                from accounts.models import Company
                profile, _ = target.profile.__class__.objects.get_or_create(user=target)
                profile.company = Company.objects.filter(pk=company_id).first() if company_id else None
                profile.save()
                messages.success(request, 'Usuario actualizado correctamente.')
                return redirect('accounts:admin_user_edit', user_id=target.pk)
            else:
                if not password:
                    messages.error(request, 'La contraseña es obligatoria para usuarios nuevos.')
                    return render(request, 'accounts/admin_user_form.html', {
                        'active_nav': 'admin_users', 'editing': False, 'target': None,
                        'companies': companies,
                    })
                new_user = User.objects.create_user(
                    username=username, email=email, password=password,
                    first_name=first_name, last_name=last_name,
                )
                new_user.is_active    = is_active
                new_user.is_staff     = is_staff
                new_user.is_superuser = is_super
                new_user.save()
                # Empresa
                company_id = request.POST.get('company') or None
                from accounts.models import Company
                profile, _ = new_user.profile.__class__.objects.get_or_create(user=new_user)
                profile.company = Company.objects.filter(pk=company_id).first() if company_id else None
                profile.save()
                messages.success(request, f'Usuario "{new_user.username}" creado correctamente.')
                return redirect('accounts:admin_user_edit', user_id=new_user.pk)

    return render(request, 'accounts/admin_user_form.html', {
        'active_nav': 'admin_users',
        'editing':    editing,
        'target':     target,
        'companies':  companies,
    })


# ─── ADMIN: EMPRESAS ─────────────────────────────────────────────

@staff_required
def admin_companies(request):
    from accounts.models import Company
    q  = request.GET.get('q', '').strip()
    qs = Company.objects.order_by('name')
    if q:
        qs = qs.filter(name__icontains=q)
    paginator = Paginator(qs, 20)
    page      = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'accounts/admin_companies.html', {
        'active_nav': 'admin_companies',
        'page_obj':   page,
        'q':          q,
        'total':      qs.count(),
    })


@staff_required
@require_http_methods(['GET', 'POST'])
def admin_company_form(request, company_id=None):
    from accounts.models import Company
    editing = company_id is not None
    target  = get_object_or_404(Company, pk=company_id) if editing else None

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete' and editing:
            name = target.name
            target.delete()
            messages.success(request, f'Empresa "{name}" eliminada.')
            return redirect('accounts:admin_companies')

        name    = request.POST.get('name', '').strip()
        email   = request.POST.get('email', '').strip()
        phone   = request.POST.get('phone', '').strip()
        web     = request.POST.get('web', '').strip()
        address = request.POST.get('address', '').strip()
        nif     = request.POST.get('nif', '').strip()

        if not name:
            messages.error(request, 'El nombre de la empresa es obligatorio.')
        else:
            if editing:
                target.name    = name
                target.email   = email
                target.phone   = phone
                target.web     = web
                target.address = address
                target.nif     = nif
                target.save()
                messages.success(request, 'Empresa actualizada correctamente.')
                return redirect('accounts:admin_company_edit', company_id=target.pk)
            else:
                company = Company.objects.create(
                    name=name, email=email, phone=phone,
                    web=web, address=address, nif=nif,
                )
                messages.success(request, f'Empresa "{company.name}" creada correctamente.')
                return redirect('accounts:admin_company_edit', company_id=company.pk)

    from courses.models import TrainingPlan
    training_plans = TrainingPlan.objects.all().order_by('name') if editing else []
    return render(request, 'accounts/admin_company_form.html', {
        'active_nav': 'admin_companies',
        'editing':    editing,
        'target':     target,
        'training_plans': training_plans,
        'attendances': target.attendances.order_by('-created_at') if editing else [],
    })


# ─── DASHBOARD PÚBLICO DE EMPRESA ────────────────────────────────

@require_http_methods(['GET', 'POST'])
def company_register(request, token):
    """Registro de usuario vinculado a una empresa mediante token."""
    from accounts.models import Company, UserProfile
    company = get_object_or_404(Company, public_token=token)

    if request.user.is_authenticated:
        # Si ya está autenticado, asignarlo a la empresa si no tiene
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if profile.company is None:
            profile.company = company
            profile.save(update_fields=['company'])
        return redirect('accounts:company_dashboard', token=token)

    reg_errors = []
    reg_data   = {}

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        email      = request.POST.get('email', '').strip()
        username   = request.POST.get('username', '').strip()
        password1  = request.POST.get('password1', '')
        password2  = request.POST.get('password2', '')
        reg_data   = {'first_name': first_name, 'last_name': last_name,
                      'email': email, 'username': username}

        if password1 != password2:
            reg_errors.append('Las contraseñas no coinciden.')
        elif User.objects.filter(username=username).exists():
            reg_errors.append('Ese nombre de usuario ya está en uso.')
        elif email and User.objects.filter(email=email).exists():
            reg_errors.append('Ya existe una cuenta con ese correo.')
        elif len(password1) < 8:
            reg_errors.append('La contraseña debe tener al menos 8 caracteres.')
        elif not username:
            reg_errors.append('El nombre de usuario es obligatorio.')
        else:
            new_user = User.objects.create_user(
                username=username, email=email, password=password1,
                first_name=first_name, last_name=last_name,
            )
            # Login PRIMERO — dispara update_last_login → user.save() → signal
            # que guardará el perfil sin empresa (aún no asignada).
            # Luego asignamos empresa en un save separado, que ya no será sobreescrito.
            _send_welcome_email(new_user)
            login(request, new_user)
            # Asignar empresa DESPUÉS de login para evitar que el signal la sobreescriba
            profile, _ = UserProfile.objects.get_or_create(user=new_user)
            profile.company = company
            profile.save(update_fields=['company'])
            return redirect('accounts:company_dashboard', token=token)

    # GET o errores: renderizar el dashboard con el formulario
    return _render_company_dashboard(request, company, reg_errors=reg_errors, reg_data=reg_data)


def _render_company_dashboard(request, company, reg_errors=None, reg_data=None):
    """Renderiza el dashboard de empresa, reutilizado por company_dashboard y company_register."""
    from courses.models import (
        Enrollment, LessonProgress, ExamAttempt, TaskSubmission
    )
    from django.db.models import Count, Avg
    from django.utils import timezone
    from datetime import timedelta

    profiles    = company.users.select_related('user').all()
    students    = [p.user for p in profiles]
    student_ids = [u.pk for u in students]

    kpis     = {}
    rankings = {}
    student_stats = []

    if student_ids:
        total_enrollments  = Enrollment.objects.filter(student_id__in=student_ids).count()
        completed_courses  = Enrollment.objects.filter(student_id__in=student_ids, progress=100).count()
        total_lessons_done = LessonProgress.objects.filter(student_id__in=student_ids).count()
        exams_passed       = ExamAttempt.objects.filter(student_id__in=student_ids, passed=True).count()
        exams_total        = ExamAttempt.objects.filter(student_id__in=student_ids).count()
        tasks_submitted    = TaskSubmission.objects.filter(student_id__in=student_ids).count()
        avg_progress       = Enrollment.objects.filter(student_id__in=student_ids).aggregate(avg=Avg('progress'))['avg'] or 0
        avg_exam_score     = ExamAttempt.objects.filter(student_id__in=student_ids).aggregate(avg=Avg('score'))['avg'] or 0
        active_30d         = User.objects.filter(
            pk__in=student_ids,
            last_login__gte=timezone.now() - timedelta(days=30)
        ).count()

        kpis = {
            'total_students':     len(students),
            'active_30d':         active_30d,
            'total_enrollments':  total_enrollments,
            'completed_courses':  completed_courses,
            'total_lessons_done': total_lessons_done,
            'exams_passed':       exams_passed,
            'exam_pass_rate':     round(exams_passed / exams_total * 100) if exams_total else 0,
            'tasks_submitted':    tasks_submitted,
            'avg_progress':       round(avg_progress, 1),
            'avg_exam_score':     round(avg_exam_score, 1),
        }

        user_map = {u.pk: u for u in students}

        def enrich(qs, extra_keys=None):
            result = []
            for row in qs:
                u = user_map.get(row['student_id'])
                if u:
                    entry = {'user': u, 'total': row['total']}
                    if extra_keys:
                        for k in extra_keys:
                            entry[k] = row.get(k)
                    result.append(entry)
            return result

        rankings = {
            'lessons': enrich(
                LessonProgress.objects.filter(student_id__in=student_ids)
                .values('student_id').annotate(total=Count('id')).order_by('-total')[:10]
            ),
            'courses': enrich(
                Enrollment.objects.filter(student_id__in=student_ids, progress=100)
                .values('student_id').annotate(total=Count('id')).order_by('-total')[:10]
            ),
            'exams': enrich(
                ExamAttempt.objects.filter(student_id__in=student_ids, passed=True)
                .values('student_id').annotate(total=Count('id'), avg_score=Avg('score'))
                .order_by('-total', '-avg_score')[:10],
                extra_keys=['avg_score']
            ),
            'tasks': enrich(
                TaskSubmission.objects.filter(student_id__in=student_ids)
                .values('student_id').annotate(total=Count('id')).order_by('-total')[:10]
            ),
        }

        for u in students:
            avg_prog = Enrollment.objects.filter(student=u).aggregate(a=Avg('progress'))['a'] or 0
            student_stats.append({
                'user':         u,
                'enrollments':  Enrollment.objects.filter(student=u).count(),
                'completed':    Enrollment.objects.filter(student=u, progress=100).count(),
                'lessons':      LessonProgress.objects.filter(student=u).count(),
                'exams_passed': ExamAttempt.objects.filter(student=u, passed=True).count(),
                'avg_progress': round(avg_prog),
                'last_login':   u.last_login,
            })
        student_stats.sort(key=lambda x: x['lessons'], reverse=True)

    return render(request, 'accounts/company_dashboard.html', {
        'company':       company,
        'student_stats': student_stats,
        'kpis':          kpis,
        'rankings':      rankings,
        'reg_errors':    reg_errors or [],
        'reg_data':      reg_data or {},
    })


def company_dashboard(request, token):
    from accounts.models import Company
    company = get_object_or_404(Company, public_token=token)
    return _render_company_dashboard(request, company)



    from django.db.models import Count, Avg, Sum, Max
    from django.utils import timezone
    from datetime import timedelta

    company = get_object_or_404(Company, public_token=token)

    # Usuarios de la empresa
    profiles = company.users.select_related('user').all()
    students = [p.user for p in profiles]
    student_ids = [u.pk for u in students]

    if not student_ids:
        return render(request, 'accounts/company_dashboard.html', {
            'company': company,
            'students': [],
            'kpis': {},
            'rankings': {},
        })

    # ── KPIs globales (código antiguo eliminado — ver _render_company_dashboard) ──


# ─── ASISTENCIA PÚBLICA DE EMPRESA ───────────────────────────────

@require_http_methods(['GET', 'POST'])
def company_attendance(request, token):
    from accounts.models import Company, Attendance
    company = get_object_or_404(Company, attendance_token=token)
    submitted = False
    errors = []

    if request.method == 'POST':
        name     = request.POST.get('name', '').strip()
        email    = request.POST.get('email', '').strip()
        phone    = request.POST.get('phone', '').strip()
        position = request.POST.get('position', '').strip()
        notes    = request.POST.get('notes', '').strip()

        if not name:
            errors.append('El nombre es obligatorio.')
        else:
            Attendance.objects.create(
                company=company,
                name=name,
                email=email,
                phone=phone,
                position=position,
                notes=notes,
            )
            submitted = True

    return render(request, 'accounts/company_attendance.html', {
        'company':   company,
        'submitted': submitted,
        'errors':    errors,
    })


# ─── ADMIN: CONTACTOS ────────────────────────────────────────────

@staff_required
def admin_contacts(request):
    from accounts.models import Contact
    q  = request.GET.get('q', '').strip()
    qs = Contact.objects.all()
    if q:
        qs = qs.filter(
            first_name__icontains=q
        ) | Contact.objects.filter(
            last_name__icontains=q
        ) | Contact.objects.filter(
            email__icontains=q
        ) | Contact.objects.filter(
            company__icontains=q
        )
        qs = qs.distinct()
    paginator = Paginator(qs, 20)
    page      = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'accounts/admin_contacts.html', {
        'active_nav': 'admin_contacts',
        'page_obj':   page,
        'q':          q,
        'total':      qs.count(),
    })


@staff_required
@require_http_methods(['GET', 'POST'])
def admin_contact_view(request, contact_id):
    from accounts.models import Contact
    contact = get_object_or_404(Contact, pk=contact_id)
    if request.method == 'POST' and request.POST.get('action') == 'delete':
        contact.delete()
        messages.success(request, 'Contacto eliminado.')
        return redirect('accounts:admin_contacts')
    return render(request, 'accounts/admin_contact_detail.html', {
        'active_nav': 'admin_contacts',
        'contact':    contact,
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
        demo_url      = request.POST.get('demo_url', '').strip()
        demo_login    = request.POST.get('demo_login', '').strip()
        demo_password = request.POST.get('demo_password', '').strip()

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
                target.demo_url      = demo_url
                target.demo_login    = demo_login
                target.demo_password = demo_password
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
                    demo_url=demo_url,
                    demo_login=demo_login,
                    demo_password=demo_password,
                )
                course.categories.set(Category.objects.filter(pk__in=cat_ids))
                messages.success(request, f'Curso "{course.title}" creado correctamente.')
                return redirect('accounts:admin_course_edit', course_id=course.pk)

    if editing:
        from courses.models import Enrollment, ExamAttempt
        kpi_enrolled  = Enrollment.objects.filter(course=target).count()
        kpi_started   = Enrollment.objects.filter(course=target, progress__gt=0).count()
        kpi_evaluated = ExamAttempt.objects.filter(exam__course=target).values('student').distinct().count()
        kpi_completed = Enrollment.objects.filter(course=target, progress=100).count()
        kpi_started_pct   = round(kpi_started   / kpi_enrolled * 100) if kpi_enrolled else 0
        kpi_evaluated_pct = round(kpi_evaluated / kpi_enrolled * 100) if kpi_enrolled else 0
        kpi_completed_pct = round(kpi_completed / kpi_enrolled * 100) if kpi_enrolled else 0
    else:
        kpi_enrolled = kpi_started = kpi_evaluated = kpi_completed = 0
        kpi_started_pct = kpi_evaluated_pct = kpi_completed_pct = 0

    return render(request, 'accounts/admin_course_form.html', {
        'active_nav':          'admin_courses',
        'editing':             editing,
        'target':              target,
        'plans':               plans,
        'categories':          categories,
        'users':               users,
        'selected_cats':       set(target.categories.values_list('pk', flat=True)) if editing else set(),
        'kpi_enrolled':        kpi_enrolled,
        'kpi_started':         kpi_started,
        'kpi_evaluated':       kpi_evaluated,
        'kpi_completed':       kpi_completed,
        'kpi_started_pct':     kpi_started_pct,
        'kpi_evaluated_pct':   kpi_evaluated_pct,
        'kpi_completed_pct':   kpi_completed_pct,
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

    paginator = Paginator(qs, 10)
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
        order_val = request.POST.get('order', '').strip()

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
                if order_val.isdigit():
                    target.order = int(order_val)
                if 'video' in request.FILES:
                    if target.video:  # remove old video
                        if os.path.isfile(target.video.path):
                            os.remove(target.video.path)
                    target.video = request.FILES['video']
                target.save()
            else:
                # Auto-calcular el siguiente orden para este curso/topic
                if order_val.isdigit():
                    next_order = int(order_val)
                else:
                    qs = Lesson.objects.filter(course_id=course_id)
                    if topic_id:
                        qs = qs.filter(topic_id=topic_id)
                    max_order = qs.aggregate(m=_Max('order'))['m'] or 0
                    next_order = max_order + 1

                target = Lesson.objects.create(
                    title=title, content=content, course=course,
                    topic=topic, is_active=is_active,
                    order=next_order,
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
        'next_order': (Lesson.objects.aggregate(m=_Max('order'))['m'] or 0) + 1 if not editing else None,
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
        # Email
        config.email_host          = request.POST.get('email_host', '').strip()
        config.email_port          = int(request.POST.get('email_port', 587) or 587)
        config.email_host_user     = request.POST.get('email_host_user', '').strip()
        # Solo actualizar contraseña si se envía un valor (evitar borrar al dejar vacío)
        pwd = request.POST.get('email_host_password', '')
        if pwd:
            config.email_host_password = pwd
        config.email_use_tls       = request.POST.get('email_use_tls') == 'on'
        config.email_use_ssl       = request.POST.get('email_use_ssl') == 'on'
        config.default_from_email  = request.POST.get('default_from_email', '').strip()
        config.send_welcome_email      = request.POST.get('send_welcome_email') == 'on'
        config.cookie_consent_enabled  = request.POST.get('cookie_consent_enabled') == 'on'
        config.cookie_consent_text     = request.POST.get('cookie_consent_text', '').strip()
        config.save()
        messages.success(request, 'Configuración guardada correctamente.')
        return redirect('accounts:admin_config')

    # ── Estadísticas del servidor ─────────────────────────────────
    import shutil, os, platform
    server_stats = {}
    try:
        # Disco
        disk = shutil.disk_usage('/')
        server_stats['disk_total']   = round(disk.total / 1024**3, 1)
        server_stats['disk_used']    = round(disk.used  / 1024**3, 1)
        server_stats['disk_free']    = round(disk.free  / 1024**3, 1)
        server_stats['disk_percent'] = round(disk.used  / disk.total * 100, 1)
        # RAM (Linux /proc/meminfo)
        with open('/proc/meminfo') as f:
            mem = {line.split(':')[0]: int(line.split(':')[1].strip().split()[0])
                   for line in f if ':' in line}
        total_mb = mem.get('MemTotal', 0) // 1024
        avail_mb = mem.get('MemAvailable', 0) // 1024
        used_mb  = total_mb - avail_mb
        server_stats['ram_total']   = total_mb
        server_stats['ram_used']    = used_mb
        server_stats['ram_free']    = avail_mb
        server_stats['ram_percent'] = round(used_mb / total_mb * 100, 1) if total_mb else 0
        # CPU load (promedio 1 min)
        load1, load5, load15 = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        server_stats['cpu_load1']   = round(load1, 2)
        server_stats['cpu_load5']   = round(load5, 2)
        server_stats['cpu_load15']  = round(load15, 2)
        server_stats['cpu_count']   = cpu_count
        server_stats['cpu_percent'] = round(load1 / cpu_count * 100, 1)
        # SO y Python
        server_stats['platform'] = platform.platform()
        server_stats['python']   = platform.python_version()
    except Exception:
        pass

    return render(request, 'accounts/admin_config.html', {
        'active_nav':   'admin_config',
        'config':       config,
        'server_stats': server_stats,
    })


# ─── BLOQUEO DE PANTALLA ─────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def lock_view(request):
    """Activa el bloqueo de pantalla en la sesión."""
    request.session['screen_locked'] = True
    return redirect('accounts:lock_screen')


@login_required
@require_http_methods(['GET', 'POST'])
def lock_screen_view(request):
    from accounts.models import UserProfile
    from django.contrib.auth.hashers import make_password, check_password as check_pwd

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    error = None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'unlock':
            pin = request.POST.get('pin', '').strip()
            if not profile.has_pin:
                error = 'No tienes PIN configurado.'
            elif not pin.isdigit() or len(pin) != 4:
                error = 'El PIN debe ser 4 dígitos.'
            elif check_pwd(pin, profile.pin_hash):
                request.session['screen_locked'] = False
                return redirect('courses:dashboard')
            else:
                error = 'PIN incorrecto. Inténtalo de nuevo.'

        elif action == 'set_pin':
            pin1 = request.POST.get('pin1', '').strip()
            pin2 = request.POST.get('pin2', '').strip()
            if not pin1.isdigit() or len(pin1) != 4:
                error = 'El PIN debe ser exactamente 4 dígitos numéricos.'
            elif pin1 != pin2:
                error = 'Los PINs no coinciden.'
            else:
                profile.pin_hash = make_password(pin1)
                profile.save(update_fields=['pin_hash'])
                # Si estaba bloqueado, desbloquear
                request.session['screen_locked'] = False
                return redirect('courses:dashboard')

    return render(request, 'accounts/lock_screen.html', {
        'profile': profile,
        'error':   error,
        'locked':  request.session.get('screen_locked', False),
    })


@login_required
@require_http_methods(['POST'])
def change_pin_view(request):
    """Cambiar o eliminar el PIN desde el perfil."""
    from accounts.models import UserProfile
    from django.contrib.auth.hashers import make_password, check_password as check_pwd

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    action = request.POST.get('pin_action')

    if action == 'set':
        pin1 = request.POST.get('pin1', '').strip()
        pin2 = request.POST.get('pin2', '').strip()
        if not pin1.isdigit() or len(pin1) != 4:
            messages.error(request, 'El PIN debe ser exactamente 4 dígitos numéricos.')
        elif pin1 != pin2:
            messages.error(request, 'Los PINs no coinciden.')
        else:
            profile.pin_hash = make_password(pin1)
            profile.save(update_fields=['pin_hash'])
            messages.success(request, 'PIN configurado correctamente.')

    elif action == 'remove':
        profile.pin_hash = ''
        profile.save(update_fields=['pin_hash'])
        messages.success(request, 'PIN eliminado.')

    return redirect('accounts:profile')


# ─── UTILIDADES DE EMAIL ─────────────────────────────────────────

def _get_email_connection():
    """Devuelve una conexión SMTP usando la config guardada en SiteConfig."""
    from accounts.models import SiteConfig
    from django.core.mail import get_connection
    cfg = SiteConfig.get()
    if not cfg.email_host or not cfg.email_host_user:
        return None, None
    conn = get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host=cfg.email_host,
        port=cfg.email_port,
        username=cfg.email_host_user,
        password=cfg.email_host_password,
        use_tls=cfg.email_use_tls,
        use_ssl=cfg.email_use_ssl,
        fail_silently=True,
    )
    from_email = cfg.default_from_email or cfg.email_host_user
    return conn, from_email


def _send_welcome_email(user):
    """Envía el email de bienvenida si está activado en SiteConfig."""
    from accounts.models import SiteConfig
    from django.core.mail import EmailMessage
    cfg = SiteConfig.get()
    if not cfg.send_welcome_email:
        return
    conn, from_email = _get_email_connection()
    if conn is None:
        return
    subject = f'¡Bienvenido/a a {cfg.site_name}!'
    body = (
        f'Hola {user.first_name or user.username},\n\n'
        f'Tu cuenta en {cfg.site_name} ha sido creada correctamente.\n'
        f'Ya puedes acceder a todos los cursos y contenidos disponibles.\n\n'
        f'¡Gracias por unirte!\n\n'
        f'El equipo de {cfg.site_name}'
    )
    try:
        EmailMessage(subject, body, from_email, [user.email], connection=conn).send()
    except Exception:
        pass


# ─── RECUPERACIÓN DE CONTRASEÑA ──────────────────────────────────

@require_http_methods(['GET', 'POST'])
def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect('courses:dashboard')

    sent = False
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        conn, from_email = _get_email_connection()
        try:
            user_obj = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            user_obj = None

        if user_obj and conn is not None:
            from accounts.models import PasswordResetToken, SiteConfig
            from django.core.mail import EmailMessage
            # Invalidar tokens previos
            PasswordResetToken.objects.filter(user=user_obj, used=False).update(used=True)
            token_obj = PasswordResetToken.objects.create(user=user_obj)
            reset_url = request.build_absolute_uri(
                f'/accounts/reset-password/{token_obj.token}/'
            )
            cfg = SiteConfig.get()
            subject = f'Recupera tu contraseña – {cfg.site_name}'
            body = (
                f'Hola {user_obj.first_name or user_obj.username},\n\n'
                f'Recibimos una solicitud para restablecer la contraseña de tu cuenta.\n\n'
                f'Haz clic en el siguiente enlace (válido durante 2 horas):\n{reset_url}\n\n'
                f'Si no solicitaste este cambio, ignora este mensaje.\n\n'
                f'El equipo de {cfg.site_name}'
            )
            try:
                EmailMessage(subject, body, from_email, [user_obj.email], connection=conn).send()
            except Exception:
                pass
        # Siempre mostrar el mismo mensaje (evitar enumeración de usuarios)
        sent = True

    return render(request, 'accounts/forgot_password.html', {'sent': sent})


@require_http_methods(['GET', 'POST'])
def reset_password_view(request, token):
    if request.user.is_authenticated:
        return redirect('courses:dashboard')

    from accounts.models import PasswordResetToken
    try:
        token_obj = PasswordResetToken.objects.select_related('user').get(token=token)
    except PasswordResetToken.DoesNotExist:
        token_obj = None

    valid = token_obj is not None and token_obj.is_valid()

    if request.method == 'POST' and valid:
        p1 = request.POST.get('password1', '')
        p2 = request.POST.get('password2', '')
        if p1 != p2:
            messages.error(request, 'Las contraseñas no coinciden.')
        elif len(p1) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
        else:
            token_obj.user.set_password(p1)
            token_obj.user.save()
            token_obj.used = True
            token_obj.save()
            messages.success(request, 'Contraseña restablecida correctamente. Ya puedes iniciar sesión.')
            return redirect('accounts:login')

    return render(request, 'accounts/reset_password.html', {'valid': valid, 'token': token})


@staff_required
def admin_config_test_email(request):
    """Envía un email de prueba al admin que lo solicita y devuelve JSON."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'message': 'Método no permitido.'}, status=405)

    conn, from_email = _get_email_connection()
    if conn is None:
        return JsonResponse({
            'ok': False,
            'message': 'La configuración SMTP está incompleta. Guarda primero el servidor y el usuario SMTP.',
        })

    from django.core.mail import EmailMessage
    from accounts.models import SiteConfig
    cfg = SiteConfig.get()
    subject = f'Prueba de email – {cfg.site_name}'
    body = (
        f'Este es un correo de prueba enviado desde el panel de {cfg.site_name}.\n\n'
        f'Si lo recibes, la configuración SMTP es correcta.'
    )
    try:
        sent = EmailMessage(subject, body, from_email, [request.user.email], connection=conn).send()
        if sent:
            return JsonResponse({
                'ok': True,
                'message': f'Email enviado correctamente a {request.user.email}.',
            })
        return JsonResponse({
            'ok': False,
            'message': 'El servidor no reportó error pero tampoco confirmó el envío.',
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'message': f'Error SMTP: {e}'})


# ─── ADMIN: VOTACIONES ───────────────────────────────────────────

@staff_required
def admin_votings(request):
    from accounts.models import Voting
    votings = Voting.objects.prefetch_related('options').order_by('-created_at')
    return render(request, 'accounts/admin_votings.html', {
        'active_nav': 'admin_votings',
        'votings':    votings,
    })


@staff_required
@require_http_methods(['GET', 'POST'])
def admin_voting_form(request, voting_id=None):
    from accounts.models import Voting, VotingOption
    editing = voting_id is not None
    target  = get_object_or_404(Voting, pk=voting_id) if editing else None

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete' and editing:
            target.delete()
            messages.success(request, 'Votación eliminada.')
            return redirect('accounts:admin_votings')

        name        = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_active   = request.POST.get('is_active') == 'on'
        ends_at_raw = request.POST.get('ends_at', '').strip()
        options_raw = [o.strip() for o in request.POST.getlist('option_name') if o.strip()]

        if not name:
            messages.error(request, 'El nombre es obligatorio.')
        elif len(options_raw) < 2:
            messages.error(request, 'Debes añadir al menos 2 opciones.')
        else:
            from django.utils.dateparse import parse_datetime
            ends_at = parse_datetime(ends_at_raw) if ends_at_raw else None

            if editing:
                target.name        = name
                target.description = description
                target.is_active   = is_active
                target.ends_at     = ends_at
                target.save()
                target.options.all().delete()
            else:
                target = Voting.objects.create(
                    name=name, description=description,
                    is_active=is_active, ends_at=ends_at,
                )

            for i, opt in enumerate(options_raw):
                VotingOption.objects.create(voting=target, name=opt, order=i)

            messages.success(request, 'Votación guardada correctamente.')
            return redirect('accounts:admin_voting_edit', voting_id=target.pk)

    return render(request, 'accounts/admin_voting_form.html', {
        'active_nav': 'admin_votings',
        'editing':    editing,
        'target':     target,
    })


# ─── PÚBLICA: VOTAR ──────────────────────────────────────────────

def public_vote(request, token):
    from accounts.models import Voting, Vote
    voting = get_object_or_404(Voting, public_token=token)

    # IP del visitante
    def get_ip(req):
        x = req.META.get('HTTP_X_FORWARDED_FOR')
        return x.split(',')[0].strip() if x else req.META.get('REMOTE_ADDR', '')

    ip = get_ip(request)
    already_voted = False
    my_vote = None

    if request.user.is_authenticated:
        my_vote = Vote.objects.filter(voting=voting, user=request.user).first()
        already_voted = my_vote is not None
    elif request.session.get(f'voted_{voting.pk}'):
        already_voted = True

    error = None
    if request.method == 'POST' and not already_voted and voting.is_open:
        option_id    = request.POST.get('option')
        voter_name   = request.POST.get('voter_name', '').strip()
        voter_email  = request.POST.get('voter_email', '').strip()
        voter_phone  = request.POST.get('voter_phone', '').strip()

        if not option_id:
            error = 'Selecciona una opción para votar.'
        elif not request.user.is_authenticated and not voter_name:
            error = 'Introduce tu nombre para votar.'
        else:
            from accounts.models import VotingOption
            option = get_object_or_404(VotingOption, pk=option_id, voting=voting)
            Vote.objects.create(
                voting=voting,
                option=option,
                user=request.user if request.user.is_authenticated else None,
                voter_name=voter_name if not request.user.is_authenticated else request.user.get_full_name() or request.user.username,
                voter_email=voter_email if not request.user.is_authenticated else request.user.email,
                voter_phone=voter_phone,
                ip_address=ip,
            )
            if request.user.is_authenticated:
                my_vote = Vote.objects.filter(voting=voting, user=request.user).first()
            else:
                request.session[f'voted_{voting.pk}'] = str(option.pk)
            already_voted = True

    return render(request, 'accounts/public_vote.html', {
        'voting':         voting,
        'already_voted':  already_voted,
        'my_vote':        my_vote,
        'session_option': request.session.get(f'voted_{voting.pk}'),
        'error':          error,
    })


def public_vote_results(request, token):
    from accounts.models import Voting
    voting = get_object_or_404(Voting, public_token=token)
    return render(request, 'accounts/public_vote_results.html', {'voting': voting})


def voting_api(request, token):
    """JSON con resultados en tiempo real."""
    from accounts.models import Voting
    from django.db.models import Count
    voting = get_object_or_404(Voting, public_token=token)
    total = voting.total_votes
    options = []
    for opt in voting.options.annotate(cnt=Count('votes')).order_by('order'):
        pct = round(opt.cnt / total * 100) if total else 0
        options.append({'id': opt.pk, 'name': opt.name, 'votes': opt.cnt, 'pct': pct})
    return JsonResponse({'total': total, 'options': options, 'is_open': voting.is_open})


# ─── CHAT DIRECTO ────────────────────────────────────────────────

@login_required
def dm_conversations(request):
    """JSON: lista de conversaciones con último mensaje y no leídos."""
    from accounts.models import DirectMessage
    from django.db.models import Q, Max, Count, OuterRef, Subquery
    me = request.user

    # IDs de usuarios con quienes hay mensajes
    partners = set(
        list(DirectMessage.objects.filter(sender=me).values_list('recipient_id', flat=True)) +
        list(DirectMessage.objects.filter(recipient=me).values_list('sender_id', flat=True))
    )
    partners.discard(me.pk)

    result = []
    for uid in partners:
        partner = User.objects.filter(pk=uid).first()
        if not partner:
            continue
        last = DirectMessage.objects.filter(
            Q(sender=me, recipient=partner) | Q(sender=partner, recipient=me)
        ).order_by('-created_at').first()
        unread = DirectMessage.objects.filter(sender=partner, recipient=me, is_read=False).count()
        result.append({
            'user_id':    partner.pk,
            'name':       partner.get_full_name() or partner.username,
            'username':   partner.username,
            'avatar':     partner.first_name[:1].upper() or partner.username[:1].upper(),
            'last_msg':   last.content[:60] if last else '',
            'last_time':  last.created_at.strftime('%H:%M') if last else '',
            'unread':     unread,
        })
    result.sort(key=lambda x: x['last_time'], reverse=True)

    total_unread = DirectMessage.objects.filter(recipient=me, is_read=False).count()
    return JsonResponse({'conversations': result, 'total_unread': total_unread})


@login_required
def dm_thread(request, user_id):
    """JSON: hilo de mensajes con un usuario + marcar como leídos."""
    from accounts.models import DirectMessage
    from django.db.models import Q
    partner = get_object_or_404(User, pk=user_id)
    me = request.user

    msgs = DirectMessage.objects.filter(
        Q(sender=me, recipient=partner) | Q(sender=partner, recipient=me)
    ).order_by('created_at')

    # Marcar leídos
    DirectMessage.objects.filter(sender=partner, recipient=me, is_read=False).update(is_read=True)

    data = [{
        'id':       m.pk,
        'content':  m.content,
        'mine':     m.sender_id == me.pk,
        'time':     m.created_at.strftime('%H:%M'),
    } for m in msgs]
    return JsonResponse({'messages': data, 'partner_name': partner.get_full_name() or partner.username})


@login_required
@require_POST
def dm_send(request):
    """JSON: enviar mensaje directo."""
    from accounts.models import DirectMessage
    import json
    try:
        body = json.loads(request.body)
    except Exception:
        body = request.POST
    recipient_id = body.get('recipient_id')
    content      = str(body.get('content', '')).strip()

    if not content or not recipient_id:
        return JsonResponse({'ok': False, 'error': 'Datos incompletos'}, status=400)
    if int(recipient_id) == request.user.pk:
        return JsonResponse({'ok': False, 'error': 'No puedes enviarte mensajes a ti mismo'}, status=400)

    recipient = get_object_or_404(User, pk=recipient_id)
    msg = DirectMessage.objects.create(
        sender=request.user, recipient=recipient, content=content
    )
    return JsonResponse({'ok': True, 'id': msg.pk, 'time': msg.created_at.strftime('%H:%M')})


@login_required
def dm_user_search(request):
    """JSON: buscar usuarios por nombre/email para iniciar chat."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'users': []})
    from django.db.models import Q
    qs = User.objects.filter(is_active=True).exclude(pk=request.user.pk)
    qs = qs.filter(
        Q(first_name__icontains=q) | Q(last_name__icontains=q) |
        Q(username__icontains=q) | Q(email__icontains=q)
    )[:10]
    users = [{
        'id':       u.pk,
        'name':     u.get_full_name() or u.username,
        'username': u.username,
        'avatar':   (u.first_name[:1] or u.username[:1]).upper(),
    } for u in qs]
    return JsonResponse({'users': users})


# ─── ADMIN: TÉRMINOS Y CONDICIONES ───────────────────────────────

@staff_required
def admin_terms(request):
    from accounts.models import TermsConditions
    terms_list = TermsConditions.objects.order_by('-created_at')
    return render(request, 'accounts/admin_terms.html', {
        'active_nav': 'admin_terms',
        'terms_list': terms_list,
    })


@staff_required
@require_http_methods(['GET', 'POST'])
def admin_terms_form(request, terms_id=None):
    from accounts.models import TermsConditions
    editing = terms_id is not None
    target  = get_object_or_404(TermsConditions, pk=terms_id) if editing else None

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete' and editing:
            target.delete()
            messages.success(request, 'Términos eliminados.')
            return redirect('accounts:admin_terms')

        title       = request.POST.get('title', '').strip() or 'Términos y Condiciones'
        description = request.POST.get('description', '').strip()
        version     = request.POST.get('version', '').strip()
        is_active   = request.POST.get('is_active') == 'on'

        if not description:
            messages.error(request, 'El contenido es obligatorio.')
        else:
            if editing:
                target.title       = title
                target.description = description
                target.version     = version
                target.is_active   = is_active
                target.save()
                messages.success(request, 'Términos actualizados.')
                return redirect('accounts:admin_terms_edit', terms_id=target.pk)
            else:
                tc = TermsConditions.objects.create(
                    title=title, description=description,
                    version=version, is_active=is_active,
                )
                messages.success(request, 'Términos creados.')
                return redirect('accounts:admin_terms_edit', terms_id=tc.pk)

    return render(request, 'accounts/admin_terms_form.html', {
        'active_nav': 'admin_terms',
        'editing':    editing,
        'target':     target,
    })


# ─── ACEPTAR TÉRMINOS (USUARIOS) ─────────────────────────────────

@login_required
@require_http_methods(['GET', 'POST'])
def accept_terms_view(request):
    from accounts.models import TermsConditions, TermsAcceptance
    active = TermsConditions.get_active()
    if not active:
        return redirect('courses:dashboard')

    already = TermsAcceptance.objects.filter(user=request.user, terms=active).exists()
    if already:
        return redirect('courses:dashboard')

    if request.method == 'POST':
        accepted = request.POST.get('accept') == 'yes'
        if accepted:
            x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR')
            TermsAcceptance.objects.create(user=request.user, terms=active, ip_address=ip)
            return redirect('courses:dashboard')
        else:
            # No acepta: cerrar sesión
            from django.contrib.auth import logout as auth_logout
            auth_logout(request)
            return redirect('accounts:login')

    return render(request, 'accounts/accept_terms.html', {'terms': active})


# ─── REGISTRO POR PLAN DE CAPACITACIÓN ──────────────────────────

def plan_register_view(request, token, company_id=None):
    from courses.models import TrainingPlan, Enrollment
    from accounts.models import SiteConfig, Company
    plan    = get_object_or_404(TrainingPlan, register_token=token, is_active=True)
    company = get_object_or_404(Company, pk=company_id) if company_id else None
    config  = SiteConfig.get()

    # El registro por enlace de empresa/plan siempre está activo (company_id indica origen empresarial)
    if not config.enable_registration and not company_id:
        return render(request, 'accounts/register_closed.html', {'plan': plan})

    error = None
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        email      = request.POST.get('email', '').strip().lower()
        username   = request.POST.get('username', '').strip()
        password1  = request.POST.get('password1', '')
        password2  = request.POST.get('password2', '')

        if not all([first_name, last_name, email, username, password1]):
            error = 'Todos los campos son obligatorios.'
        elif password1 != password2:
            error = 'Las contraseñas no coinciden.'
        elif len(password1) < 6:
            error = 'La contraseña debe tener al menos 6 caracteres.'
        elif User.objects.filter(username=username).exists():
            error = 'Ese nombre de usuario ya está en uso.'
        elif User.objects.filter(email=email).exists():
            error = 'Ya existe una cuenta con ese correo electrónico.'
        else:
            user = User.objects.create_user(
                username=username, email=email,
                password=password1,
                first_name=first_name, last_name=last_name,
            )
            from django.contrib.auth import login as auth_login
            auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            if company:
                from accounts.models import UserProfile
                UserProfile.objects.filter(user=user).update(company=company)
            courses = plan.courses.filter(is_published=True)
            for course in courses:
                Enrollment.objects.get_or_create(student=user, course=course)
            return redirect('courses:dashboard')

    kpi_registered = kpi_started = kpi_evaluated = 0
    kpi_started_pct = kpi_evaluated_pct = 0
    if company:
        from courses.models import ExamAttempt as _EA
        plan_courses = plan.courses.filter(is_published=True)
        kpi_registered = (Enrollment.objects
                          .filter(course__in=plan_courses, student__profile__company=company)
                          .values('student').distinct().count())
        kpi_started    = (Enrollment.objects
                          .filter(course__in=plan_courses, student__profile__company=company, progress__gt=0)
                          .values('student').distinct().count())
        kpi_evaluated  = (_EA.objects
                          .filter(exam__course__in=plan_courses, student__profile__company=company)
                          .values('student').distinct().count())
        if kpi_registered:
            kpi_started_pct   = round(kpi_started   / kpi_registered * 100)
            kpi_evaluated_pct = round(kpi_evaluated / kpi_registered * 100)

    return render(request, 'accounts/plan_register.html', {
        'plan':              plan,
        'company':           company,
        'error':             error,
        'kpi_registered':    kpi_registered,
        'kpi_started':       kpi_started,
        'kpi_evaluated':     kpi_evaluated,
        'kpi_started_pct':   kpi_started_pct,
        'kpi_evaluated_pct': kpi_evaluated_pct,
    })

def public_cv(request, username):
    from courses.models import Course, Enrollment
    target_user = get_object_or_404(User, username=username, is_active=True)
    try:
        profile = target_user.profile
    except Exception:
        from django.http import Http404
        raise Http404
    if not profile.cv_public or not (profile.cv_headline or profile.cv_summary or profile.cv_experience or profile.cv_education or profile.cv_skills):
        from django.http import Http404
        raise Http404

    # Cursos como profesor
    courses_taught = Course.objects.filter(
        instructor=target_user, is_published=True
    ).order_by('-created_at')

    # Cursos como estudiante
    enrollments = Enrollment.objects.filter(
        student=target_user
    ).select_related('course').order_by('-enrolled_at') if not courses_taught.exists() else []

    return render(request, 'accounts/public_cv.html', {
        'target_user':    target_user,
        'profile':        profile,
        'courses_taught': courses_taught,
        'enrollments':    enrollments,
        'is_teacher':     courses_taught.exists(),
    })


# ─── GRUPOS DE CHAT (ADMIN) ──────────────────────────────────────

@login_required
def admin_chat_groups(request):
    if not request.user.is_staff:
        return redirect('courses:dashboard')
    from accounts.models import ChatGroup
    groups = ChatGroup.objects.prefetch_related('companies', 'members').order_by('name')
    return render(request, 'accounts/admin_chat_groups.html', {
        'active_nav': 'admin_chat_groups',
        'groups': groups,
    })


@login_required
def admin_chat_group_form(request, group_id=None):
    if not request.user.is_staff:
        return redirect('courses:dashboard')
    from accounts.models import ChatGroup, Company
    editing = group_id is not None
    group   = get_object_or_404(ChatGroup, pk=group_id) if editing else None

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete' and editing:
            group.delete()
            messages.success(request, 'Grupo eliminado.')
            return redirect('accounts:admin_chat_groups')

        name        = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_active   = request.POST.get('is_active') == '1'
        company_ids = request.POST.getlist('companies')
        member_ids  = request.POST.getlist('members')

        if not name:
            messages.error(request, 'El nombre es obligatorio.')
        else:
            if editing:
                group.name        = name
                group.description = description
                group.is_active   = is_active
                group.save()
            else:
                group = ChatGroup.objects.create(
                    name=name, description=description,
                    is_active=is_active, created_by=request.user,
                )
            group.companies.set(Company.objects.filter(pk__in=company_ids))
            group.members.set(User.objects.filter(pk__in=member_ids))
            messages.success(request, f'Grupo "{group.name}" guardado.')
            return redirect('accounts:admin_chat_group_edit', group_id=group.pk)

    all_companies = Company.objects.order_by('name')
    all_users     = User.objects.filter(is_active=True).select_related('profile').order_by('first_name', 'last_name', 'username')
    return render(request, 'accounts/admin_chat_group_form.html', {
        'active_nav':     'admin_chat_groups',
        'editing':        editing,
        'group':          group,
        'all_companies':  all_companies,
        'all_users':      all_users,
    })


# ─── GRUPOS DE CHAT (API USUARIO) ────────────────────────────────

@login_required
def user_groups_api(request):
    """Devuelve los grupos a los que pertenece el usuario autenticado."""
    from accounts.models import ChatGroup
    if request.user.is_staff:
        groups = ChatGroup.objects.filter(is_active=True).prefetch_related('companies', 'members')
    else:
        groups = ChatGroup.objects.filter(is_active=True).prefetch_related('companies', 'members')
    result = []
    for g in groups:
        if g.is_member(request.user):
            last = g.messages.last()
            result.append({
                'id':          g.pk,
                'name':        g.name,
                'last':        last.content[:60] if last else '',
                'time':        last.created_at.strftime('%H:%M') if last else '',
                'last_msg_id': last.pk if last else 0,
            })
    return JsonResponse({'groups': result})


@login_required
def group_messages_api(request, group_id):
    """GET: mensajes del grupo. POST: enviar mensaje."""
    from accounts.models import ChatGroup, ChatGroupMessage
    group = get_object_or_404(ChatGroup, pk=group_id, is_active=True)
    if not group.is_member(request.user):
        return JsonResponse({'ok': False, 'error': 'No perteneces a este grupo.'}, status=403)

    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
        except Exception:
            data = {}
        content = data.get('content', '').strip()
        if not content:
            return JsonResponse({'ok': False, 'error': 'Mensaje vacío.'}, status=400)
        msg = ChatGroupMessage.objects.create(group=group, sender=request.user, content=content)
        return JsonResponse({
            'ok':      True,
            'id':      msg.pk,
            'sender':  request.user.get_full_name() or request.user.username,
            'content': msg.content,
            'time':    msg.created_at.strftime('%H:%M'),
            'mine':    True,
        })

    # GET
    since_id = int(request.GET.get('since', 0))
    msgs = group.messages.select_related('sender').filter(pk__gt=since_id).order_by('created_at')[:80]
    return JsonResponse({'messages': [
        {
            'id':      m.pk,
            'sender':  m.sender.get_full_name() or m.sender.username,
            'content': m.content,
            'time':    m.created_at.strftime('%H:%M'),
            'mine':    m.sender_id == request.user.pk,
        }
        for m in msgs
    ]})


# ─── SALA DE REUNIÓN POR EMPRESA ─────────────────────────────────

@login_required
def company_meeting(request, company_id=None):
    from accounts.models import Company
    if request.user.is_staff:
        if company_id:
            company = get_object_or_404(Company, pk=company_id)
        else:
            companies = Company.objects.order_by('name')
            return render(request, 'accounts/meeting_select.html', {
                'active_nav': 'meeting',
                'companies':  companies,
            })
    else:
        try:
            company = request.user.profile.company
        except Exception:
            company = None
        if not company:
            return render(request, 'accounts/meeting_no_company.html', {
                'active_nav': 'meeting',
            })

    display_name = request.user.get_full_name() or request.user.username
    return render(request, 'accounts/meeting_room.html', {
        'active_nav':   'meeting',
        'company':      company,
        'display_name': display_name,
    })


@login_required
def meeting_signal_post(request):
    """POST: enviar señal WebRTC (offer, answer, ice, join, leave)."""
    import json
    from accounts.models import Company, MeetingSignal
    from django.utils import timezone
    from datetime import timedelta
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'ok': False}, status=400)

    company = get_object_or_404(Company, pk=body.get('company_id'))
    # Limpiar señales antiguas (> 60 s)
    MeetingSignal.objects.filter(
        company=company,
        created_at__lt=timezone.now() - timedelta(seconds=60)
    ).delete()

    sig = MeetingSignal.objects.create(
        company=company,
        peer_id=body.get('peer_id', ''),
        target=body.get('target', ''),
        stype=body.get('stype', ''),
        data=json.dumps(body.get('data', {})),
    )
    return JsonResponse({'ok': True, 'id': sig.pk})


@login_required
def meeting_signal_poll(request):
    """GET: obtener señales nuevas para este peer."""
    from accounts.models import Company, MeetingSignal
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Q

    company  = get_object_or_404(Company, pk=request.GET.get('company_id'))
    peer_id  = request.GET.get('peer_id', '')
    since_id = int(request.GET.get('since', 0))
    cutoff   = timezone.now() - timedelta(seconds=45)

    signals = MeetingSignal.objects.filter(
        company=company,
        id__gt=since_id,
        created_at__gte=cutoff,
    ).filter(
        Q(target='') | Q(target=peer_id)
    ).exclude(peer_id=peer_id)

    return JsonResponse({'signals': [
        {'id': s.pk, 'peer_id': s.peer_id, 'stype': s.stype,
         'data': s.data, 'target': s.target}
        for s in signals
    ]})


# ─── EVALUACIONES DE PLATAFORMA ──────────────────────────────────

@login_required
@require_POST
def platform_rating_submit(request):
    from accounts.models import PlatformRating
    rating  = request.POST.get('rating', '').strip()
    comment = request.POST.get('comment', '').strip()
    if rating not in ('happy', 'neutral', 'sad'):
        return JsonResponse({'ok': False, 'error': 'Valoración inválida'}, status=400)
    PlatformRating.objects.create(user=request.user, rating=rating, comment=comment)
    return JsonResponse({'ok': True})


@staff_required
def admin_platform_ratings(request):
    from accounts.models import PlatformRating
    ratings  = PlatformRating.objects.select_related('user').order_by('-created_at')
    total    = ratings.count()
    n_happy  = ratings.filter(rating='happy').count()
    n_neutral = ratings.filter(rating='neutral').count()
    n_sad    = ratings.filter(rating='sad').count()
    return render(request, 'accounts/admin_platform_ratings.html', {
        'active_nav': 'admin_ratings',
        'ratings':    ratings,
        'total':      total,
        'n_happy':    n_happy,
        'n_neutral':  n_neutral,
        'n_sad':      n_sad,
    })


# ─── VERSIONES ────────────────────────────────────────────────────────────────────

@staff_required
def admin_versions(request):
    from accounts.models import AppVersion
    versions = AppVersion.objects.prefetch_related('features').all()
    return render(request, 'accounts/admin_versions.html', {
        'active_nav': 'admin_versions',
        'versions':   versions,
    })


@staff_required
def admin_version_create(request):
    from accounts.models import AppVersion
    if request.method == 'POST':
        version    = request.POST.get('version', '').strip()
        title      = request.POST.get('title', '').strip()
        released_at = request.POST.get('released_at', '').strip()
        is_current  = request.POST.get('is_current') == '1'
        if version and title and released_at:
            v = AppVersion.objects.create(
                version=version, title=title,
                released_at=released_at, is_current=is_current,
            )
            return redirect('accounts:admin_version_edit', version_id=v.pk)
    return redirect('accounts:admin_versions')


@staff_required
def admin_version_edit(request, version_id):
    from accounts.models import AppVersion, AppVersionFeature, FEATURE_CATEGORY
    v = get_object_or_404(AppVersion, pk=version_id)
    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        if action == 'save':
            v.version     = request.POST.get('version', v.version).strip()
            v.title       = request.POST.get('title', v.title).strip()
            v.released_at = request.POST.get('released_at', str(v.released_at)).strip()
            v.is_current  = request.POST.get('is_current') == '1'
            v.save()
        elif action == 'add_feature':
            text     = request.POST.get('text', '').strip()
            category = request.POST.get('category', 'feature')
            if text:
                last = v.features.order_by('order').last()
                AppVersionFeature.objects.create(
                    version=v, category=category, text=text,
                    order=(last.order + 1) if last else 0,
                )
        elif action == 'delete_feature':
            fid = request.POST.get('feature_id')
            AppVersionFeature.objects.filter(pk=fid, version=v).delete()
        return redirect('accounts:admin_version_edit', version_id=v.pk)
    return render(request, 'accounts/admin_version_edit.html', {
        'active_nav':       'admin_versions',
        'v':                v,
        'feature_categories': FEATURE_CATEGORY,
    })


@staff_required
def admin_version_delete(request, version_id):
    from accounts.models import AppVersion
    v = get_object_or_404(AppVersion, pk=version_id)
    if request.method == 'POST':
        v.delete()
    return redirect('accounts:admin_versions')


def api_version_changelog(request, version_id):
    """JSON con los detalles de una versión para el modal wizard."""
    from accounts.models import AppVersion
    v = get_object_or_404(AppVersion, pk=version_id)
    features = list(v.features.values('category', 'text', 'order'))
    return JsonResponse({
        'id':          v.pk,
        'version':     v.version,
        'title':       v.title,
        'released_at': v.released_at.strftime('%d/%m/%Y'),
        'is_current':  v.is_current,
        'features':    features,
    })


def api_all_versions(request):
    """JSON con todas las versiones (para el modal wizard del usuario)."""
    from accounts.models import AppVersion
    versions = []
    for v in AppVersion.objects.prefetch_related('features').all():
        versions.append({
            'id':          v.pk,
            'version':     v.version,
            'title':       v.title,
            'released_at': v.released_at.strftime('%d/%m/%Y'),
            'is_current':  v.is_current,
            'features':    list(v.features.values('category', 'text')),
        })
    return JsonResponse({'versions': versions})


@login_required
@require_POST
def api_nav_more_save(request):
    expanded = request.POST.get('expanded') == '1'
    request.user.profile.nav_more_expanded = expanded
    request.user.profile.save(update_fields=['nav_more_expanded'])
    return JsonResponse({'ok': True, 'expanded': expanded})

