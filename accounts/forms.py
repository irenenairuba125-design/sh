from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import User


class RegisterForm(UserCreationForm):
    phone = forms.CharField(
        max_length=20,
        required=True,
        help_text='Used for MTN MoMo / Airtel Money payments, e.g. 0771234567',
    )
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.is_blocked:
            raise ValidationError(
                'Your account has been blocked. Contact the school administrator.',
                code='blocked',
            )
