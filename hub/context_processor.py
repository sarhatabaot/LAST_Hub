from django.conf import settings


def project_info(request):
    return {
        "PROJECT_VERSION": settings.PROJECT_VERSION,
        "PROJECT_SOURCE_URL": settings.PROJECT_SOURCE_URL
    }