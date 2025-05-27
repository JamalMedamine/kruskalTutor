from django.contrib.auth import authenticate
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import User, Quiz, Question, Assignment, AssignmentSubmission, Certificate, ChatMessage, ChatSession, Lesson, LessonProgress,QuizResult
from .serializer import UserSerializer , QuestionSerializer , QuizSerializer,QuizResultSerializer,LessonSerializer,ChatMessageSerializer,AssignmentSerializer
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
                return {"error": "Invalid JSON from LLM", "raw": data["choices"][0]["message"]["content"]}

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
    
@api_view(['GET'])
def createChatSession(request, pk):
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=404)

    chat_session = ChatSession.objects.create(user=user)
    return Response({"session_id": chat_session.id}, status=201)

@api_view(['POST', 'GET'])
def chat_message(request, pk , session_id):
    try:
        chat_session = ChatSession.objects.get(pk=session_id, user__pk=pk)
    except ChatSession.DoesNotExist:
        return Response({"error": "Chat session not found."}, status=404)
    
    if request.method == 'GET':
        messages = ChatMessage.objects.filter(session=chat_session).order_by('id')
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        userPrompt = request.data.get('content')
        if not userPrompt:
            return Response({"error": "Content is required."}, status=400)
        
        prompt = prompt = f"""
                            Analyze the following user prompt: '{userPrompt}'.  
                            If it is about Kruskal's algorithm, respond in JSON format with:  
                            {{
                                "response": "[relevant answer about Kruskal's algorithm]"
                            }}  
                            Otherwise, respond with a JSON containing an excuse:  
                            {{
                                "response": "[polite excuse explaining you can only discuss Kruskal's algorithm]"
                            }}
                            """

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        llm_response = loop.run_until_complete(invoke_chute(prompt))

        if isinstance(llm_response, dict) and "error" in llm_response:
            return Response({"error": llm_response["error"]}, status=500)
        
        if not isinstance(llm_response, dict) or "response" not in llm_response:
            return Response({
                "error": "Invalid lesson format from LLM",
                "raw": llm_response
            }, status=400)
       
        
        
        user_message = ChatMessage.objects.create(
            session=chat_session, 
            content=userPrompt, 
            response=llm_response.get("response", "No response from LLM")
        )
        serializer = ChatMessageSerializer(user_message)

        return Response(serializer.data, status=201)
       

@api_view(['GET'])
def getLessonsByUser(request, user_id):
    try:
        user = User.objects.get(pk=user_id)
        lessons = Lesson.objects.filter(user=user).order_by('id')
        Lesson.objects.all().delete()
        if not lessons.exists():
            # Liste des titres pour les 6 lessons, à modifier selon besoins
            lesson_titles = [
                "Sorting Edges in Kruskal's Algorithm",
                "Union-Find Data Structure",
                "Cycle Detection with Union-Find",
                "Step-by-Step Execution of Kruskal's Algorithm",
                "Optimization Techniques",
                "Complexity Analysis"
            ]

            lessons_data = []

            for title in lesson_titles:
                prompt = f"""
                Create a detailed lesson about "{title}" in JSON format with this structure:
                {{
                    "title": "{title}",
                    "content": [
                        {{
                            "section_title": "Explanation",
                            "section_content": "Provide a detailed explanation of about 10-15 lines."
                        }},
                        {{
                            "section_title": "Example",
                            "section_content": "Provide example or Python code snippet if relevant."
                        }}
                    ],
                    "key_points": [
                        "Summarize the 3-5 most important points of this lesson."
                    ]
                }}
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

                lessons_data.append(llm_response)

            # Sauvegarde en base
            for l in lessons_data:
                Lesson.objects.create(
                    user=user,
                    title=l.get("title", ""),
                    content={
                        "sections": l.get("content", []),
                        "key_points": l.get("key_points", [])
                    }
                )

            lessons = Lesson.objects.filter(user=user).order_by('id')

        # Préparer la réponse en format JSON
        data = []
        for lesson in lessons:
            progress = LessonProgress.objects.filter(user=user, lesson=lesson).first()
            is_completed = progress.is_completed if progress else False

            data.append({
                "id": lesson.id,
                "title": lesson.title,
                "content": lesson.content,
                "created_at": lesson.created_at,
                "is_completed": is_completed
            })

        return Response(data)

    except User.DoesNotExist:
        return Response({"error": "Utilisateur introuvable"}, status=404)







@api_view(['POST'])
def completeLesson(request, user_id, lesson_id):
    try:
        user = User.objects.get(pk=user_id)
        lesson = Lesson.objects.get(pk=lesson_id, user=user)

        # Marquer comme terminée (pas besoin de vérifier l'exercice ici)
        progress, created = LessonProgress.objects.get_or_create(user=user, lesson=lesson)
        progress.is_completed = True
        progress.save()

        return Response({"message": "Leçon marquée comme complétée."}, status=200)

    except Lesson.DoesNotExist:
        return Response({"error": "Leçon introuvable"}, status=404)
    except User.DoesNotExist:
        return Response({"error": "Utilisateur introuvable"}, status=404)


@api_view(['GET', 'POST'])
def get_assignment_by_lesson(request, user_id, lesson_id):
    try:
        user = User.objects.get(pk=user_id)
        lesson = Lesson.objects.get(pk=lesson_id, user=user)

        # Vérifie que l'utilisateur a bien terminé le cours actuel
        progress = LessonProgress.objects.filter(user=user, lesson=lesson, is_completed=True).exists()
        if not progress:
            return Response({"error": "Vous devez d'abord terminer le cours avant d'accéder à l'exercice."}, status=403)

        # Vérifie l'accès selon les conditions pédagogiques
        if not can_access_lesson(user, lesson_id):
            return Response({"error": "Accès refusé. Terminez d'abord le cours précédent et son exercice."}, status=403)

        if request.method == 'GET':
            assignment = Assignment.objects.filter(lesson=lesson, user=user).first()
            if assignment:
                serializer = AssignmentSerializer(assignment)
                return Response(serializer.data)

            # Sinon on génère dynamiquement un exercice avec l'IA
            prompt = f"""
