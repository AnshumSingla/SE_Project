# 🤖 Automated Email Reminder System

A multi-agent system using **Microsoft AutoGen** that automatically scans your Gmail for job opportunities, extracts deadlines, and creates Google Calendar reminders.

## ✨ Features

- **📧 Gmail Integration**: Automatically scans your Gmail for new emails
- **🤖 Multi-Agent AI**: Uses AutoGen agents for intelligent email classification
- **🎯 Smart Detection**: Identifies job postings, interviews, assessments, and deadlines
- **📅 Calendar Integration**: Creates Google Calendar reminders with smart alerts
- **⚡ Dual Mode**: LLM-powered analysis with rule-based fallback
- **🔍 Advanced Search**: Find specific job-related emails
- **📊 Analytics**: Track job applications and deadlines

## 🏗️ System Architecture

The system uses **Approach 1: Multi-Agent Pipeline** with these specialized agents:

```
📧 Gmail Scanner → 🔍 Email Classifier → ⏰ Deadline Extractor → 📅 Calendar Manager
```

### Agent Roles:

- **Gmail Agent**: Fetches emails using Gmail API
- **Classifier Agent**: Identifies job-related emails using AI
- **Deadline Agent**: Extracts dates and deadlines
- **Calendar Agent**: Creates Google Calendar reminders

## 🚀 Quick Start

### 1. Clone and Install

```bash
git clone <your-repo>
cd SE_Project
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements_full.txt
```

### 2. Setup Environment Variables

Create a `.env` file based on `.env.template`:

```bash
cp .env.template .env
```

Edit `.env` with your API keys:

```env
OPENAI_API_KEY=sk-your-openai-api-key
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json
CALENDAR_CREDENTIALS_FILE=calendar_credentials.json
CALENDAR_TOKEN_FILE=calendar_token.json
```

### 3. Setup Google APIs

#### Gmail API Setup:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Gmail API**
4. Create **OAuth 2.0 Client ID** credentials
5. Download as `credentials.json`
6. Set authorized redirect URIs: `http://localhost`

#### Google Calendar API Setup:

1. In the same project, enable **Google Calendar API**
2. Use the same credentials file or create separate ones
3. Download as `calendar_credentials.json`

### 4. Run the System

#### Demo Mode (No APIs needed):

```bash
python main_demo.py
```

#### Full System with Gmail:

```bash
python complete_system.py
```

## 📋 Usage Examples

### Basic Email Scanning

```python
from complete_system import IntegratedEmailReminderSystem

# Initialize system
system = IntegratedEmailReminderSystem()

# Scan last 7 days of emails
results = system.scan_gmail_and_process(
    max_emails=50,
    days_back=7
)
```

### Search Specific Emails

```python
# Search for interview emails
results = system.search_job_emails("interview")

# Search by company
results = system.search_job_emails("from:company.com")
```

### Get Upcoming Deadlines

```python
upcoming = system.get_upcoming_deadlines(days_ahead=30)
for deadline in upcoming:
    print(f"📅 {deadline['title']} - {deadline['start_time']}")
```

## 🎯 Email Classification

The system automatically detects:

### Job-Related Categories:

- **📝 Applications**: Job application deadlines
- **🎯 Interviews**: Interview invitations and confirmations
- **💻 Assessments**: Coding challenges and technical tests
- **✉️ Responses**: Required responses and confirmations
- **📅 Events**: Career fairs, networking events
- **🎓 Academic**: University applications, scholarships

### Deadline Types:

- Application submissions
- Interview scheduling
- Assessment completions
- Response requirements
- Event registrations

## 📅 Calendar Integration Features

### Smart Reminders:

- **1 week before** (for applications)
- **1 day before** (all deadlines)
- **1 hour before** (urgent deadlines)
- **Custom alerts** based on deadline type

### Event Details:

- 🏷️ Color-coded by urgency (Red for urgent, Orange for applications)
- 📝 Detailed descriptions with action items
- 🔗 Links back to original emails
- 📊 Metadata for tracking and analytics

