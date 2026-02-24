from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseProvider(ABC):
    def __init__(self, credentials: Dict[str, Any]):
        self.credentials = credentials
    
    @abstractmethod
    def send(self, from_email: str, to_email: str, subject: str, html_body: str, text_body: str = None) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def verify(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_rate_limit(self) -> int:
        pass
