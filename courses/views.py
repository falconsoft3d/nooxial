from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Avg
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
    })


@login_required
def my_courses(request):
    enrollments = (Enrollment.objects
                   .filter(student=request.user)
                   .select_related('course')
                   .prefetch_related('course__categories')
                   .annotate(avg_rating=Avg('course__reviews__rating'))
                   .order_by('-enrolled_at'))
    return render(request, 'courses/my_courses.html', {
        'active_nav':  'my_courses',
        'enrollments': enrollments,
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
    course = get_object_or_404(Course, slug=slug, is_published=True)
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
        'avg_rating':      CourseReview.objects.filter(course=course).aggregate(avg=Avg('rating'))['avg'],
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