## 🔧 Configuration Options

### Email Scanning Settings:

```python
# In .env file
MAX_EMAILS_TO_PROCESS=50
DAYS_BACK_TO_SCAN=7
DEFAULT_TIMEZONE=America/New_York
```

### Gmail Search Queries:

- `from:careers@company.com` - Specific sender
- `subject:interview` - Subject keywords
- `after:2025/11/01` - Date ranges
- `has:attachment` - Emails with attachments

## 🛠️ Troubleshooting

### Common Issues:

#### 1. **Gmail Authentication Failed**

```bash
# Delete existing tokens and re-authenticate
rm token.json
python complete_system.py
```

#### 2. **OpenAI API Quota Exceeded**

- System automatically falls back to rule-based analysis
- No functionality is lost

#### 3. **Calendar Permission Denied**

```bash
# Delete calendar tokens and re-authenticate
rm calendar_token.json
python complete_system.py
```

#### 4. **No Emails Found**

- Check Gmail API quotas
- Verify OAuth scopes include Gmail read access
- Try broader date ranges

### Debug Mode:

```python
# Enable verbose logging
import os
os.environ['AUTOGEN_LOGGING'] = 'DEBUG'
```

## 📊 System Modes

### 1. **Full Mode** (complete_system.py)

- Gmail integration ✅
- Calendar integration ✅
- LLM analysis ✅
- Rule-based fallback ✅

### 2. **Demo Mode** (main_demo.py)

- Sample emails ✅
- Rule-based analysis ✅
- Calendar event creation ✅
- No API keys needed ✅

### 3. **LLM Mode** (main.py)

- AutoGen agents ✅
- Requires OpenAI API ✅
- Advanced analysis ✅

## 🔄 Automation Options

### Schedule Regular Scans:

#### Windows Task Scheduler:

```cmd
schtasks /create /tn "EmailReminder" /tr "python C:\path\to\complete_system.py" /sc daily /st 09:00
```

#### Linux Cron:

```bash
# Add to crontab
0 9 * * * /path/to/venv/bin/python /path/to/complete_system.py
```

### Webhook Integration:

- Set up Gmail push notifications
- Trigger analysis on new emails
- Real-time deadline detection

## 🎓 Extending the System

### Add New Email Types:

```python
# In main_demo.py, extend job_keywords list
job_keywords.extend([
    'scholarship', 'fellowship', 'grant',
    'conference', 'workshop', 'seminar'
])
```

### Custom Deadline Patterns:

```python
# Add new regex patterns for deadlines
deadline_patterns.append(r'submit\s+before\s+(\w+\s+\d{1,2})')
```

### Additional Calendar Features:

- Multiple calendar support
- Custom reminder intervals
- Integration with other calendar systems

## 📈 Performance Tips

1. **Limit Email Scope**: Use specific Gmail queries to reduce processing time
2. **Batch Processing**: Process emails in chunks for large mailboxes
3. **Caching**: Results are cached to avoid re-processing same emails
4. **API Quotas**: Monitor Gmail and Calendar API usage

## 🔒 Security & Privacy

- **OAuth 2.0**: Secure Google API authentication
- **Local Storage**: All data processed locally
- **No Email Storage**: Emails are analyzed but not permanently stored
- **Encrypted Tokens**: API tokens are encrypted and stored securely

## 📞 Support

### Need Help?

1. Check the troubleshooting section
2. Review Google API documentation
3. Verify all credentials and permissions
4. Test with demo mode first

### Contributing:

- Fork the repository
- Create feature branches
- Submit pull requests
- Follow coding standards

---

## 🎯 Next Steps After Setup:

1. **Test with Demo**: Run `python main_demo.py` first
2. **Configure APIs**: Set up Gmail and Calendar credentials
3. **Customize Keywords**: Adjust job keywords for your needs
4. **Set Automation**: Schedule regular scans
5. **Monitor Results**: Check calendar for created reminders

**Happy job hunting! 🚀**
