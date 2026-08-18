from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.db.models import F, Q, Avg, Count
from django.contrib.auth.models import User
from .models import Course, Category, Enrollment, Lesson, LessonProgress, Exam, ExamAttempt, LessonComment, CourseReview, ExamUpload, Task, TaskSubmission, DocFolder, DocFile


@login_required
def dashboard(request):
    from django.db.models import OuterRef
    from django.contrib.auth.models import User as AuthUser

    enrollments = (Enrollment.objects
                   .filter(student=request.user)
                   .select_related('course')
                   .prefetch_related('course__categories')
                   .annotate(avg_rating=Avg('course__reviews__rating'))
                   .order_by('-enrolled_at'))

    enrolled_count   = enrollments.count()
    completed_count  = enrollments.filter(progress=100).count()
    overall_progress = int(enrollments.aggregate(avg=Avg('progress'))['avg'] or 0)

    # Certificados: último intento aprobado por examen
    certificates_count = ExamAttempt.objects.filter(
        student=request.user,
        passed=True,
    ).filter(
        attempted_at=ExamAttempt.objects.filter(
            student=request.user,
            exam=OuterRef('exam'),
        ).order_by('-attempted_at').values('attempted_at')[:1]
    ).count()

    # KPIs personales
    enrolled_course_ids = enrollments.values_list('course_id', flat=True)

    lessons_total     = Lesson.objects.filter(course__in=enrolled_course_ids, is_active=True).count()
    lessons_done      = LessonProgress.objects.filter(student=request.user, lesson__course__in=enrolled_course_ids).count()

    tasks_total       = Task.objects.filter(lesson__course__in=enrolled_course_ids, is_active=True).count()
    tasks_done        = TaskSubmission.objects.filter(student=request.user, task__lesson__course__in=enrolled_course_ids).count()

    exams_total       = Exam.objects.filter(course__in=enrolled_course_ids, is_active=True).count()
    exams_passed      = certificates_count

    total_students    = AuthUser.objects.filter(is_active=True, is_staff=False).count()

    # Puntos de gamificación: 1 por clase, 10 por examen aprobado
    user_points = lessons_done * 1 + exams_passed * 10

    # Top 10 ranking global de puntos
    from django.db.models import Count, Value, IntegerField, ExpressionWrapper
    from django.db.models.functions import Coalesce

    lesson_pts = (LessonProgress.objects
                  .values('student')
                  .annotate(pts=Count('id')))
    exam_pts   = (ExamAttempt.objects
                  .filter(passed=True)
                  .values('student')
                  .annotate(pts=Count('id')))

    # Build points dict per user
    pts_map = {}
    for row in lesson_pts:
        pts_map[row['student']] = pts_map.get(row['student'], 0) + row['pts']
    for row in exam_pts:
        pts_map[row['student']] = pts_map.get(row['student'], 0) + row['pts'] * 10

    top10_ids    = sorted(pts_map, key=lambda uid: pts_map[uid], reverse=True)[:10]
    top10_users  = {u.pk: u for u in AuthUser.objects.filter(pk__in=top10_ids).select_related('profile')}
    top10 = [
        {'user': top10_users[uid], 'points': pts_map[uid]}
        for uid in top10_ids if uid in top10_users
    ]

    kpis = {
        'students':       total_students,
        'courses_done':   completed_count,
        'courses_total':  enrolled_count,
        'lessons_done':   lessons_done,
        'lessons_total':  lessons_total,
        'tasks_done':     tasks_done,
        'tasks_total':    tasks_total,
        'exams_passed':   exams_passed,
        'exams_total':    exams_total,
    }

    return render(request, 'courses/dashboard.html', {
        'active_nav':         'home',
        'overall_progress':   overall_progress,
        'enrolled_count':     enrolled_count,
        'completed_count':    completed_count,
        'certificates_count': certificates_count,
        'enrollments':        enrollments,
        'kpis':               kpis,
        'user_points':        user_points,
        'lessons_done':       lessons_done,
        'exams_passed':       exams_passed,
        'top10':              top10,
    })


@login_required
def my_courses(request):
    enrollments = (Enrollment.objects
                   .filter(student=request.user)
                   .select_related('course')
                   .prefetch_related('course__categories')
                   .annotate(avg_rating=Avg('course__reviews__rating'))
                   .order_by('-enrolled_at'))

    enrolled_ids = {enr.course_id for enr in enrollments}

    available_courses = (Course.objects
                         .filter(is_published=True)
                         .exclude(pk__in=enrolled_ids)
                         .prefetch_related('categories')
                         .annotate(avg_rating=Avg('reviews__rating'))
                         .order_by('-created_at'))

    return render(request, 'courses/my_courses.html', {
        'active_nav':        'my_courses',
        'enrollments':       enrollments,
        'available_courses': available_courses,
    })


@login_required
def biblioteca(request, folder_id=None):
    current_folder = DocFolder.objects.get(pk=folder_id) if folder_id else None
    subfolders = DocFolder.objects.filter(parent=current_folder).order_by('order', 'name')
    files      = DocFile.objects.filter(folder=current_folder).order_by('name') if current_folder else []
    root_folders = DocFolder.objects.filter(parent=None).order_by('order', 'name')

    return render(request, 'courses/biblioteca.html', {
        'active_nav':     'biblioteca',
        'current_folder': current_folder,
        'subfolders':     subfolders,
        'files':          files,
        'root_folders':   root_folders,
        'breadcrumb':     current_folder.breadcrumb() if current_folder else [],
    })


def course_list(request):
    category_slug = request.GET.get('categoria', '')
    q = request.GET.get('q', '').strip()

    courses = Course.objects.filter(is_published=True).prefetch_related('categories').order_by('-created_at')

    if category_slug:
        courses = courses.filter(categories__slug=category_slug)

    if q:
        courses = courses.filter(title__icontains=q)

    categories = Category.objects.order_by('order', 'name')

    # IDs de cursos en los que el usuario ya está inscrito
    enrolled_ids = set()
    if request.user.is_authenticated:
        enrolled_ids = set(
            Enrollment.objects.filter(student=request.user).values_list('course_id', flat=True)
        )

    return render(request, 'courses/course_list.html', {
        'courses':      courses,
        'categories':   categories,
        'selected_cat': category_slug,
        'q':            q,
        'enrolled_ids': enrolled_ids,
    })


