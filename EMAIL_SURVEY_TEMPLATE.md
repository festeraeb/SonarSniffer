# SAR Platform Survey - Email Template

**Send this email to all SAR teams with the attached HTML file**

---

## Email Content

```
Subject: SAR Platform Survey - Community Input Needed (Deadline: Dec 31)

Hi [Team Name/SAR Community],

We're developing a unified Search & Rescue platform and need YOUR feedback to get it right.

Please complete the SAR Platform Survey by December 31, 2025 (Midnight).
Time to complete: 10-15 minutes

HOW TO RESPOND:
1. Download and open the attached file: SAR_PLATFORM_SURVEY_INTERACTIVE.html
2. Double-click the file to open it in your browser
3. Fill out the survey (works offline - no internet needed!)
4. Click the "✓ Submit Response" button at the bottom
5. You'll be redirected to submit to our online form

Your operational insights are invaluable - whether you're a small volunteer team or a major SAR 
organization, your feedback directly shapes the platform development.

QUESTIONS?
Contact: Thom (festeraeb)
Email: festeraeb@sar-platform.com

Together, we're building tools that save lives.

---

[Attach file: SAR_PLATFORM_SURVEY_INTERACTIVE.html]
```

---

## Key Points:

✅ **Single file attachment** - Easy for recipients
✅ **Works offline** - They can fill it out without internet
✅ **One-click submission** - Opens Google Forms link when done
✅ **Professional** - Clean, organized survey
✅ **Mobile-friendly** - Works on phones and tablets
✅ **No printing needed** - All digital

---

## Setup Instructions for You:

1. **Create Google Form**:
   - Go to `https://forms.google.com`
   - Create new form titled "SAR Platform Survey - Community Input"
   - Copy questions from `GOOGLE_FORM_QUESTIONS.txt`
   - Once created, copy your form's URL

2. **Update the HTML file**:
   - Open `SAR_PLATFORM_SURVEY_INTERACTIVE.html` in a text editor
   - Find this line: `window.open('https://docs.google.com/forms/d/[FORM_ID]/viewform', '_blank');`
   - Replace `[FORM_ID]` with your actual Google Form ID
   - Save the file

3. **Send the email**:
   - Attach the updated `SAR_PLATFORM_SURVEY_INTERACTIVE.html` file
   - Send to all SAR teams by December 31, 2025

---

## Data Flow:

```
Survey Taker
    ↓
Opens HTML file locally
    ↓
Fills out survey (offline)
    ↓
Clicks "Submit Response"
    ↓
Redirected to Google Form link
    ↓
Response submitted to Google Forms
    ↓
Auto-collected in your Google Form responses
    ↓
Auto-populated in linked Google Sheet
```

All responses automatically collected in one place for easy analysis!

---

**Created**: November 26, 2025  
**Version**: 1.0
