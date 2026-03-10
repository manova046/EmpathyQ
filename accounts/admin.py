from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import  ExpertProfile



@admin.register(ExpertProfile)
class ExpertProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'qualification', 'is_approved')
    list_editable = ('is_approved',)
