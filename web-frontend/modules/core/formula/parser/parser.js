import antlr4 from 'antlr4'
import JadawelFormulaLexer from '@jadawel/modules/core/formula/parser/generated/JadawelFormulaLexer'
import JadawelFormula from '@jadawel/modules/core/formula/parser/generated/JadawelFormula'
import { JadawelFormulaParserError } from '@jadawel/modules/core/formula/parser/errors'

/**
 * Attempts to parse an input string into a Jadawel Formula. If it fails a
 * JadawelFormulaParserError will be raised.
 *
 * @param formula
 * @return {*} The resulting antlr4 parse tree of the formula
 */
export default function parseJadawelFormula(formula) {
  const chars = new antlr4.InputStream(formula)
  const lexer = new JadawelFormulaLexer(chars)
  const tokens = new antlr4.CommonTokenStream(lexer)
  const parser = new JadawelFormula(tokens)
  parser.removeErrorListeners()
  // noinspection JSUnusedLocalSymbols
  parser.addErrorListener({
    syntaxError: (recognizer, offendingSymbol, line, column, msg, err) => {
      throw new JadawelFormulaParserError(offendingSymbol, line, column, msg)
    },
  })
  parser.buildParseTrees = true
  return parser.root()
}

export function getTokenStreamForFormula(formula) {
  const chars = new antlr4.InputStream(formula)
  const lexer = new JadawelFormulaLexer(chars)
  const stream = new antlr4.CommonTokenStream(lexer)
  stream.lazyInit()
  stream.fill()
  return stream
}
