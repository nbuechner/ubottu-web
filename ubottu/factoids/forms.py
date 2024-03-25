from django.forms import ModelForm, Textarea
from .models import Fact
class FactForm(ModelForm):
    class Meta:
        model = Fact
        fields = '__all__'
        widgets = {
                'value': Textarea(attrs={'cols': 60, 'rows': 10}),
        }