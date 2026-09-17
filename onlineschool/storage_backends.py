from django.conf import settings
from django.core.files.storage import FileSystemStorage

# Lesson videos and notes are saved here instead of MEDIA_ROOT so there is no public
# URL that can serve them - the only way to read a file from this storage is through
# a Django view that checks payment/enrollment first (see courses/views.py).
protected_storage = FileSystemStorage(location=str(settings.PROTECTED_MEDIA_ROOT))
