import { readFile, rm, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

/**
 * Rewrites the Arabic month names bundled inside `vuejs3-datepicker`.
 *
 * The library ships a Levantine locale under its `ar` key (كانون الثاني،
 * شباط، آذار، …) while the app's users expect the Gregorian names used
 * across the Gulf and Egypt (يناير، فبراير، مارس، …). The library exposes
 * no way to override a bundled locale — its `language` prop only selects a
 * key from an internal, unexported map — so the names are patched in
 * place in `node_modules` after `yarn install`.
 *
 * The replacement is a plain 1:1 name mapping, so it stays correct as
 * long as the `ar` locale keeps using the Levantine spelling. Every other
 * bundled locale (including Tunisian `arTn`) uses different month names
 * and is left untouched.
 */

const LEVANTINE_TO_GREGORIAN = new Map([
  ['كانون الثاني', 'يناير'],
  ['شباط', 'فبراير'],
  ['آذار', 'مارس'],
  ['نيسان', 'أبريل'],
  ['ايار', 'مايو'],
  ['حزيران', 'يونيو'],
  ['تموز', 'يوليو'],
  ['آب', 'أغسطس'],
  ['أيلول', 'سبتمبر'],
  ['تشرين الاول', 'أكتوبر'],
  ['تشرين الثاني', 'نوفمبر'],
  ['كانون الاول', 'ديسمبر'],
])

const BUNDLE_FILES = [
  'vuejs3-datepicker/build/vuejs3-datepicker.js',
  'vuejs3-datepicker/build/vuejs3-datepicker.umd.cjs',
]

const projectRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '..'
)

let patchedAny = false

for (const relativePath of BUNDLE_FILES) {
  const filePath = path.join(projectRoot, 'node_modules', relativePath)
  let source
  try {
    source = await readFile(filePath, 'utf8')
  } catch {
    // The package is absent (e.g. a partial install); nothing to patch.
    continue
  }

  let patched = source
  for (const [levantine, gregorian] of LEVANTINE_TO_GREGORIAN) {
    patched = patched.split(levantine).join(gregorian)
  }

  if (patched !== source) {
    await writeFile(filePath, patched, 'utf8')
    patchedAny = true
    console.log(`patched Arabic month names in ${relativePath}`)
  }
}

if (!patchedAny) {
  console.log('no Levantine month names found; datepicker left unchanged')
} else {
  // Vite pre-bundles dependencies and can otherwise keep serving the old
  // locale even after the package bundle is patched. This directory is a
  // generated cache and will be recreated from the corrected source.
  await rm(path.join(projectRoot, 'node_modules/.cache/vite/client/deps'), {
    recursive: true,
    force: true,
  })
  console.log('cleared the Vite dependency cache after patching the datepicker')
}
