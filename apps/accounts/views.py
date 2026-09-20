from django.http import HttpResponse


def home(request):
    return HttpResponse(
        "FlowMind AI Accounts"
    )