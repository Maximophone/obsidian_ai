"""
External services configuration settings.
Contains URLs, endpoints, and other settings for external services used by the application.
"""

# Google API scopes for Gmail and GDoc integration
GOOGLE_SCOPES = [
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/apps.groups.migration',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file',
]
