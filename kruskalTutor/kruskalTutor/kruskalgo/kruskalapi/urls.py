from django.urls import path , include
from . import views 

urlpatterns = [
    path('register/', views.Register,name="register"),
    path('login/', views.Login,name="login"),
    path('users/', views.get_user_list, name='user_list'),
    path('user/<int:pk>/', views.user_detail, name='user_detail'),
    path('user/<int:pk>/prequesitesQuiz/', views.getQuizbyUser, name='prequesitesQuiz'),
    path('user/<int:pk>/introduction/', views.getIntro, name='quiz_list'),
    path('user/<int:pk>/createSession/', views.createChatSession, name='create_chat_session'),
    path('user/<int:pk>/session/<int:session_id>/chat/', views.chat_message,name='chat_message'),

    # Liste des leçons accessibles par l'utilisateur
    path('user/<int:user_id>/lessons/', views.getLessonsByUser, name='lessons_by_user'),
    # Contenu d'une leçon pour un utilisateur
    path('user/<int:user_id>/lessons/<int:lesson_id>/', views.view_lesson_content, name='lesson_content'),
    # Marquer une leçon comme complétée
    path('user/<int:user_id>/lessons/<int:lesson_id>/complete/', views.completeLesson, name='complete_lesson'),
    # Voir les exercices pour une leçon
    path('user/<int:user_id>/lessons/<int:lesson_id>/assignments/', views.get_assignment_by_lesson, name='assignments_by_lesson'),

]