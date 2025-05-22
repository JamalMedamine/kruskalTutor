from django.contrib.auth import authenticate
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import User, Quiz, Question, Assignment, AssignmentSubmission, Certificate, ChatMessage, ChatSession, Lesson, LessonProgress,QuizResult
from .serializer import UserSerializer , QuestionSerializer , QuizSerializer,QuizResultSerializer,LessonSerializer
import aiohttp
import asyncio
import json
import logging
import re
logger = logging.getLogger(__name__)

def extract_json_from_markdown(text):
    match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)
    return None

async def invoke_chute(prompt):
    if not prompt or prompt.strip() == "":
        return {"error": "Prompt is empty. Cannot call LLM."}
    api_token = "cpk_02eae620a5fb4ff0bdf2e65f5e613946.917e4dab6a7c504ca882cb76be6f8f33.haSvr6ZIhCtg3YEUxwDSxDkMED6nmT9E"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "deepseek-ai/DeepSeek-V3-0324",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "max_tokens": 1024,
        "temperature": 0.7
    }

    async with aiohttp.ClientSession() as session:
        async with session.post("https://llm.chutes.ai/v1/chat/completions", headers=headers, json=body) as response:
            if response.status != 200:
                error_text = await response.text()
                return {"error": f"Chute API request failed with status {response.status}: {error_text}"}

            data = await response.json()

            # Safely access choices
            if "choices" not in data:
                return {"error": f"Unexpected response format: {json.dumps(data)}"}

            cleaned_json = extract_json_from_markdown(data["choices"][0]["message"]["content"])
            if not cleaned_json:
                return {"error": "Invalid JSON from LLM", "raw": content}

            quiz_data = json.loads(cleaned_json)
            return quiz_data





@api_view(['GET'])
def get_user_list(request):
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def Register(request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def Login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user is not None:
        return Response({"message": "Login successful"}, status=status.HTTP_200_OK)
    else:
        return Response({"error": "Invalid username or password"}, status=status.HTTP_400_BAD_REQUEST)
        
@api_view(['GET', 'PUT', 'DELETE'])
def user_detail(request, pk):
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = UserSerializer(user)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET', 'POST'])
def getQuizbyUser(request, pk):
    if request.method == 'GET':
        try:
            quiz = Quiz.objects.prefetch_related('questions').get(user__pk=pk, is_final=False)
            serializer = QuizSerializer(quiz)
            return Response(serializer.data)
        except Quiz.DoesNotExist:
            try:
                user = User.objects.get(pk=pk)
            except User.DoesNotExist:
                return Response({"error": "User not found."}, status=404)

            prompt = (
                "Create a prequesites Kruskal's Algorithm quiz in JSON format:\n"
                "{ \"title\": \"Kruskal Quiz\", \"is_final\": false, \"questions\": [\n"
                "{\"text\": \"Question text\", \"option_a\": \"A\", \"option_b\": \"B\", \"option_c\": \"C\", \"option_d\": \"D\", \"correct_option\": \"A\" }\n"
                "] }"
            )
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            llm_response = loop.run_until_complete(invoke_chute(prompt))
            
            if isinstance(llm_response, dict) and "error" in llm_response:
                return Response({"error": llm_response["error"]}, status=500)

            
            quiz_data = llm_response

        
            if not isinstance(quiz_data, dict) or "questions" not in quiz_data:
                return Response({
                    "error": "Invalid quiz format from LLM",
                    "raw": quiz_data
                }, status=400)

            quiz = Quiz.objects.create(
                user=user,
                title=quiz_data.get("title", "Generated Quiz"),
                is_final=quiz_data.get("is_final", False)
            )

            for q in quiz_data.get("questions", []):
                Question.objects.create(
                    quiz=quiz,
                    text=q.get("text", ""),
                    option_a=q.get("option_a", ""),
                    option_b=q.get("option_b", ""),
                    option_c=q.get("option_c", ""),
                    option_d=q.get("option_d", ""),
                    correct_option=q.get("correct_option", "")
                )

            quiz_with_questions = Quiz.objects.prefetch_related('questions').get(pk=quiz.pk)
            serializer = QuizSerializer(quiz_with_questions)
            return Response(serializer.data, status=201)
    elif request.method == 'POST':
        try:
            
            quiz = Quiz.objects.prefetch_related('questions').get(user__pk=pk, is_final=False)
            responses = [
                request.data.get('response1'),
                request.data.get('response2'), 
                request.data.get('response3'),
                request.data.get('response4'),
                request.data.get('response5')
            ]
            
            
            questions = quiz.questions.all().order_by('id')
            if len(questions) != 5:
                return Response({"error": "Quiz should have exactly 5 questions"}, status=400)
            
            
            correct_answers = [q.correct_option for q in questions]
            score = sum(1 for i in range(5) if responses[i] == correct_answers[i]) / 5 * 100
            
           
            passed = score >= 70
            
           
            QuizResult.objects.create(
                user=quiz.user,
                quiz=quiz,
                score=score,
                passed=passed
            )
            
            quizResult = QuizResult.objects.get(user=quiz.user, quiz=quiz)
            serializer = QuizResultSerializer(quizResult)
            return Response(serializer.data, status=201)
            
        except Quiz.DoesNotExist:
            return Response({"error": "No active quiz found for this user"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=400)
        
@api_view(['GET'])
def getIntro(request, pk):
    try:
        lesson = Lesson.objects.get(user__pk=pk, title="Introduction to Kruskal's Algorithm")
        serializer = LessonSerializer(lesson) 
        return Response(serializer.data)
    except Lesson.DoesNotExist:
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=404)
        
        prompt = """
        Create a concise introductory lesson about Kruskal's Algorithm in JSON format with this structure:
        {
            "title": "Introduction to Kruskal's Algorithm",
            "content": [
                {
                    "section_title": "What is Kruskal's Algorithm?",
                    "section_content": "Kruskal's algorithm is a greedy approach to find the Minimum Spanning Tree (MST) in a connected, undirected graph. Developed by Joseph Kruskal in 1956, it efficiently constructs an MST by always adding the next lowest-weight edge that doesn't form a cycle."
                },
                {
                    "section_title": "Key Characteristics",
                    "section_content": [
                        "Works on weighted, undirected graphs",
                        "Time complexity: O(E log V) using Union-Find",
                        "Guaranteed to find the optimal solution",
                        "Naturally parallelizable process"
                    ]
                },
                {
                    "section_title": "Why It Matters",
                    "section_content": "Kruskal's algorithm has practical applications in network design, circuit wiring, and transportation systems where we need to connect all points at minimum cost without loops."
                }
            ],
            "key_points": [
                "Greedy algorithm for Minimum Spanning Trees",
                "Works by sorting and selectively adding edges",
                "Uses Union-Find data structure for efficiency"
            ]
        }
        """
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        llm_response = loop.run_until_complete(invoke_chute(prompt))
            
        if isinstance(llm_response, dict) and "error" in llm_response:
            return Response({"error": llm_response["error"]}, status=500)

      
        if not isinstance(llm_response, dict) or "content" not in llm_response:
            return Response({
                "error": "Invalid lesson format from LLM",
                "raw": llm_response
            }, status=400)
            
        lesson = Lesson.objects.create(
            user=user,
            title=llm_response.get("title", "Introduction to Kruskal's Algorithm"),
            content={
                "sections": llm_response["content"],
                "key_points": llm_response.get("key_points", [])
            }
        )
        
        serializer = LessonSerializer(lesson)
        return Response(serializer.data, status=201)
                