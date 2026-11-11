"""Signals fired by the jobs app.

The notifications app (another team member) can connect receivers to these,
so jobs does not depend on how notifications are stored.
"""
from django.dispatch import Signal

# Sent when a handyman marks a job as completed (FR-A-8.4, FR-C-3.3).
job_completed = Signal()  # provides: job