def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    # Solo el instructor o usuarios con acceso pueden ver cursos no publicados
    if not course.is_published:
        is_instructor = request.user.is_authenticated and (
            course.instructor == request.user or request.user.is_staff
        )
        is_enrolled = request.user.is_authenticated and Enrollment.objects.filter(
            student=request.user, course=course
        ).exists()
        if not (is_instructor or is_enrolled):
            from django.http import Http404
            raise Http404
    topics = (course.topics
              .filter(is_active=True)
              .prefetch_related(
                  'lessons',
                  'lessons__attachments',
                  'lessons__comments',
                  'lessons__comments__author',
                  'lessons__comments__author__profile',
                  'lessons__comments__replies',
                  'lessons__comments__replies__author',
                  'lessons__comments__replies__author__profile',
                  'lessons__tasks',
              ))

    enrollment = None
    completed_ids   = set()
    submitted_tasks = set()
    passed_exam     = None
    all_completed   = False
    if request.user.is_authenticated:
        enrollment = Enrollment.objects.filter(student=request.user, course=course).first()
        if enrollment:
            completed_ids = set(
                LessonProgress.objects.filter(
                    student=request.user, lesson__course=course
                ).values_list('lesson_id', flat=True)
            )
            submitted_tasks = set(
                TaskSubmission.objects.filter(
                    student=request.user, task__lesson__course=course
                ).values_list('task_id', flat=True)
            )
            total_lessons = Lesson.objects.filter(course=course, is_active=True).count()
            total_tasks   = Task.objects.filter(lesson__course=course, is_active=True).count()
            total         = total_lessons + total_tasks
            done          = len(completed_ids) + len(submitted_tasks)
            all_completed = (total > 0 and done >= total)
            exam = getattr(course, 'exam', None)
            if exam and exam.is_active:
                latest_attempt = ExamAttempt.objects.filter(
                    student=request.user, exam=exam
                ).order_by('-attempted_at').first()
                passed_exam = latest_attempt if (latest_attempt and latest_attempt.passed) else None

    return render(request, 'courses/course_detail.html', {
        'course':          course,
        'topics':          topics,
        'enrollment':      enrollment,
        'completed_ids':   completed_ids,
        'submitted_tasks': submitted_tasks,
        'all_completed':   all_completed,
        'pending_tasks':   Task.objects.filter(
            lesson__course=course, is_active=True
        ).select_related('lesson').exclude(
            pk__in=submitted_tasks
        ) if enrollment else [],
        'exam':            getattr(course, 'exam', None) if enrollment else None,
        'passed_exam':     passed_exam,
        'reviews':         CourseReview.objects.filter(course=course).select_related('student', 'student__profile').order_by('-created_at'),
        'user_review':     CourseReview.objects.filter(course=course, student=request.user).first() if enrollment else None,
        'avg_rating':          CourseReview.objects.filter(course=course).aggregate(avg=Avg('rating'))['avg'],
        'enrollment_count':    Enrollment.objects.filter(course=course).count(),
    })


@login_required
@require_POST
def submit_task(request, slug, task_id):
    course = get_object_or_404(Course, slug=slug, is_published=True)
    task   = get_object_or_404(Task, pk=task_id, lesson__course=course, is_active=True)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course)

    existing = TaskSubmission.objects.filter(student=request.user, task=task).first()

    if existing:
        # Desmarcar
        existing.delete()
    else:
        attachment = request.FILES.get('attachment') if task.requires_attachment else None
        TaskSubmission.objects.create(
            task=task, student=request.user, attachment=attachment
        )

    # Recalcular progreso
    total_lessons = Lesson.objects.filter(course=course, is_active=True).count()
    total_tasks   = Task.objects.filter(lesson__course=course, is_active=True).count()
    total = total_lessons + total_tasks
    if total:
        done_lessons = LessonProgress.objects.filter(student=request.user, lesson__course=course).count()
        done_tasks   = TaskSubmission.objects.filter(student=request.user, task__lesson__course=course).count()
        enrollment.progress = int((done_lessons + done_tasks) * 100 / total)
        enrollment.save(update_fields=['progress'])

    return redirect(f"{request.META.get('HTTP_REFERER', '/')}#task-{task_id}")


@login_required
@require_POST
def add_comment(request, slug, lesson_id):
    course   = get_object_or_404(Course, slug=slug, is_published=True)
    lesson   = get_object_or_404(Lesson, pk=lesson_id, course=course)
    get_object_or_404(Enrollment, student=request.user, course=course)

    content   = request.POST.get('content', '').strip()
    parent_id = request.POST.get('parent_id', '').strip()

    if content:
        parent = LessonComment.objects.filter(pk=parent_id, lesson=lesson).first() if parent_id else None
        LessonComment.objects.create(
            lesson=lesson,
            author=request.user,
            parent=parent,
            content=content,
        )
    return redirect(f"{request.META.get('HTTP_REFERER', '/')}#lesson-{lesson_id}")


@login_required
@require_POST
def review_course(request, slug):
    course = get_object_or_404(Course, slug=slug, is_published=True)
    get_object_or_404(Enrollment, student=request.user, course=course)

    try:
        rating = int(request.POST.get('rating', 0))
        if not 1 <= rating <= 5:
            raise ValueError
    except (ValueError, TypeError):
        return redirect('courses:course_detail', slug=slug)

    comment = request.POST.get('comment', '').strip()
    CourseReview.objects.update_or_create(
        course=course, student=request.user,
        defaults={'rating': rating, 'comment': comment},
    )
    return redirect(f"{request.META.get('HTTP_REFERER', '/')}#valoraciones")


@login_required
@require_POST
def enroll(request, slug):
    course = get_object_or_404(Course, slug=slug, is_published=True)
    Enrollment.objects.get_or_create(student=request.user, course=course)
    return redirect('courses:course_detail', slug=slug)


@login_required
@require_POST
def toggle_lesson(request, slug, lesson_id):
    course = get_object_or_404(Course, slug=slug, is_published=True)
    lesson = get_object_or_404(Lesson, pk=lesson_id, course=course)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course)

    done, created = LessonProgress.objects.get_or_create(student=request.user, lesson=lesson)
    if not created:
        done.delete()  # desmarcar si ya estaba marcado

    # Recalcular progreso del enrollment
    total = Lesson.objects.filter(course=course, is_active=True).count()
    if total:
        completed = LessonProgress.objects.filter(
            student=request.user, lesson__course=course
        ).count()
        enrollment.progress = int(completed * 100 / total)
        enrollment.save(update_fields=['progress'])

    return redirect(f"{request.META.get('HTTP_REFERER', '/')}#lesson-{lesson_id}")


def course_list(request):
    category_slug = request.GET.get('categoria', '')
    q = request.GET.get('q', '').strip()

    courses = Course.objects.filter(is_published=True).prefetch_related('categories').order_by('-created_at')

    if category_slug:
        courses = courses.filter(categories__slug=category_slug)

    if q:
        courses = courses.filter(title__icontains=q)

    categories = Category.objects.order_by('order', 'name')

    enrolled_ids = set()
    if request.user.is_authenticated:
        enrolled_ids = set(
            Enrollment.objects.filter(student=request.user).values_list('course_id', flat=True)
        )

    return render(request, 'courses/course_list.html', {
        'courses':      courses,
        'categories':   categories,
        'selected_cat': category_slug,
        'q':            q,
        'enrolled_ids': enrolled_ids,
    })


