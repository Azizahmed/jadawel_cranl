# Generated from JadawelFormula.g4 by ANTLR 4.9
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .JadawelFormula import JadawelFormula
else:
    from JadawelFormula import JadawelFormula

# This class defines a complete generic visitor for a parse tree produced by JadawelFormula.

class JadawelFormulaVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by JadawelFormula#root.
    def visitRoot(self, ctx:JadawelFormula.RootContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by JadawelFormula#FieldReference.
    def visitFieldReference(self, ctx:JadawelFormula.FieldReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by JadawelFormula#StringLiteral.
    def visitStringLiteral(self, ctx:JadawelFormula.StringLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by JadawelFormula#Brackets.
    def visitBrackets(self, ctx:JadawelFormula.BracketsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by JadawelFormula#BooleanLiteral.
    def visitBooleanLiteral(self, ctx:JadawelFormula.BooleanLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by JadawelFormula#RightWhitespaceOrComments.
    def visitRightWhitespaceOrComments(self, ctx:JadawelFormula.RightWhitespaceOrCommentsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by JadawelFormula#DecimalLiteral.
    def visitDecimalLiteral(self, ctx:JadawelFormula.DecimalLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by JadawelFormula#LeftWhitespaceOrComments.
    def visitLeftWhitespaceOrComments(self, ctx:JadawelFormula.LeftWhitespaceOrCommentsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by JadawelFormula#FunctionCall.
    def visitFunctionCall(self, ctx:JadawelFormula.FunctionCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by JadawelFormula#FieldByIdReference.
    def visitFieldByIdReference(self, ctx:JadawelFormula.FieldByIdReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by JadawelFormula#LookupFieldReference.
    def visitLookupFieldReference(self, ctx:JadawelFormula.LookupFieldReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by JadawelFormula#IntegerLiteral.
    def visitIntegerLiteral(self, ctx:JadawelFormula.IntegerLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by JadawelFormula#BinaryOp.
    def visitBinaryOp(self, ctx:JadawelFormula.BinaryOpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by JadawelFormula#ws_or_comment.
    def visitWs_or_comment(self, ctx:JadawelFormula.Ws_or_commentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by JadawelFormula#func_name.
    def visitFunc_name(self, ctx:JadawelFormula.Func_nameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by JadawelFormula#field_reference.
    def visitField_reference(self, ctx:JadawelFormula.Field_referenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by JadawelFormula#identifier.
    def visitIdentifier(self, ctx:JadawelFormula.IdentifierContext):
        return self.visitChildren(ctx)



del JadawelFormula