from django.shortcuts import render

def handyman_dashboard(request):
    return render(request, 'dashboard/handyman_dashboard.html')

def assigned_jobs(request):
    return render(request, 'dashboard/handyman_assigned_jobs.html')

def job_requests(request):
    return render(request, 'dashboard/handyman_job_requests.html')

def job_tracking(request):
    return render(request, 'dashboard/handyman_job_tracking.html')

def job_in_progress(request):
    return render(request, 'dashboard/handyman_job_in_progress.html')

def job_completed(request):
    return render(request, 'dashboard/handyman_job_completed.html')

def report_customer(request):
    return render(request, 'dashboard/handyman_report_customer.html')

def notifications(request):
    return render(request, 'dashboard/handyman_notifs.html')