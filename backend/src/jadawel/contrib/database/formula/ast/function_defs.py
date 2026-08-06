from abc import ABC
from datetime import timedelta
from decimal import Decimal
from typing import List

from django.contrib.postgres.aggregates import JSONBAgg
from django.db.models import (
    Avg,
    Case,
    Count,
    DecimalField,
    Expression,
    ExpressionWrapper,
    F,
    Func,
    JSONField,
    Max,
    Min,
    OuterRef,
    StdDev,
    Subquery,
    Sum,
    Value,
    Variance,
    When,
    fields,
)
from django.db.models.functions import (
    Abs,
    Cast,
    Ceil,
    Coalesce,
    Concat,
    Exp,
    Extract,
    Floor,
    Greatest,
    JSONObject,
    Least,
    Left,
    Length,
    Ln,
    Log,
    Lower,
    Mod,
    Power,
    Replace,
    Reverse,
    Right,
    Sign,
    Sqrt,
    StrIndex,
    Trim,
    Upper,
)
from django.db.models.functions.datetime import TimezoneMixin

from jadawel.contrib.database.fields.models import NUMBER_MAX_DECIMAL_PLACES
from jadawel.contrib.database.formula.ast.function import (
    CollapseManyJadawelFunction,
    JadawelFunctionDefinition,
    NumOfArgsBetween,
    NumOfArgsGreaterThan,
    OneArgumentJadawelFunction,
    ThreeArgumentJadawelFunction,
    TwoArgumentJadawelFunction,
    ZeroArgumentJadawelFunction,
    aggregate_expr_with_metadata_filters,
    aggregate_wrapper,
    construct_aggregate_wrapper_queryset,
    construct_not_null_filters_for_inner_join,
)
from jadawel.contrib.database.formula.ast.tree import (
    JadawelDecimalLiteral,
    JadawelExpression,
    JadawelExpressionContext,
    JadawelFunctionCall,
    JadawelIntegerLiteral,
    JadawelStringLiteral,
)
from jadawel.contrib.database.formula.expression_generator.django_expressions import (
    AndExpr,
    EqualsExpr,
    GreaterThanExpr,
    GreaterThanOrEqualExpr,
    IsNullExpr,
    JadawelStringAgg,
    JSONBArrayGetElement,
    JSONBArrayJoinValues,
    JSONBArraySlice,
    JSONBArrayUniqueByValue,
    LessThanEqualOrExpr,
    LessThanExpr,
    NotEqualsExpr,
    NotExpr,
    OrExpr,
)
from jadawel.contrib.database.formula.expression_generator.exceptions import (
    JadawelToDjangoExpressionGenerationError,
)
from jadawel.contrib.database.formula.expression_generator.generator import (
    JoinIdsType,
    WrappedExpressionWithMetadata,
)
from jadawel.contrib.database.formula.types.formula_type import (
    JadawelFormulaType,
    JadawelFormulaValidType,
    UnTyped,
)
from jadawel.contrib.database.formula.types.formula_types import (
    JadawelFormulaArrayType,
    JadawelFormulaBooleanType,
    JadawelFormulaButtonType,
    JadawelFormulaCharType,
    JadawelFormulaDateType,
    JadawelFormulaDurationType,
    JadawelFormulaLinkType,
    JadawelFormulaMultipleCollaboratorsType,
    JadawelFormulaMultipleSelectType,
    JadawelFormulaNumberType,
    JadawelFormulaSingleFileType,
    JadawelFormulaSingleSelectType,
    JadawelFormulaTextType,
    JadawelFormulaURLType,
    JadawelJSONBObjectBaseType,
    calculate_number_type,
    literal,
)
from jadawel.contrib.database.formula.types.type_checker import (
    JadawelArgumentTypeChecker,
    MustBeManyExprChecker,
)


class JadawelTimezoneMixinOverride(TimezoneMixin):
    def get_tzname(self):
        return None


class JadawelExtract(JadawelTimezoneMixinOverride, Extract):
    pass


def register_formula_functions(registry):
    # Text functions
    registry.register(JadawelUpper())
    registry.register(JadawelLower())
    registry.register(JadawelConcat())
    registry.register(JadawelToText())
    registry.register(JadawelToVarchar())
    registry.register(JadawelT())
    registry.register(JadawelReplace())
    registry.register(JadawelSearch())
    registry.register(JadawelLength())
    registry.register(JadawelReverse())
    registry.register(JadawelContains())
    registry.register(JadawelLeft())
    registry.register(JadawelRight())
    registry.register(JadawelTrim())
    registry.register(JadawelRegexReplace())
    registry.register(JadawelEncodeUri())
    registry.register(JadawelEncodeUriComponent())
    # Number functions
    registry.register(JadawelMultiply())
    registry.register(JadawelDivide())
    registry.register(JadawelToNumber())
    registry.register(JadawelErrorToNan())
    registry.register(JadawelGreatest())
    registry.register(JadawelLeast())
    registry.register(JadawelMod())
    registry.register(JadawelRound())
    registry.register(JadawelInt())
    registry.register(JadawelEven())
    registry.register(JadawelOdd())
    registry.register(JadawelTrunc())
    registry.register(JadawelSplitPart())
    registry.register(JadawelLn())
    registry.register(JadawelExp())
    registry.register(JadawelLog())
    registry.register(JadawelSqrt())
    registry.register(JadawelPower())
    registry.register(JadawelAbs())
    registry.register(JadawelCeil())
    registry.register(JadawelFloor())
    registry.register(JadawelSign())
    registry.register(JadawelIsNaN())
    registry.register(JadawelWhenNan())
    # Boolean functions
    registry.register(JadawelIf())
    registry.register(JadawelEqual())
    registry.register(JadawelIsBlank())
    registry.register(JadawelIsNull())
    registry.register(JadawelNot())
    registry.register(JadawelNotEqual())
    registry.register(JadawelGreaterThan())
    registry.register(JadawelGreaterThanOrEqual())
    registry.register(JadawelLessThan())
    registry.register(JadawelLessThanOrEqual())
    registry.register(JadawelAnd())
    registry.register(JadawelOr())
    # Date functions
    registry.register(JadawelDatetimeFormat())
    registry.register(JadawelDatetimeFormatTz())
    registry.register(JadawelDay())
    registry.register(JadawelMonth())
    registry.register(JadawelYear())
    registry.register(JadawelSecond())
    registry.register(JadawelToDate())
    registry.register(JadawelDateDiff())
    registry.register(JadawelBcToNull())
    registry.register(JadawelNow())
    registry.register(JadawelToday())
    registry.register(JadawelToDateTz())
    # Date interval functions
    registry.register(JadawelDateInterval())
    registry.register(JadawelSecondsToDuration())
    registry.register(JadawelDurationToSeconds())
    # Special functions
    registry.register(JadawelAdd())
    registry.register(JadawelMinus())
    registry.register(JadawelErrorToNull())
    registry.register(JadawelRowId())
    registry.register(JadawelWhenEmpty())
    # Array functions
    registry.register(JadawelArrayAgg())
    registry.register(Jadawel2dArrayAgg())
    registry.register(JadawelMultipleSelectOptionsAgg())
    registry.register(JadawelAny())
    registry.register(JadawelEvery())
    registry.register(JadawelMax())
    registry.register(JadawelMin())
    registry.register(JadawelCount())
    registry.register(JadawelFilter())
    registry.register(JadawelAggJoin())
    registry.register(JadawelStdDevPop())
    registry.register(JadawelStdDevSample())
    registry.register(JadawelVarianceSample())
    registry.register(JadawelVariancePop())
    registry.register(JadawelAvg())
    registry.register(JadawelSum())
    # Single Select functions
    registry.register(JadawelGetSingleSelectValue())
    # Multiple Select functions
    registry.register(JadawelHasOption())
    registry.register(JadawelMultipleSelectCount())
    registry.register(JadawelStringAggMultipleSelectValues())
    # Link functions
    registry.register(JadawelLink())
    registry.register(JadawelButton())
    registry.register(JadawelGetLinkUrl())
    registry.register(JadawelGetLinkLabel())
    # JSON functions
    registry.register(JadawelJsonbExtractPathText())
    registry.register(JadawelIndex())
    # FIle functions
    registry.register(JadawelGetFileVisibleName())
    registry.register(JadawelGetFileMimeType())
    registry.register(JadawelGetFileSize())
    registry.register(JadawelGetImageWidth())
    registry.register(JadawelGetImageHeight())
    registry.register(JadawelIsImage())
    registry.register(JadawelArrayAggNoNesting())
    registry.register(JadawelGetFileCount())
    registry.register(JadawelToURL())
    # Array utility functions
    registry.register(JadawelArrayUnique())
    registry.register(JadawelArrayLength())
    registry.register(JadawelArrayJoinValues())
    registry.register(JadawelArraySlice())
    registry.register(JadawelFirst())
    registry.register(JadawelLast())
    # ManyToMany functions
    registry.register(JadawelStringAggManyToManyValues())
    registry.register(JadawelManyToManyCount())
    registry.register(JadawelManyToManyAgg())


class JadawelUpper(OneArgumentJadawelFunction):
    type = "upper"
    arg_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaTextType(nullable=arg.expression_type.nullable)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Upper(arg, output_field=fields.TextField())


class JadawelLower(OneArgumentJadawelFunction):
    type = "lower"
    arg_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaTextType(nullable=arg.expression_type.nullable)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Lower(arg, output_field=fields.TextField())


class JadawelDatetimeFormat(TwoArgumentJadawelFunction):
    type = "datetime_format"
    arg1_type = [JadawelFormulaDateType]
    arg2_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaTextType(nullable=arg1.expression_type.nullable)
        )

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        if isinstance(arg1, Value) and arg1.value is None:
            return Value("")
        return Coalesce(
            Trim(
                Func(
                    arg1,
                    arg2,
                    function="to_char",
                    output_field=fields.TextField(),
                )
            ),
            Value(""),
            output_field=fields.TextField(),
        )


class JadawelDatetimeFormatTz(ThreeArgumentJadawelFunction):
    type = "datetime_format_tz"
    arg1_type = [JadawelFormulaDateType]
    arg2_type = [JadawelFormulaTextType]
    arg3_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
        arg3: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(JadawelFormulaTextType(nullable=True))

    def to_django_expression(
        self, arg1: Expression, arg2: Expression, arg3: Expression
    ) -> Expression:
        return Trim(
            Coalesce(
                Func(
                    arg1,
                    arg2,
                    arg3,
                    function="try_datetime_format_tz",
                    output_field=fields.TextField(),
                ),
                Value(""),
                output_field=fields.TextField(),
            ),
        )


class JadawelEncodeUri(OneArgumentJadawelFunction):
    type = "encode_uri"
    arg_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaTextType(nullable=arg.expression_type.nullable)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(
            arg,
            function="try_encode_uri",
            output_field=fields.TextField(),
        )


