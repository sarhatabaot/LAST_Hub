from django import forms

from hub.models import AccountRequest


class AccountRequestForm(forms.ModelForm):
    class Meta:
        model = AccountRequest
        fields = ["name", "email", "organization", "justification"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Full name"}),
            "email": forms.EmailInput(attrs={"placeholder": "name@example.org"}),
            "organization": forms.TextInput(attrs={"placeholder": "Organization or team (optional)"}),
            "justification": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Briefly describe your role and why you need access."}
            ),
        }
