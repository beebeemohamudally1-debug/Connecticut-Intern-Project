from django.contrib import admin

from .models import Job, ProgressReport, TimeLog, WorkEvidence


class TimeLogInline(admin.TabularInline):
    model = TimeLog
    extra = 0


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('reference', 'service_name', 'customer', 'handyman', 'status', 'due_date', 'is_flagged')
    list_filter = ('status', 'is_flagged', 'payout_stage')
    search_fields = ('reference', 'service_name', 'customer__username', 'handyman__username')
    inlines = [TimeLogInline]


admin.site.register(ProgressReport)
admin.site.register(WorkEvidence)
