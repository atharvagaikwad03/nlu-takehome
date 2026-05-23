import re
from flask import jsonify

#exception so routes can raise and Flask returns errorwith 400
class ValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

#routes doesn't go for try and except just throws a error
def registerErrorHandlers(app):
    @app.errorhandler(ValidationError)
    def handleValidationError(e):
        return jsonify({"error": e.message}), 400


def stripControlChars(s: str) -> str:
    # strip ASCII control chars 
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", s)

#validate author field
def sanitizeAuthor(value) -> str:
    if not isinstance(value, str):
        raise ValidationError("author must be a string")
    value = value.strip()
    value = stripControlChars(value)
    if not value:
        raise ValidationError("author cannot be empty")
    if len(value) > 200:
        raise ValidationError("author must be 200 characters or fewer")
    return value

#validate comment field
def sanitizeComment(value) -> str:
    if not isinstance(value, str):
        raise ValidationError("comment must be a string")
    value = value.strip()
    value = stripControlChars(value)
    if not value:
        raise ValidationError("comment cannot be empty")
    if len(value) > 5000:
        raise ValidationError("comment must be 5000 characters or fewer")
    return value

#validate since query param 
def validateSince(value) -> str:
    if not value:
        raise ValidationError("since query parameter is required (format: YYYY-MM-DD)")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValidationError("since must be a valid date in YYYY-MM-DD format")
    # guard against invalid dates slipping through the regex
    try:
        from datetime import date
        year, month, day = value.split("-")
        date(int(year), int(month), int(day))
    except ValueError:
        raise ValidationError("since must be a valid calendar date")
    return value