@login_required
def take_exam(request, slug):
    course = get_object_or_404(Course, slug=slug, is_published=True)
    exam   = get_object_or_404(Exam, course=course, is_active=True)
    get_object_or_404(Enrollment, student=request.user, course=course)

    questions = exam.questions.prefetch_related('choices').order_by('order')
    attempts  = ExamAttempt.objects.filter(student=request.user, exam=exam).order_by('-attempted_at')

    if request.method == 'POST':
        multiple_qs = questions.filter(question_type='multiple')
        upload_qs   = questions.filter(question_type='upload')
        total_multiple = multiple_qs.count()
        total_upload   = upload_qs.count()
        total = questions.count()
        correct = 0

        # Evaluar opción múltiple
        for question in multiple_qs:
            choice_id = request.POST.get(f'q_{question.pk}')
            if choice_id:
                try:
                    choice = question.choices.get(pk=choice_id)
                    if choice.is_correct:
                        correct += 1
                except Exception:
                    pass

        # Contar adjuntos subidos como correctos
        for question in upload_qs:
            if f'q_{question.pk}' in request.FILES:
                correct += 1  # auto-correcto si sube algo

        score  = int(correct * 100 / total) if total else 0
        passed = score >= exam.passing_score
        attempt = ExamAttempt.objects.create(
            student=request.user, exam=exam, score=score, passed=passed
        )

        # Guardar archivos subidos
        for question in upload_qs:
            f = request.FILES.get(f'q_{question.pk}')
            if f:
                ExamUpload.objects.create(attempt=attempt, question=question, file=f)

        return redirect('courses:exam_result', slug=slug, attempt_id=attempt.pk)

    return render(request, 'courses/exam.html', {
        'course':    course,
        'exam':      exam,
        'questions': questions,
        'attempts':  attempts,
    })


@login_required
def exam_result(request, slug, attempt_id):
    course  = get_object_or_404(Course, slug=slug, is_published=True)
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id, student=request.user, exam__course=course)
    all_attempts = ExamAttempt.objects.filter(student=request.user, exam=attempt.exam).order_by('-attempted_at')
    best_passed  = all_attempts.filter(passed=True).order_by('-attempted_at').first()
    # Solo puede descargar si el ÚLTIMO intento fue aprobado
    last_attempt_passed = all_attempts.first()  # ya ordenado por -attempted_at
    can_download = last_attempt_passed and last_attempt_passed.passed

    return render(request, 'courses/exam_result.html', {
        'course':       course,
        'attempt':      attempt,
        'all_attempts': all_attempts,
        'best_passed':  best_passed,
        'can_download': can_download,
    })


@login_required
def certificate(request, slug):
    import qrcode, io, base64
    from accounts.models import UserProfile
    course   = get_object_or_404(Course, slug=slug, is_published=True)
    get_object_or_404(Enrollment, student=request.user, course=course)
    exam     = get_object_or_404(Exam, course=course, is_active=True)
    passed   = ExamAttempt.objects.filter(
        student=request.user, exam=exam
    ).order_by('-attempted_at').first()
    if not passed or not passed.passed:
        return redirect('courses:take_exam', slug=slug)

    student_profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        sig_data = request.POST.get('signature_data', '').strip()
        if sig_data:
            student_profile.signature = sig_data
            student_profile.save()
        return redirect('courses:certificate', slug=slug)

    if not student_profile.has_signature:
        return render(request, 'courses/certificate_sign.html', {
            'course':  course,
            'attempt': passed,
        })

    instructor_profile, _ = UserProfile.objects.get_or_create(user=course.instructor)

    # Generar QR con URL de verificación pública
    verify_url = request.build_absolute_uri(f'/verificar/{passed.pk}/')
    qr = qrcode.QRCode(box_size=5, border=2,
                       error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    qr_b64 = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()

    return render(request, 'courses/certificate.html', {
        'course':               course,
        'student':              request.user,
        'attempt':              passed,
        'student_signature':    student_profile.signature,
        'instructor_signature': instructor_profile.signature if instructor_profile.has_signature else None,
        'qr_code':              qr_b64,
        'verify_url':           verify_url,
    })


def verify_certificate(request, attempt_id):
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id, passed=True)
    return render(request, 'courses/certificate_verify.html', {
        'attempt': attempt,
        'course':  attempt.exam.course,
        'student': attempt.student,
    })



# ─── PROFESORES ──────────────────────────────────────────────────

@login_required
def teachers_list(request):
    from courses.models import Enrollment, TeacherRating
    from django.db.models import Avg, Count
    # Profesores de los cursos en los que está inscrito el estudiante
    enrolled_course_ids = Enrollment.objects.filter(
        student=request.user
    ).values_list("course_id", flat=True)

    teachers = (
        User.objects
        .filter(courses_taught__pk__in=enrolled_course_ids, is_active=True)
        .distinct()
        .annotate(
            avg_rating=Avg("teacher_ratings__rating"),
            rating_count=Count("teacher_ratings"),
        )
        .order_by("first_name", "last_name")
    )

    # Valoraciones ya dadas por este estudiante
    my_ratings = {
        r.teacher_id: r.rating
        for r in TeacherRating.objects.filter(student=request.user)
    }

    # Mensajes no leídos por profesor
    from courses.models import TeacherMessage
    unread = {
        tm["teacher_id"]: tm["cnt"]
        for tm in TeacherMessage.objects.filter(
            student=request.user, sender=F("teacher"), is_read=False
        ).values("teacher_id").annotate(cnt=Count("id"))
    }

    return render(request, "courses/teachers.html", {
        "active_nav": "teachers",
        "teachers":   teachers,
        "my_ratings": my_ratings,
        "unread":     unread,
    })


@login_required
def teacher_detail(request, teacher_id):
    from courses.models import TeacherRating, TeacherMessage, Enrollment
    teacher = get_object_or_404(User, pk=teacher_id, is_active=True)

    # Verificar que el estudiante comparte al menos un curso con el profesor
    enrolled_course_ids = Enrollment.objects.filter(
        student=request.user
    ).values_list("course_id", flat=True)
    if not User.objects.filter(
        pk=teacher_id, courses_taught__pk__in=enrolled_course_ids
    ).exists() and not request.user.is_staff:
        from django.http import Http404
        raise Http404

    # Cursos del profesor en los que está inscrito este estudiante
    from courses.models import Course
    shared_courses = Course.objects.filter(
        instructor=teacher, pk__in=enrolled_course_ids, is_published=True
    )

    # Valoración del estudiante actual
    my_rating = TeacherRating.objects.filter(
        teacher=teacher, student=request.user
    ).first()

    # Todas las valoraciones públicas
    all_ratings = TeacherRating.objects.filter(
        teacher=teacher
    ).select_related("student", "student__profile").order_by("-created_at")

    from django.db.models import Avg
    avg_rating = all_ratings.aggregate(avg=Avg("rating"))["avg"]

    # Hilo de mensajes con este profesor
    messages_qs = TeacherMessage.objects.filter(
        teacher=teacher, student=request.user
    ).select_related("sender")

    # Marcar como leídos los mensajes del profesor al estudiante
    TeacherMessage.objects.filter(
        teacher=teacher, student=request.user, sender=teacher, is_read=False
    ).update(is_read=True)

    return render(request, "courses/teacher_detail.html", {
        "active_nav":    "teachers",
        "teacher":       teacher,
        "shared_courses": shared_courses,
        "my_rating":     my_rating,
        "all_ratings":   all_ratings,
        "avg_rating":    avg_rating,
        "messages":      messages_qs,
    })


