const { unsupportedJadawelFieldTypes } = require('./constants')

/**
 * Fetches the fields of a table and converts them to an array with valid Zapier
 * field objects.
 */
const getRowInputValues = async (z, bundle) => {
  if (!bundle.inputData.tableID) {
    throw new Error('The `tableID` must be provided.')
  }

  const fieldsGetRequest = await z.request({
    url: `${bundle.authData.apiURL}/api/database/fields/table/${bundle.inputData.tableID}/`,
    method: 'GET',
    headers: {
      'Accept': 'application/json',
      'Authorization': `Token ${bundle.authData.apiToken}`,
    },
  })

  return fieldsGetRequest.json.map(v => {
    return mapJadawelFieldTypesToZapierTypes(v)
  })
}

/**
 * Fetches the fields and converts the input data to Jadawel row compatible data.
 */
const prepareInputDataForJadawel = async (z, bundle) => {
  if (!bundle.inputData.tableID) {
    throw new Error('The `tableID` must be provided.')
  }

  const fieldsGetRequest = await z.request({
    url: `${bundle.authData.apiURL}/api/database/fields/table/${bundle.inputData.tableID}/`,
    method: 'GET',
    headers: {
      'Accept': 'application/json',
      'Authorization': `Token ${bundle.authData.apiToken}`,
    },
  })

  let rowData = { id: bundle.inputData.rowID }
  fieldsGetRequest
    .json
    .filter(
      (jadawelField) =>
        jadawelField.read_only
          || !unsupportedJadawelFieldTypes.includes(jadawelField.type)
    )
    .filter((jadawelField) => bundle.inputData.hasOwnProperty(jadawelField.name))
    .forEach(jadawelField => {
      let value = bundle.inputData[jadawelField.name]

      if (jadawelField.type === 'multiple_collaborators') {
        value = value.map(id => {
          return { id }}
        )
      }

      rowData[jadawelField.name] = value
    })

  return rowData
}

/**
 * Converts the provided Jadawel field type object to a Zapier compatible object.
 */
const mapJadawelFieldTypesToZapierTypes = (jadawelField) => {
  const zapType = {
    key: jadawelField.name,
    label: jadawelField.name,
    type: 'string'
  }

  if (jadawelField.type === 'long_text') {
    zapType.type = 'text'
  }

  if (jadawelField.type === 'boolean') {
    zapType.type = 'boolean'
  }

  if (jadawelField.type === 'number') {
    zapType.type = 'integer'

    if (jadawelField.number_decimal_places > 0) {
      zapType.type = 'float'
    }
  }

  if (jadawelField.type === 'boolean') {
    zapType.type = 'boolean'
  }

  if (jadawelField.type === 'rating') {
    zapType.type = 'integer'
  }

  if (['single_select', 'multiple_select'].includes(jadawelField.type)) {
    const choices = {}
    jadawelField.select_options.forEach(el => {
      choices[`${el.id}`] = el.value
    })
    zapType.type = 'string'
    zapType.choices = choices
  }

  if (jadawelField.type === 'multiple_select') {
    zapType.list = true
  }

  if (jadawelField.type === 'link_row') {
    zapType.type = 'integer'
    zapType.helpText = 'Provide row ids that you want to link to.'
    zapType.list = true
  }

  if (jadawelField.type === 'multiple_collaborators') {
    zapType.type = 'integer'
    zapType.helpText = 'Provide user ids that you want to link to.'
    zapType.list = true
  }

  if (jadawelField.type === 'date' && !jadawelField.date_include_time) {
    zapType.type = 'date'
    zapType.helpText =
      'the date fields accepts a date in ISO format (e.g. 2020-01-01)'
  }

  if (jadawelField.type === 'date' && jadawelField.date_include_time) {
    zapType.type = 'datetime'
    zapType.helpText =
      'the date fields accepts date and time in ISO format (e.g. 2020-01-01 12:00)'
  }

  if (
    jadawelField.read_only
    || unsupportedJadawelFieldTypes.includes(jadawelField.type)
  ) {
    // Read only and the file field are not supported.
    return
  }

  return zapType
}

module.exports = {
  getRowInputValues,
  prepareInputDataForJadawel,
  mapJadawelFieldTypesToZapierTypes,
}
