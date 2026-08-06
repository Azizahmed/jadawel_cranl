import parseJadawelFormula from '@jadawel/modules/core/formula/parser/parser'
import { JadawelFormulaParserError } from '@jadawel/modules/core/formula/parser/errors'

describe('Jadawel Formula Tests', () => {
  const validFormulas = ["lower('test')", "upper('test')"]
  const invalidFormulas = [
    ['a', JadawelFormulaParserError],
    ['12ssda3', JadawelFormulaParserError],
  ]

  test.each(validFormulas)(
    'valid jadawel formulas do not raise a parser error',
    (value) => {
      expect(parseJadawelFormula(value)).toBeTruthy()
    }
  )

  test.each(invalidFormulas)(
    'invalid jadawel formulas raise a parser error',
    (value, exception) => {
      expect(() => parseJadawelFormula(value)).toThrow(exception)
    }
  )
})
