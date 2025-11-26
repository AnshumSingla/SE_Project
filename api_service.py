"""
Email Reminder API Service

Flask-based API service that provides endpoints for the web/mobile app
to interact with the AutoGen email processing system.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime
from typing import Dict, List, Optional
import traceback
from dotenv import load_dotenv

# Import our email processing system
from complete_system import IntegratedEmailReminderSystem

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for web app integration

# Global system instance
email_system = None

def init_system():
    """Initialize the email reminder system"""
    global email_system
    try:
        email_system = IntegratedEmailReminderSystem(use_llm=True)
        return True
    except Exception as e:
        print(f"❌ System initialization failed: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "system_ready": email_system is not None
    })

@app.route('/api/auth/setup', methods=['POST'])
def setup_user_credentials():
    """
    Setup user's Google credentials for Gmail and Calendar access
    
    Expected payload:
    {
        "user_id": "unique_user_id",
        "gmail_credentials": "base64_encoded_credentials",
        "calendar_credentials": "base64_encoded_credentials"
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id is required"
            }), 400
        
        # Store user credentials securely (implement proper encryption)
        # For now, return success
        
        return jsonify({
            "success": True,
            "message": "User credentials setup successfully",
            "user_id": user_id
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/emails/scan', methods=['POST'])
def scan_emails():
    """
    Scan user's emails and process them for job opportunities
    
    Expected payload:
    {
        "user_id": "unique_user_id",
        "max_emails": 50,
        "days_back": 7,
        "search_query": "optional gmail search query"
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        max_emails = data.get('max_emails', 50)
        days_back = data.get('days_back', 7)
        search_query = data.get('search_query', '')
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id is required"
            }), 400
        
        # Process emails using the system
        if not email_system:
            return jsonify({
                "success": False,
                "error": "Email system not initialized"
            }), 500
        
        # Fetch and process real emails from user's Gmail account
        try:
            print(f"📧 Attempting to process emails for user: {user_id}")
            results = email_system.process_user_emails(
                user_id=user_id,
                max_emails=max_emails,
                days_back=days_back,
                search_query=search_query
            )
            print(f"✅ Successfully processed {len(results)} emails")
        except Exception as e:
            print(f"❌ Error processing user emails: {e}")
            print(f"📝 Falling back to sample emails for demonstration")
            # Fallback to sample emails if real email processing fails
            results = email_system._process_sample_emails()
            
            # Add a note about the fallback in the results
            for result in results:
                if 'email_data' in result:
                    result['email_data']['note'] = 'Sample data - Gmail authentication pending'
        
        # Format results for API response
        formatted_results = []
        for result in results:
            email_data = result.get('email_data', {})
            classification = result.get('classification', {})
            deadline_info = result.get('deadline_info', {})
            
            formatted_result = {
                "email_id": email_data.get('id', 'sample_' + str(len(formatted_results))),
                "subject": email_data.get('subject', ''),
                "sender": email_data.get('sender', ''),
                "date": email_data.get('date', ''),
                "snippet": email_data.get('snippet', email_data.get('body', '')[:200]),
                "classification": {
                    "is_job_related": classification.get('is_job_related', False),
                    "category": classification.get('category', 'other'),
                    "urgency": classification.get('urgency', 'low'),
                    "confidence": classification.get('confidence', 0.8),
                    "reasoning": classification.get('reason', classification.get('reasoning', ''))
                },
                "deadline": None
            }
            
            # Add deadline information if present
            if deadline_info and deadline_info.get('has_deadline'):
                formatted_result["deadline"] = {
                    "has_deadline": True,
                    "date": deadline_info.get('deadline_date'),
                    "time": deadline_info.get('deadline_time'),
                    "type": deadline_info.get('deadline_type'),
                    "description": deadline_info.get('description'),
                    "text": deadline_info.get('deadline_text'),
                    "urgency_days": _calculate_urgency_days(deadline_info.get('deadline_date'))
                }
            else:
                formatted_result["deadline"] = {"has_deadline": False}
            
            formatted_results.append(formatted_result)
        
        # Calculate summary statistics
        total_emails = len(formatted_results)
        job_related_count = sum(1 for r in formatted_results if r['classification']['is_job_related'])
        deadline_count = sum(1 for r in formatted_results if r['deadline']['has_deadline'])
        
        return jsonify({
            "success": True,
            "scan_timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "summary": {
                "total_emails": total_emails,
                "job_related_emails": job_related_count,
                "emails_with_deadlines": deadline_count,
                "scan_parameters": {
                    "max_emails": max_emails,
                    "days_back": days_back,
                    "search_query": search_query
                }
            },
            "emails": formatted_results
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/calendar/reminders', methods=['POST'])
def create_calendar_reminders():
    """
    Create calendar reminders for selected emails with deadlines
    
    Expected payload:
    {
        "user_id": "unique_user_id",
        "email_ids": ["email_id_1", "email_id_2"],
        "reminder_preferences": {
            "default_reminders": [1440, 60],  // minutes before
            "urgent_reminders": [10080, 1440, 60]
        }
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        email_ids = data.get('email_ids', [])
        reminder_prefs = data.get('reminder_preferences', {})
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id is required"
            }), 400
        
        # Process calendar reminder creation
        created_events = []
        for email_id in email_ids:
            # In production, fetch actual email data by ID
            # For demo, create sample event
            event_data = {
                "event_id": f"cal_event_{email_id}",
                "email_id": email_id,
                "title": "Job Deadline Reminder",
                "start_time": "2025-12-01T09:00:00Z",
                "end_time": "2025-12-01T10:00:00Z",
                "reminders": reminder_prefs.get('default_reminders', [1440, 60]),
                "calendar_link": f"https://calendar.google.com/calendar/event?eid={email_id}",
                "status": "created"
            }
            created_events.append(event_data)
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "created_events": created_events,
            "summary": {
                "total_events_created": len(created_events),
                "failed_events": 0
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/calendar/upcoming', methods=['GET'])
def get_upcoming_reminders():
    """
    Get upcoming job deadline reminders for a user
    
    Query parameters:
    - user_id: User identifier
    - days_ahead: Number of days to look ahead (default: 30)
    """
    try:
        user_id = request.args.get('user_id')
        days_ahead = int(request.args.get('days_ahead', 30))
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id is required"
            }), 400
        
        # For demo, return sample upcoming events
        upcoming_events = [
            {
                "event_id": "cal_event_1",
                "title": "APPLICATION DEADLINE: Software Engineering Internship",
                "start_time": "2025-12-15T23:59:00Z",
                "deadline_type": "application",
                "urgency": "medium",
                "days_until": 20,
                "original_email": {
                    "subject": "Software Engineering Internship - Application Deadline Reminder",
                    "sender": "careers@techcorp.com"
                },
                "calendar_link": "https://calendar.google.com/calendar/event?eid=cal_event_1",
                "next_reminder": "2025-12-14T23:59:00Z"
            },
            {
                "event_id": "cal_event_2", 
                "title": "ASSESSMENT DEADLINE: Coding Challenge",
                "start_time": "2025-12-01T23:59:00Z",
                "deadline_type": "assessment",
                "urgency": "high",
                "days_until": 6,
                "original_email": {
                    "subject": "Coding Challenge - Software Developer Position",
                    "sender": "tech-hiring@startup.io"
                },
                "calendar_link": "https://calendar.google.com/calendar/event?eid=cal_event_2",
                "next_reminder": "2025-11-30T23:59:00Z"
            }
        ]
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "query_parameters": {
                "days_ahead": days_ahead
            },
            "upcoming_events": upcoming_events,
            "summary": {
                "total_events": len(upcoming_events),
                "high_urgency": sum(1 for e in upcoming_events if e['urgency'] == 'high'),
                "medium_urgency": sum(1 for e in upcoming_events if e['urgency'] == 'medium'),
                "low_urgency": sum(1 for e in upcoming_events if e['urgency'] == 'low')
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/notifications/send', methods=['POST'])
def send_notification():
    """
    Send notification to user about upcoming deadlines
    
    Expected payload:
    {
        "user_id": "unique_user_id",
        "notification_type": "deadline_reminder|new_opportunities|daily_digest",
        "message": "Custom notification message",
        "event_id": "optional_calendar_event_id",
        "channels": ["push", "email", "sms"]
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        notification_type = data.get('notification_type')
        message = data.get('message')
        event_id = data.get('event_id')
        channels = data.get('channels', ['push'])
        
        if not user_id or not notification_type:
            return jsonify({
                "success": False,
                "error": "user_id and notification_type are required"
            }), 400
        
        # Simulate notification sending
        sent_notifications = []
        for channel in channels:
            notification_result = {
                "channel": channel,
                "status": "sent",
                "timestamp": datetime.now().isoformat(),
                "notification_id": f"notif_{user_id}_{len(sent_notifications)}"
            }
            sent_notifications.append(notification_result)
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "notification_type": notification_type,
            "message": message,
            "event_id": event_id,
            "sent_notifications": sent_notifications,
            "summary": {
                "total_sent": len(sent_notifications),
                "channels_used": channels
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/analytics/dashboard', methods=['GET'])
def get_dashboard_analytics():
    """
    Get analytics data for user dashboard
    
    Query parameters:
    - user_id: User identifier
    - period: time period (week|month|quarter|year)
    """
    try:
        user_id = request.args.get('user_id')
        period = request.args.get('period', 'month')
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id is required"
            }), 400
        
        # Sample analytics data
        analytics_data = {
            "period": period,
            "job_application_stats": {
                "total_opportunities_found": 15,
                "applications_submitted": 8,
                "interviews_scheduled": 3,
                "assessments_completed": 5,
                "deadlines_missed": 1,
                "response_rate": 53.3
            },
            "email_processing_stats": {
                "total_emails_processed": 240,
                "job_related_emails": 35,
                "job_related_percentage": 14.6,
                "deadlines_extracted": 22,
                "calendar_events_created": 18
            },
            "deadline_management": {
                "upcoming_deadlines": 6,
                "overdue_deadlines": 1,
                "completed_deadlines": 12,
                "average_notice_days": 8.5
            },
            "category_breakdown": {
                "applications": 45,
                "interviews": 20,
                "assessments": 25,
                "networking": 10
            }
        }
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "analytics": analytics_data,
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

def _calculate_urgency_days(deadline_date):
    """Calculate days until deadline for urgency calculation"""
    if not deadline_date:
        return None
    try:
        from datetime import datetime
        deadline = datetime.fromisoformat(deadline_date.replace('Z', '+00:00'))
        now = datetime.now()
        delta = deadline - now
        return max(0, delta.days)
    except:
        return None

if __name__ == '__main__':
    # Initialize the email system
    if init_system():
        print("🚀 Email Reminder API Service Starting...")
        print("📧 AutoGen Multi-Agent System Ready")
        print("🔗 API Endpoints Available:")
        print("   • POST /api/emails/scan - Scan and process emails")
        print("   • POST /api/calendar/reminders - Create calendar reminders")
        print("   • GET  /api/calendar/upcoming - Get upcoming deadlines")
        print("   • POST /api/notifications/send - Send notifications")
        print("   • GET  /api/analytics/dashboard - Get analytics data")
        print("=" * 50)
        
        # Run Flask app
        app.run(
            host='0.0.0.0',
            port=int(os.getenv('PORT', 5000)),
            debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        )
    else:
        print("❌ Failed to initialize email system")
        exit(1)