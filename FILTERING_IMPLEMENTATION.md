# Filtering System Implementation Guide

## Overview

This document describes the comprehensive filtering system implemented to prevent expired and duplicate reminders from appearing in the dashboard.

## Problem Addressed

Previously, the `/api/emails/scan` endpoint showed:

- ❌ Old deadlines that had already passed
- ❌ Deadlines already added to Google Calendar
- ❌ Cluttered dashboard with irrelevant items

## Solution Implemented

### 1. Future Deadline Filtering

**Purpose:** Filter out expired deadlines

**Implementation:**

```python
def _is_future_deadline(deadline_date: str) -> bool:
    """Check if deadline is today or in the future"""
    if not deadline_date:
        return False
    try:
        deadline = datetime.fromisoformat(deadline_date.replace('Z', '+00:00'))
        return deadline.date() >= datetime.now().date()
    except Exception as e:
        print(f"⚠️ Error checking deadline date: {e}")
        return False
```

**How it works:**

- Parses deadline date to datetime object
- Compares deadline.date() with today's date
- Returns True only if deadline is today or future
- Safely handles invalid dates

### 2. Duplicate Detection

**Purpose:** Avoid showing reminders already synced to Google Calendar

**Implementation:**

```python
def _get_existing_calendar_events():
    """Load all existing 'Job Deadline' events from Google Calendar"""
    # ... authentication code ...

    results = service.events().list(
        calendarId='primary',
        timeMin=now,
        timeMax=end,
        singleEvents=True,
        orderBy='startTime',
        q='Job Deadline'  # Search for events with this text
    ).execute()

    # Extract and normalize event summaries
    existing_titles = set()
    for event in results.get('items', []):
        summary = event.get('summary', '')
        if summary:
            existing_titles.add(summary.strip().lower())

    return existing_titles
```

**How it works:**

- Queries Google Calendar for events in next 365 days
- Searches for events containing "Job Deadline"
- Normalizes titles (lowercase, stripped)
- Returns set of existing event titles
- Handles authentication errors gracefully

### 3. Integration in /api/emails/scan

**Filter Logic:**

```python
# Load existing calendar events once
existing_titles = _get_existing_calendar_events()

for result in results:
    # ... extract email data ...

    # Filter 1: Skip emails without deadlines
    if not deadline_info or not deadline_info.get('has_deadline'):
        skipped_count += 1
        continue

    # Filter 2: Skip expired deadlines
    deadline_date = deadline_info.get('deadline_date')
    if not _is_future_deadline(deadline_date):
        print(f"⏭️ Skipping expired deadline for: {subject[:50]}...")
        expired_count += 1
        skipped_count += 1
        continue

    # Filter 3: Skip duplicates in Google Calendar
    subject = email_data.get('subject', '').strip().lower()
    is_duplicate = any(subject in existing or existing in subject
                      for existing in existing_titles)
    if is_duplicate:
        print(f"🔄 Skipping duplicate (already in calendar): {subject[:50]}...")
        duplicate_count += 1
        skipped_count += 1
        continue

    # Email passes all filters - add to results
    formatted_results.append(formatted_result)
```

### 4. Enhanced Response Statistics

**API Response includes detailed filtering stats:**

```json
{
  "success": true,
  "summary": {
    "total_emails_scanned": 50,
    "total_emails": 8,
    "expired_filtered": 12,
    "duplicates_filtered": 15,
    "total_filtered": 30,
    "emails_with_deadlines": 8
  },
  "emails": [...]
}
```

**Console Output:**

```
📊 Filtering summary:
   ⏭️  Expired deadlines: 12
   🔄 Duplicates (in calendar): 15
   ❌ Total filtered: 30
   ✅ New reminders to show: 8
```

## Benefits

### ✅ Clean Dashboard

- Shows only relevant, upcoming deadlines
- No clutter from past events
- No duplicate entries

### ✅ Cross-Device Sync

- Respects existing Google Calendar events
- Prevents duplicate notifications
- Consistent experience across devices

### ✅ Efficient Processing

- Batch loads calendar events (one API call)
- Fast comparison using sets
- Clear logging for debugging

### ✅ Error Handling

- Gracefully handles missing credentials
- Continues processing if calendar check fails
- Detailed error logging

## Testing

Run the test suite:

```bash
python test_filtering_system.py
```

**Test Coverage:**

1. ✅ Future deadline filtering
2. ✅ Duplicate detection
3. ✅ Complete filtering summary
4. ✅ Statistics accuracy

## Usage

### From Frontend

```javascript
// Scan emails - filtering happens automatically
const response = await apiService.scanEmails(user.id, {
  max_emails: 50,
  days_back: 30,
});

console.log(`New reminders: ${response.summary.total_emails}`);
console.log(`Duplicates filtered: ${response.summary.duplicates_filtered}`);
console.log(`Expired filtered: ${response.summary.expired_filtered}`);
```

### From API

```bash
curl -X POST http://localhost:5000/api/emails/scan \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "102084675131750001139",
    "max_emails": 50,
    "days_back": 30
  }'
```

## Filter Hierarchy

1. **No Deadline** → Skip immediately
2. **Expired Deadline** → Check date, skip if past
3. **Duplicate in Calendar** → Compare with existing events, skip if found
4. **Processing Status** → Skip if marked as duplicate/rejected during processing
5. **Pass All Filters** → Include in response

## Performance Considerations

- Calendar events loaded **once** per scan request
- Set-based comparison for O(1) duplicate checking
- Early filtering reduces data processing
- Minimal API calls to Google Calendar

## Future Enhancements

### Optional Features:

1. **Update Instead of Skip**: Modify existing events instead of skipping
2. **Configurable Timeframe**: Allow users to set future days range
3. **Smart Matching**: Fuzzy matching for better duplicate detection
4. **Caching**: Cache calendar events for faster repeated scans

## Troubleshooting

### No Duplicates Detected

**Cause:** `calendar_token.json` not found
**Solution:** Authenticate with Google Calendar first

### All Events Filtered

**Cause:** All deadlines are expired or duplicates
**Solution:** Expected behavior - check Google Calendar for existing events

### Unexpected Duplicates

**Cause:** Subject line variations
**Solution:** Check console logs for comparison details

## Code Locations

- **Helper Functions**: `api_service.py` lines 1007-1070
- **Filtering Logic**: `api_service.py` lines 335-368
- **Statistics**: `api_service.py` lines 405-432
- **Tests**: `test_filtering_system.py`

## Summary

The filtering system ensures users see **only new, relevant, upcoming deadlines** by:

- ✅ Rejecting past deadlines
- ✅ Detecting Google Calendar duplicates
- ✅ Providing detailed filtering statistics
- ✅ Maintaining clean dashboard experience

This implementation follows the methodology outlined in the requirements and provides a production-ready solution for preventing expired and duplicate reminders.
