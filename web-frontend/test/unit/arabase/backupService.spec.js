import MockAdapter from 'axios-mock-adapter'

import BackupService from '@jadawel/modules/arabase/services/backup'

describe('backup admin service', () => {
  let client = null
  let mock = null
  let service = null

  beforeEach(() => {
    const { $client } = useNuxtApp()
    client = $client
    mock = new MockAdapter(client, { onNoMatch: 'throwException' })
    service = BackupService(client)
  })

  afterEach(() => {
    mock.restore()
  })

  test('reads the overview from the admin endpoint', async () => {
    mock.onGet('/arabase/admin/backup/').reply(200, {
      enabled: true,
      schedule: { frequency: 'daily', crontab: '0 23 * * *' },
      health: { status: 'ok', healthy: true, configuration_errors: [] },
    })

    const { data } = await service.fetchOverview()

    expect(data.schedule.frequency).toBe('daily')
    expect(data.health.healthy).toBe(true)
  })

  test('sends the frequency as a PATCH', async () => {
    mock.onPatch('/arabase/admin/backup/').reply(200, {
      enabled: true,
      schedule: { frequency: 'hourly', crontab: '0 * * * *' },
      health: { status: 'ok', healthy: true, configuration_errors: [] },
    })

    await service.setFrequency('hourly')

    expect(JSON.parse(mock.history.patch[0].data)).toEqual({
      frequency: 'hourly',
    })
  })

  test('queues a manual run', async () => {
    mock.onPost('/arabase/admin/backup/run/').reply(202)

    await service.runNow()

    expect(mock.history.post).toHaveLength(1)
  })

  test('sends the restore target under its snake_case name', async () => {
    // The backend rejects the live database, so the target has to reach it
    // intact — a silently dropped field would look like a validation bug.
    mock.onPost('/arabase/admin/backup/restore/').reply(202, {
      key: 'postgres/jadawel-20260815T230000Z.dump',
      target: 'postgresql://u:***@scratch:5432/copy',
    })

    const { data } = await service.restore(
      'postgres/jadawel-20260815T230000Z.dump',
      'postgresql://u:hunter2@scratch:5432/copy'
    )

    expect(JSON.parse(mock.history.post[0].data)).toEqual({
      key: 'postgres/jadawel-20260815T230000Z.dump',
      target_database_url: 'postgresql://u:hunter2@scratch:5432/copy',
    })
    // The response never carries the password back.
    expect(data.target).not.toContain('hunter2')
  })
})
