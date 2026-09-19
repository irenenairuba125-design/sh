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
    role = forms.CharField(required=False, widget=forms.HiddenInput)
    headline = forms.CharField(max_length=120, required=False, label='What you teach',
                               help_text='e.g. "Contracts that hold up"')
    location = forms.CharField(max_length=80, required=False, label='Where you are based',
                               help_text='e.g. Kampala')
    bio = forms.CharField(required=False, label='About you', widget=forms.Textarea(attrs={'rows': 3}),
                          help_text='Two or three lines about your experience.')
    payout_phone = forms.CharField(max_length=20, required=False, label='Mobile-money number for payouts',
                                   help_text='Where you will be paid, e.g. 0771234567')

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'password1', 'password2']

    TEACHER_FIELDS = ['headline', 'location', 'bio', 'payout_phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs['class'] = 'form-control'
        self.fields['username'].help_text = 'Letters, numbers and @ . + - _ only.'
        self.fields['password1'].help_text = 'At least 8 characters, not only numbers.'
        self.fields['password2'].help_text = ''

    def clean_role(self):
        # Only learners and teachers can self-register; admins are never created here.
        return 'teacher' if self.cleaned_data.get('role') in ('teacher', 'creator') else 'student'

    def clean(self):
        data = super().clean()
        if data.get('role') == 'teacher':
            for name in ('headline', 'location', 'payout_phone'):
                if not data.get(name):
                    self.add_error(name, 'This is needed so you can teach and be paid.')
        return data


class ProfileForm(forms.ModelForm):
    phone = forms.CharField(max_length=20, required=True, help_text='Used for MTN MoMo / Airtel Money payments, e.g. 0771234567')
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'headline', 'location', 'bio', 'payout_phone']
        labels = {'headline': 'What you teach', 'location': 'Where you are based',
                  'bio': 'About you', 'payout_phone': 'Mobile-money number for payouts'}
        widgets = {'bio': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not (self.instance and self.instance.role == User.Role.TEACHER):
            for name in ('headline', 'location', 'bio', 'payout_phone'):
                self.fields.pop(name, None)
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