class JadawelEncodeUriComponent(OneArgumentJadawelFunction):
    type = "encode_uri_component"
    arg_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaTextType(nullable=arg.expression_type.nullable)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(
            arg,
            function="try_encode_uri_component",
            output_field=fields.TextField(),
        )


class JadawelToText(OneArgumentJadawelFunction):
    type = "totext"
    arg_type = [JadawelFormulaValidType]
    try_coerce_nullable_args_to_not_null = False

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return arg.expression_type.cast_to_text(func_call, arg).with_valid_type(
            JadawelFormulaTextType()
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Coalesce(
            Cast(arg, output_field=fields.TextField()),
            Value(""),
            output_field=fields.TextField(),
        )


class JadawelToVarchar(OneArgumentJadawelFunction):
    """
    Internal function not registered in the frontend intentionally as we don't want
    users making char types. Used purely for working with our JadawelFormulaCharType
    on internal operations.
    """

    type = "tovarchar"
    arg_type = [JadawelFormulaTextType]
    try_coerce_nullable_args_to_not_null = False

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return arg.with_valid_type(
            JadawelFormulaCharType(nullable=arg.expression_type.nullable)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Cast(arg, output_field=fields.CharField())


class JadawelT(OneArgumentJadawelFunction):
    type = "t"
    arg_type = [JadawelFormulaValidType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        if isinstance(arg.expression_type, JadawelFormulaTextType):
            return arg
        else:
            return func_call.with_valid_type(
                JadawelFormulaTextType(nullable=arg.expression_type.nullable)
            )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Cast(Value(""), output_field=fields.TextField())


class JadawelConcat(JadawelFunctionDefinition):
    type = "concat"
    num_args = NumOfArgsGreaterThan(1)
    try_coerce_nullable_args_to_not_null = False

    @property
    def arg_types(self) -> JadawelArgumentTypeChecker:
        return lambda _, _2: [JadawelFormulaValidType]

    def type_function_given_valid_args(
        self,
        args: List[JadawelExpression[JadawelFormulaValidType]],
        expression: "JadawelFunctionCall[UnTyped]",
    ) -> JadawelExpression[JadawelFormulaType]:
        typed_args = [JadawelToText()(a) for a in args]
        return expression.with_args(typed_args).with_valid_type(
            JadawelFormulaTextType()
        )

    def to_django_expression_given_args(
        self, expr_args: List[WrappedExpressionWithMetadata], *args, **kwargs
    ) -> WrappedExpressionWithMetadata:
        return WrappedExpressionWithMetadata.from_args(
            Concat(*[e.expression for e in expr_args], output_field=fields.TextField()),
            expr_args,
        )


class JadawelAdd(TwoArgumentJadawelFunction):
    type = "add"
    operator = "+"
    arg1_type = [JadawelFormulaNumberType]
    arg2_type = [JadawelFormulaNumberType]

    @property
    def arg_types(self) -> JadawelArgumentTypeChecker:
        def type_checker(arg_index: int, arg_types: List[JadawelFormulaType]):
            if arg_index == 1:
                return arg_types[0].addable_types
            else:
                return [JadawelFormulaValidType]

        return type_checker

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return arg1.expression_type.add(func_call, arg1, arg2)

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        # date + interval = date
        # non date/interval types + non date/interval types = first arg type always

        first_arg_is_duration = isinstance(arg1.output_field, fields.DurationField)
        second_arg_is_duration = isinstance(arg2.output_field, fields.DurationField)
        first_arg_is_date = isinstance(arg1.output_field, fields.DateField)
        second_arg_is_date = isinstance(arg2.output_field, fields.DateField)
        if (first_arg_is_duration or second_arg_is_duration) and (
            first_arg_is_date or second_arg_is_date
        ):
            # interval + date = datetime
            # date + interval = datetime
            output_field = fields.DateTimeField()
        elif first_arg_is_duration:
            # interval + interval = interval
            # interval + datetime = datetime
            output_field = arg2.output_field
        else:
            output_field = arg1.output_field
        return ExpressionWrapper(arg1 + arg2, output_field=output_field)


class JadawelMultiply(TwoArgumentJadawelFunction):
    type = "multiply"
    operator = "*"
    arg1_type = [JadawelFormulaNumberType]
    arg2_type = [JadawelFormulaNumberType]

    @property
    def arg_types(self) -> JadawelArgumentTypeChecker:
        def type_checker(arg_index: int, arg_types: List[JadawelFormulaType]):
            if arg_index == 1:
                return arg_types[0].multipliable_types
            else:
                return [JadawelFormulaValidType]

        return type_checker

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaNumberType],
        arg2: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return arg1.expression_type.multiply(func_call, arg1, arg2)

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        if isinstance(arg1.output_field, fields.DurationField):
            total_secs = Extract(arg1, "epoch", output_field=arg2.output_field) * arg2
            return ExpressionWrapper(
                timedelta(seconds=1) * total_secs,
                output_field=arg1.output_field,
            )
        else:
            return ExpressionWrapper(arg1 * arg2, output_field=arg1.output_field)


class JadawelMinus(TwoArgumentJadawelFunction):
    type = "minus"
    operator = "-"
    arg1_type = [JadawelFormulaNumberType]
    arg2_type = [JadawelFormulaNumberType]

    @property
    def arg_types(self) -> JadawelArgumentTypeChecker:
        def type_checker(arg_index: int, arg_types: List[JadawelFormulaType]):
            if arg_index == 1:
                # Only type check the left hand side is one of the subtractable types
                # of the right hand side argument.
                return arg_types[0].subtractable_types
            else:
                return [JadawelFormulaValidType]

        return type_checker

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return arg1.expression_type.minus(func_call, arg1, arg2)

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        first_arg_is_duration = isinstance(arg1.output_field, fields.DurationField)
        second_arg_is_duration = isinstance(arg2.output_field, fields.DurationField)
        first_arg_is_date = isinstance(arg1.output_field, fields.DateField)
        second_arg_is_date = isinstance(arg2.output_field, fields.DateField)
        if first_arg_is_duration and second_arg_is_duration:
            # interval - interval = interval
            output_field = fields.DurationField()
        elif first_arg_is_date and second_arg_is_duration:
            # date/datetime - interval = datetime
            output_field = fields.DateTimeField()
        elif first_arg_is_date and second_arg_is_date:
            # date - date = interval (django does this magic)
            output_field = fields.DurationField()
        else:
            output_field = arg1.output_field

        return ExpressionWrapper(arg1 - arg2, output_field=output_field)


class JadawelGreatest(TwoArgumentJadawelFunction):
    type = "greatest"
    arg1_type = [JadawelFormulaNumberType]
    arg2_type = [JadawelFormulaNumberType]
    try_coerce_nullable_args_to_not_null = False

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaNumberType],
        arg2: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            calculate_number_type([arg1.expression_type, arg2.expression_type]),
            nullable=arg1.expression_type.nullable and arg2.expression_type.nullable,
        )

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return Greatest(arg1, arg2, output_field=arg1.output_field)


class JadawelLeast(TwoArgumentJadawelFunction):
    type = "least"
    arg1_type = [JadawelFormulaNumberType]
    arg2_type = [JadawelFormulaNumberType]
    try_coerce_nullable_args_to_not_null = False

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaNumberType],
        arg2: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            calculate_number_type([arg1.expression_type, arg2.expression_type]),
            nullable=arg1.expression_type.nullable and arg2.expression_type.nullable,
        )

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return Least(arg1, arg2, output_field=arg1.output_field)


class JadawelRound(TwoArgumentJadawelFunction):
    type = "round"
    arg1_type = [JadawelFormulaNumberType]
    arg2_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaNumberType],
        arg2: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        if isinstance(arg2, JadawelIntegerLiteral):
            guessed_number_decimal_places = arg2.literal
        elif isinstance(arg2, JadawelDecimalLiteral):
            guessed_number_decimal_places = int(arg2.literal)
        else:
            guessed_number_decimal_places = NUMBER_MAX_DECIMAL_PLACES

        return func_call.with_valid_type(
            JadawelFormulaNumberType(
                number_decimal_places=min(
                    max(guessed_number_decimal_places, 0), NUMBER_MAX_DECIMAL_PLACES
                )
            )
        )

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return handle_arg_being_nan(
            arg_to_check_if_nan=arg2,
            when_nan=Value(Decimal("NaN")),
            when_not_nan=(
                Func(
                    Cast(
                        arg1,
                        output_field=DecimalField(
                            max_digits=JadawelFormulaNumberType.MAX_DIGITS,
                            decimal_places=NUMBER_MAX_DECIMAL_PLACES,
                        ),
                    ),
                    # The round function requires an integer input.
                    trunc_numeric_to_int(arg2),
                    function="round",
                    output_field=arg1.output_field,
                )
            ),
        )


class JadawelMod(TwoArgumentJadawelFunction):
    type = "mod"
    arg1_type = [JadawelFormulaNumberType]
    arg2_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaNumberType],
        arg2: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            calculate_number_type([arg1.expression_type, arg2.expression_type])
        )

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return Case(
            When(
                condition=(
                    EqualsExpr(arg2, Value(0), output_field=fields.BooleanField())
                ),
                then=Value(Decimal("NaN")),
            ),
            default=Mod(arg1, arg2, output_field=arg1.output_field),
            output_field=arg1.output_field,
        )


class JadawelPower(TwoArgumentJadawelFunction):
    type = "power"
    arg1_type = [JadawelFormulaNumberType]
    arg2_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaNumberType],
        arg2: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            calculate_number_type([arg1.expression_type, arg2.expression_type])
        )

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return Power(arg1, arg2, output_field=arg1.output_field)


class JadawelLog(TwoArgumentJadawelFunction):
    type = "log"
    arg1_type = [JadawelFormulaNumberType]
    arg2_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaNumberType],
        arg2: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            calculate_number_type([arg1.expression_type, arg2.expression_type])
        )

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return Case(
            When(
                condition=(
                    LessThanEqualOrExpr(
                        arg1, Value(0), output_field=fields.BooleanField()
                    )
                ),
                then=Value(Decimal("NaN")),
            ),
            When(
                condition=(
                    LessThanEqualOrExpr(
                        arg2, Value(0), output_field=fields.BooleanField()
                    )
                ),
                then=Value(Decimal("NaN")),
            ),
            default=Log(arg1, arg2, output_field=arg1.output_field),
            output_field=arg1.output_field,
        )


class JadawelAbs(OneArgumentJadawelFunction):
    type = "abs"
    arg_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        return Abs(arg, output_field=arg.output_field)


class JadawelExp(OneArgumentJadawelFunction):
    type = "exp"
    arg_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        return Exp(arg, output_field=arg.output_field)


