"""Django Forms for the Accounts & B2B module.

These only validate input (Django Forms do not need the ORM to work), the
actual read/write against MongoDB happens in repo.py once a form is valid.
Field names match the <input name="..."> already used in the templates
under Frontend/templates/accounts/, so the GUI mock-ups built in Viec 6
work as-is once wired to these forms.
"""
import re

from django import forms

from . import repo

TAX_CODE_RE = re.compile(r'^\d{10}$|^\d{13}$')
PHONE_RE = re.compile(r'^[0-9]{9,11}$')


class RegisterForm(forms.Form):
    account_type = forms.ChoiceField(choices=[('retail', 'Retail'), ('wholesale', 'Wholesale')])
    full_name = forms.CharField(max_length=120)
    email = forms.EmailField()
    password = forms.CharField(min_length=8)
    password2 = forms.CharField(min_length=8)
    company_name = forms.CharField(max_length=200, required=False)
    tax_code = forms.CharField(max_length=13, required=False)
    agree = forms.BooleanField()

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if repo.find_user_by_email(email):
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean(self):
        cleaned = super().clean()
        pw1, pw2 = cleaned.get('password'), cleaned.get('password2')
        if pw1 and pw2 and pw1 != pw2:
            self.add_error('password2', 'Passwords do not match.')

        if cleaned.get('account_type') == 'wholesale':
            if not cleaned.get('company_name'):
                self.add_error('company_name', 'Company name is required for a business account.')
            tax_code = cleaned.get('tax_code') or ''
            if not TAX_CODE_RE.match(tax_code):
                self.add_error('tax_code', 'Tax code must be 10 or 13 digits.')
        return cleaned


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField()
    remember = forms.BooleanField(required=False)


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()


class ResetPasswordForm(forms.Form):
    password = forms.CharField(min_length=8)
    password2 = forms.CharField(min_length=8)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('password2'):
            self.add_error('password2', 'Passwords do not match.')
        return cleaned


class ProfileForm(forms.Form):
    full_name = forms.CharField(max_length=120)
    phone = forms.CharField(max_length=11, required=False)
    avatar = forms.ImageField(required=False)

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if phone and not PHONE_RE.match(phone):
            raise forms.ValidationError('Phone number must be 9 to 11 digits.')
        return phone

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            if avatar.size > 2 * 1024 * 1024:
                raise forms.ValidationError('Image must be 2MB or smaller.')
            if avatar.content_type not in ('image/jpeg', 'image/png'):
                raise forms.ValidationError('Only JPG or PNG images are accepted.')
        return avatar


class ChangePasswordForm(forms.Form):
    current_password = forms.CharField()
    password = forms.CharField(min_length=8)
    password2 = forms.CharField(min_length=8)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('password2'):
            self.add_error('password2', 'Passwords do not match.')
        return cleaned


class AddressForm(forms.Form):
    receiver_name = forms.CharField(max_length=120)
    phone = forms.CharField(max_length=11)
    province = forms.CharField(max_length=120)
    district = forms.CharField(max_length=120)
    detail = forms.CharField(max_length=250)
    is_default = forms.BooleanField(required=False)

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if not PHONE_RE.match(phone):
            raise forms.ValidationError('Phone number must be 9 to 11 digits.')
        return phone


class WholesaleRegisterForm(forms.Form):
    company_name = forms.CharField(max_length=200)
    tax_code = forms.CharField(max_length=13)
    company_address = forms.CharField(max_length=250)
    contact_person = forms.CharField(max_length=120)

    def clean_tax_code(self):
        tax_code = self.cleaned_data['tax_code']
        if not TAX_CODE_RE.match(tax_code):
            raise forms.ValidationError('Tax code must be 10 or 13 digits.')
        return tax_code
