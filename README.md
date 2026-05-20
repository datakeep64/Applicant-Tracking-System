# Applicant Tracking & Verification System

## Overview

This project is an applicant tracking and verification prototype built with Streamlit, SQLite, and Python. It simulates administrative case handling with document checklist enforcement, status workflows, officer remarks, follow-up tracking, and audit logging.

## Features

- Application intake with structured case details
- Automatic document requirement validation by application type
- Duplicate detection using email and phone
- Priority flags for operational triage
- Follow-up tracking with contact dates and due dates
- Status workflow constraints for review integrity
- Per-case audit history and timeline tracking
- Search by applicant name or case ID
- Export report options including filtered CSV output

## Technologies Used

- Python
- Streamlit
- SQLite
- Pandas

## Use Case

This application is designed to model real-world administrative workflows for application processing, including verification tasks, compliance checks, and case review management. It is useful for demonstrating how an operations system can enforce document policies, manage follow-ups, and maintain accountability through audit logs.

## Getting Started

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies from `requirements.txt`.
4. Run the app with:

```bash
streamlit run app.py
```

## Future Improvements

- Email notifications for follow-up actions
- Role-based access control for reviewers and admins
- Enhanced search and filtering capabilities
- More advanced reporting and dashboard views
