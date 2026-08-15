from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('mis-cursos/', views.my_courses, name='my_courses'),
    path('documentos/', views.biblioteca, name='biblioteca'),
    path('documentos/<int:folder_id>/', views.biblioteca, name='biblioteca_folder'),
    path('cursos/', views.course_list, name='course_list'),
    path('cursos/<slug:slug>/', views.course_detail, name='course_detail'),
    path('cursos/<slug:slug>/inscribirse/', views.enroll, name='enroll'),
    path('cursos/<slug:slug>/clase/<int:lesson_id>/completar/', views.toggle_lesson, name='toggle_lesson'),
    path('cursos/<slug:slug>/tarea/<int:task_id>/entregar/', views.submit_task, name='submit_task'),
    path('cursos/<slug:slug>/clase/<int:lesson_id>/comentar/', views.add_comment, name='add_comment'),
    path('cursos/<slug:slug>/valorar/', views.review_course, name='review_course'),
    path('cursos/<slug:slug>/examen/', views.take_exam, name='take_exam'),
    path('cursos/<slug:slug>/examen/<int:attempt_id>/resultado/', views.exam_result, name='exam_result'),
    path('cursos/<slug:slug>/certificado/', views.certificate, name='certificate'),
]
