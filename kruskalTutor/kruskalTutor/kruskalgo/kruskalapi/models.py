from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    is_student = models.BooleanField(default=True)
    registered_at = models.DateTimeField(auto_now_add=True)

class Quiz(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quizzes')  
    title = models.CharField(max_length=200)
    is_final = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Question(models.Model):
    quiz = models.ForeignKey('Quiz', on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    assignment = models.ForeignKey('Assignment', on_delete=models.CASCADE, related_name='questions', null=True, blank=True)

    text = models.TextField()
    option_a = models.CharField(max_length=200)
    option_b = models.CharField(max_length=200)
    option_c = models.CharField(max_length=200)
    option_d = models.CharField(max_length=200)
    correct_option = models.CharField(max_length=1)

class QuizResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.FloatField()
    passed = models.BooleanField()
    taken_at = models.DateTimeField(auto_now_add=True)

class Lesson(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lessons')  
    title = models.CharField(max_length=200)
    content = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

class Assignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignments') 
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    instructions = models.TextField()
    sample_input = models.TextField(blank=True)
    sample_output = models.TextField(blank=True)

class LessonProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

class AssignmentSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    submission_text = models.TextField()
    feedback = models.TextField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    response = models.TextField(default="null")
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

class Certificate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz_result = models.OneToOneField(QuizResult, on_delete=models.CASCADE)
    issued_at = models.DateTimeField(auto_now_add=True)
    certificate_file = models.FileField(upload_to='certificates/', null=True, blank=True)