class JadawelEven(OneArgumentJadawelFunction):
    type = "even"
    arg_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(JadawelFormulaBooleanType())

    def to_django_expression(self, arg: Expression) -> Expression:
        return EqualsExpr(
            Mod(arg, Value(2), output_field=arg.output_field),
            Value(0),
            output_field=fields.BooleanField(),
        )


class JadawelOdd(OneArgumentJadawelFunction):
    type = "odd"
    arg_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(JadawelFormulaBooleanType())

    def to_django_expression(self, arg: Expression) -> Expression:
        return EqualsExpr(
            Mod(arg, Value(2), output_field=arg.output_field),
            Value(1),
            output_field=fields.BooleanField(),
        )


class JadawelLn(OneArgumentJadawelFunction):
    type = "ln"
    arg_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        # If we get given a negative number ln will crash, instead just return NaN.
        return Case(
            When(
                condition=(
                    LessThanEqualOrExpr(
                        arg, Value(0), output_field=fields.BooleanField()
                    )
                ),
                then=Value(Decimal("NaN")),
            ),
            default=Ln(arg, output_field=arg.output_field),
            output_field=arg.output_field,
        )


class JadawelSqrt(OneArgumentJadawelFunction):
    type = "sqrt"
    arg_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        # If we get given a negative number sqrt will crash, instead just return NaN.
        return Case(
            When(
                condition=(
                    LessThanExpr(arg, Value(0), output_field=fields.BooleanField())
                ),
                then=Value(Decimal("NaN")),
            ),
            default=Sqrt(arg, output_field=arg.output_field),
            output_field=arg.output_field,
        )


class JadawelSign(OneArgumentJadawelFunction):
    type = "sign"
    arg_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaNumberType(number_decimal_places=0)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Sign(arg, output_field=int_like_numeric_output_field())


class JadawelCeil(OneArgumentJadawelFunction):
    type = "ceil"
    arg_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaNumberType(number_decimal_places=0)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Ceil(arg, output_field=int_like_numeric_output_field())


class JadawelFloor(OneArgumentJadawelFunction):
    type = "floor"
    arg_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaNumberType(number_decimal_places=0)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Floor(arg, output_field=int_like_numeric_output_field())


class JadawelSplitPart(ThreeArgumentJadawelFunction):
    type = "split_part"
    arg1_type = [JadawelFormulaTextType]
    arg2_type = [JadawelFormulaTextType]
    arg3_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaTextType],
        arg2: JadawelExpression[JadawelFormulaTextType],
        arg3: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaTextType(
                nullable=arg1.expression_type.nullable
                or arg2.expression_type.nullable
                or arg3.expression_type.nullable
            )
        )

    def to_django_expression(
        self, arg1: Expression, arg2: Expression, arg3: Expression
    ) -> Expression:
        return Case(
            When(
                condition=(
                    LessThanEqualOrExpr(
                        arg3, Value(0), output_field=fields.BooleanField()
                    )
                ),
                then=Value(""),
            ),
            default=Func(
                arg1,
                arg2,
                trunc_numeric_to_int(arg3),
                function="SPLIT_PART",
                output_field=fields.CharField(),
            ),
            output_field=fields.CharField(),
        )


class JadawelTrunc(OneArgumentJadawelFunction):
    type = "trunc"
    arg_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaNumberType(
                number_decimal_places=0, nullable=arg.expression_type.nullable
            )
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(arg, function="trunc", output_field=int_like_numeric_output_field())


def int_like_numeric_output_field() -> fields.DecimalField:
    return fields.DecimalField(
        max_digits=JadawelFormulaNumberType.MAX_DIGITS, decimal_places=0
    )


class JadawelIsNaN(OneArgumentJadawelFunction):
    type = "is_nan"
    arg_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaBooleanType(nullable=arg.expression_type.nullable)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return EqualsExpr(
            arg, Value(Decimal("NaN")), output_field=fields.BooleanField()
        )


class JadawelWhenNan(TwoArgumentJadawelFunction):
    type = "when_nan"
    arg1_type = [JadawelFormulaNumberType]
    arg2_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaNumberType],
        arg2: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            calculate_number_type([arg1.expression_type, arg2.expression_type]),
        )

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return handle_arg_being_nan(arg1, arg2, arg1)


class JadawelInt(JadawelTrunc):
    """
    Kept for backwards compatability as was introduced in v3 of formula language but
    renamed to trunc in v4.
    """

    type = "int"


def trunc_numeric_to_int(expr: Expression) -> Expression:
    return Cast(
        Func(expr, function="trunc", output_field=expr.output_field),
        output_field=fields.IntegerField(),
    )


def handle_arg_being_nan(
    arg_to_check_if_nan: Expression,
    when_nan: Expression,
    when_not_nan: Expression,
) -> Expression:
    return Case(
        When(
            condition=(
                EqualsExpr(
                    arg_to_check_if_nan,
                    Value(Decimal("Nan")),
                    output_field=fields.BooleanField(),
                )
            ),
            then=when_nan,
        ),
        default=when_not_nan,
        output_field=when_not_nan.output_field,
    )


class JadawelDivide(TwoArgumentJadawelFunction):
    type = "divide"
    operator = "/"

    arg1_type = [JadawelFormulaNumberType]
    arg2_type = [JadawelFormulaNumberType]

    @property
    def arg_types(self) -> JadawelArgumentTypeChecker:
        def type_checker(arg_index: int, arg_types: List[JadawelFormulaType]):
            if arg_index == 1:
                return arg_types[0].dividable_types
            else:
                return [JadawelFormulaValidType]

        return type_checker

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaNumberType],
        arg2: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        # Show all the decimal places we can by default if the user makes a formula
        # with a division to prevent weird results like `1/3=0`
        return arg1.expression_type.divide(func_call, arg1, arg2)

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        if isinstance(arg1.output_field, fields.DurationField):
            expression = timedelta(seconds=1) * (
                Extract(arg1, "epoch", output_field=arg2.output_field) / arg2
            )
            output_field = arg1.output_field
            safe_value = Value(None)
        else:
            # Prevent divide by zero's by swapping 0 for NaN causing the entire
            # expression to evaluate to NaN. The front-end then treats NaN values as a
            # per cell error to display to the user.
            output_field = fields.DecimalField(
                max_digits=JadawelFormulaNumberType.MAX_DIGITS,
                decimal_places=NUMBER_MAX_DECIMAL_PLACES,
            )
            expression = arg1 / Cast(arg2, output_field=output_field)
            safe_value = Value(Decimal("NaN"))
        safe_expression = Case(
            When(
                condition=(
                    EqualsExpr(arg2, Value(0), output_field=fields.BooleanField())
                ),
                then=safe_value,
            ),
            default=expression,
            output_field=output_field,
        )

        return ExpressionWrapper(safe_expression, output_field=output_field)


class JadawelHasOption(TwoArgumentJadawelFunction):
    type = "has_option"
    arg1_type = [
        JadawelFormulaMultipleSelectType,
        JadawelFormulaArrayType,
        MustBeManyExprChecker(JadawelFormulaSingleSelectType),
    ]
    arg2_type = [JadawelFormulaTextType]
    aggregate = True

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaTextType],
    ) -> JadawelExpression[JadawelFormulaType]:
        arg1_type = arg1.expression_type
        # Convert a lookup to a single select field to be a JSONArray of single
        # selects to make the `to_django_expression` work.
        if isinstance(arg1_type, JadawelFormulaSingleSelectType) and arg1.many:
            return JadawelHasOption().call_and_type_with_args(
                [JadawelArrayAggNoNesting().call_and_type_with_args([arg1]), arg2]
            )
        return func_call.with_valid_type(JadawelFormulaBooleanType())

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return EqualsExpr(
            Func(
                Func(arg1, function="jsonb_array_elements"),
                Value("value"),
                function="jsonb_extract_path_text",
                output_field=fields.CharField(),
            ),
            arg2,
            output_field=fields.BooleanField(),
        )

    def to_django_expression_given_args(
        self,
        args: List["WrappedExpressionWithMetadata"],
        context: JadawelExpressionContext,
    ) -> "WrappedExpressionWithMetadata":
        expr_with_metadata = WrappedExpressionWithMetadata.from_args(
            self.to_django_expression(args[0].expression, args[1].expression), args
        )
        subquery = construct_aggregate_wrapper_queryset(
            expr_with_metadata, context.model
        )

        # This subquery would return more than one row, but we only care if
        # there is at least one result that is true, so order by the result
        # and take the first row.
        expr: Expression = Subquery(subquery.order_by("-result")[:1])

        return WrappedExpressionWithMetadata(
            ExpressionWrapper(
                Coalesce(expr, Value(False, output_field=fields.BooleanField())),
                output_field=fields.BooleanField(),
            )
        )


class JadawelEqual(TwoArgumentJadawelFunction):
    type = "equal"
    operator = "="
    try_coerce_nullable_args_to_not_null = False

    # Overridden by the arg_types property below
    arg1_type = [JadawelFormulaValidType]
    arg2_type = [JadawelFormulaValidType]

    @property
    def arg_types(self) -> JadawelArgumentTypeChecker:
        def type_checker(arg_index: int, arg_types: List[JadawelFormulaType]):
            if arg_index == 1:
                return arg_types[0].comparable_types
            else:
                return [JadawelFormulaValidType]

        return type_checker

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        arg1_type = arg1.expression_type
        arg2_type = arg2.expression_type
        if type(arg1_type) is not type(arg2_type):
            # If trying to compare two types which can be compared, but are of different
            # types, then first cast them to text and then compare.
            # We to ourselves via the __class__ property here so subtypes of this type
            # use themselves here instead of us!

            return self.__class__()(
                JadawelToText()(arg1),
                JadawelToText()(arg2),
            )
        else:
            return func_call.with_valid_type(JadawelFormulaBooleanType())

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return Case(
            When(
                condition=IsNullExpr(arg1, output_field=fields.BooleanField()),
                then=IsNullExpr(arg2, output_field=fields.BooleanField()),
            ),
            default=EqualsExpr(arg1, arg2, output_field=fields.BooleanField()),
            output_field=fields.BooleanField(),
        )


