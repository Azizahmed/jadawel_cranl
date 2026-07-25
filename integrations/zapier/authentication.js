module.exports = {
  type: 'custom',
  test: {
    url: `{{bundle.authData.apiURL}}/api/database/tokens/check/`,
    method: 'GET',
    headers: { 'Authorization': 'Token {{bundle.authData.apiToken}}' },
  },
  fields: [
    {
      computed: false,
      key: 'apiToken',
      required: true,
      label: 'Jadawel API token',
      type: 'string',
      helpText:
        'Please enter your Jadawel API token. Can be found by clicking on your ' +
        'account in the top left corner -> Settings -> API tokens.'
    },
    {
      computed: false,
      key: 'apiURL',
      required: true,
      label: 'Jadawel API URL',
      type: 'string',
      helpText:
        'Please enter the API URL of your Jadawel installation, for example ' +
        'https://jadawel.example.com.'
    },
  ],
  connectionLabel: 'Jadawel API authentication',
  customConfig: {}
}
