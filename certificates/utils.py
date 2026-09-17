from .models import Certificate


def issue_certificate_if_passed(user, course):
    certificate, _ = Certificate.objects.get_or_create(user=user, course=course)
    return certificate
