from rest_framework import serializers
from .models import User , Quiz,Question,QuizResult,Lesson,ChatMessage, Assignment, LessonProgress, AssignmentSubmission, ChatSession

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user
    
class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option']

class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Quiz
        fields = ['id', 'user', 'title', 'is_final', 'created_at', 'questions']

class QuizResultSerializer(serializers.ModelSerializer):
     class Meta:
        model = QuizResult
        fields = ['id', 'user', 'quiz', 'score', 'passed', 'taken_at']

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'user', 'title', 'content', 'created_at']

class chatSessionSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = ChatSession
        fields = ['id', 'user', 'started_at']

class ChatMessageSerializer(serializers.ModelSerializer):
    session = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = ChatMessage
        fields = ['id','session', 'content','response', 'timestamp']


class LessonSerializer(serializers.ModelSerializer):
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ['id', 'title', 'content', 'created_at', 'is_completed']

    def get_is_completed(self, obj):
        user = self.context.get('user')
        if not user:
            return False
        return LessonProgress.objects.filter(user=user, lesson=obj, is_completed=True).exists()





class AssignmentSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Assignment
        fields = ['id', 'title', 'instructions', 'sample_input', 'sample_output', 'questions']

