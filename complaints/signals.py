"""Signals fired by the complaints app, for the notifications app to listen to."""
from django.dispatch import Signal

complaint_submitted = Signal()         # complaint            (FR-A-8.6, FR-H-7.5)
complaint_enquiry_sent = Signal()      # complaint, message   (FR-C-3.5, FR-H-8.3)
complaint_response_received = Signal() # complaint, message   (FR-A-8.7)
complaint_status_changed = Signal()    # complaint            (FR-C-3.4)
