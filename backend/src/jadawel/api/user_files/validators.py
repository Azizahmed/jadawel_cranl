from rest_framework.exceptions import ValidationError

from jadawel.core.user_files.exceptions import InvalidUserFileNameError
from jadawel.core.user_files.models import UserFile


def user_file_name_validator(value):
    try:
        UserFile.deconstruct_name(value)
    except InvalidUserFileNameError:
        raise ValidationError("The user file name is invalid.", code="invalid")
