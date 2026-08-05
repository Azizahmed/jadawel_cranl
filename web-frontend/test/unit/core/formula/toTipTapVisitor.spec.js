import { TestApp } from '@jadawel/test/helpers/testApp'
import { RuntimeFunctionCollection } from '@jadawel/modules/core/functionCollection'
import { ToTipTapVisitor } from '@jadawel/modules/core/formula/tiptap/toTipTapVisitor'
import parseBaserowFormula from '@jadawel/modules/core/formula/parser/parser'
import testCases from '@jadawel_test_cases/tip_tap_visitor_cases.json'

describe('toTipTapVisitor', () => {
  let testApp = null
  beforeEach(() => {
    testApp = new TestApp()
  })

  testCases.forEach(({ formula, content }) => {
    it(`should return the expected formula for ${formula}`, () => {
      const functionCollection = new RuntimeFunctionCollection(
        testApp.store.$registry
      )
      // We don't want to test empty formula
      if (formula) {
        const tree = parseBaserowFormula(formula)
        const result = new ToTipTapVisitor(functionCollection).visit(tree)
        expect(result).toEqual(content)
      }
    })
  })
})
