import csv
import io
from utils.validators import is_valid_email
from models import db
from models.recipient_list import RecipientList, Recipient

class CSVImportService:
    @staticmethod
    def parse_csv(content: str) -> dict:
        try:
            reader = csv.DictReader(io.StringIO(content))
            headers = reader.fieldnames
            
            if not headers:
                return {'error': 'No headers found'}
            
            email_field = next((h for h in headers if h.lower() in ['email', 'e-mail', 'mail']), None)
            
            if not email_field:
                return {'error': 'No email column found', 'headers': headers}
            
            rows = []
            seen = set()
            
            for row in reader:
                email = row.get(email_field, '').strip().lower()
                
                if not email or not is_valid_email(email):
                    continue
                
                if email in seen:
                    continue
                
                seen.add(email)
                rows.append({'email': email, 'data': {k: v for k, v in row.items() if k != email_field}})
            
            return {'headers': headers, 'email_field': email_field, 'rows': rows, 'count': len(rows)}
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def create_list(user_id: int, name: str, rows: list) -> RecipientList:
        recipient_list = RecipientList(user_id=user_id, name=name, recipient_count=len(rows))
        db.session.add(recipient_list)
        db.session.flush()
        
        for row in rows:
            recipient = Recipient(list_id=recipient_list.id, email=row['email'], data=row['data'])
            db.session.add(recipient)
        
        db.session.commit()
        return recipient_list
