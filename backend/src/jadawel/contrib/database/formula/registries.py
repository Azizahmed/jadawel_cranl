from jadawel.core.formula.parser.exceptions import FormulaFunctionTypeDoesNotExist
from jadawel.core.registry import Registry


class JadawelFormulaFunctionRegistry(Registry):
    name = "formula_function"
    does_not_exist_exception_class = FormulaFunctionTypeDoesNotExist


formula_function_registry = JadawelFormulaFunctionRegistry()
