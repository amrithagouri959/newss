from django.shortcuts import render, redirect, get_object_or_404
from .models import Employee, WorkSession
from .forms import LoginForm, UserRegistrationForm
from django.contrib.auth import authenticate, logout, login
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from itertools import groupby
from datetime import date

def server_login(request):
    return render(request, "server/login.html")


def login_page(request):
    return render(request, "emp/login.html")


def server_page(request):
    return render(request, "server/welcome.html")


def client_page():
    return HttpResponseRedirect(reverse("emp:employee_selection"))


def password_login(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("emp:dashboard"))

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = request.POST["username"]
            password = request.POST["password"]
            user = authenticate(username=username, password=password)

            if user:
                if user.is_active:
                    login(request, user)
                    return HttpResponseRedirect(reverse("emp:dashboard"))
                else:
                    return HttpResponse("Something happened: User is not active")
            else:
                messages.error(
                    request, "Invalid username or password. Please try again."
                )
    else:
        form = LoginForm()

    context = {"form": form}

    return render(request, "emp/password_login.html", context)


def register(request):
    if request.user.is_authenticated:
        return HttpResponse("First logout")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST, request.FILES)

        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()

            Employee.objects.create(
                user=user,
                photo=request.FILES.get("photo"),
            )

            return HttpResponseRedirect(reverse("emp:server"))
    else:
        form = UserRegistrationForm()

    context = {"form": form}

    return render(request, "emp/register.html", context)


@login_required
def start_work(request):
    employee = Employee.objects.get(user=request.user)
    description = request.POST.get("description", "")
    machine_number = request.POST.get("machine", None)

    WorkSession.objects.create(
        employee=employee,
        start_time=timezone.now(),
        description=description,
        machine=machine_number
    )

    response = redirect("emp:dashboard")
    if machine_number:
        response.set_cookie("machine", machine_number, max_age=30*24*60*60)  # 30 days
    return response


@login_required
def end_work(request, session_id):
    session = WorkSession.objects.get(id=session_id)
    session.end_time = timezone.now()
    session.save()
    return redirect("emp:dashboard")


@login_required
def pause_work(request, session_id):
    session = WorkSession.objects.get(id=session_id)
    session.paused = True
    session.pause_time = timezone.now()
    session.save()
    return redirect("emp:dashboard")


@login_required
def resume_work(request, session_id):
    session = WorkSession.objects.get(id=session_id)
    if session.paused:
        pause_duration = timezone.now() - session.pause_time
        session.start_time += pause_duration
        session.paused = False
        session.pause_time = None
        session.save()
    return redirect("emp:dashboard")


@login_required
def update_session_description(request, session_id):
    if request.method == "POST":
        session = get_object_or_404(WorkSession, id=session_id)
        session.description = request.POST.get("description", "")
        session.save()
    return redirect("emp:dashboard")


def dashboard(request):
    if request.user.is_authenticated:
        employee = Employee.objects.get(user=request.user)
        sessions = WorkSession.objects.filter(employee=employee).order_by("-start_time")

        sessions_grouped_by_day = {}
        for day, group in groupby(sessions, key=lambda s: s.start_time.date()):
            sessions_grouped_by_day[day] = list(group)

        latest_session = sessions.first()
        today = date.today()

        context = {
            "latest_session": latest_session,
            "sessions_grouped_by_day": sessions_grouped_by_day,
            "today": today,
        }
        return render(request, "emp/dashboard.html", context)
    else:
        return HttpResponseRedirect(reverse("emp:employee_selection"))


@login_required
def user_logout(request):
    username = request.user.first_name + " " + request.user.last_name
    logout(request)
    return HttpResponseRedirect(reverse("emp:goodbye") + f"?username={username}")


def goodbye(request):
    username = request.GET.get("username")
    if not username:
        username = "User"
    return render(request, "emp/goodbye.html", {"username": username})


def employee_selection(request):
    employees = Employee.objects.all()
    return render(request, 'emp/employee_selection.html', {'employees': employees})