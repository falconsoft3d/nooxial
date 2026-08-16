from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('mis-cursos/', views.my_courses, name='my_courses'),
    path('documentos/', views.biblioteca, name='biblioteca'),
    path('documentos/<int:folder_id>/', views.biblioteca, name='biblioteca_folder'),
    # Mis documentos (personal)
    path('mis-docs/', views.my_docs, name='my_docs'),
    path('mis-docs/carpeta/<int:folder_id>/', views.my_docs, name='my_docs_folder'),
    path('mis-docs/carpeta/nueva/', views.my_docs_new_folder, name='my_docs_new_folder'),
    path('mis-docs/carpeta/<int:folder_id>/nueva/', views.my_docs_new_folder, name='my_docs_new_subfolder'),
    path('mis-docs/carpeta/<int:folder_id>/editar/', views.my_docs_edit_folder, name='my_docs_edit_folder'),
    path('mis-docs/carpeta/<int:folder_id>/eliminar/', views.my_docs_delete_folder, name='my_docs_delete_folder'),
    path('mis-docs/carpeta/<int:folder_id>/subir/', views.my_docs_upload_file, name='my_docs_upload_file'),
    path('mis-docs/archivo/<int:file_id>/eliminar/', views.my_docs_delete_file, name='my_docs_delete_file'),
    path('mis-docs/carpeta/<int:folder_id>/nota/nueva/', views.my_docs_note_edit, name='my_docs_note_new'),
    path('mis-docs/nota/<int:note_id>/editar/', views.my_docs_note_edit, name='my_docs_note_edit'),
    path('mis-docs/nota/<int:note_id>/eliminar/', views.my_docs_note_delete, name='my_docs_note_delete'),
    path('mis-docs/nota/<int:note_id>/compartir/', views.my_docs_note_share, name='my_docs_note_share'),
    path('mis-docs/grabar/', views.my_docs_record_upload, name='my_docs_record_upload'),
    path('nota/<uuid:token>/', views.public_note_view, name='public_note'),
    # Profesores
    path('profesores/', views.teachers_list, name='teachers'),
    path('profesores/<int:teacher_id>/', views.teacher_detail, name='teacher_detail'),
    path('profesores/<int:teacher_id>/mensaje/', views.teacher_send_message, name='teacher_send_message'),
    path('profesores/<int:teacher_id>/valorar/', views.teacher_rate, name='teacher_rate'),
    # Bandeja del profesor
    path('mis-mensajes/', views.teacher_inbox, name='teacher_inbox'),
    path('mis-mensajes/<int:student_id>/', views.teacher_thread, name='teacher_thread'),
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
