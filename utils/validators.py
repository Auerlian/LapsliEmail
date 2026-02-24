import re
from email_validator import validate_email, EmailNotValidError

def is_valid_email(email: str) -> bool:
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False

def check_spam_score(subject: str, body: str) -> dict:
    score = 0
    flags = []
    
    spam_words = ['free', 'click here', 'act now', 'limited time', 'winner', 'congratulations', 
                  'urgent', 'guarantee', 'no obligation', 'risk free', 'cash bonus']
    all_text = (subject + ' ' + body).lower()
    
    for word in spam_words:
        if word in all_text:
            score += 1
            flags.append(f"Contains spam word: {word}")
    
    if subject.isupper() and len(subject) > 5:
        score += 2
        flags.append("Subject is all caps")
    
    if subject.count('!') > 2:
        score += 1
        flags.append("Too many exclamation marks")
    
    if len(subject) > 100:
        score += 1
        flags.append("Subject line too long")
    
    if not subject:
        score += 2
        flags.append("Missing subject line")
    
    url_count = len(re.findall(r'https?://', body))
    if url_count > 5:
        score += 1
        flags.append(f"Too many URLs ({url_count})")
    
    return {'score': score, 'flags': flags, 'is_spam': score > 4}

def validate_unsubscribe_token(token: str) -> dict:
    """Validate unsubscribe token format"""
    if not token or len(token) < 32:
        return {'valid': False, 'error': 'Invalid token'}
    
    return {'valid': True}
