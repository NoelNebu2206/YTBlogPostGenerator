from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from pytube import YouTube
from django.conf import settings
import os
import assemblyai as aai
import cohere
from .models import BlogPost

# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
            #return JsonResponse({'content': yt_link})
        except(KeyError, json.JSONDecodeError):
            return JsonResponse({'error: Invalid JSON data sent'}, status=400)
        
        #get yt title
        title = yt_title(yt_link)
        
        #get transcript using Assembly AI
        transcript = get_transcript(yt_link)
        #return JsonResponse({'content': transcript})
        if not transcript:
            return JsonResponse({'error': 'Failed to get transcript'}, status=500)

        #Use Cohere to generate blog content
        blog_content = generate_blog_from_transcript(transcript)
        if not blog_content:
            return JsonResponse({'error': 'Failed to generate blog content'}, status=500)
        
        #save blog article to database
        new_blog_article = BlogPost.objects.create(
            user=request.user,
            youtube_title=title,
            youtube_link=yt_link,
            generated_content=blog_content
        )

        new_blog_article.save()

        #return blog article as a response
        return JsonResponse({'content': blog_content})

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

def yt_title(yt_link):
    yt = YouTube(yt_link)
    title = yt.title
    return title

def download_audio(yt_link):
    yt = YouTube(yt_link)
    audio = yt.streams.filter(only_audio=True).first()
    out_file = audio.download(output_path=settings.MEDIA_ROOT)
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    os.rename(out_file, new_file)
    return new_file

def get_transcript(yt_link):
    audio_file = download_audio(yt_link)
    #print("got the audio file")
    aai.settings.api_key = "9426f42791ba4b10b1cac3977cc053e8"

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)
    #print("transcript generated is:", transcript.text)

    return transcript.text

def generate_blog_from_transcript(transcript):
    # Use Cohere API to generate blog content
    cohere_api_key = "AtPKXCoEnTZlZdO2ntfu45juRMYkNtAvZdWssjWS"
    client = cohere.Client(cohere_api_key)
    prompt = f"Based on the following transcript from a YouTube video, write a comprehensive blog article, write it based on the transcript, but dont make it look like a youtube video, make it look like a proper blog article:\n\nTranscript:\n\n{transcript}\n\nArticle:"
    print("prompt is :",prompt)
    response = client.chat(
            message=prompt,
            model='command-r',
            max_tokens=4000,
            temperature=0.6
        )
    
    return response.text

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = "Invalid username or password"
            return render(request, 'login.html', {'error_message': error_message})
    return render(request, 'login.html')

def user_signup(request):
    print("Request contents", request.POST)
    if request.method == 'POST':
        username= request.POST['username']
        password= request.POST['password']
        email= request.POST['email']
        repeatPassword= request.POST['repeatPassword']

        if password == repeatPassword:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
                #return render(request, 'index.html')
            except:
                error_message = "Error creating account"
                return render(request, 'signup.html', {'error_message': error_message})
        else:
            return render(request, 'signup.html', {'error_message': 'Passwords do not match.'})
        
    return render(request, 'signup.html')

def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, "all-blogs.html", {'blog_articles': blog_articles})

def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request, "blog-details.html", {'blog_article_detail': blog_article_detail})
    else:
        return redirect('/')
    
def user_logout(request):
    logout(request)
    return redirect('/')