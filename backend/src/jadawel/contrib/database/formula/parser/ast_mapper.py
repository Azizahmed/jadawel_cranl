from decimal import Decimal

from jadawel.contrib.database.formula.ast.tree import (
    JadawelBooleanLiteral,
    JadawelDecimalLiteral,
    JadawelExpression,
    JadawelFieldReference,
    JadawelFunctionCall,
    JadawelIntegerLiteral,
    JadawelStringLiteral,
)
from jadawel.contrib.database.formula.registries import formula_function_registry
from jadawel.contrib.database.formula.types.formula_type import UnTyped
from jadawel.core.formula.parser.exceptions import (
    FieldByIdReferencesAreDeprecated,
    FormulaFunctionTypeDoesNotExist,
    InvalidNumberOfArguments,
    JadawelFormulaSyntaxError,
    MaximumFormulaSizeError,
    UnknownOperator,
)
from jadawel.core.formula.parser.generated.JadawelFormula import JadawelFormula
from jadawel.core.formula.parser.generated.JadawelFormulaVisitor import (
    JadawelFormulaVisitor,
)
from jadawel.core.formula.parser.parser import (
    convert_string_literal_token_to_string,
    get_parse_tree_for_formula,
)


def raw_formula_to_untyped_expression(
    formula: str,
) -> JadawelExpression[UnTyped]:
    """
    Takes a raw user input string, syntax checks it to see if it matches the syntax of
    a Jadawel Formula (raises a JadawelFormulaSyntaxError if not) and converts it into
    an untyped JadawelExpression.

    :param formula: A raw user supplied string possibly in the format of a Jadawel
        Formula.
    :return: An untyped JadawelExpression which represents the provided raw formula.
    :raises JadawelFormulaSyntaxError: If the supplied formula is not in the syntax
        of the Jadawel Formula language.
    """

    try:
        tree = get_parse_tree_for_formula(formula)
        return JadawelFormulaToJadawelASTMapper().visit(tree)
    except RecursionError:
        raise MaximumFormulaSizeError()


class JadawelFormulaToJadawelASTMapper(JadawelFormulaVisitor):
    """
    A Visitor which transforms an Antlr parse tree into a JadawelExpression AST.

    Raises an UnknownBinaryOperator if the formula contains an unknown binary operator.

    Raises an UnknownFunctionDefinition if the formula has a function call to a function
    not in the registry.
    """

    def visitRoot(self, ctx: JadawelFormula.RootContext):
        return ctx.expr().accept(self)

    def visitStringLiteral(self, ctx: JadawelFormula.StringLiteralContext):
        # noinspection PyTypeChecker
        literal = self.process_string(ctx)
        return JadawelStringLiteral(literal, None)

    def visitDecimalLiteral(self, ctx: JadawelFormula.DecimalLiteralContext):
        return JadawelDecimalLiteral(Decimal(ctx.getText()), None)

    def visitBooleanLiteral(self, ctx: JadawelFormula.BooleanLiteralContext):
        return JadawelBooleanLiteral(ctx.TRUE() is not None, None)

    def visitBrackets(self, ctx: JadawelFormula.BracketsContext):
        return ctx.expr().accept(self)

    def process_string(self, ctx):
        literal_without_outer_quotes = ctx.getText()[1:-1]
        if ctx.SINGLEQ_STRING_LITERAL() is not None:
            literal = literal_without_outer_quotes.replace("\\'", "'")
        else:
            literal = literal_without_outer_quotes.replace('\\"', '"')
        return literal

    def visitFunctionCall(self, ctx: JadawelFormula.FunctionCallContext):
        function_name = ctx.func_name().accept(self).lower()
        function_argument_expressions = ctx.expr()

        return self._do_func(function_argument_expressions, function_name)

    def _do_func(self, function_argument_expressions, function_name):
        function_def = self._get_function_def(function_name)
        self._check_function_call_valid(function_argument_expressions, function_def)
        args = [expr.accept(self) for expr in function_argument_expressions]
        return JadawelFunctionCall[UnTyped](function_def, args, None)

    def visitBinaryOp(self, ctx: JadawelFormula.BinaryOpContext):
        if ctx.PLUS():
            op = "add"
        elif ctx.MINUS():
            op = "minus"
        elif ctx.SLASH():
            op = "divide"
        elif ctx.EQUAL():
            op = "equal"
        elif ctx.BANG_EQUAL():
            op = "not_equal"
        elif ctx.STAR():
            op = "multiply"
        elif ctx.GT():
            op = "greater_than"
        elif ctx.LT():
            op = "less_than"
        elif ctx.GTE():
            op = "greater_than_or_equal"
        elif ctx.LTE():
            op = "less_than_or_equal"
        elif ctx.AMP_AMP():
            op = "and"
        elif ctx.PIPE_PIPE():
            op = "or"
        else:
            raise UnknownOperator(ctx.getText())

        return self._do_func(ctx.expr(), op)

    @staticmethod
    def _check_function_call_valid(function_argument_expressions, function_def):
        num_expressions = len(function_argument_expressions)
        if not function_def.num_args.test(num_expressions):
            raise InvalidNumberOfArguments(function_def, num_expressions)

    @staticmethod
    def _get_function_def(function_name):
        try:
            function_def = formula_function_registry.get(function_name)
        except FormulaFunctionTypeDoesNotExist:
            raise JadawelFormulaSyntaxError(f"{function_name} is not a valid function")
        return function_def

    def visitFunc_name(self, ctx: JadawelFormula.Func_nameContext):
        return ctx.getText()

    def visitIdentifier(self, ctx: JadawelFormula.IdentifierContext):
        return ctx.getText()

    def visitIntegerLiteral(self, ctx: JadawelFormula.IntegerLiteralContext):
        return JadawelIntegerLiteral[UnTyped](int(ctx.getText()), None)

    def visitFieldReference(self, ctx: JadawelFormula.FieldReferenceContext):
        reference = ctx.field_reference()
        field_name = convert_string_literal_token_to_string(
            reference.getText(), reference.SINGLEQ_STRING_LITERAL()
        )
        return JadawelFieldReference[UnTyped](field_name, None, None)

    def visitLookupFieldReference(
        self, ctx: JadawelFormula.LookupFieldReferenceContext
    ):
        reference = ctx.field_reference(0)
        field_name = convert_string_literal_token_to_string(
            reference.getText(), reference.SINGLEQ_STRING_LITERAL()
        )
        lookup = ctx.field_reference(1)
        lookup_name = convert_string_literal_token_to_string(
            lookup.getText(), reference.SINGLEQ_STRING_LITERAL()
        )
        return JadawelFieldReference[UnTyped](field_name, lookup_name, None)

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


