from django.contrib import admin
from django.forms import ModelForm, Textarea
from .models import Fact
from .forms import FactForm

class FactAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'ftype', 'create_date', 'change_date', 'author', 'popularity')
    list_filter = ('ftype', 'create_date', 'author')  # Fields to add filters for
    search_fields = ('name', 'value')
    form = FactForm
    def get_form(self, request, obj=None, **kwargs):
        # Check if an instance is being added (obj is None) to exclude 'author_id' field
        if obj is None:  # This means a new instance is being created
            self.exclude = ('author',)
        else:  # Editing an existing instance
            self.exclude = []
        form = super(FactAdmin, self).get_form(request, obj, **kwargs)
        return form

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Indicates a new instance
            # Automatically set 'author_id' to current user for new instances
            obj.author_id = request.user.id
        super().save_model(request, obj, form, change)
    
admin.site.register(Fact, FactAdmin)
