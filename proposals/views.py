from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from datetime import timedelta
from .models import Proposal

@staff_member_required
def weekly_changelog(request):
    """
    Generate and download a weekly changelog text file showing all proposal changes
    in the past 7 days. Accessible at /admin/changelog
    """
    # Calculate date range for the past week
    end_date = timezone.now()
    start_date = end_date - timedelta(days=7)
    
    # Get all historical records for proposals in the past week
    from .models import Proposal
    historical_proposals = Proposal.history.filter(
        history_date__gte=start_date,
        history_date__lte=end_date
    ).order_by('-history_date')
    
    # Generate changelog content
    changelog_lines = []
    changelog_lines.append("GCIR-GMS Weekly Changelog Report")
    changelog_lines.append("=" * 50)
    changelog_lines.append(f"Period: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
    changelog_lines.append(f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    changelog_lines.append("")
    
    if not historical_proposals.exists():
        changelog_lines.append("No changes found in the past week.")
    else:
        changelog_lines.append(f"Total changes found: {historical_proposals.count()}")
        changelog_lines.append("")
        
        for record in historical_proposals:
            # Determine change type
            change_type = {
                '+': 'CREATED',
                '~': 'MODIFIED', 
                '-': 'DELETED'
            }.get(record.history_type, 'UNKNOWN')
            
            changelog_lines.append(f"[{record.history_date.strftime('%Y-%m-%d %H:%M:%S')}] {change_type}")
            changelog_lines.append(f"  GCIR Code: {record.gcir_code or 'N/A'}")
            changelog_lines.append(f"  Title: {record.title}")
            changelog_lines.append(f"  Status: {record.status}")
            changelog_lines.append(f"  Department: {record.department}")
            changelog_lines.append(f"  Project Type: {record.project_type}")
            
            if record.history_user:
                changelog_lines.append(f"  Changed by: {record.history_user.username}")
            else:
                changelog_lines.append(f"  Changed by: System")
                
            if record.history_change_reason:
                changelog_lines.append(f"  Reason: {record.history_change_reason}")
                
            changelog_lines.append("")  # Empty line between records
    
    # Create the response with text file download
    response = HttpResponse(
        "\n".join(changelog_lines),
        content_type='text/plain'
    )
    
    # Set headers to trigger download
    filename = f"gcir_changelog_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.txt"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response
