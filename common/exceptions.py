"""
Common exception classes
"""


class BaseAppException(Exception):
    """앱 기본 예외 클래스"""
    
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class ValidationException(BaseAppException):
    """유효성 검증 예외"""
    pass


class BusinessLogicException(BaseAppException):
    """비즈니스 로직 예외"""
    pass


class ExternalAPIException(BaseAppException):
    """외부 API 호출 예외"""
    
    def __init__(self, message: str, api_name: str = None, status_code: int = None):
        self.api_name = api_name
        self.status_code = status_code
        super().__init__(message)


class DataNotFoundException(BaseAppException):
    """데이터 없음 예외"""
    pass


class PermissionDeniedException(BaseAppException):
    """권한 거부 예외"""
    pass
