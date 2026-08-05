from typing import Any

from jadawel.core.formula.parser.exceptions import (
    BaserowFormulaException,
    BaserowFormulaSyntaxError,
    MaximumFormulaSizeError,
)
from jadawel.core.formula.parser.generated.BaserowFormula import BaserowFormula
from jadawel.core.formula.parser.generated.BaserowFormulaVisitor import (
    BaserowFormulaVisitor,
)
from jadawel.core.formula.types import (
    BASEROW_FORMULA_MODE_RAW,
    BaserowFormulaObject,
    FormulaContext,
    FunctionCollection,
)

__all__ = [
    BaserowFormulaException,
    MaximumFormulaSizeError,
    BaserowFormulaVisitor,
    BaserowFormula,
    BaserowFormulaSyntaxError,
]

from jadawel.core.formula.parser.formula_execution_visitor import (
    BaserowFormulaExecutionVisitor,
)
from jadawel.core.formula.parser.parser import get_parse_tree_for_formula


def resolve_formula(
    formula: BaserowFormulaObject,
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

    if formula["mode"] == BASEROW_FORMULA_MODE_RAW:
        return formula["formula"]

    tree = get_parse_tree_for_formula(formula["formula"])
    return BaserowFormulaExecutionVisitor(functions, formula_context).visit(tree)
