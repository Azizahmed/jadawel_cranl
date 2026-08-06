/**
 * This file can be used in combination with intellij idea so the @jadawel path
 * resolves.
 *
 * Intellij IDEA: Preferences -> Languages & Frameworks -> JavaScript -> Webpack ->
 * webpack configuration file
 */

const path = require('path')

module.exports = {
  resolve: {
    extensions: ['.js', '.json', '.vue', '.ts'],
    root: path.resolve(__dirname),
    alias: {
      '@jadawel': path.resolve(__dirname),
      '@jadawel_test_cases': path.resolve(__dirname, '../tests/cases'),
    },
  },
}
