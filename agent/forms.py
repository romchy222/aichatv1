from django import forms


class ChatMessageForm(forms.Form):
    """Form for handling chat message input"""
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Type your message here...',
            'required': True
        }),
        max_length=1000,
        help_text="Enter your question or message (max 1000 characters)"
    )
    
    def clean_message(self):
        message = self.cleaned_data['message']
        if len(message.strip()) < 3:
            raise forms.ValidationError("Message must be at least 3 characters long.")
        return message.strip()


class FAQSearchForm(forms.Form):
    """Form for searching FAQ entries"""
    
    q = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search FAQ...',
        }),
        max_length=200,
        required=False
    )
    
    category = forms.ChoiceField(
        choices=[('', 'All Categories')] + [
            ('schedules', 'Schedules'),
            ('documents', 'Documents'),
            ('scholarships', 'Scholarships'),
            ('exams', 'Exams'),
            ('administration', 'Administration'),
            ('general', 'General'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        required=False
    )
