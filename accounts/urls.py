from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/',    views.login_view,    name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/',   views.logout_view,   name='logout'),
    path('profile/',  views.profile_view,  name='profile'),
    # Bloqueo de pantalla
    path('lock/',        views.lock_view,        name='lock'),
    path('lock-screen/', views.lock_screen_view, name='lock_screen'),
    path('change-pin/',  views.change_pin_view,  name='change_pin'),
    path('unlock/',      views.lock_screen_view, name='unlock'),
    # Chat directo
    path('chat/api/conversations/',           views.dm_conversations,   name='dm_conversations'),
    path('chat/api/thread/<int:user_id>/',    views.dm_thread,          name='dm_thread'),
    path('chat/api/send/',                    views.dm_send,            name='dm_send'),
    path('chat/api/users/',                   views.dm_user_search,     name='dm_user_search'),
    # Admin: gestión de usuarios
    path('panel/progreso/',               views.admin_progress,      name='admin_progress'),
    path('panel/usuarios/',               views.admin_users,         name='admin_users'),
    path('panel/usuarios/nuevo/',         views.admin_user_form,     name='admin_user_new'),
    path('panel/usuarios/<int:user_id>/', views.admin_user_form,     name='admin_user_edit'),
    # Admin: empresas
    path('panel/empresas/',                  views.admin_companies,    name='admin_companies'),
    path('panel/empresas/nueva/',            views.admin_company_form, name='admin_company_new'),
    path('panel/empresas/<int:company_id>/', views.admin_company_form, name='admin_company_edit'),
    # Dashboard público de empresa (con token)
    path('empresa/<uuid:token>/dashboard/',   views.company_dashboard,    name='company_dashboard'),
    path('empresa/<uuid:token>/registro/',    views.company_register,     name='company_register'),
    # Asistencia pública de empresa
    path('empresa/<uuid:token>/asistencia/',  views.company_attendance,   name='company_attendance'),
    # Admin: contactos
    path('panel/contactos/',                    views.admin_contacts,      name='admin_contacts'),
    path('panel/contactos/<int:contact_id>/',   views.admin_contact_view,  name='admin_contact_detail'),
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
    path('panel/config/',            views.admin_config,            name='admin_config'),
    path('panel/config/test-email/', views.admin_config_test_email, name='admin_config_test_email'),
    # Admin: términos y condiciones
    path('panel/terminos/',                 views.admin_terms,      name='admin_terms'),
    path('panel/terminos/nuevo/',           views.admin_terms_form, name='admin_terms_new'),
    path('panel/terminos/<int:terms_id>/',  views.admin_terms_form, name='admin_terms_edit'),
    # Reuniones por empresa (WebRTC)
    path('reunion/',                            views.company_meeting,       name='meeting'),
    path('reunion/empresa/<int:company_id>/',   views.company_meeting,       name='meeting_company'),
    path('reunion/signal/',                     views.meeting_signal_post,   name='meeting_signal_post'),
    path('reunion/signal/poll/',                views.meeting_signal_poll,   name='meeting_signal_poll'),
    # Currículum público
    path('curriculo/<str:username>/', views.public_cv, name='public_cv'),
    # Aceptar T&C (usuarios)
    path('aceptar-terminos/', views.accept_terms_view, name='accept_terms'),
    # Registro por plan de capacitación (asocia empresa + plan)
    path('registro/empresa/<int:company_id>/plan/<uuid:token>/', views.plan_register_view, name='plan_register'),
    # Admin: grupos de chat
    path('panel/grupos-chat/',                        views.admin_chat_groups,       name='admin_chat_groups'),
    path('panel/grupos-chat/nuevo/',                  views.admin_chat_group_form,   name='admin_chat_group_new'),
    path('panel/grupos-chat/<int:group_id>/',         views.admin_chat_group_form,   name='admin_chat_group_edit'),
    # API: grupos de chat (usuario)
    path('api/grupos/',                               views.user_groups_api,         name='user_groups_api'),
    path('api/grupos/<int:group_id>/mensajes/',       views.group_messages_api,      name='group_messages_api'),
    # Admin: votaciones
    path('panel/votaciones/',                    views.admin_votings,      name='admin_votings'),
    path('panel/votaciones/nueva/',              views.admin_voting_form,  name='admin_voting_new'),
    path('panel/votaciones/<int:voting_id>/',    views.admin_voting_form,  name='admin_voting_edit'),
    # Pública: votar + dashboard live
    path('votar/<uuid:token>/',                  views.public_vote,        name='public_vote'),
    path('votar/<uuid:token>/resultados/',       views.public_vote_results, name='public_vote_results'),
    path('votar/<uuid:token>/api/',              views.voting_api,          name='voting_api'),
    # Recuperación de contraseña
    path('forgot-password/',               views.forgot_password_view, name='forgot_password'),
    path('reset-password/<uuid:token>/',   views.reset_password_view,  name='reset_password'),
    # Evaluaciones de plataforma
    path('api/evaluar/',        views.platform_rating_submit,  name='platform_rating_submit'),
    path('panel/evaluaciones/', views.admin_platform_ratings,  name='admin_platform_ratings'),
    # Versiones
    path('panel/versiones/',                              views.admin_versions,        name='admin_versions'),
    path('panel/versiones/nueva/',                        views.admin_version_create,  name='admin_version_create'),
    path('panel/versiones/<int:version_id>/',             views.admin_version_edit,    name='admin_version_edit'),
    path('panel/versiones/<int:version_id>/eliminar/',    views.admin_version_delete,  name='admin_version_delete'),
    path('api/versiones/',                                views.api_all_versions,      name='api_all_versions'),
    path('api/versiones/<int:version_id>/',               views.api_version_changelog, name='api_version_changelog'),
    path('api/nav-more/',                                 views.api_nav_more_save,     name='api_nav_more_save'),
]
