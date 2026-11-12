from django.contrib import admin

from .models import Complaint, ComplaintEvidence, ComplaintLog, ComplaintMessage


class ReadOnlyHistory(admin.ModelAdmin):
    """Complaint history must not be edited or deleted (NFR-H-11.2)."""
    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Complaint)
class ComplaintAdmin(ReadOnlyHistory):
    list_display = ('reference', 'subject', 'submitted_by', 'against', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('reference', 'subject', 'submitted_by__username')


admin.site.register(ComplaintMessage, ReadOnlyHistory)
admin.site.register(ComplaintEvidence, ReadOnlyHistory)
admin.site.register(ComplaintLog, ReadOnlyHistory)