@login_required
@require_POST
def teacher_send_message(request, teacher_id):
    from courses.models import TeacherMessage
    from django.contrib import messages as djmsg
    teacher = get_object_or_404(User, pk=teacher_id, is_active=True)
    content = request.POST.get("content", "").strip()

    if not content:
        djmsg.error(request, "El mensaje no puede estar vacío.")
        if request.user == teacher:
            return redirect("courses:teacher_inbox")
        return redirect("courses:teacher_detail", teacher_id=teacher_id)

    # El profesor responde a un estudiante (student_id viene en el POST)
    if request.user == teacher:
        student_id = request.POST.get("student_id")
        if not student_id:
            djmsg.error(request, "No se ha especificado el destinatario.")
            return redirect("courses:teacher_inbox")
        student = get_object_or_404(User, pk=student_id)
    else:
        # Un estudiante escribe a su profesor; evitar mensajear a uno mismo
        if request.user.pk == teacher.pk:
            djmsg.error(request, "No puedes enviarte un mensaje a ti mismo.")
            return redirect("courses:teachers")
        student = request.user

    TeacherMessage.objects.create(
        teacher=teacher,
        student=student,
        sender=request.user,
        content=content,
    )

    if request.user == teacher:
        return redirect("courses:teacher_thread", student_id=student.pk)
    return redirect("courses:teacher_detail", teacher_id=teacher_id)


@login_required
@require_POST
def teacher_rate(request, teacher_id):
    from courses.models import TeacherRating
    teacher = get_object_or_404(User, pk=teacher_id, is_active=True)
    try:
        rating_val = int(request.POST.get("rating", 5))
        if not 1 <= rating_val <= 5:
            raise ValueError
    except (ValueError, TypeError):
        rating_val = 5

    comment = request.POST.get("comment", "").strip()
    TeacherRating.objects.update_or_create(
        teacher=teacher, student=request.user,
        defaults={"rating": rating_val, "comment": comment},
    )
    from django.contrib import messages as djmsg
    djmsg.success(request, "¡Valoración guardada!")
    return redirect("courses:teacher_detail", teacher_id=teacher_id)


@login_required
def teacher_inbox(request):
    """Vista del profesor: bandeja de mensajes de sus estudiantes."""
    from courses.models import TeacherMessage
    from django.db.models import Max, Count

    # Hilos agrupados por estudiante
    threads = (
        TeacherMessage.objects
        .filter(teacher=request.user)
        .values("student_id")
        .annotate(
            last_msg=Max("created_at"),
            unread=Count("id", filter=Q(sender=F("student"), is_read=False)),
        )
        .order_by("-last_msg")
    )

    student_ids = [t["student_id"] for t in threads]
    students_map = {u.pk: u for u in User.objects.filter(pk__in=student_ids)}

    thread_list = []
    for t in threads:
        s = students_map.get(t["student_id"])
        if s:
            last = TeacherMessage.objects.filter(
                teacher=request.user, student=s
            ).order_by("-created_at").first()
            thread_list.append({
                "student": s,
                "last_msg": last,
                "unread": t["unread"],
            })

    return render(request, "courses/teacher_inbox.html", {
        "active_nav": "teachers",
        "threads":    thread_list,
    })


@login_required
def teacher_thread(request, student_id):
    """El profesor ve el hilo completo con un estudiante."""
    from courses.models import TeacherMessage
    student = get_object_or_404(User, pk=student_id)
    # Solo el profesor del hilo puede verlo
    msgs = TeacherMessage.objects.filter(
        teacher=request.user, student=student
    ).select_related("sender")

    # Marcar leídos los del estudiante
    TeacherMessage.objects.filter(
        teacher=request.user, student=student, sender=student, is_read=False
    ).update(is_read=True)

    return render(request, "courses/teacher_thread.html", {
        "active_nav": "teachers",
        "student":    student,
        "messages":   msgs,
    })


# ─── MIS DOCUMENTOS ──────────────────────────────────────────────

@login_required
def my_docs(request, folder_id=None):
    from courses.models import UserFolder, UserFile, UserNote, UserWhiteboard, FolderShare, UserPresentation, UserCAD, SavedLink
    from django.db.models import Q
    current = None
    if folder_id:
        current = get_object_or_404(UserFolder, pk=folder_id, user=request.user)

    subfolders    = UserFolder.objects.filter(user=request.user, parent=current).order_by('name')
    files         = UserFile.objects.filter(user=request.user, folder=current) if current else []
    notes         = UserNote.objects.filter(user=request.user, folder=current) if current else []
    whiteboards   = UserWhiteboard.objects.filter(user=request.user, folder=current) if current else []
    presentations = UserPresentation.objects.filter(user=request.user, folder=current) if current else []
    cad_files     = UserCAD.objects.filter(user=request.user, folder=current) if current else []
    root_folders  = UserFolder.objects.filter(user=request.user, parent=None).order_by('name')

    # Carpetas compartidas conmigo (solo en la raíz)
    shared_folders = []
    global_shared_folders = []
    if not current:
        try:
            company = request.user.profile.company
        except Exception:
            company = None
        shared_folders = (FolderShare.objects
                          .filter(Q(with_user=request.user) |
                                  (Q(with_company=company) if company else Q(pk__in=[])))
                          .select_related('folder', 'folder__user', 'shared_by')
                          .order_by('folder__name'))
        global_shared_folders = (UserFolder.objects
                                  .filter(shared_with_all=True)
                                  .exclude(user=request.user)
                                  .select_related('user')
                                  .order_by('name'))

    return render(request, 'courses/my_docs.html', {
        'active_nav':            'my_docs',
        'current':               current,
        'subfolders':            subfolders,
        'files':                 files,
        'notes':                 notes,
        'whiteboards':           whiteboards,
        'presentations':         presentations,
        'cad_files':             cad_files,
        'root_folders':          root_folders,
        'breadcrumb':            current.breadcrumb() if current else [],
        'shared_folders':        shared_folders,
        'global_shared_folders': global_shared_folders,
    })


@login_required
@require_POST
def my_docs_new_folder(request, folder_id=None):
    from courses.models import UserFolder
    name = request.POST.get('name', '').strip()
    parent = None
    if folder_id:
        parent = get_object_or_404(UserFolder, pk=folder_id, user=request.user)
    if name:
        UserFolder.objects.get_or_create(user=request.user, parent=parent, name=name)
    if parent:
        return redirect('courses:my_docs_folder', folder_id=parent.pk)
    return redirect('courses:my_docs')


@login_required
@require_POST
def my_docs_edit_folder(request, folder_id):
    from courses.models import UserFolder
    folder = get_object_or_404(UserFolder, pk=folder_id, user=request.user)
    name = request.POST.get('name', '').strip()
    if name:
        folder.name = name
        folder.save(update_fields=['name'])
    if folder.parent:
        return redirect('courses:my_docs_folder', folder_id=folder.parent_id)
    return redirect('courses:my_docs')


@login_required
@require_POST
def my_docs_delete_folder(request, folder_id):
    from courses.models import UserFolder
    folder = get_object_or_404(UserFolder, pk=folder_id, user=request.user)
    parent_id = folder.parent_id
    folder.delete()
    if parent_id:
        return redirect('courses:my_docs_folder', folder_id=parent_id)
    return redirect('courses:my_docs')


