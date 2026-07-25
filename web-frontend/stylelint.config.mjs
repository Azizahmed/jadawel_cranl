export default {
  extends: ['stylelint-config-standard-scss'],
  plugins: ['stylelint-selector-bem-pattern', 'stylelint-use-logical'],
  overrides: [
    { files: ['**/*.scss'], customSyntax: 'postcss-scss' },
    { files: ['**/*.vue'], customSyntax: 'postcss-html' },
    {
      // Jadawel fork: new fork code must be RTL-safe from the start — physical
      // left/right/margin-left/etc. are hard errors under modules/arabase.
      files: ['modules/arabase/**/*.{scss,vue}'],
      rules: { 'csstools/use-logical': 'always' },
    },
  ],
  rules: {
    // Your BEM class name regex
    'selector-class-pattern': [
      '^[a-z]([-]?[a-z0-9]+)*(__[a-z0-9]([-]?[a-z0-9]+)*)?(--[a-z0-9]([-]?[a-z0-9]+)*)?$',
      {
        resolveNestedSelectors: true,
        message: function expected(selectorValue) {
          return `Expected class selector "${selectorValue}" to match BEM CSS pattern https://en.bem.info/methodology/css. Selector validation tool: https://regexr.com/3apms`
        },
      },
    ],

    // Your BEM plugin rule
    'plugin/selector-bem-pattern': {
      componentName: '[A-Z]+',
      componentSelectors: {
        initial: '^\\.{componentName}(?:-[a-z]+)?$',
        combined: '^\\.combined-{componentName}-[a-z]+$',
      },
      utilitySelectors: '^\\.util-[a-z]+$',
    },

    // SCSS: use the SCSS-aware at-rule rule
    'at-rule-no-unknown': null,
    'scss/at-rule-no-unknown': [
      true,
      {
        ignoreAtRules: [
          '/regex/',
          'function',
          'if',
          'each',
          'else',
          'include',
          'mixin',
          'return',
          'extend',
          'for',
          'use',
          'forward',
        ],
      },
    ],

    'scss/dollar-variable-pattern': null,
    'scss/dollar-variable-empty-line-before': null,

    // Keep your other choices
    'media-feature-range-notation': 'prefix',
    'color-function-notation': 'legacy',
    'scss/no-global-function-names': null,
    'alpha-value-notation': 'number',
    'selector-not-notation': 'simple',
    'color-function-alias-notation': null,

    // Jadawel fork (RTL): flag physical inline properties (left/right, margin-left,
    // text-align: left/right, …) so they can be migrated to CSS logical properties.
    // Set to `warning` globally because the upstream SCSS has a large legacy surface
    // (~180 files) still to convert file-by-file; this turns that backlog into a
    // visible worklist without breaking CI. New fork code (modules/arabase) is held
    // to `error` via the override above. Raise this to an array with severity
    // 'error' once the core conversion is complete.
    'csstools/use-logical': ['always', { severity: 'warning' }],
  },
}
