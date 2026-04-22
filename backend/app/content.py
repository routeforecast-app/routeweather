from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models import LegalDocument


DEFAULT_LEGAL_DOCUMENTS = {
    "privacy": {
        "title": "Privacy Notice",
        "body": """Last updated: [DATE]

This Privacy Notice explains how we collect, use, and protect your personal data when you use [YOUR DOMAIN] (“the Service”).

1. What we collect
We may collect:

* Email address (for account creation and login)
* Account data (saved routes, preferences)
* Technical data (IP address, browser type, device info)
* Usage data (how you use the Service)

2. How we use your data
We use your data to:

* Create and manage your account
* Send essential emails (e.g. password reset, account notifications)
* Provide and improve the Service
* Ensure security and prevent abuse

We do not sell your personal data.

3. Emails
We send transactional emails only, such as:

* Account registration
* Password reset
* Important service updates

4. Advertising
We use Google AdSense to display advertisements.

Google and its partners may use cookies to:

* Show personalised ads
* Measure ad performance

You can learn how Google uses data here:
https://policies.google.com/technologies/ads

5. Cookies
We use cookies and similar technologies. See our Cookie Notice for details.

6. Data sharing
We may share data with:

* Hosting providers
* Email delivery services
* Analytics providers
* Advertising partners (e.g. Google AdSense)

We only share what is necessary.

7. Data retention
We keep your data as long as your account is active or as needed to provide the Service.

8. Your rights (UK/EU users)
You have the right to:

* Access your data
* Correct inaccurate data
* Request deletion of your data
* Object to processing

To request this, contact: [YOUR EMAIL]

9. Security
We take reasonable steps to protect your data, but no system is completely secure.

10. Contact
For any privacy questions:
Email: [YOUR EMAIL]""",
    },
    "terms": {
        "title": "Terms and Conditions",
        "body": """Last updated: [DATE]

By using [YOUR DOMAIN], you agree to these Terms.

1. Use of the Service
You agree to:

* Use the Service lawfully
* Not misuse or attempt to disrupt the Service
* Keep your account details secure

2. Accounts
You are responsible for:

* Your account activity
* Keeping your login details secure

We may suspend accounts that violate these Terms.

3. Service description
This Service provides route-based weather planning tools for walking and cycling.

We do not guarantee:

* Accuracy of weather data
* Availability of the Service at all times

Use the Service at your own risk.

4. Advertising
The Service may display advertisements, including Google AdSense ads.

We are not responsible for:

* Third-party ad content
* External websites linked through ads

5. Paid features (future)
We may offer paid features or subscriptions.

Additional terms may apply to paid services.

6. Limitation of liability
We are not liable for:

* Loss or damage from use of the Service
* Decisions made based on weather data

7. Changes to the Service
We may modify or stop parts of the Service at any time.

8. Changes to Terms
We may update these Terms. Continued use means you accept updates.

9. Governing law
These Terms are governed by the laws of England and Wales.

10. Contact
Email: [YOUR EMAIL]""",
    },
    "cookies": {
        "title": "Cookie Notice",
        "body": """Last updated: [DATE]

This Cookie Notice explains how [YOUR DOMAIN] uses cookies.

1. What are cookies
Cookies are small text files stored on your device when you visit a website.

2. How we use cookies
We use cookies to:

* Keep you logged in
* Improve site performance
* Understand usage
* Show advertisements

3. Advertising cookies
We use Google AdSense.

Google may use cookies to:

* Show personalised ads
* Measure ad performance

Learn more:
https://policies.google.com/technologies/ads

4. Types of cookies we use

* Essential cookies (login, security)
* Analytics cookies (usage tracking)
* Advertising cookies (ads and targeting)

5. Managing cookies
You can:

* Control cookies in your browser settings
* Disable cookies (may affect functionality)

6. Consent
We will request your consent before using non-essential cookies.

7. Contact
Email: [YOUR EMAIL]""",
    },
    "contact": {
        "title": "Contact Details",
        "body": """Last updated: [DATE]

For all RouteForcast enquiries, please contact:

Email: [YOUR EMAIL]
Website: [YOUR DOMAIN]

You can use this contact point for:

* Privacy queries
* Terms and account questions
* Support requests
* Data access or deletion requests

We aim to respond as soon as reasonably possible.""",
    },
}


def seed_legal_documents(session: Session) -> None:
    for document_type, document in DEFAULT_LEGAL_DOCUMENTS.items():
        existing = session.exec(
            select(LegalDocument).where(LegalDocument.document_type == document_type)
        ).first()
        if existing:
            updated_title = existing.title.replace("RouteWeather", "RouteForcast")
            updated_body = existing.body.replace("RouteWeather", "RouteForcast")
            if updated_title != existing.title or updated_body != existing.body:
                existing.title = updated_title
                existing.body = updated_body
                existing.updated_at = datetime.now(timezone.utc)
                session.add(existing)
            continue
        session.add(
            LegalDocument(
                document_type=document_type,
                title=document["title"],
                body=document["body"],
            )
        )
    session.commit()


def update_legal_document(document: LegalDocument, title: str, body: str) -> LegalDocument:
    document.title = title.strip()
    document.body = body.strip()
    document.updated_at = datetime.now(timezone.utc)
    return document