@login_required
@require_POST
def my_docs_upload_file(request, folder_id):
    from courses.models import UserFolder, UserFile
    folder = get_object_or_404(UserFolder, pk=folder_id, user=request.user)
    uploaded = request.FILES.get('file')
    if uploaded:
        UserFile.objects.create(
            folder=folder, user=request.user,
            name=uploaded.name, file=uploaded,
        )
    return redirect('courses:my_docs_folder', folder_id=folder_id)


@login_required
@require_POST
def my_docs_delete_file(request, file_id):
    from courses.models import UserFile
    import os
    f = get_object_or_404(UserFile, pk=file_id, user=request.user)
    folder_id = f.folder_id
    if f.file and os.path.isfile(f.file.path):
        os.remove(f.file.path)
    f.delete()
    return redirect('courses:my_docs_folder', folder_id=folder_id)


@login_required
def my_docs_note_edit(request, folder_id=None, note_id=None):
    from courses.models import UserFolder, UserNote
    note   = None
    folder = None

    if note_id:
        note   = get_object_or_404(UserNote, pk=note_id, user=request.user)
        folder = note.folder
    elif folder_id:
        folder = get_object_or_404(UserFolder, pk=folder_id, user=request.user)

    if request.method == 'POST':
        title   = request.POST.get('title', '').strip() or 'Sin título'
        content = request.POST.get('content', '')
        if note:
            note.title   = title
            note.content = content
            note.save()
        else:
            note = UserNote.objects.create(
                folder=folder, user=request.user,
                title=title, content=content,
            )
        return redirect('courses:my_docs_folder', folder_id=note.folder_id)

    return render(request, 'courses/my_docs_note.html', {
        'active_nav': 'my_docs',
        'note':       note,
        'folder':     folder,
    })


@login_required
@require_POST
def my_docs_note_delete(request, note_id):
    from courses.models import UserNote
    note = get_object_or_404(UserNote, pk=note_id, user=request.user)
    folder_id = note.folder_id
    note.delete()
    return redirect('courses:my_docs_folder', folder_id=folder_id)


@login_required
@require_POST
def my_docs_note_share(request, note_id):
    import uuid
    from courses.models import UserNote
    note   = get_object_or_404(UserNote, pk=note_id, user=request.user)
    action = request.POST.get('action', 'enable')
    if action == 'disable':
        note.share_token = None
    else:
        if not note.share_token:
            note.share_token = uuid.uuid4()
    note.save(update_fields=['share_token'])
    return redirect('courses:my_docs_note_edit', note_id=note.pk)


def public_note_view(request, token):
    from courses.models import UserNote
    note = get_object_or_404(UserNote, share_token=token)
    return render(request, 'courses/public_note.html', {'note': note})


# ─── SUBIDA DE GRABACIÓN DE PANTALLA ─────────────────────────────

@login_required
@require_POST
def my_docs_record_upload(request):
    """Recibe un archivo de grabación de pantalla y lo guarda en Mis documentos."""
    from courses.models import UserFolder, UserFile
    from django.utils.timezone import localtime, now
    import os

    recording = request.FILES.get('recording')
    if not recording:
        return JsonResponse({'ok': False, 'error': 'No se recibió ningún archivo.'}, status=400)

    # Carpeta automática "Grabaciones"
    folder, _ = UserFolder.objects.get_or_create(
        user=request.user, name='Grabaciones', parent=None
    )

    timestamp = localtime(now()).strftime('%Y%m%d_%H%M%S')
    filename  = f'Grabacion_{timestamp}.webm'

    file_obj = UserFile(folder=folder, user=request.user, name=filename)
    file_obj.file.save(filename, recording, save=True)

    return JsonResponse({'ok': True, 'name': filename})


# ─── COMPARTIR ARCHIVOS Y CARPETAS ───────────────────────────────

@login_required
@require_POST
def my_docs_share_file(request, file_id):
    """Genera o revoca el token de compartir de un archivo."""
    import uuid as _uuid
    from courses.models import UserFile
    f = get_object_or_404(UserFile, pk=file_id, user=request.user)
    if f.share_token:
        f.share_token = None
    else:
        f.share_token = _uuid.uuid4()
    f.save(update_fields=['share_token'])
    return JsonResponse({'ok': True, 'shared': f.share_token is not None,
                         'token': str(f.share_token) if f.share_token else None})


@login_required
@require_POST
def my_docs_share_folder(request, folder_id):
    """Genera o revoca el token de compartir de una carpeta."""
    import uuid as _uuid
    from courses.models import UserFolder
    folder = get_object_or_404(UserFolder, pk=folder_id, user=request.user)
    if folder.share_token:
        folder.share_token = None
    else:
        folder.share_token = _uuid.uuid4()
    folder.save(update_fields=['share_token'])
    return JsonResponse({'ok': True, 'shared': folder.share_token is not None,
                         'token': str(folder.share_token) if folder.share_token else None})


def public_file_view(request, token):
    """Página pública de un archivo compartido."""
    from courses.models import UserFile
    f = get_object_or_404(UserFile, share_token=token)
    f.view_count = F('view_count') + 1
    f.save(update_fields=['view_count'])
    f.refresh_from_db(fields=['view_count'])
    return render(request, 'courses/public_file.html', {'file': f})


def public_folder_view(request, token):
    """Página pública de una carpeta compartida."""
    from courses.models import UserFolder
    folder = get_object_or_404(UserFolder, share_token=token)
    folder.view_count = F('view_count') + 1
    folder.save(update_fields=['view_count'])
    folder.refresh_from_db(fields=['view_count'])
    files = folder.files.select_related('user').order_by('name')
    notes = folder.notes.filter(share_token__isnull=False).order_by('title')
    return render(request, 'courses/public_folder.html', {
        'folder': folder, 'files': files, 'notes': notes,
    })


# ─── PIZARRAS (WHITEBOARD) ────────────────────────────────────────

@login_required
def my_docs_whiteboard_new(request, folder_id):
    from courses.models import UserFolder, UserWhiteboard
    folder = get_object_or_404(UserFolder, pk=folder_id, user=request.user)
    wb = UserWhiteboard.objects.create(user=request.user, folder=folder)
    return redirect('courses:my_docs_whiteboard', whiteboard_id=wb.pk)


@login_required
def my_docs_whiteboard(request, whiteboard_id):
    from courses.models import UserWhiteboard
    wb = get_object_or_404(UserWhiteboard, pk=whiteboard_id, user=request.user)
    return render(request, 'courses/whiteboard.html', {
        'active_nav': 'my_docs',
        'wb': wb,
    })


@login_required
@require_POST
def my_docs_whiteboard_save(request, whiteboard_id):
    """Guardar datos JSON de la pizarra (AJAX)."""
    import json
    from courses.models import UserWhiteboard
    wb = get_object_or_404(UserWhiteboard, pk=whiteboard_id, user=request.user)
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'ok': False}, status=400)
    title = body.get('title', '').strip() or 'Pizarra sin título'
    data  = body.get('data', '')
    wb.title = title
    wb.data  = data if isinstance(data, str) else json.dumps(data)
    wb.save(update_fields=['title', 'data', 'updated_at'])
    return JsonResponse({'ok': True})


