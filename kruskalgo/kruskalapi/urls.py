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
    path('user/<int:pk>/session/<int:session_id>/chat/', views.chat_message,name='chat_message')
]