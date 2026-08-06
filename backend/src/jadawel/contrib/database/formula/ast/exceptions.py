from django.conf import settings

from jadawel.core.formula.parser.exceptions import JadawelFormulaException


class InvalidStringLiteralProvided(JadawelFormulaException):
    pass


class InvalidIntLiteralProvided(JadawelFormulaException):
    pass


class InvalidDecimalLiteralProvided(JadawelFormulaException):
    pass


class UnknownFieldReference(JadawelFormulaException):
    def __init__(self, unknown_field_name):
        super().__init__(
            f"there is no field called {unknown_field_name} but the "
            f"formula contained a reference to it"
        )


class TooLargeStringLiteralProvided(JadawelFormulaException):
    def __init__(self):
        super().__init__(
            f"an embedded string in the formula over the "
            f"maximum length of {settings.MAX_FORMULA_STRING_LENGTH} "
        )
