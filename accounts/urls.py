from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/',    views.login_view,    name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/',   views.logout_view,   name='logout'),
    path('profile/',  views.profile_view,  name='profile'),
    # Admin: gestión de usuarios
    path('panel/progreso/',               views.admin_progress,      name='admin_progress'),
    path('panel/usuarios/',               views.admin_users,         name='admin_users'),
    path('panel/usuarios/nuevo/',         views.admin_user_form,     name='admin_user_new'),
    path('panel/usuarios/<int:user_id>/', views.admin_user_form,     name='admin_user_edit'),
    # Admin: categorías
    path('panel/categorias/',                     views.admin_categories,     name='admin_categories'),
    path('panel/categorias/nuevo/',               views.admin_category_form,  name='admin_category_new'),
    path('panel/categorias/<int:category_id>/',   views.admin_category_form,  name='admin_category_edit'),
    # Admin: planes de capacitación
    path('panel/planes/',               views.admin_plans,     name='admin_plans'),
    path('panel/planes/nuevo/',         views.admin_plan_form, name='admin_plan_new'),
    path('panel/planes/<int:plan_id>/', views.admin_plan_form, name='admin_plan_edit'),
    # Admin: cursos
    path('panel/cursos/',                 views.admin_courses,     name='admin_courses'),
    path('panel/cursos/nuevo/',           views.admin_course_form, name='admin_course_new'),
    path('panel/cursos/<int:course_id>/', views.admin_course_form, name='admin_course_edit'),
    # Admin: temas
    path('panel/temas/',                views.admin_topics,     name='admin_topics'),
    path('panel/temas/nuevo/',          views.admin_topic_form, name='admin_topic_new'),
    path('panel/temas/<int:topic_id>/', views.admin_topic_form, name='admin_topic_edit'),
    # Admin: clases
    path('panel/clases/',                   views.admin_lessons,     name='admin_lessons'),
    path('panel/clases/nuevo/',             views.admin_lesson_form, name='admin_lesson_new'),
    path('panel/clases/<int:lesson_id>/',   views.admin_lesson_form, name='admin_lesson_edit'),
    # Admin: tareas
    path('panel/tareas/',                        views.admin_tasks,            name='admin_tasks'),
    path('panel/tareas/nuevo/',                  views.admin_task_form,        name='admin_task_new'),
    path('panel/tareas/<int:task_id>/',          views.admin_task_form,        name='admin_task_edit'),
    path('panel/tareas/<int:task_id>/entregas/', views.admin_task_submissions, name='admin_task_submissions'),
    # Admin: exámenes
    path('panel/examenes/',                 views.admin_exams,     name='admin_exams'),
    path('panel/examenes/nuevo/',           views.admin_exam_form, name='admin_exam_new'),
    path('panel/examenes/<int:exam_id>/',   views.admin_exam_form, name='admin_exam_edit'),
    # Admin: biblioteca
    path('panel/biblioteca/',                                    views.admin_biblioteca,    name='admin_biblioteca'),
    path('panel/biblioteca/carpeta/nueva/',                      views.admin_folder_form,   name='admin_folder_new'),
    path('panel/biblioteca/carpeta/<int:folder_id>/',             views.admin_biblioteca,    name='admin_folder'),
    path('panel/biblioteca/carpeta/<int:folder_id>/editar/',      views.admin_folder_form,   name='admin_folder_edit'),
    path('panel/biblioteca/carpeta/<int:folder_id>/subcarpeta/',  views.admin_folder_form,   name='admin_subfolder_new'),
    path('panel/biblioteca/carpeta/<int:folder_id>/subir/',       views.admin_file_upload,   name='admin_file_upload'),
    path('panel/biblioteca/archivo/<int:file_id>/eliminar/',      views.admin_file_delete,   name='admin_file_delete'),
    # Admin: artículos
    path('panel/articulos/',                  views.admin_articles,     name='admin_articles'),
    path('panel/articulos/nuevo/',            views.admin_article_form, name='admin_article_new'),
    path('panel/articulos/<int:article_id>/', views.admin_article_form, name='admin_article_edit'),
    # Soporte (usuario)
    path('soporte/enviar/',                 views.support_send,    name='support_send'),
    path('soporte/mensajes/',               views.support_messages, name='support_messages'),
    # Admin: soporte
    path('panel/soporte/',                          views.admin_support,        name='admin_support'),
    path('panel/soporte/<int:ticket_id>/',           views.admin_support_thread, name='admin_support_thread'),
    path('panel/soporte/<int:ticket_id>/responder/', views.admin_support_reply,  name='admin_support_reply'),
    # Admin: configuración general
    path('panel/config/', views.admin_config, name='admin_config'),
]
