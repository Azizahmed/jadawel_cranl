from typing import Any

from jadawel.core.formula.parser.exceptions import (
    JadawelFormulaException,
    JadawelFormulaSyntaxError,
    MaximumFormulaSizeError,
)
from jadawel.core.formula.parser.generated.JadawelFormula import JadawelFormula
from jadawel.core.formula.parser.generated.JadawelFormulaVisitor import (
    JadawelFormulaVisitor,
)
from jadawel.core.formula.types import (
    JADAWEL_FORMULA_MODE_RAW,
    FormulaContext,
    FunctionCollection,
    JadawelFormulaObject,
)

__all__ = [
    JadawelFormulaException,
    MaximumFormulaSizeError,
    JadawelFormulaVisitor,
    JadawelFormula,
    JadawelFormulaSyntaxError,
]

from jadawel.core.formula.parser.formula_execution_visitor import (
    JadawelFormulaExecutionVisitor,
)
from jadawel.core.formula.parser.parser import get_parse_tree_for_formula


def resolve_formula(
    formula: JadawelFormulaObject,
    functions: FunctionCollection,
    formula_context: FormulaContext,
) -> Any:
    """
    Helper to resolve a formula given the formula_context.

    :param formula: the formula itself.
    :param functions: The collection of functions that can be used in formulas.
    :param formula_context: A dict like object that contains the data that can
        be accessed in from the formulas.
    :return: the formula result.
    """

    # If we receive a blank formula string, don't attempt to parse it.
    if not formula["formula"]:
        return formula["formula"]

    if formula["mode"] == JADAWEL_FORMULA_MODE_RAW:
        return formula["formula"]

    tree = get_parse_tree_for_formula(formula["formula"])
    return JadawelFormulaExecutionVisitor(functions, formula_context).visit(tree)
