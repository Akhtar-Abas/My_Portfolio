from django.urls import path
from . import views

urlpatterns = [
    # PDF upload endpoint (legacy)
    path('upload/', views.upload_pdf, name='upload_pdf'),
    
    # Question answering endpoints
    path('question/', views.ask_question, name='ask_question'),
    path('chat/', views.ask_question, name='chat'),  # Frontend-friendly endpoint
]