class JadawelFieldReferenceVisitor(JadawelFormulaVisitor):
    """
    Visitor which visits a Jadawel Formula parse tree and returns a set of field
    references found in the formula. This is used for example when importing
    new tables with formula fields to import the fields in the correct order.
    """

    def visitRoot(self, ctx: JadawelFormula.RootContext):
        return ctx.expr().accept(self)

    def visitStringLiteral(self, ctx: JadawelFormula.StringLiteralContext):
        return set()

    def visitDecimalLiteral(self, ctx: JadawelFormula.DecimalLiteralContext):
        return set()

    def visitBooleanLiteral(self, ctx: JadawelFormula.BooleanLiteralContext):
        return set()

    def visitBrackets(self, ctx: JadawelFormula.BracketsContext):
        return ctx.expr().accept(self)

    def visitLookupFieldReference(
        self, ctx: JadawelFormula.LookupFieldReferenceContext
    ):
        reference = ctx.field_reference(1)
        field_name = convert_string_literal_token_to_string(
            reference.getText(), reference.SINGLEQ_STRING_LITERAL()
        )

        reference = ctx.field_reference(0)
        via_field_name = convert_string_literal_token_to_string(
            reference.getText(), reference.SINGLEQ_STRING_LITERAL()
        )

        if not field_name:
            return set()

        return {(field_name, via_field_name)}

    def visitFunctionCall(self, ctx: JadawelFormula.FunctionCallContext):
        args = set()
        for expr in ctx.expr():
            args.update(expr.accept(self))
        return args

    def visitFunc_name(self, ctx: JadawelFormula.Func_nameContext):
        return set()

    def visitIdentifier(self, ctx: JadawelFormula.IdentifierContext):
        return set()

    def visitIntegerLiteral(self, ctx: JadawelFormula.IntegerLiteralContext):
        return set()

    def visitFieldReference(self, ctx: JadawelFormula.FieldReferenceContext):
        reference = ctx.field_reference()
        field_name = convert_string_literal_token_to_string(
            reference.getText(), reference.SINGLEQ_STRING_LITERAL()
        )
        return {(field_name, None)}

    def visitFieldByIdReference(self, ctx: JadawelFormula.FieldByIdReferenceContext):
        return set()

    def visitLeftWhitespaceOrComments(
        self, ctx: JadawelFormula.LeftWhitespaceOrCommentsContext
    ):
        return ctx.expr().accept(self)

    def visitRightWhitespaceOrComments(
        self, ctx: JadawelFormula.RightWhitespaceOrCommentsContext
    ):
        return ctx.expr().accept(self)

    def visitBinaryOp(self, ctx: JadawelFormula.RightWhitespaceOrCommentsContext):
        args = set()
        for expr in ctx.expr():
            args.update(expr.accept(self))
        return args
