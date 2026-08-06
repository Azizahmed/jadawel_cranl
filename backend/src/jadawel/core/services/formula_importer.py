from abc import ABC, abstractmethod

from jadawel.core.formula import JadawelFormula, JadawelFormulaVisitor
from jadawel.core.formula.parser.exceptions import (
    FieldByIdReferencesAreDeprecated,
    JadawelFormulaSyntaxError,
)
from jadawel.core.utils import to_path


class JadawelFormulaImporter(JadawelFormulaVisitor, ABC):
    """
    This visitor do nothing with most of the context but update the path of the
    `get()` function.
    """

    @abstractmethod
    def get_data_provider_type_registry(self): ...

    def __init__(self, id_mapping, **kwargs):
        self.id_mapping = id_mapping
        self.extra_context = kwargs

    def visitRoot(self, ctx: JadawelFormula.RootContext):
        return ctx.expr().accept(self)

    def visitStringLiteral(self, ctx: JadawelFormula.StringLiteralContext):
        # noinspection PyTypeChecker
        return ctx.getText()

    def visitDecimalLiteral(self, ctx: JadawelFormula.DecimalLiteralContext):
        return ctx.getText()

    def visitBooleanLiteral(self, ctx: JadawelFormula.BooleanLiteralContext):
        return ctx.getText()

    def visitBrackets(self, ctx: JadawelFormula.BracketsContext):
        return ctx.expr().accept(self)

    def process_string(self, ctx):
        ctx.getText()

    def visitFunctionCall(self, ctx: JadawelFormula.FunctionCallContext):
        function_name = ctx.func_name().accept(self).lower()
        function_argument_expressions = ctx.expr()

        return self._do_func_import(function_argument_expressions, function_name)

    def _do_func_import(self, function_argument_expressions, function_name: str):
        args = [expr.accept(self) for expr in function_argument_expressions]

        # If it's a get function then let's update the path
        if function_name == "get" and isinstance(
            function_argument_expressions[0], JadawelFormula.StringLiteralContext
        ):
            unquoted_arg = args[0]

            data_provider_name, *path = to_path(unquoted_arg[1:-1])
            data_provider_type = self.get_data_provider_type_registry().get(
                data_provider_name
            )

            unquoted_arg_list = data_provider_type.import_path(
                path, self.id_mapping, **self.extra_context
            )

            args = [f"'{'.'.join([data_provider_name, *unquoted_arg_list])}'"]

        return f"{function_name}({','.join(args)})"

    def visitBinaryOp(self, ctx: JadawelFormula.BinaryOpContext):
        args = [expr.accept(self) for expr in ctx.expr()]
        return f" {ctx.op.text} ".join(args)

    def visitFunc_name(self, ctx: JadawelFormula.Func_nameContext):
        return ctx.getText()

    def visitIdentifier(self, ctx: JadawelFormula.IdentifierContext):
        return ctx.getText()

    def visitIntegerLiteral(self, ctx: JadawelFormula.IntegerLiteralContext):
        return ctx.getText()

    def visitFieldReference(self, ctx: JadawelFormula.FieldReferenceContext):
        """
        Handle field('name') syntax. There is no native support for this function
        in services, so we raise an error.
        """

        raise JadawelFormulaSyntaxError("'field' is not a a supported function")

    def visitFieldByIdReference(self, ctx: JadawelFormula.FieldByIdReferenceContext):
        raise FieldByIdReferencesAreDeprecated()

    def visitLeftWhitespaceOrComments(
        self, ctx: JadawelFormula.LeftWhitespaceOrCommentsContext
    ):
        return ctx.expr().accept(self)

    def visitRightWhitespaceOrComments(
        self, ctx: JadawelFormula.RightWhitespaceOrCommentsContext
    ):
        return ctx.expr().accept(self)
