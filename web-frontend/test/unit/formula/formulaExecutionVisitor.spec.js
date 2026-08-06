import parseJadawelFormula from '@jadawel/modules/core/formula/parser/parser'
import JadawelFormulaExecutionVisitor from '@jadawel/modules/core/formula/parser/formulaExecutionVisitor.js'
import {
  VALID_FORMULA_EXECUTION_TESTS,
  INVALID_FORMULA_EXECUTION_TESTS,
} from '@jadawel_test_cases/formula_visitor_cases'
import { TestApp } from '@jadawel/test/helpers/testApp'

describe('JadawelFormulaExecutionVisitor', () => {
  let testApp = null
  beforeEach(() => {
    testApp = new TestApp()
  })

  test.each(VALID_FORMULA_EXECUTION_TESTS)(
    'should correctly resolve the formula %s',
    ({ formula, result, context }) => {
      const tree = parseJadawelFormula(formula)
      expect(
        new JadawelFormulaExecutionVisitor(
          {
            get(name) {
              return testApp.store.$registry.get('runtimeFormulaFunction', name)
            },
          },
          context
        ).visit(tree)
      ).toEqual(result)
    }
  )

  test.each(INVALID_FORMULA_EXECUTION_TESTS)(
    'should correctly raise an error for formula %s',
    ({ formula, context }) => {
      const tree = parseJadawelFormula(formula)
      expect(() =>
        new JadawelFormulaExecutionVisitor(
          {
            get(name) {
              return testApp.store.$registry.get('runtimeFormulaFunction', name)
            },
          },
          context
        ).visit(tree)
      ).toThrow()
    }
  )
})