@login_required
@require_POST
def my_docs_whiteboard_delete(request, whiteboard_id):
    from courses.models import UserWhiteboard
    wb = get_object_or_404(UserWhiteboard, pk=whiteboard_id, user=request.user)
    folder_id = wb.folder_id
    wb.delete()
    if folder_id:
        return redirect('courses:my_docs_folder', folder_id=folder_id)
    return redirect('courses:my_docs')


@login_required
@require_POST
def my_docs_whiteboard_share(request, whiteboard_id):
    import uuid as _uuid
    from courses.models import UserWhiteboard
    wb = get_object_or_404(UserWhiteboard, pk=whiteboard_id, user=request.user)
    if wb.share_token:
        wb.share_token = None
    else:
        wb.share_token = _uuid.uuid4()
    wb.save(update_fields=['share_token'])
    return JsonResponse({'ok': True, 'shared': wb.share_token is not None,
                         'token': str(wb.share_token) if wb.share_token else None})


def public_whiteboard_view(request, token):
    from courses.models import UserWhiteboard
    wb = get_object_or_404(UserWhiteboard, share_token=token)
    wb.view_count = F('view_count') + 1
    wb.save(update_fields=['view_count'])
    wb.refresh_from_db(fields=['view_count'])
    return render(request, 'courses/public_whiteboard.html', {'wb': wb})


# ─── COMPARTIR CARPETA CON USUARIO / EMPRESA ─────────────────────

@login_required
def folder_share_api(request, folder_id):
    """Gestiona compartir directo de una carpeta con usuario o empresa."""
    from courses.models import UserFolder, FolderShare
    from accounts.models import Company
    folder = get_object_or_404(UserFolder, pk=folder_id, user=request.user)

    if request.method == 'POST':
        action    = request.POST.get('action')
        ttype     = request.POST.get('type')          # 'user' | 'company'
        target_id = request.POST.get('target_id', '').strip()
        share_id  = request.POST.get('share_id', '').strip()

        if action == 'add':
            if ttype == 'user' and target_id:
                from django.contrib.auth.models import User as _User
                target_user = get_object_or_404(_User, pk=target_id)
                if target_user != request.user:
                    FolderShare.objects.get_or_create(
                        folder=folder, shared_by=request.user,
                        with_user=target_user, with_company=None,
                    )
            elif ttype == 'company' and target_id:
                company = get_object_or_404(Company, pk=target_id)
                FolderShare.objects.get_or_create(
                    folder=folder, shared_by=request.user,
                    with_user=None, with_company=company,
                )

        elif action == 'remove' and share_id:
            FolderShare.objects.filter(pk=share_id, folder=folder, shared_by=request.user).delete()

    # Devuelve lista actual de shares
    shares = FolderShare.objects.filter(folder=folder, shared_by=request.user).select_related(
        'with_user', 'with_company'
    )
    data = []
    for s in shares:
        if s.with_user_id:
            data.append({'id': s.pk, 'type': 'user',
                         'name': s.with_user.get_full_name() or s.with_user.username,
                         'sub': s.with_user.username})
        else:
            data.append({'id': s.pk, 'type': 'company',
                         'name': str(s.with_company), 'sub': 'empresa'})
    return JsonResponse({'ok': True, 'shares': data})


@login_required
def folder_share_search(request):
    """Búsqueda de usuarios y empresas para compartir carpetas."""
    from accounts.models import Company
    q = request.GET.get('q', '').strip()
    results = []
    if len(q) >= 2:
        from django.contrib.auth.models import User as _User
        from django.db.models import Q
        users = _User.objects.filter(is_active=True).exclude(pk=request.user.pk).filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) |
            Q(username__icontains=q) | Q(email__icontains=q)
        )[:8]
        for u in users:
            results.append({'id': u.pk, 'type': 'user',
                            'name': u.get_full_name() or u.username,
                            'sub': u.username})
        companies = Company.objects.filter(name__icontains=q)[:5]
        for c in companies:
            results.append({'id': c.pk, 'type': 'company', 'name': c.name, 'sub': 'empresa'})
    return JsonResponse({'results': results})


@login_required
@require_POST
def folder_share_all(request, folder_id):
    """Activa o desactiva compartir una carpeta con todos los usuarios."""
    from courses.models import UserFolder
    folder = get_object_or_404(UserFolder, pk=folder_id, user=request.user)
    enable = request.POST.get('action', 'enable') == 'enable'
    folder.shared_with_all = enable
    folder.save(update_fields=['shared_with_all'])
    return JsonResponse({'ok': True, 'shared_with_all': folder.shared_with_all})


@login_required
def shared_folder_view(request, folder_id):
    """Vista de lectura de una carpeta compartida directamente con el usuario."""
    from courses.models import UserFolder, UserFile, UserNote, UserWhiteboard, FolderShare
    from accounts.models import Company
    from django.db.models import Q
    folder = get_object_or_404(UserFolder, pk=folder_id)

    # Verificar acceso
    try:
        company = request.user.profile.company
    except Exception:
        company = None

    has_access = folder.shared_with_all or FolderShare.objects.filter(
        folder=folder
    ).filter(
        Q(with_user=request.user) | (Q(with_company=company) if company else Q(pk__in=[]))
    ).exists()

    if not has_access and folder.user != request.user:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('No tienes acceso a esta carpeta.')

    files       = folder.files.order_by('name')
    notes       = folder.notes.order_by('title')
    whiteboards = folder.whiteboards.order_by('title')

    return render(request, 'courses/my_docs.html', {
        'active_nav':    'my_docs',
        'current':       folder,
        'subfolders':    [],
        'files':         files,
        'notes':         notes,
        'whiteboards':   whiteboards,
        'root_folders':  [],
        'breadcrumb':    [folder],
        'shared_folders': [],
        'readonly':      True,
        'shared_owner':  folder.user,
    })


# ─── CAPTURADOR DE ARCHIVOS ──────────────────────────────────────────────────────

@login_required
@require_POST
def folder_capture_toggle(request, folder_id):
    """Genera o revoca el token de captura de una carpeta."""
    import uuid as _uuid
    from courses.models import UserFolder
    folder = get_object_or_404(UserFolder, pk=folder_id, user=request.user)
    if folder.capture_token:
        folder.capture_token = None
    else:
        folder.capture_token = _uuid.uuid4()
    folder.save(update_fields=['capture_token'])
    return JsonResponse({
        'ok': True,
        'active': folder.capture_token is not None,
        'token': str(folder.capture_token) if folder.capture_token else None,
    })


def folder_capture_view(request, token):
    """Página pública de captura: cualquiera con el link puede subir archivos."""
    from courses.models import UserFolder
    folder = get_object_or_404(UserFolder, capture_token=token)
    try:
        importados = UserFolder.objects.get(user=folder.user, parent=folder, name='Importados')
        files = list(importados.files.order_by('-created_at'))
    except UserFolder.DoesNotExist:
        files = []
    return render(request, 'courses/folder_capture.html', {
        'folder': folder,
        'token': str(token),
        'files': files,
    })


