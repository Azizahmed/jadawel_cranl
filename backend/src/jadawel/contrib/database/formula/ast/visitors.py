import abc
from typing import Generic, TypeVar

from jadawel.contrib.database.formula.ast import tree

Y = TypeVar("Y")
X = TypeVar("X")


class JadawelFormulaASTVisitor(abc.ABC, Generic[Y, X]):
    @abc.abstractmethod
    def visit_string_literal(self, string_literal: "tree.JadawelStringLiteral[Y]") -> X:
        pass

    @abc.abstractmethod
    def visit_function_call(self, function_call: "tree.JadawelFunctionCall[Y]") -> X:
        pass

    @abc.abstractmethod
    def visit_int_literal(self, int_literal: "tree.JadawelIntegerLiteral[Y]") -> X:
        pass

    @abc.abstractmethod
    def visit_field_reference(
        self, field_reference: "tree.JadawelFieldReference[Y]"
    ) -> X:
        pass

    @abc.abstractmethod
    def visit_decimal_literal(
        self, decimal_literal: "tree.JadawelDecimalLiteral[Y]"
    ) -> X:
        pass

    @abc.abstractmethod
    def visit_boolean_literal(
        self, boolean_literal: "tree.JadawelBooleanLiteral[Y]"
    ) -> X:
        pass