class JadawelIf(ThreeArgumentJadawelFunction):
    type = "if"
    try_coerce_nullable_args_to_not_null = False

    arg1_type = [JadawelFormulaBooleanType]
    # Overridden by the type function property below
    arg2_type = [JadawelFormulaValidType]
    arg3_type = [JadawelFormulaValidType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
        arg3: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        arg2_type = arg2.expression_type
        arg3_type = arg3.expression_type
        if type(arg2_type) is not type(arg3_type):
            # Replace the current if func_call with one which casts both args to text
            # if they are of different types as PostgreSQL requires all cases of a case
            # statement to be of the same type.
            return JadawelIf()(
                arg1,
                JadawelToText()(arg2),
                JadawelToText()(arg3),
            )
        else:
            if isinstance(arg2_type, JadawelFormulaNumberType) and isinstance(
                arg3_type, JadawelFormulaNumberType
            ):
                resulting_type = calculate_number_type([arg2_type, arg3_type])
            else:
                resulting_type = arg2_type

            return func_call.with_valid_type(
                resulting_type,
                nullable=arg2_type.nullable or arg3_type.nullable,
            )

    def to_django_expression(
        self, arg1: Expression, arg2: Expression, arg3: Expression
    ) -> Expression:
        return Case(
            When(condition=arg1, then=arg2),
            default=arg3,
            output_field=arg2.output_field,
        )


class JadawelDurationToSeconds(OneArgumentJadawelFunction):
    type = "toseconds"
    arg_type = [JadawelFormulaDurationType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaNumberType(number_decimal_places=0)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Extract(arg, "epoch", output_field=int_like_numeric_output_field())


class JadawelSecondsToDuration(OneArgumentJadawelFunction):
    type = "toduration"
    arg_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(JadawelFormulaDurationType(nullable=True))

    def to_django_expression(self, arg: Expression) -> Expression:
        return ExpressionWrapper(
            Case(
                When(
                    condition=(
                        EqualsExpr(
                            arg,
                            Value(Decimal("NaN")),
                            output_field=fields.BooleanField(),
                        )
                    ),
                    then=Value(None),
                ),
                default=timedelta(seconds=1) * arg,
                output_field=fields.DurationField(),
            ),
            output_field=fields.DurationField(),
        )


class JadawelToNumber(OneArgumentJadawelFunction):
    type = "tonumber"
    arg_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaNumberType(number_decimal_places=NUMBER_MAX_DECIMAL_PLACES)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(
            arg,
            function="try_cast_to_numeric",
            output_field=int_like_numeric_output_field(),
        )


class JadawelErrorToNan(OneArgumentJadawelFunction):
    type = "error_to_nan"
    arg_type = [JadawelFormulaNumberType]
    is_wrapper = True

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(
            arg, function="replace_errors_with_nan", output_field=arg.output_field
        )


class JadawelErrorToNull(OneArgumentJadawelFunction):
    type = "error_to_null"
    arg_type = [JadawelFormulaValidType]
    is_wrapper = True

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        # FIXME: This function should set `nullable=True` on the resulting type,
        # but since this is used as the most external wrapper function, don't
        # want to loose the real nullable state of the expression. This should
        # be fixed in the future (e.g. saving only the inner expression and wrapping
        # at runtime somehow).

        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(
            arg, function="replace_errors_with_null", output_field=arg.output_field
        )


class JadawelIsBlank(OneArgumentJadawelFunction):
    type = "isblank"
    arg_type = [JadawelFormulaValidType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return arg.expression_type.is_blank(func_call, arg)

    def to_django_expression(self, arg: Expression) -> Expression:
        return EqualsExpr(
            Coalesce(
                arg,
                Value(""),
            ),
            Value(""),
            output_field=fields.BooleanField(),
        )


class JadawelIsNull(OneArgumentJadawelFunction):
    type = "is_null"
    arg_type = [JadawelFormulaValidType]
    try_coerce_nullable_args_to_not_null = False

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(JadawelFormulaBooleanType())

    def to_django_expression(self, arg: Expression) -> Expression:
        return IsNullExpr(arg, output_field=fields.BooleanField())


class JadawelNot(OneArgumentJadawelFunction):
    type = "not"
    arg_type = [JadawelFormulaBooleanType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaBooleanType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(JadawelFormulaBooleanType())

    def to_django_expression(self, arg: Expression) -> Expression:
        return NotExpr(arg, output_field=fields.BooleanField())


class JadawelNotEqual(JadawelEqual):
    type = "not_equal"
    operator = "!="

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return NotEqualsExpr(
            arg1,
            arg2,
            output_field=fields.BooleanField(),
        )


class BaseLimitComparableFunction(TwoArgumentJadawelFunction, ABC):
    # Overridden by the arg_types property below
    arg1_type = [JadawelFormulaValidType]
    arg2_type = [JadawelFormulaValidType]

    @property
    def arg_types(self) -> JadawelArgumentTypeChecker:
        def type_checker(arg_index: int, arg_types: List[JadawelFormulaType]):
            if arg_index == 1:
                return arg_types[0].limit_comparable_types
            else:
                return [JadawelFormulaValidType]

        return type_checker

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(JadawelFormulaBooleanType())


class JadawelGreaterThan(BaseLimitComparableFunction):
    type = "greater_than"
    operator = ">"

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return GreaterThanExpr(
            arg1,
            arg2,
            output_field=fields.BooleanField(),
        )


class JadawelGreaterThanOrEqual(BaseLimitComparableFunction):
    type = "greater_than_or_equal"
    operator = ">="

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return GreaterThanOrEqualExpr(
            arg1,
            arg2,
            output_field=fields.BooleanField(),
        )


class JadawelLessThan(BaseLimitComparableFunction):
    type = "less_than"
    operator = "<"

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return LessThanExpr(
            arg1,
            arg2,
            output_field=fields.BooleanField(),
        )


class JadawelLessThanOrEqual(BaseLimitComparableFunction):
    type = "less_than_or_equal"
    operator = "<="

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return LessThanEqualOrExpr(
            arg1,
            arg2,
            output_field=fields.BooleanField(),
        )


class JadawelNow(ZeroArgumentJadawelFunction):
    type = "now"
    needs_periodic_update = True

    def type_function(
        self, func_call: JadawelFunctionCall[UnTyped]
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaDateType(
                date_format="ISO", date_include_time=True, date_time_format="24"
            )
        )

    def to_django_expression(self) -> Expression:
        pass

    def to_django_expression_given_args(
        self,
        args: List["WrappedExpressionWithMetadata"],
        context: JadawelExpressionContext,
    ) -> "WrappedExpressionWithMetadata":
        return WrappedExpressionWithMetadata(
            Value(context.get_utc_now(), output_field=fields.DateTimeField()),
        )


class JadawelToday(ZeroArgumentJadawelFunction):
    type = "today"
    needs_periodic_update = True

    def type_function(
        self, func_call: JadawelFunctionCall[UnTyped]
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaDateType(
                date_format="ISO",
                date_include_time=False,
                date_time_format="24",
                date_force_timezone="UTC",
            )
        )

    def to_django_expression(self) -> Expression:
        pass

    def to_django_expression_given_args(
        self,
        args: List["WrappedExpressionWithMetadata"],
        context: JadawelExpressionContext,
    ) -> "WrappedExpressionWithMetadata":
        return WrappedExpressionWithMetadata(
            Value(context.get_utc_now(), output_field=fields.DateField()),
        )


class JadawelToDate(TwoArgumentJadawelFunction):
    type = "todate"
    arg1_type = [JadawelFormulaTextType]
    arg2_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaDateType(
                date_format="ISO",
                date_include_time=False,
                date_time_format="24",
                nullable=True,
            )
        )

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return Func(
            arg1,
            arg2,
            function="try_cast_to_date",
            output_field=fields.DateTimeField(),
        )


class JadawelToDateTz(ThreeArgumentJadawelFunction):
    type = "todate_tz"
    arg1_type = [JadawelFormulaTextType]
    arg2_type = [JadawelFormulaTextType]
    arg3_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
        arg3: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaDateType(
                date_format="ISO",
                date_include_time=True,
                date_time_format="24",
                date_show_tzinfo=True,
                date_force_timezone=getattr(arg3, "literal", None),
                nullable=True,
            )
        )

    def to_django_expression(
        self, arg1: Expression, arg2: Expression, arg3: Expression
    ) -> Expression:
        return Func(
            arg1,
            arg2,
            arg3,
            function="try_cast_to_date_tz",
            output_field=fields.DateTimeField(),
        )


class JadawelDay(OneArgumentJadawelFunction):
    type = "day"
    arg_type = [JadawelFormulaDateType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaNumberType(
                number_decimal_places=0, nullable=arg.expression_type.nullable
            )
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return JadawelExtract(arg, "day", output_field=int_like_numeric_output_field())


class JadawelMonth(OneArgumentJadawelFunction):
    type = "month"
    arg_type = [JadawelFormulaDateType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaNumberType(
                number_decimal_places=0, nullable=arg.expression_type.nullable
            )
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return JadawelExtract(
            arg, "month", output_field=int_like_numeric_output_field()
        )


class JadawelDateDiff(ThreeArgumentJadawelFunction):
    type = "date_diff"

    arg1_type = [JadawelFormulaTextType]
    arg2_type = [JadawelFormulaDateType]
    arg3_type = [JadawelFormulaDateType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
        arg3: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        nullable = arg2.expression_type.nullable or arg3.expression_type.nullable
        return func_call.with_valid_type(
            JadawelFormulaNumberType(number_decimal_places=0, nullable=nullable)
        )

    def to_django_expression(
        self, arg1: Expression, arg2: Expression, arg3: Expression
    ) -> Expression:
        return Func(
            arg1,
            arg2,
            arg3,
            function="date_diff",
            output_field=int_like_numeric_output_field(),
        )


class JadawelAnd(TwoArgumentJadawelFunction):
    type = "and"
    operator = "&&"
    arg1_type = [JadawelFormulaBooleanType]
    arg2_type = [JadawelFormulaBooleanType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(JadawelFormulaBooleanType())

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return AndExpr(arg1, arg2, output_field=fields.BooleanField())


class JadawelOr(TwoArgumentJadawelFunction):
    type = "or"
    arg1_type = [JadawelFormulaBooleanType]
    arg2_type = [JadawelFormulaBooleanType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(JadawelFormulaBooleanType())

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return OrExpr(arg1, arg2, output_field=fields.BooleanField())


class JadawelDateInterval(OneArgumentJadawelFunction):
    type = "date_interval"
    arg_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(JadawelFormulaDurationType(nullable=True))

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(
            arg, function="try_cast_to_interval", output_field=fields.DurationField()
        )


class JadawelReplace(ThreeArgumentJadawelFunction):
    type = "replace"
    arg1_type = [JadawelFormulaTextType]
    arg2_type = [JadawelFormulaTextType]
    arg3_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
        arg3: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(JadawelFormulaTextType(nullable=False))

    def to_django_expression(
        self, arg1: Expression, arg2: Expression, arg3: Expression
    ) -> Expression:
        return Replace(arg1, arg2, arg3, output_field=fields.TextField())


class JadawelSearch(TwoArgumentJadawelFunction):
    type = "search"
    arg1_type = [JadawelFormulaTextType]
    arg2_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaNumberType(number_decimal_places=0)
        )

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return StrIndex(arg1, arg2, output_field=int_like_numeric_output_field())


class JadawelContains(TwoArgumentJadawelFunction):
    type = "contains"
    arg1_type = [JadawelFormulaTextType]
    arg2_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(JadawelFormulaBooleanType())

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return NotEqualsExpr(
            StrIndex(arg1, arg2), Value(0), output_field=fields.BooleanField()
        )


class JadawelRowId(ZeroArgumentJadawelFunction):
    type = "row_id"
    requires_refresh_after_insert = True

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaNumberType(number_decimal_places=0)
        )

    def to_django_expression(self) -> Expression:
        pass

    def to_django_expression_given_args(
        self,
        args: List["WrappedExpressionWithMetadata"],
        context: JadawelExpressionContext,
    ) -> "WrappedExpressionWithMetadata":
        if context.model_instance is None:
            return WrappedExpressionWithMetadata(
                ExpressionWrapper(F("id"), output_field=int_like_numeric_output_field())
            )
        else:
            # noinspection PyUnresolvedReferences
            return WrappedExpressionWithMetadata(
                Cast(
                    Value(context.model_instance.id),
                    output_field=fields.IntegerField(),
                )
            )


class JadawelLength(OneArgumentJadawelFunction):
    type = "length"
    arg_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaNumberType(number_decimal_places=0)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Length(arg, output_field=int_like_numeric_output_field())


class JadawelReverse(OneArgumentJadawelFunction):
    type = "reverse"
    arg_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        return Reverse(arg, output_field=fields.TextField())


class JadawelWhenEmpty(TwoArgumentJadawelFunction):
    type = "when_empty"
    arg1_type = [JadawelFormulaValidType]
    arg2_type = [JadawelFormulaValidType]
    try_coerce_nullable_args_to_not_null = False

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        if not isinstance(arg1.expression_type, type(arg2.expression_type)):
            return func_call.with_invalid_type(
                "both inputs for when_empty must be the same type"
            )
        return func_call.with_valid_type(
            arg1.expression_type, nullable=arg2.expression_type.nullable
        )

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return Coalesce(arg1, arg2, output_field=arg2.output_field)


def _calculate_aggregate_orders(join_ids: JoinIdsType):
    orders = []
    for join in reversed(join_ids):
        orders.append(join[0] + "__order")
        orders.append(join[0] + "__id")
    return orders


def array_agg_expression(
    args: List["WrappedExpressionWithMetadata"],
    context: JadawelExpressionContext,
    nest_in_value: bool,
):
    pre_annotations = dict()
    aggregate_filters = []
    join_ids = []
    for child in args:
        pre_annotations.update(child.pre_annotations)
        aggregate_filters.extend(child.aggregate_filters)
        join_ids.extend(child.join_ids)

    join_ids = list(dict.fromkeys(join_ids))
    orders = _calculate_aggregate_orders(join_ids)
    if nest_in_value:
        json_builder_args = {"value": args[0].expression}
        # Remove any duplicates from join_ids
        if len(join_ids) > 1:
            json_builder_args["ids"] = JSONObject(
                **{tbl: F(i + "__id") for i, tbl in join_ids}
            )
        else:
            json_builder_args["id"] = F(join_ids[0][0] + "__id")
        expr = JSONBAgg(JSONObject(**json_builder_args), order_by=orders)
    else:
        expr = JSONBAgg(args[0].expression, order_by=orders)
    wrapped_expr = aggregate_wrapper(
        WrappedExpressionWithMetadata(
            expr, pre_annotations, aggregate_filters, join_ids
        ),
        context.model,
    ).expression
    return WrappedExpressionWithMetadata(
        Coalesce(
            wrapped_expr,
            Value([], output_field=JSONField()),
            output_field=JSONField(),
        )
    )


def string_agg_array_of_multiple_select_field(
    expr_with_metadata: WrappedExpressionWithMetadata, model, delimiter=", "
) -> WrappedExpressionWithMetadata:
    """
    This function aggregates an array of multiple select field values into a
    single string. The array is a result of a lookup operation. For every linked
    row, each select option value will be separated by the delimiter provided as
    argument.

    For example, consider a formula like `totext(lookup('link_row_field',
    'multiple_select_field'))`. This formula would call this function to
    aggregate the values. The result would be an array like:

    [{"id": $linked_row_1, "value": "option1, option2"}, ...]

    In this array of JSON objects, $linked_row_1 is the id of the linked row,
    while "option1" and "option2" are the values of the selected options in the
    multiple select field looked up.

    :param expr_with_metadata: The expression to aggregate.
    :param model: The model to aggregate on.
    :param delimiter: The delimiter to use to separate the values.
    :return: The wrapped expression with metadata needed to aggregate the get
        the expected result.
    """

    # We need to enforce that each filtered relation is not null so django generates us
    # inner joins.
    not_null_filters_for_inner_join = construct_not_null_filters_for_inner_join(
        expr_with_metadata.pre_annotations
    )
    aggregated_filters = aggregate_expr_with_metadata_filters(expr_with_metadata)

    # There is only one tuple of (field, database_table) in this case in the join_ids,
    # the one needed to join the linked table.
    join_field, _ = expr_with_metadata.join_ids[0]

    extract_value_subquery = Subquery(
        model.objects_and_trash.annotate(**expr_with_metadata.pre_annotations)
        .filter(
            id=OuterRef("id"),
            **{join_field: OuterRef(join_field)},
            **not_null_filters_for_inner_join,
        )
        .values(
            result=Func(
                Func(expr_with_metadata.expression, function="jsonb_array_elements"),
                Value("value"),
                function="jsonb_extract_path_text",
                output_field=fields.CharField(),
            )
        )
        .filter(aggregated_filters)
    )

    join_field_id = f"{join_field}__id"
    json_builder_args = {"value": F("value"), "id": F(join_field_id)}
    orders = _calculate_aggregate_orders(expr_with_metadata.join_ids)

    string_agg_values_subquery = Subquery(
        model.objects_and_trash.annotate(**expr_with_metadata.pre_annotations)
        .filter(id=OuterRef("id"), **not_null_filters_for_inner_join)
        .annotate(
            value=Func(
                Func(extract_value_subquery, function="array"),
                Value(delimiter),
                function="array_to_string",
            )
        )
        .annotate(res=JSONObject(**json_builder_args))
        .values(result=JSONBAgg(F("res"), order_by=orders))[:1],
        output_field=JSONField(),
    )

    return WrappedExpressionWithMetadata(
        ExpressionWrapper(string_agg_values_subquery, output_field=JSONField())
    )


def aggregate_many_to_many_values(
    expr_with_metadata: WrappedExpressionWithMetadata, model
) -> WrappedExpressionWithMetadata:
    """
    This function aggregates values coming from a many-to-many field
    (i.e. multiple select field or multiple collaborators field) into a
    JSON array. The array is a result of a lookup operation. Each item
    will be represented by a JSON object with an id, and the properties
    of the many-to-many field. For a multiple select field, the JSON
    object will contain a value and a color. For a multiple collaborators
    field, the JSON object will contain a user id and the first_name of the
    user.

    For example, consider a formula like `lookup('link_row_field',
    'multiple_select_field')`. This formula would call this function to
    aggregate the select options. The result would be an array like:

    [{
        "id": $linked_row_1,
        "value": [
            {"id": 1, "color": "red", "value": "option1"},
            {"id": 2, "color": "green", "value": "option2"},
        ]
    }, ...]

    In this array of JSON objects, $linked_row_1 is the id of the linked row,
    while the JSON objects inside the "value" array are the JSON serialized
    version of the options selected in the multiple select field looked up.

    :param expr_with_metadata: The expression to aggregate.
    :param model: The model to aggregate on.
    :param delimiter: The delimiter to use to separate the values.
    :return: The wrapped expression with metadata needed to aggregate the get
        the expected result.
    """

    # We need to enforce that each filtered relation is not null so django generates us
    # inner joins.

    not_null_filters_for_inner_join = construct_not_null_filters_for_inner_join(
        expr_with_metadata.pre_annotations
    )

    aggregated_filters = aggregate_expr_with_metadata_filters(expr_with_metadata)

    # There is only one tuple of (field, database_table) in this case in the join_ids,
    # the one needed to join the linked table.
    join_field, _ = expr_with_metadata.join_ids[0]

    inner_subquery = Subquery(
        model.objects_and_trash.annotate(**expr_with_metadata.pre_annotations)
        .filter(
            id=OuterRef("id"),
            **{join_field: OuterRef(join_field)},
            **not_null_filters_for_inner_join,
        )
        .values(result=expr_with_metadata.expression)
        .filter(aggregated_filters)
    )

    join_field_id = f"{join_field}__id"
    json_builder_args = {"value": inner_subquery, "id": F(join_field_id)}
    orders = _calculate_aggregate_orders(expr_with_metadata.join_ids)

    subquery = Subquery(
        model.objects_and_trash.annotate(**expr_with_metadata.pre_annotations)
        .filter(id=OuterRef("id"), **not_null_filters_for_inner_join)
        .annotate(res=JSONObject(**json_builder_args))
        .values(result=JSONBAgg(F("res"), order_by=orders))[:1],
        output_field=JSONField(),
    )

    return WrappedExpressionWithMetadata(
        ExpressionWrapper(
            Coalesce(subquery, Value([], output_field=JSONField())),
            output_field=JSONField(),
        )
    )


class JadawelArrayAgg(OneArgumentJadawelFunction, CollapseManyJadawelFunction):
    type = "array_agg"
    arg_type = [MustBeManyExprChecker(JadawelFormulaValidType)]
    aggregate = True

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(JadawelFormulaArrayType(arg.expression_type))

    def to_django_expression(self, arg: Expression) -> Expression:
        pass

    def to_django_expression_given_args(
        self,
        args: List["WrappedExpressionWithMetadata"],
        context: JadawelExpressionContext,
    ) -> "WrappedExpressionWithMetadata":
        return array_agg_expression(args, context, nest_in_value=True)


class JadawelArrayAggNoNesting(JadawelArrayAgg, CollapseManyJadawelFunction):
    type = "array_agg_no_nesting"

    def to_django_expression(self, arg: Expression) -> Expression:
        pass

    def to_django_expression_given_args(
        self,
        args: List["WrappedExpressionWithMetadata"],
        context: JadawelExpressionContext,
    ) -> "WrappedExpressionWithMetadata":
        return array_agg_expression(args, context, nest_in_value=False)


class JadawelManyToManyAgg(OneArgumentJadawelFunction, CollapseManyJadawelFunction):
    type = "many_to_many_agg"
    arg_type = [
        MustBeManyExprChecker(
            JadawelFormulaMultipleSelectType, JadawelFormulaMultipleCollaboratorsType
        )
    ]
    aggregate = True

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(JadawelFormulaArrayType(arg.expression_type))

    def to_django_expression(self, arg: Expression) -> Expression:
        return arg

    def to_django_expression_given_args(
        self,
        args: List["WrappedExpressionWithMetadata"],
        context: JadawelExpressionContext,
    ) -> "WrappedExpressionWithMetadata":
        expr = aggregate_many_to_many_values(args[0], context.model)
        return super().to_django_expression_given_args([expr], context)


# Deprecated, use JadawelManyToManyAgg instead. This is kept for backwards compatibility
# and will be removed in the future with a proper formula migration.
class JadawelMultipleSelectOptionsAgg(JadawelManyToManyAgg):
    type = "multiple_select_options_agg"


class Jadawel2dArrayAgg(OneArgumentJadawelFunction, CollapseManyJadawelFunction):
    type = "array_agg_unnesting"
    arg_type = [MustBeManyExprChecker(JadawelFormulaArrayType)]
    aggregate = True

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(
            Func(JSONBAgg(arg), function="jsonb_array_elements"),
            function="jsonb_array_elements",
            output_field=JSONField(),
        )

    def to_django_expression_given_args(
        self,
        args: List["WrappedExpressionWithMetadata"],
        context: JadawelExpressionContext,
    ) -> "WrappedExpressionWithMetadata":
        subquery = super().to_django_expression_given_args(args, context)
        return WrappedExpressionWithMetadata(
            Func(Func(subquery.expression, function="array"), function="to_jsonb")
        )


class JadawelManyToManyCount(OneArgumentJadawelFunction):
    type = "many_to_many_count"
    arg_type = [
        JadawelFormulaMultipleSelectType,
        JadawelFormulaMultipleCollaboratorsType,
    ]
    aggregate = True

    def can_accept_arg(self, arg):
        return isinstance(
            arg.expression_type, JadawelFormulaMultipleSelectType
        ) or isinstance(arg.expression_type, JadawelFormulaMultipleCollaboratorsType)

    def type_function(
        self,
        func_call: JadawelFunctionCall,
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaNumberType(number_decimal_places=0)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(arg, function="jsonb_array_elements")

    def to_django_expression_given_args(
        self,
        args: List["WrappedExpressionWithMetadata"],
        context: JadawelExpressionContext,
    ) -> "WrappedExpressionWithMetadata":
        subquery = super().to_django_expression_given_args(args, context)
        return WrappedExpressionWithMetadata(
            Coalesce(
                Func(
                    Func(subquery.expression, function="array"),
                    Value(1),
                    function="array_length",
                    output_field=fields.IntegerField(),
                ),
                Value(0),
                output_field=fields.IntegerField(),
            )
        )


# Deprecated, use JadawelManyToManyAgg instead. This is kept for backwards compatibility
# and will be removed in the future with a proper formula migration.
class JadawelMultipleSelectCount(JadawelManyToManyCount):
    type = "multiple_select_count"
    arg_type = [JadawelFormulaMultipleSelectType]

    def can_accept_arg(self, arg):
        return isinstance(arg.expression_type, JadawelFormulaMultipleSelectType)


class JadawelStringAggManyToManyValues(OneArgumentJadawelFunction):
    type = "string_agg_many_to_many_values"
    arg_type = [
        JadawelFormulaMultipleSelectType,
        JadawelFormulaMultipleCollaboratorsType,
    ]
    aggregate = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Can be overridden in type_function from the arg.expression_type
        self.value_key = "value"

    def type_function(
        self,
        func_call: JadawelFunctionCall,
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        if value_key := getattr(
            arg.expression_type, "custom_string_agg_value_key", None
        ):
            self.value_key = value_key
        return func_call.with_valid_type(JadawelFormulaTextType())

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(
            Func(arg, function="jsonb_array_elements"),
            Value(self.value_key),
            function="jsonb_extract_path_text",
            output_field=fields.TextField(),
        )

    def to_django_expression_given_args(
        self,
        args: List["WrappedExpressionWithMetadata"],
        context: JadawelExpressionContext,
    ) -> "WrappedExpressionWithMetadata":
        subquery = super().to_django_expression_given_args(args, context)
        return WrappedExpressionWithMetadata(
            Func(
                Func(subquery.expression, function="array"),
                Value(", "),
                function="array_to_string",
            )
        )


# Deprecated, use JadawelManyToManyAgg instead. This is kept for backwards compatibility
# and will be removed in the future with a proper formula migration.
class JadawelStringAggMultipleSelectValues(JadawelStringAggManyToManyValues):
    type = "string_agg_multiple_select_values"


class JadawelCount(OneArgumentJadawelFunction):
    type = "count"
    arg_type = [
        MustBeManyExprChecker(JadawelFormulaValidType),
        JadawelFormulaMultipleSelectType,
        JadawelFormulaMultipleCollaboratorsType,
        JadawelFormulaArrayType,
    ]
    aggregate = True
    try_coerce_nullable_args_to_not_null = False

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        if JadawelGetFileCount().can_accept_arg(arg):
            return JadawelGetFileCount()(arg)

        if isinstance(arg.expression_type, JadawelFormulaArrayType):
            return JadawelArrayLength()(arg)

        return arg.expression_type.count(func_call, arg).with_valid_type(
            JadawelFormulaNumberType(number_decimal_places=0)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        """
        Generate a Django COUNT expression for counting rows.

        Uses COUNT(*) instead of COUNT(arg) to ensure we count all rows that match
        the query criteria, regardless of whether any specific field values are NULL.

        :param arg: The field expression that would be counted (ignored in favor of *)
        :return: Django Count expression using COUNT(*)
        """

        return Count("*", output_field=int_like_numeric_output_field())


class JadawelGetFileCount(OneArgumentJadawelFunction):
    type = "get_file_count"
    arg_type = [JadawelFormulaArrayType]

    def can_accept_arg(self, arg):
        return isinstance(arg.expression_type, JadawelFormulaArrayType) and isinstance(
            arg.expression_type.sub_type, JadawelFormulaSingleFileType
        )

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        if not self.can_accept_arg(arg):
            return func_call.with_invalid_type("can only count file fields")
        else:
            return func_call.with_valid_type(
                JadawelFormulaNumberType(number_decimal_places=0)
            )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(
            arg, function="jsonb_array_length", output_field=fields.IntegerField()
        )


class JadawelArrayUnique(OneArgumentJadawelFunction):
    type = "array_unique"
    arg_type = [JadawelFormulaValidType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        # When referencing a lookup field, unwrap_at_field_level converts it
        # back to a "many" expression. Collapse it to an array first.
        if arg.many:
            arg = arg.expression_type.collapse_many(arg)

        if not isinstance(arg.expression_type, JadawelFormulaArrayType):
            return func_call.with_invalid_type(
                "array_unique requires an array field as input."
            )

        sub_type = arg.expression_type.sub_type
        if not sub_type.item_is_in_nested_value_object_when_in_array:
            return func_call.with_invalid_type(
                "array_unique does not support file fields."
            )
        return func_call.with_args([arg]).with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        return JSONBArrayUniqueByValue(arg)


class JadawelArraySlice(ThreeArgumentJadawelFunction):
    type = "array_slice"
    arg1_type = [JadawelFormulaValidType]
    arg2_type = [JadawelFormulaNumberType]
    arg3_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaNumberType],
        arg3: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        if arg1.many:
            arg1 = arg1.expression_type.collapse_many(arg1)

        if not isinstance(arg1.expression_type, JadawelFormulaArrayType):
            return func_call.with_invalid_type("array_slice requires an array input.")

        return func_call.with_args([arg1, arg2, arg3]).with_valid_type(
            arg1.expression_type
        )

    def to_django_expression(
        self, arg1: Expression, arg2: Expression, arg3: Expression
    ) -> Expression:
        either_nan = EqualsExpr(
            arg2, Value(Decimal("NaN")), output_field=fields.BooleanField()
        ) | EqualsExpr(arg3, Value(Decimal("NaN")), output_field=fields.BooleanField())

        start_int = trunc_numeric_to_int(arg2)
        count_int = trunc_numeric_to_int(arg3)
        abs_count = Func(count_int, function="ABS", output_field=fields.IntegerField())

        is_reverse = LessThanExpr(
            count_int, Value(0), output_field=fields.BooleanField()
        )

        array_len = Func(
            arg1, function="jsonb_array_length", output_field=fields.IntegerField()
        )

        # Resolve negative start to a 0-based position
        resolved_start = Case(
            When(
                condition=GreaterThanOrEqualExpr(
                    start_int, Value(0), output_field=fields.BooleanField()
                ),
                then=start_int,
            ),
            default=Greatest(
                ExpressionWrapper(
                    array_len + start_int, output_field=fields.IntegerField()
                ),
                Value(0),
            ),
            output_field=fields.IntegerField(),
        )

        # Forward: offset = resolved_start
        # Backward: offset = max(0, resolved_start - abs_count + 1)
        offset_expr = Case(
            When(
                condition=is_reverse,
                then=Greatest(
                    ExpressionWrapper(
                        resolved_start - abs_count + Value(1),
                        output_field=fields.IntegerField(),
                    ),
                    Value(0),
                ),
            ),
            default=resolved_start,
            output_field=fields.IntegerField(),
        )

        # Forward: 0 → NULL (all remaining), else count
        # Backward: abs(count) — but clamped to (resolved_start + 1)
        #   so we don't go past the beginning
        limit_expr = Case(
            When(
                condition=is_reverse,
                then=Least(
                    abs_count,
                    ExpressionWrapper(
                        resolved_start + Value(1),
                        output_field=fields.IntegerField(),
                    ),
                ),
            ),
            When(
                condition=EqualsExpr(
                    count_int, Value(0), output_field=fields.BooleanField()
                ),
                then=Value(None),
            ),
            default=count_int,
            output_field=fields.IntegerField(),
        )

        return Case(
            When(condition=either_nan, then=Value([], output_field=JSONField())),
            default=JSONBArraySlice(arg1, offset_expr, limit_expr, is_reverse),
            output_field=JSONField(),
        )


class JadawelIndexShortcut(OneArgumentJadawelFunction):
    arg_type = [JadawelFormulaValidType]
    _index: int

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        if arg.many:
            arg = arg.expression_type.collapse_many(arg)

        if not isinstance(arg.expression_type, JadawelFormulaArrayType):
            return func_call.with_invalid_type(f"{self.type} requires an array input.")

        from jadawel.contrib.database.formula.registries import (
            formula_function_registry,
        )

        num_type = JadawelFormulaNumberType(0)
        index_func = formula_function_registry.get("index")
        return index_func.call_and_type_with_args(
            [arg, JadawelIntegerLiteral(self._index, num_type)]
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        raise NotImplementedError("type_function delegates to index")


class JadawelFirst(JadawelIndexShortcut):
    type = "first"
    _index = 0


class JadawelLast(JadawelIndexShortcut):
    type = "last"
    _index = -1


class JadawelArrayLength(OneArgumentJadawelFunction):
    type = "array_length"
    arg_type = [JadawelFormulaArrayType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaNumberType(number_decimal_places=0)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(
            arg, function="jsonb_array_length", output_field=fields.IntegerField()
        )


class JadawelArrayJoinValues(TwoArgumentJadawelFunction):
    type = "array_join_values"
    arg1_type = [JadawelFormulaArrayType]
    arg2_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(JadawelFormulaTextType())

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return JSONBArrayJoinValues(arg1, arg2)


class JadawelFilter(TwoArgumentJadawelFunction):
    type = "filter"
    arg1_type = [JadawelFormulaValidType]
    arg2_type = [JadawelFormulaBooleanType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        if not arg1.many:
            return func_call.with_invalid_type(
                "first input to filter must be an expression of many values ("
                "a lookup function call or a field reference to a lookup/link "
                "field)"
            )
        valid_type = func_call.with_valid_type(arg1.expression_type)
        # Force all usages of filter to be immediately wrapped by an aggregate call
        # otherwise formula behaviour when filtering is odd.
        valid_type.requires_aggregate_wrapper = True
        return valid_type

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return arg1

    def to_django_expression_given_args(
        self,
        args: List["WrappedExpressionWithMetadata"],
        context: JadawelExpressionContext,
    ) -> "WrappedExpressionWithMetadata":
        result = super().to_django_expression_given_args(args, context)
        return WrappedExpressionWithMetadata(
            result.expression,
            result.pre_annotations,
            result.aggregate_filters + [args[1].expression],
            result.join_ids,
        )


def _to_django_aggregate_number_or_duration_expression(
    func: Expression, arg: Expression, **func_kwargs
):
    """
    An utility function to create an aggregate expression for a number or duration
    field.

    :param func: The aggregate function to use.
    :param arg: The expression to aggregate.
    :param func_kwargs: Additional keyword arguments to pass to the aggregate function.
    :return: The aggregate expression.
    """

    if isinstance(arg.output_field, fields.DurationField):
        expr = func(Extract(arg, "epoch"), **func_kwargs) * timedelta(seconds=1)
    else:
        expr = func(arg, **func_kwargs)
    return ExpressionWrapper(expr, output_field=arg.output_field)


class JadawelAny(OneArgumentJadawelFunction):
    type = "any"
    arg_type = [MustBeManyExprChecker(JadawelFormulaBooleanType)]
    aggregate = True

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(arg, function="bool_or", output_field=fields.BooleanField())


class JadawelEvery(OneArgumentJadawelFunction):
    type = "every"
    arg_type = [MustBeManyExprChecker(JadawelFormulaBooleanType)]
    aggregate = True

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(arg, function="every", output_field=fields.BooleanField())


class JadawelMax(OneArgumentJadawelFunction):
    type = "max"
    arg_type = [
        MustBeManyExprChecker(
            JadawelFormulaTextType,
            JadawelFormulaNumberType,
            JadawelFormulaCharType,
            JadawelFormulaDateType,
            JadawelFormulaDurationType,
        ),
    ]
    aggregate = True
    try_coerce_nullable_args_to_not_null = False

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        return _to_django_aggregate_number_or_duration_expression(Max, arg)


class JadawelMin(OneArgumentJadawelFunction):
    type = "min"
    arg_type = [
        MustBeManyExprChecker(
            JadawelFormulaTextType,
            JadawelFormulaNumberType,
            JadawelFormulaCharType,
            JadawelFormulaDateType,
            JadawelFormulaDurationType,
        ),
    ]
    aggregate = True
    try_coerce_nullable_args_to_not_null = False

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        return _to_django_aggregate_number_or_duration_expression(Min, arg)


class JadawelAvg(OneArgumentJadawelFunction):
    type = "avg"
    arg_type = [
        MustBeManyExprChecker(JadawelFormulaNumberType, JadawelFormulaDurationType),
    ]
    aggregate = True
    try_coerce_nullable_args_to_not_null = False

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        return _to_django_aggregate_number_or_duration_expression(Avg, arg)


class JadawelStdDevPop(OneArgumentJadawelFunction):
    type = "stddev_pop"
    arg_type = [
        MustBeManyExprChecker(JadawelFormulaNumberType, JadawelFormulaDurationType)
    ]
    aggregate = True
    try_coerce_nullable_args_to_not_null = False

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        return _to_django_aggregate_number_or_duration_expression(
            StdDev, arg, sample=False
        )


class JadawelStdDevSample(OneArgumentJadawelFunction):
    type = "stddev_sample"
    arg_type = [
        MustBeManyExprChecker(JadawelFormulaNumberType, JadawelFormulaDurationType)
    ]
    aggregate = True
    try_coerce_nullable_args_to_not_null = False

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        return _to_django_aggregate_number_or_duration_expression(
            StdDev, arg, sample=True
        )


class JadawelAggJoin(TwoArgumentJadawelFunction):
    type = "join"
    arg1_type = [MustBeManyExprChecker(JadawelFormulaTextType), JadawelFormulaArrayType]
    arg2_type = [JadawelFormulaTextType]
    aggregate = True

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        if isinstance(arg1.expression_type, JadawelFormulaArrayType):
            return JadawelArrayJoinValues()(arg1, arg2)
        return func_call.with_valid_type(JadawelFormulaTextType())

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        pass

    def to_django_expression_given_args(
        self,
        args: List["WrappedExpressionWithMetadata"],
        context: JadawelExpressionContext,
    ) -> "WrappedExpressionWithMetadata":
        pre_annotations = {}
        aggregate_filters = []
        join_ids = []
        for child in args:
            pre_annotations.update(child.pre_annotations)
            aggregate_filters.extend(child.aggregate_filters)
            join_ids.extend(child.join_ids)

        # Remove any duplicates from join_ids
        join_ids = list(dict.fromkeys(join_ids))
        orders = _calculate_aggregate_orders(join_ids)
        return aggregate_wrapper(
            WrappedExpressionWithMetadata(
                JadawelStringAgg(
                    args[0].expression,
                    args[1].expression,
                    order_by=orders,
                    output_field=fields.TextField(),
                ),
                pre_annotations,
                aggregate_filters,
                join_ids,
            ),
            context.model,
        )


class JadawelSum(OneArgumentJadawelFunction):
    type = "sum"
    aggregate = True
    arg_type = [
        MustBeManyExprChecker(JadawelFormulaNumberType, JadawelFormulaDurationType),
    ]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        return _to_django_aggregate_number_or_duration_expression(Sum, arg)


class JadawelVarianceSample(OneArgumentJadawelFunction):
    type = "variance_sample"
    aggregate = True
    arg_type = [
        MustBeManyExprChecker(JadawelFormulaNumberType, JadawelFormulaDurationType)
    ]
    try_coerce_nullable_args_to_not_null = False

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        return _to_django_aggregate_number_or_duration_expression(
            Variance, arg, sample=True
        )


class JadawelVariancePop(OneArgumentJadawelFunction):
    type = "variance_pop"
    aggregate = True
    arg_type = [
        MustBeManyExprChecker(JadawelFormulaNumberType, JadawelFormulaDurationType)
    ]
    try_coerce_nullable_args_to_not_null = False

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type)

    def to_django_expression(self, arg: Expression) -> Expression:
        return _to_django_aggregate_number_or_duration_expression(
            Variance, arg, sample=False
        )


class JadawelGetSingleSelectValue(OneArgumentJadawelFunction):
    type = "get_single_select_value"
    arg_type = [JadawelFormulaSingleSelectType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaTextType(nullable=arg.expression_type.nullable)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(
            arg,
            Value("value"),
            function="jsonb_extract_path_text",
            output_field=fields.TextField(),
        )


def _index_output_field(mode):
    """Return a fresh Django output_field for the given extraction mode."""

    from jadawel.contrib.database.formula.types.formula_types import (
        _lookup_formula_type_from_string,
    )

    try:
        return _lookup_formula_type_from_string(mode).output_field_class()
    except Exception:
        return fields.TextField()


def _unwrap_literal_value(django_expr):
    """
    Extract the Python value from a Django expression that wraps a
    ``Value(...)`` — e.g. ``Cast(Value('x'), TextField())``.
    """

    while not hasattr(django_expr, "value"):
        if (
            hasattr(django_expr, "source_expressions")
            and django_expr.source_expressions
        ):
            django_expr = django_expr.source_expressions[0]
        else:
            return None
    return django_expr.value


class JadawelIndex(JadawelFunctionDefinition):
    type = "index"
    num_args = NumOfArgsBetween(2, 4)

    @property
    def arg_types(self) -> JadawelArgumentTypeChecker:
        def type_checker(arg_index, arg_types):
            if arg_index == 0:
                return [JadawelFormulaValidType]
            elif arg_index == 1:
                return [JadawelFormulaNumberType]
            else:
                return [JadawelFormulaTextType]  # mode + sql literals

        return type_checker

    def type_function_given_valid_args(
        self,
        args: List[JadawelExpression[JadawelFormulaValidType]],
        func_call: JadawelFunctionCall[UnTyped],
    ) -> JadawelExpression[JadawelFormulaType]:
        if len(args) not in (2, 4):
            return func_call.with_invalid_type(
                "index requires exactly 2 arguments: an array and an index."
            )

        arg1, arg2 = args[0], args[1]

        if arg1.many:
            arg1 = arg1.expression_type.collapse_many(arg1)

        if not isinstance(arg1.expression_type, JadawelFormulaArrayType):
            return func_call.with_invalid_type("index requires an array input.")

        sub_type = arg1.expression_type.sub_type

        if len(args) == 4:
            return func_call.with_args(list(args)).with_valid_type(sub_type)

        mode_literal = JadawelStringLiteral(
            sub_type.array_index_mode, JadawelFormulaTextType()
        )
        sql_literal = JadawelStringLiteral(
            sub_type.array_index_sql, JadawelFormulaTextType()
        )

        return func_call.with_args(
            [arg1, arg2, mode_literal, sql_literal]
        ).with_valid_type(sub_type)

    def to_django_expression_given_args(
        self,
        args: List["WrappedExpressionWithMetadata"],
        context: JadawelExpressionContext,
    ) -> "WrappedExpressionWithMetadata":
        mode = _unwrap_literal_value(args[2].expression) or "text"
        value_sql = _unwrap_literal_value(args[3].expression) or "{elem} ->> 'value'"
        safe_index = handle_arg_being_nan(
            args[1].expression,
            Value(None, output_field=fields.IntegerField()),
            args[1].expression,
        )
        expr = JSONBArrayGetElement(
            args[0].expression,
            safe_index,
            value_sql,
            _index_output_field(mode),
        )
        return WrappedExpressionWithMetadata.from_args(expr, args)


class JadawelJsonbExtractPathText(JadawelFunctionDefinition):
    type = "jsonb_extract_path_text"
    num_args = NumOfArgsGreaterThan(1)

    @property
    def arg_types(self) -> JadawelArgumentTypeChecker:
        def type_checker(arg_index: int, arg_types: List[JadawelFormulaType]):
            if arg_index == 0:
                return [JadawelJSONBObjectBaseType]
            else:
                return [JadawelFormulaTextType]

        return type_checker

    def type_function_given_valid_args(
        self,
        args: List[JadawelExpression[JadawelFormulaValidType]],
        expression: "JadawelFunctionCall[UnTyped]",
    ) -> JadawelExpression[JadawelFormulaType]:
        return expression.with_valid_type(JadawelFormulaTextType(nullable=True))

    def to_django_expression_given_args(
        self, expr_args: List[WrappedExpressionWithMetadata], *args, **kwargs
    ) -> WrappedExpressionWithMetadata:
        return WrappedExpressionWithMetadata(
            Func(
                *[e.expression for e in expr_args],
                function="jsonb_extract_path_text",
                output_field=fields.TextField(),
            )
        )

    def __call__(
        self,
        arg: JadawelExpression[JadawelJSONBObjectBaseType],
        *path: JadawelExpression[JadawelFormulaTextType],
    ) -> JadawelFunctionCall[JadawelFormulaTextType]:
        return self.call_and_type_with_args([arg, *path])


class JadawelGetFileVisibleName(OneArgumentJadawelFunction):
    type = "get_file_visible_name"
    arg_type = [JadawelFormulaSingleFileType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaSingleFileType],
    ) -> JadawelExpression[JadawelFormulaTextType]:
        return JadawelJsonbExtractPathText()(arg, literal("visible_name"))

    def to_django_expression(self, arg: Expression) -> Expression:
        return arg


class JadawelGetFileMimeType(OneArgumentJadawelFunction):
    type = "get_file_mime_type"
    arg_type = [JadawelFormulaSingleFileType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaSingleFileType],
    ) -> JadawelExpression[JadawelFormulaTextType]:
        return JadawelJsonbExtractPathText()(arg, literal("mime_type"))

    def to_django_expression(self, arg: Expression) -> Expression:
        return arg


class JadawelGetFileSize(OneArgumentJadawelFunction):
    type = "get_file_size"
    arg_type = [JadawelFormulaSingleFileType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaSingleFileType],
    ) -> JadawelExpression[JadawelFormulaNumberType]:
        return func_call.with_valid_type(
            JadawelFormulaNumberType(
                nullable=arg.expression_type.nullable, number_decimal_places=0
            )
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Cast(
            Func(
                arg,
                Value("size"),
                function="jsonb_extract_path_text",
                output_field=fields.IntegerField(),
            ),
            output_field=fields.IntegerField(),
        )


class JadawelGetImageWidth(OneArgumentJadawelFunction):
    type = "get_image_width"
    arg_type = [JadawelFormulaSingleFileType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaSingleFileType],
    ) -> JadawelExpression[JadawelFormulaNumberType]:
        return func_call.with_valid_type(
            JadawelFormulaNumberType(nullable=True, number_decimal_places=0)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Cast(
            Func(
                arg,
                Value("image_width"),
                function="jsonb_extract_path_text",
                output_field=fields.IntegerField(),
            ),
            output_field=fields.IntegerField(),
        )


class JadawelGetImageHeight(OneArgumentJadawelFunction):
    type = "get_image_height"
    arg_type = [JadawelFormulaSingleFileType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaSingleFileType],
    ) -> JadawelExpression[JadawelFormulaNumberType]:
        return func_call.with_valid_type(
            JadawelFormulaNumberType(nullable=True, number_decimal_places=0)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Cast(
            Func(
                arg,
                Value("image_height"),
                function="jsonb_extract_path_text",
                output_field=fields.IntegerField(),
            ),
            output_field=fields.IntegerField(),
        )


class JadawelIsImage(OneArgumentJadawelFunction):
    type = "is_image"
    arg_type = [JadawelFormulaSingleFileType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaSingleFileType],
    ) -> JadawelExpression[JadawelFormulaBooleanType]:
        return func_call.with_valid_type(
            JadawelFormulaBooleanType(nullable=arg.expression_type.nullable)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Coalesce(
            Cast(
                Func(
                    arg,
                    Value("is_image"),
                    function="jsonb_extract_path_text",
                    output_field=fields.BooleanField(),
                ),
                output_field=fields.BooleanField(),
            ),
            Value(False),
            output_field=fields.BooleanField(),
        )


class JadawelGetLinkUrl(OneArgumentJadawelFunction):
    type = "get_link_url"
    arg_type = [JadawelFormulaLinkType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaTextType(nullable=arg.expression_type.nullable)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(
            arg,
            Value("url"),
            function="jsonb_extract_path_text",
            output_field=fields.TextField(),
        )


class JadawelGetLinkLabel(OneArgumentJadawelFunction):
    type = "get_link_label"
    arg_type = [JadawelFormulaLinkType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaTextType(nullable=arg.expression_type.nullable)
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(
            arg,
            Value("label"),
            function="jsonb_extract_path_text",
            output_field=fields.TextField(),
        )


class JadawelLeft(TwoArgumentJadawelFunction):
    type = "left"
    arg1_type = [JadawelFormulaTextType]
    arg2_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg1.expression_type, nullable=True)

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return handle_arg_being_nan(
            arg_to_check_if_nan=arg2,
            when_nan=Value(None),
            when_not_nan=(
                Left(arg1, trunc_numeric_to_int(arg2), output_field=fields.TextField())
            ),
        )


class JadawelRight(TwoArgumentJadawelFunction):
    type = "right"
    arg1_type = [JadawelFormulaTextType]
    arg2_type = [JadawelFormulaNumberType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaNumberType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg1.expression_type, nullable=True)

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return handle_arg_being_nan(
            arg_to_check_if_nan=arg2,
            when_nan=Value(None),
            when_not_nan=(
                Right(
                    arg1,
                    trunc_numeric_to_int(arg2),
                    output_field=fields.TextField(),
                )
            ),
        )


class JadawelRegexReplace(ThreeArgumentJadawelFunction):
    type = "regex_replace"
    arg1_type = [JadawelFormulaTextType]
    arg2_type = [JadawelFormulaTextType]
    arg3_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
        arg3: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg1.expression_type)

    def to_django_expression(
        self, arg1: Expression, arg2: Expression, arg3: Expression
    ) -> Expression:
        return Func(
            arg1,
            arg2,
            arg3,
            Value("g", output_field=fields.TextField()),
            Value("#ERROR!", output_field=fields.TextField()),
            function="try_regexp_replace",
            output_field=fields.TextField(),
        )


class JadawelLink(JadawelFunctionDefinition):
    type = "link"
    num_args = NumOfArgsBetween(1, 2, inclusive=True)
    try_coerce_nullable_args_to_not_null = False

    @property
    def arg_types(self) -> JadawelArgumentTypeChecker:
        return lambda _, _2: [JadawelFormulaTextType]

    def type_function_given_valid_args(
        self,
        args: List[JadawelExpression[JadawelFormulaValidType]],
        expression: "JadawelFunctionCall[UnTyped]",
    ) -> JadawelExpression[JadawelFormulaType]:
        typed_args = [JadawelToText()(a) for a in args]
        return expression.with_args(typed_args).with_valid_type(
            JadawelFormulaLinkType(nullable=args[0].expression_type.nullable)
        )

    def to_django_expression_given_args(
        self, expr_args: List[WrappedExpressionWithMetadata], *args, **kwargs
    ) -> WrappedExpressionWithMetadata:
        url_kwargs = {"url": expr_args[0].expression}
        if len(expr_args) > 1:
            url_kwargs["label"] = expr_args[1].expression
        expr = JSONObject(**url_kwargs)
        return WrappedExpressionWithMetadata.from_args(
            ExpressionWrapper(expr, output_field=JSONField()),
            expr_args,
        )


class JadawelButton(TwoArgumentJadawelFunction):
    type = "button"
    arg1_type = [JadawelFormulaTextType]
    arg2_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg1: JadawelExpression[JadawelFormulaValidType],
        arg2: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaButtonType(nullable=arg1.expression_type.nullable)
        )

    def to_django_expression(self, arg1: Expression, arg2: Expression) -> Expression:
        return JSONObject(url=arg1, label=arg2)


class JadawelTrim(OneArgumentJadawelFunction):
    type = "trim"
    arg_type = [JadawelFormulaTextType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return JadawelRegexReplace()(arg, literal("(^\\s+|\\s+$)"), literal(""))

    def to_django_expression(self, arg: Expression) -> Expression:
        # This function should always be completely substituted when typing and replaced
        # with JadawelRegexReplace and hence this should never be called.
        raise JadawelToDjangoExpressionGenerationError()


class JadawelYear(OneArgumentJadawelFunction):
    type = "year"
    arg_type = [JadawelFormulaDateType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(
            JadawelFormulaNumberType(
                number_decimal_places=0, nullable=arg.expression_type.nullable
            )
        )

    def to_django_expression(self, arg: Expression) -> Expression:
        return JadawelExtract(arg, "year", output_field=int_like_numeric_output_field())


class JadawelSecond(OneArgumentJadawelFunction):
    type = "second"
    arg_type = [JadawelFormulaDateType]

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaDateType],
    ) -> JadawelExpression[JadawelFormulaType]:
        if not arg.expression_type.date_include_time:
            return func_call.with_invalid_type(
                "cannot extract seconds from a date without time"
            )
        else:
            return func_call.with_valid_type(
                JadawelFormulaNumberType(
                    number_decimal_places=0, nullable=arg.expression_type.nullable
                )
            )

    def to_django_expression(self, arg: Expression) -> Expression:
        return JadawelExtract(
            arg, "second", output_field=int_like_numeric_output_field()
        )


class JadawelBcToNull(OneArgumentJadawelFunction):
    type = "bc_to_null"
    arg_type = [JadawelFormulaDateType]
    is_wrapper = True

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(arg.expression_type, nullable=True)

    def to_django_expression(self, arg: Expression) -> Expression:
        expr_to_get_year = JadawelExtract(
            arg, "year", output_field=int_like_numeric_output_field()
        )
        return Case(
            When(
                condition=LessThanExpr(
                    expr_to_get_year, Value(0), output_field=fields.BooleanField()
                ),
                then=Value(None, output_field=arg.output_field),
            ),
            default=arg,
        )


class JadawelToURL(OneArgumentJadawelFunction):
    type = "tourl"
    arg_type = [JadawelFormulaTextType]
    try_coerce_nullable_args_to_not_null = False

    def type_function(
        self,
        func_call: JadawelFunctionCall[UnTyped],
        arg: JadawelExpression[JadawelFormulaValidType],
    ) -> JadawelExpression[JadawelFormulaType]:
        return func_call.with_valid_type(JadawelFormulaURLType())

    def to_django_expression(self, arg: Expression) -> Expression:
        return Func(arg, function="try_cast_to_url", output_field=fields.CharField())