Create a multiple-choice exercise with 5 questions related specifically to the following lesson.
The exercise must be conceptually aligned with the content and learning objective of the lesson.
Avoid asking to write or complete code. Only use multiple-choice questions.

Lesson Title: "{lesson.title}"
Lesson Content: "{lesson.content}"

Return the result strictly in the following JSON format:
{{ 
  "title": "Exercice - {lesson.title}",
  "questions": [
    {{
      "text": "Question text",
      "option_a": "A",
      "option_b": "B",
      "option_c": "C",
      "option_d": "D",
      "correct_option": "A"
    }}
  ]
}}
"""

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            llm_response = loop.run_until_complete(invoke_chute(prompt))

            if isinstance(llm_response, dict) and "error" in llm_response:
                return Response({"error": llm_response["error"]}, status=500)

            data = llm_response
            if not isinstance(data, dict) or "questions" not in data:
                return Response({"error": "Format JSON invalide"}, status=400)

            assignment = Assignment.objects.create(
                user=user,
                lesson=lesson,
                title=data.get("title", "Exercice Kruskal"),
                instructions="Répondez aux questions suivantes"
            )

            for q in data["questions"]:
                Question.objects.create(
                    assignment=assignment,
                    text=q.get("text", ""),
                    option_a=q.get("option_a", ""),
                    option_b=q.get("option_b", ""),
                    option_c=q.get("option_c", ""),
                    option_d=q.get("option_d", ""),
                    correct_option=q.get("correct_option", "A"),
                )

            serializer = AssignmentSerializer(assignment)
            return Response(serializer.data, status=201)

        elif request.method == 'POST':
            assignment = Assignment.objects.filter(lesson=lesson, user=user).first()
            if not assignment:
                return Response({"error": "Aucun exercice pour cette leçon"}, status=404)

            questions = assignment.questions.all().order_by('id')
            responses = [request.data.get(f'response{i+1}') for i in range(questions.count())]

            correct_answers = [q.correct_option for q in questions]
            score = sum(1 for i in range(len(questions)) if responses[i] == correct_answers[i]) / len(questions) * 100
            passed = score >= 50

            AssignmentSubmission.objects.create(
                user=user,
                assignment=assignment,
                submission_text=str(responses),
                feedback="Correction automatique",
                score=score
            )

            # Marquer la leçon comme complétée si réussite
            if passed:
                progress, _ = LessonProgress.objects.get_or_create(user=user, lesson=lesson)
                progress.is_completed = True
                progress.save()

            return Response({
                "score": score,
                "passed": passed,
                "corrections": [
                    {
                        "question": questions[i].text,
                        "your_answer": responses[i],
                        "expected": correct_answers[i],
                        "is_correct": responses[i] == correct_answers[i]
                    }
                    for i in range(len(questions))
                ]
            })

    except User.DoesNotExist:
        return Response({"error": "Utilisateur introuvable"}, status=404)
    except Lesson.DoesNotExist:
        return Response({"error": "Leçon introuvable"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)



def can_access_lesson(user, lesson_id):
    try:
        current_lesson = Lesson.objects.get(pk=lesson_id)
        print(f"current_lesson.id = {current_lesson.id}, user.id = {user.id}")

        # Liste ordonnée de toutes les leçons partagées
        lessons = Lesson.objects.all().order_by('id')
        lesson_ids = list(lessons.values_list('id', flat=True))
        print(f"lesson_ids = {lesson_ids}")

        if lesson_id not in lesson_ids:
            print("Leçon pas dans la liste.")
            return False

        current_index = lesson_ids.index(lesson_id)
        print(f"Index de la leçon actuelle = {current_index}")

        # ✅ Autoriser l'accès à la première leçon sans condition
        if current_index == 0:
            print("Première leçon : accessible.")
            return True

        # 🔒 Vérification pour les autres leçons
        previous_lesson_id = lesson_ids[current_index - 1]
        previous_lesson = Lesson.objects.get(id=previous_lesson_id)

        progress = LessonProgress.objects.filter(
            user=user,
            lesson=previous_lesson,
            is_completed=True
        ).exists()
        print(f"Leçon précédente complétée ? {progress}")

        assignment = Assignment.objects.filter(lesson=previous_lesson).first()
        passed_exercise = False
        if assignment:
            submission = AssignmentSubmission.objects.filter(
                user=user, assignment=assignment
            ).order_by('-submitted_at').first()
            passed_exercise = submission and submission.score and submission.score >= 50
        print(f"Exercice précédent réussi ? {passed_exercise}")

        return progress and passed_exercise

    except Lesson.DoesNotExist:
        print("Leçon inexistante.")
        return False
    except Exception as e:
        print(f"Exception can_access_lesson: {e}")
        return False



@api_view(['GET'])
def view_lesson_content(request, user_id, lesson_id):
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({"error": "Utilisateur introuvable"}, status=404)

    try:
        lesson = Lesson.objects.get(pk=lesson_id)
    except Lesson.DoesNotExist:
        return Response({"error": "Leçon introuvable"}, status=404)

    # Vérifie si l'utilisateur peut accéder à cette leçon
    if not can_access_lesson(user, lesson_id):
        return Response({"error": "Cours verrouillé. Terminez d'abord les étapes précédentes."}, status=403)

    # OK : on renvoie le contenu du cours
    return Response({
        "id": lesson.id,
        "title": lesson.title,
        "content": lesson.content
    })

