from django.shortcuts import get_object_or_404, render

from .models import Certificate


def verify_certificate(request, code):
    certificate = get_object_or_404(Certificate, certificate_code=code)
    return render(request, 'certificates/certificate.html', {'certificate': certificate})
