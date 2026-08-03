import { WidgetType } from '@baserow/modules/dashboard/widgetTypes'
import ChartWidget from '@baserow/modules/arabase/dashboard/components/widget/ChartWidget'
import ChartWidgetSettings from '@baserow/modules/arabase/dashboard/components/widget/ChartWidgetSettings'
import BarChartSvg from '@baserow/modules/arabase/assets/images/widgets/bar_chart_widget.svg?url'
import LineChartSvg from '@baserow/modules/arabase/assets/images/widgets/line_chart_widget.svg?url'
import PieChartSvg from '@baserow/modules/arabase/assets/images/widgets/pie_chart_widget.svg?url'
import DoughnutChartSvg from '@baserow/modules/arabase/assets/images/widgets/doughnut_chart_widget.svg?url'

/**
 * One widget type presented as four tiles.
 *
 * Bar, line, pie and doughnut need identical configuration and users routinely
 * try one then switch, so they are variations of a single `chart` type rather
 * than four types. A variation only decides which `chart_type` the widget is
 * created with; the settings panel can change it afterwards.
 */
export class ChartWidgetType extends WidgetType {
  static getType() {
    return 'chart'
  }

  get name() {
    return this.app.$i18n.t('chartWidget.name')
  }

  get createWidgetImage() {
    return BarChartSvg
  }

  get component() {
    return ChartWidget
  }

  get settingsComponent() {
    return ChartWidgetSettings
  }

  get variations() {
    const { $i18n: i18n } = this.app
    return [
      {
        name: i18n.t('chartWidget.bar'),
        createWidgetImage: BarChartSvg,
        type: this,
        params: { chart_type: 'bar' },
        dropdownIcon: 'iconoir-bar-chart',
      },
      {
        name: i18n.t('chartWidget.line'),
        createWidgetImage: LineChartSvg,
        type: this,
        params: { chart_type: 'line' },
        dropdownIcon: 'iconoir-graph-up',
      },
      {
        name: i18n.t('chartWidget.pie'),
        createWidgetImage: PieChartSvg,
        type: this,
        params: { chart_type: 'pie' },
        dropdownIcon: 'iconoir-pie-chart',
      },
      {
        name: i18n.t('chartWidget.doughnut'),
        createWidgetImage: DoughnutChartSvg,
        type: this,
        params: { chart_type: 'doughnut' },
        dropdownIcon: 'iconoir-pie-chart',
      },
    ]
  }

  getOrder() {
    return 10
  }

  isLoading(widget, data) {
    const dataSourceId = widget.data_source_id
    if (data[dataSourceId] && Object.keys(data[dataSourceId]).length !== 0) {
      return false
    }
    return true
  }
}
