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
      '@jadawel_premium': path.resolve(
        __dirname,
        '../premium/web-frontend/modules/baserow_premium'
      ),
      '@jadawel_premium_test': path.resolve(
        __dirname,
        '../premium/web-frontend/test'
      ),
      '@jadawel_enterprise': path.resolve(
        __dirname,
        '../enterprise/web-frontend/modules/baserow_enterprise'
      ),
      '@jadawel_enterprise_test': path.resolve(
        __dirname,
        '../enterprise/web-frontend/test'
      ),
      '@jadawel_test_cases': path.resolve(__dirname, '../tests/cases'),
    },
  },
}
