import {
  ChartWidgetType,
  ProgressWidgetType,
  RecordsListWidgetType,
  UpcomingDatesWidgetType,
} from '@jadawel/modules/arabase/dashboard/widgetTypes'

const widgetTypes = [
  ChartWidgetType,
  ProgressWidgetType,
  RecordsListWidgetType,
  UpcomingDatesWidgetType,
]

describe('Arabase async widget components', () => {
  test.each(widgetTypes)(
    '%s loads its renderer and settings chunks',
    async (Type) => {
      const type = new Type({
        app: {
          $i18n: {
            t: (key) => key,
          },
        },
      })

      await expect(type.component.__asyncLoader()).resolves.toBeTruthy()
      await expect(type.settingsComponent.__asyncLoader()).resolves.toBeTruthy()
    }
  )
})