def folder_capture_upload(request, token):
    """Recibe archivos arrastrados y los guarda en subcarpeta 'Importados'."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)
    from courses.models import UserFolder, UserFile
    folder = get_object_or_404(UserFolder, capture_token=token)

    # Obtener o crear subcarpeta "Importados" dentro de la carpeta destino
    importados, _ = UserFolder.objects.get_or_create(
        user=folder.user,
        parent=folder,
        name='Importados',
    )

    uploaded = request.FILES.getlist('files')
    if not uploaded:
        return JsonResponse({'ok': False, 'error': 'Sin archivos'}, status=400)

    MAX_SIZE = 50 * 1024 * 1024  # 50 MB por archivo
    saved = []
    for f in uploaded:
        if f.size > MAX_SIZE:
            continue
        import os
        safe_name = os.path.basename(f.name) or 'archivo'
        uf = UserFile.objects.create(
            folder=importados,
            user=folder.user,
            name=safe_name,
            file=f,
        )
        saved.append({'name': safe_name, 'url': uf.file.url, 'id': uf.pk})

    return JsonResponse({'ok': True, 'saved': saved})


# ─── PLANOS CAD ──────────────────────────────────────────────────────────────────

@login_required
def my_docs_cad_new(request, folder_id):
    from courses.models import UserFolder, UserCAD
    folder = get_object_or_404(UserFolder, pk=folder_id, user=request.user)
    cad = UserCAD.objects.create(user=request.user, folder=folder)
    return redirect('courses:my_docs_cad', cad_id=cad.pk)


@login_required
def my_docs_cad(request, cad_id):
    from courses.models import UserCAD
    cad = get_object_or_404(UserCAD, pk=cad_id, user=request.user)
    return render(request, 'courses/cad.html', {
        'active_nav': 'my_docs',
        'cad': cad,
    })


@login_required
@require_POST
def my_docs_cad_save(request, cad_id):
    import json
    from courses.models import UserCAD
    cad = get_object_or_404(UserCAD, pk=cad_id, user=request.user)
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'ok': False}, status=400)
    title = body.get('title', '').strip() or 'Plano sin título'
    data  = body.get('data', '')
    cad.title = title
    cad.data  = data if isinstance(data, str) else json.dumps(data)
    cad.save(update_fields=['title', 'data', 'updated_at'])
    return JsonResponse({'ok': True})


@login_required
@require_POST
def my_docs_cad_delete(request, cad_id):
    from courses.models import UserCAD
    cad = get_object_or_404(UserCAD, pk=cad_id, user=request.user)
    folder_id = cad.folder_id
    cad.delete()
    if folder_id:
        return redirect('courses:my_docs_folder', folder_id=folder_id)
    return redirect('courses:my_docs')


# ─── PRESENTACIONES ──────────────────────────────────────────────────────────────

@login_required
def my_docs_presentation_new(request, folder_id):
    from courses.models import UserFolder, UserPresentation, PRESENTATION_DEMO
    folder = get_object_or_404(UserFolder, pk=folder_id, user=request.user)
    pres = UserPresentation.objects.create(
        user=request.user, folder=folder,
        content=PRESENTATION_DEMO,
    )
    return redirect('courses:my_docs_presentation_edit', presentation_id=pres.pk)


@login_required
def my_docs_presentation_edit(request, presentation_id):
    from courses.models import UserPresentation, REVEAL_THEMES
    pres = get_object_or_404(UserPresentation, pk=presentation_id, user=request.user)
    if request.method == 'POST':
        pres.title   = request.POST.get('title', pres.title).strip() or pres.title
        pres.content = request.POST.get('content', pres.content)
        pres.theme   = request.POST.get('theme', pres.theme)
        pres.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True})
        return redirect('courses:my_docs_presentation_edit', presentation_id=pres.pk)
    return render(request, 'courses/presentation_edit.html', {
        'active_nav': 'my_docs',
        'pres':       pres,
        'themes':     REVEAL_THEMES,
    })


@login_required
@require_POST
def my_docs_presentation_delete(request, presentation_id):
    from courses.models import UserPresentation
    pres = get_object_or_404(UserPresentation, pk=presentation_id, user=request.user)
    folder_id = pres.folder_id
    pres.delete()
    if folder_id:
        return redirect('courses:my_docs_folder', folder_id=folder_id)
    return redirect('courses:my_docs')


@login_required
def my_docs_presentation_present(request, presentation_id):
    from courses.models import UserPresentation
    pres = get_object_or_404(UserPresentation, pk=presentation_id, user=request.user)
    return render(request, 'courses/presentation_present.html', {'pres': pres})


@login_required
@require_POST
def my_docs_presentation_share(request, presentation_id):
    import uuid as _uuid
    from courses.models import UserPresentation
    pres = get_object_or_404(UserPresentation, pk=presentation_id, user=request.user)
    if pres.share_token:
        pres.share_token = None
    else:
        pres.share_token = _uuid.uuid4()
    pres.save(update_fields=['share_token'])
    return JsonResponse({
        'ok': True,
        'shared': pres.share_token is not None,
        'token': str(pres.share_token) if pres.share_token else None,
    })


def public_presentation_view(request, token):
    from courses.models import UserPresentation
    from django.db.models import F
    pres = get_object_or_404(UserPresentation, share_token=token)
    pres.view_count = F('view_count') + 1
    pres.save(update_fields=['view_count'])
    pres.refresh_from_db(fields=['view_count'])
    return render(request, 'courses/presentation_present.html', {'pres': pres, 'is_public': True})


@login_required
def my_docs_search(request):
    """Búsqueda global en Mis documentos del usuario autenticado."""
    from courses.models import UserFolder, UserFile, UserNote, UserWhiteboard, UserPresentation
    from django.db.models import Q
    q = request.GET.get('q', '').strip()
    results = []
    if len(q) >= 1:
        folders = UserFolder.objects.filter(user=request.user, name__icontains=q).order_by('name')[:8]
        for obj in folders:
            results.append({
                'type': 'folder', 'icon': '📁',
                'name': obj.name,
                'url': '/dashboard/mis-docs/carpeta/{}/'.format(obj.pk),
                'sub': 'Carpeta',
            })
        files = UserFile.objects.filter(user=request.user, name__icontains=q).order_by('name')[:8]
        for obj in files:
            results.append({
                'type': 'file', 'icon': '📄',
                'name': obj.name,
                'url': obj.file.url,
                'sub': obj.folder.name if obj.folder else '—',
                'new_tab': True,
            })
        notes = UserNote.objects.filter(user=request.user, title__icontains=q).order_by('title')[:6]
        for obj in notes:
            results.append({
                'type': 'note', 'icon': '📝',
                'name': obj.title,
                'url': '/dashboard/mis-docs/nota/{}/editar/'.format(obj.pk),
                'sub': obj.folder.name if obj.folder else '—',
            })
        pres_qs = UserPresentation.objects.filter(user=request.user, title__icontains=q).order_by('title')[:6]
        for obj in pres_qs:
            results.append({
                'type': 'presentation', 'icon': '🎞️',
                'name': obj.title,
                'url': '/dashboard/mis-docs/presentacion/{}/'.format(obj.pk),
                'sub': obj.folder.name if obj.folder else '—',
            })
    return JsonResponse({'results': results, 'q': q})


# ─── ENLACES GUARDADOS ───────────────────────────────────────────────────────

@login_required
@require_http_methods(['GET', 'POST'])
def my_docs_link_create(request):
    from courses.models import SavedLink
    from django.db.models import Q
    if request.method == 'POST':
        name      = request.POST.get('name', '').strip()
        url       = request.POST.get('url', '').strip()
        link_user = request.POST.get('link_user', '').strip()
        link_pass = request.POST.get('link_pass', '').strip()
        is_public = request.POST.get('is_public', '1') == '1'
        if name and url:
            SavedLink.objects.create(
                user=request.user,
                name=name,
                url=url,
                link_user=link_user,
                link_pass=link_pass,
                is_public=is_public,
            )
        next_url = request.POST.get('next', '')
        from django.utils.http import url_has_allowed_host_and_scheme
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect('courses:saved_links')
    return redirect('courses:my_docs')


@login_required
@require_POST
def my_docs_link_delete(request, link_id):
    from courses.models import SavedLink
    link = get_object_or_404(SavedLink, pk=link_id, user=request.user)
    link.delete()
    return redirect('courses:saved_links')


@login_required
@require_POST
def my_docs_link_toggle(request, link_id):
    from courses.models import SavedLink
    link = get_object_or_404(SavedLink, pk=link_id, user=request.user)
    link.is_public = not link.is_public
    link.save(update_fields=['is_public'])
    return JsonResponse({'ok': True, 'is_public': link.is_public})


@login_required
def saved_links(request):
    from courses.models import SavedLink
    from django.db.models import Q
    links = SavedLink.objects.filter(
        Q(is_public=True) | Q(user=request.user)
    ).select_related('user').order_by('-created_at')
    return render(request, 'courses/saved_links.html', {
        'active_nav': 'saved_links',
        'links': links,
    })


# ─── LISTAS DE CHEQUEO ───────────────────────────────────────────────────────

@login_required
def checklists(request):
    from courses.models import Checklist
    from django.db.models import Q
    own     = Checklist.objects.filter(user=request.user).prefetch_related('items')
    public  = Checklist.objects.filter(is_public=True).exclude(user=request.user).prefetch_related('items')
    return render(request, 'courses/checklists.html', {
        'active_nav': 'checklists',
        'own':    own,
        'public': public,
    })


@login_required
def checklist_create(request):
    from courses.models import Checklist
    if request.method == 'POST':
        name      = request.POST.get('name', '').strip()
        is_public = request.POST.get('is_public', '1') == '1'
        if name:
            cl = Checklist.objects.create(user=request.user, name=name, is_public=is_public)
            return redirect('courses:checklist_detail', pk=cl.pk)
    return redirect('courses:checklists')


@login_required
def checklist_detail(request, pk):
    from courses.models import Checklist
    from django.db.models import Q
    cl = get_object_or_404(Checklist, pk=pk)
    # Only owner or public checklists accessible to logged-in users
    if not cl.is_public and cl.user != request.user:
        return redirect('courses:checklists')
    return render(request, 'courses/checklist_detail.html', {
        'active_nav': 'checklists',
        'cl': cl,
        'is_owner': cl.user == request.user,
        'public_url': request.build_absolute_uri('/dashboard/checklist/{}/'.format(cl.share_token)),
    })


@login_required
@require_POST
def checklist_delete(request, pk):
    from courses.models import Checklist
    cl = get_object_or_404(Checklist, pk=pk, user=request.user)
    cl.delete()
    return redirect('courses:checklists')


@login_required
@require_POST
def checklist_toggle_public(request, pk):
    from courses.models import Checklist
    cl = get_object_or_404(Checklist, pk=pk, user=request.user)
    cl.is_public = not cl.is_public
    cl.save(update_fields=['is_public'])
    return JsonResponse({'ok': True, 'is_public': cl.is_public})


@login_required
@require_POST
def checklist_rename(request, pk):
    from courses.models import Checklist
    cl = get_object_or_404(Checklist, pk=pk, user=request.user)
    name = request.POST.get('name', '').strip()
    if name:
        cl.name = name
        cl.save(update_fields=['name', 'updated_at'])
    return JsonResponse({'ok': True, 'name': cl.name})


@login_required
@require_POST
def checklist_item_add(request, pk):
    from courses.models import Checklist, ChecklistItem
    cl = get_object_or_404(Checklist, pk=pk, user=request.user)
    text = request.POST.get('text', '').strip()
    if not text:
        return JsonResponse({'ok': False, 'error': 'Texto vacío'}, status=400)
    order = cl.items.count()
    item  = ChecklistItem.objects.create(checklist=cl, text=text, order=order)
    cl.save(update_fields=['updated_at'])
    return JsonResponse({'ok': True, 'id': item.pk, 'text': item.text, 'is_done': item.is_done})


@login_required
@require_POST
def checklist_item_toggle(request, item_id):
    from courses.models import ChecklistItem
    item = get_object_or_404(ChecklistItem, pk=item_id, checklist__user=request.user)
    item.is_done = not item.is_done
    item.save(update_fields=['is_done'])
    cl = item.checklist
    cl.save(update_fields=['updated_at'])
    return JsonResponse({'ok': True, 'is_done': item.is_done,
                         'done': cl.done_count, 'total': cl.total_count})


@login_required
@require_POST
def checklist_item_delete(request, item_id):
    from courses.models import ChecklistItem
    item = get_object_or_404(ChecklistItem, pk=item_id, checklist__user=request.user)
    cl = item.checklist
    item.delete()
    cl.save(update_fields=['updated_at'])
    return JsonResponse({'ok': True, 'done': cl.done_count, 'total': cl.total_count})


@login_required
@require_POST
def checklist_item_reorder(request, pk):
    import json
    from courses.models import Checklist, ChecklistItem
    cl = get_object_or_404(Checklist, pk=pk, user=request.user)
    try:
        ids = json.loads(request.body)
    except Exception:
        return JsonResponse({'ok': False}, status=400)
    for pos, item_id in enumerate(ids):
        ChecklistItem.objects.filter(pk=item_id, checklist=cl).update(order=pos)
    cl.save(update_fields=['updated_at'])
    return JsonResponse({'ok': True})


@login_required
@require_POST
def checklist_item_set_duration(request, item_id):
    from courses.models import ChecklistItem
    item = get_object_or_404(ChecklistItem, pk=item_id, checklist__user=request.user)
    try:
        duration = max(1, int(request.POST.get('duration', 1)))
    except ValueError:
        duration = 1
    item.duration = duration
    item.save(update_fields=['duration'])
    return JsonResponse({'ok': True, 'duration': item.duration})


def public_checklist_view(request, token):
    """Vista pública sin login para compartir una lista."""
    from courses.models import Checklist
    cl = get_object_or_404(Checklist, share_token=token)
    return render(request, 'courses/public_checklist.html', {'cl': cl})
