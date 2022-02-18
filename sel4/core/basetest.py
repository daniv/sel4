import time
from typing import Literal

import pytest
from _pytest import unittest
from loguru import logger
from pydantic import Field, validate_arguments, PositiveInt, BaseModel
from rich.highlighter import ReprHighlighter

from sel4.utils.typeutils import OptionalFloat, OptionalInt, NoneStr
from .exceptions import TimeLimitExceededException

from ..conf import settings


class PytestUnitTestCase(unittest.UnitTestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._called_setup = False
        self._called_teardown = False
        from .runtime import runtime_store, start_time_ms, time_limit
        self.store: pytest.Stash = runtime_store
        self.slow_mode = self.config.getoption("slow_mode", False)

    def __get_new_timeout(self, timeout: OptionalInt = None) -> int:
        import math

        try:
            timeout_multiplier = float(self.config.getoption("timeout_multiplier", 1))
            if timeout_multiplier <= 0.5:
                timeout_multiplier = 0.5
            timeout = int(math.ceil(timeout_multiplier * timeout))
            return timeout
        except ArithmeticError | Exception:
            # Wrong data type for timeout_multiplier (expecting int or float)
            return timeout

    @validate_arguments
    def set_time_limit(self, time_limit: OptionalFloat = None):
        if time_limit:
            from .runtime import time_limit

            runtime_store[time_limit] = time_limit
        else:
            runtime_store[time_limit] = None
        current_time_limit = runtime_store[time_limit]
        if current_time_limit and current_time_limit > 0:
            self._time_limit = runtime_store[time_limit]
        else:
            self._time_limit = None
            runtime_store[time_limit] = None

    @validate_arguments
    def get_timeout(
            self,
            timeout: OptionalInt = None,
            default_tm: int = Field(strict=True, gt=0)
    ) -> int:
        if not timeout:
            return default_tm
        if self.config.getoption("timeout_multiplier", None) and timeout == default_tm:
            logger.debug("Recalculating new timeout")
            return self.__get_new_timeout(timeout)
        return timeout

    @staticmethod
    def get_beautiful_soup(source: str):
        """
        BeautifulSoup is a toolkit for dissecting an HTML document
        and extracting what you need. It's great for screen-scraping!
        See: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
        """
        from bs4 import BeautifulSoup
        logger.debug("Create instance of BeautifulSoup base on page source")
        soup = BeautifulSoup(source, "html.parser")
        return soup

    def _check_if_time_limit_exceeded(self):
        from .runtime import start_time_ms, time_limit
        if self.store.get(time_limit, None):
            _time_limit = self.store[time_limit]
            now_ms = int(time.time() * 1000)
            _start_time_ms = self.store[start_time_ms]
            time_limit_ms = int(_time_limit * 1000.0)

            if now_ms > _start_time_ms + time_limit_ms:
                display_time_limit = time_limit
                plural = "s"
                if float(int(time_limit)) == float(time_limit):
                    display_time_limit = int(time_limit)
                    if display_time_limit == 1:
                        plural = ""
                message = f"This test has exceeded the time limit of {display_time_limit} second{plural}!"
                message = "\n " + message
                raise TimeLimitExceededException(message)

    def sleep(self, seconds):
        from .runtime import time_limit
        limit = self.store.get(time_limit, None)
        if limit:
            time.sleep(seconds)
        elif seconds < 0.4:
            self._check_if_time_limit_exceeded()
            time.sleep(seconds)
            self._check_if_time_limit_exceeded()
        else:
            start_ms = time.time() * 1000.0
            stop_ms = start_ms + (seconds * 1000.0)
            for x in range(int(seconds * 5)):
                self._check_if_time_limit_exceeded()
                now_ms = time.time() * 1000.0
                if now_ms >= stop_ms:
                    break
                time.sleep(0.2)

    def _slow_mode_pause_if_active(self):
        if self.config.getoption("slow_mode", False):
            wait_time = settings.DEFAULT_DEMO_MODE_TIMEOUT
            if self.config.getoption("demo_sleep", False):
                wait_time = float(self.config.getoption("demo_sleep"))
            time.sleep(wait_time)

    def wait(self, seconds):
        """ Same as self.sleep() - Some JS frameworks use this method name. """
        self.sleep(seconds)


class DataCharts:
    def __init__(self):
        self._chart_data = {}
        self._chart_count = 0
        self._chart_label = {}
        self._chart_xcount = 0
        self._chart_first_series = {}
        self._chart_series_count = {}

    def create_pie_chart(self, chart_data: "ChartData"):
        """Creates a JavaScript pie chart using "HighCharts".
        @Params
        chart_name - If creating multiple charts,
                     use this to select which one.
        title - The title displayed for the chart.
        subtitle - The subtitle displayed for the chart.
        data_name - The series name. Useful for multi-series charts.
                    If no data_name, will default to using "Series 1".
        unit - The description label given to the chart's y-axis values.
        libs - The option to include Chart libraries (JS and CSS files).
               Should be set to True (default) for the first time creating
               a chart on a web page. If creating multiple charts on the
               same web page, you won't need to re-import the libraries
               when creating additional charts.
        labels - If True, displays labels on the chart for data points.
        legend - If True, displays the data point legend on the chart.
        """
        chart_data.style = "pie"
        self.__create_highchart(chart_data)

    def create_bar_chart(self, chart_data: "ChartData"):
        """Creates a JavaScript bar chart using "HighCharts".
        @Params
        chart_name - If creating multiple charts,
                     use this to select which one.
        title - The title displayed for the chart.
        subtitle - The subtitle displayed for the chart.
        data_name - The series name. Useful for multi-series charts.
                    If no data_name, will default to using "Series 1".
        unit - The description label given to the chart's y-axis values.
        libs - The option to include Chart libraries (JS and CSS files).
               Should be set to True (default) for the first time creating
               a chart on a web page. If creating multiple charts on the
               same web page, you won't need to re-import the libraries
               when creating additional charts.
        labels - If True, displays labels on the chart for data points.
        legend - If True, displays the data point legend on the chart.
        """
        chart_data.style = "bar"
        self.__create_highchart(chart_data)

    def create_column_chart(self, chart_data: "ChartData"):
        """Creates a JavaScript column chart using "HighCharts".
        @Params
        chart_name - If creating multiple charts,
                     use this to select which one.
        title - The title displayed for the chart.
        subtitle - The subtitle displayed for the chart.
        data_name - The series name. Useful for multi-series charts.
                    If no data_name, will default to using "Series 1".
        unit - The description label given to the chart's y-axis values.
        libs - The option to include Chart libraries (JS and CSS files).
               Should be set to True (default) for the first time creating
               a chart on a web page. If creating multiple charts on the
               same web page, you won't need to re-import the libraries
               when creating additional charts.
        labels - If True, displays labels on the chart for data points.
        legend - If True, displays the data point legend on the chart.
        """
        chart_data.style = "column"
        self.__create_highchart(chart_data)

    def create_line_chart(self, chart_data: "ChartData"):
        """Creates a JavaScript line chart using "HighCharts".
        @Params
        chart_name - If creating multiple charts,
                     use this to select which one.
        title - The title displayed for the chart.
        subtitle - The subtitle displayed for the chart.
        data_name - The series name. Useful for multi-series charts.
                    If no data_name, will default to using "Series 1".
        unit - The description label given to the chart's y-axis values.
        zero - If True, the y-axis always starts at 0. (Default: False).
        libs - The option to include Chart libraries (JS and CSS files).
               Should be set to True (default) for the first time creating
               a chart on a web page. If creating multiple charts on the
               same web page, you won't need to re-import the libraries
               when creating additional charts.
        labels - If True, displays labels on the chart for data points.
        legend - If True, displays the data point legend on the chart.
        """
        chart_data.style = "line"
        self._create_highchart(chart_data)

    def create_area_chart(self, chart_data: "ChartData"):
        """Creates a JavaScript area chart using "HighCharts".
        @Params
        chart_name - If creating multiple charts,
                     use this to select which one.
        title - The title displayed for the chart.
        subtitle - The subtitle displayed for the chart.
        data_name - The series name. Useful for multi-series charts.
                    If no data_name, will default to using "Series 1".
        unit - The description label given to the chart's y-axis values.
        zero - If True, the y-axis always starts at 0. (Default: False).
        libs - The option to include Chart libraries (JS and CSS files).
               Should be set to True (default) for the first time creating
               a chart on a web page. If creating multiple charts on the
               same web page, you won't need to re-import the libraries
               when creating additional charts.
        labels - If True, displays labels on the chart for data points.
        legend - If True, displays the data point legend on the chart.
        """
        chart_data.style = "area"
        self._create_highchart(chart_data)

    def _create_highchart(self, chart_data: "ChartData"):
        """ Creates a JavaScript chart using the "HighCharts" library. """

        chart_data.title = chart_data.title.replace("'", "\\'")
        chart_data.subtitle = chart_data.subtitle.replace("'", "\\'")
        chart_data.unit = chart_data.unit.replace("'", "\\'")
        self._chart_count += 1
        # If chart_libs format is changed, also change: save_presentation()
        chart_libs = """
               <script src="%s"></script>
               <script src="%s"></script>
               <script src="%s"></script>
               <script src="%s"></script>
               """ % (
            constants.HighCharts.HC_JS,
            constants.HighCharts.EXPORTING_JS,
            constants.HighCharts.EXPORT_DATA_JS,
            constants.HighCharts.ACCESSIBILITY_JS,
        )
        if not libs:
            chart_libs = ""
        chart_css = """
               <style>
               .highcharts-figure, .highcharts-data-table table {
                   min-width: 320px;
                   max-width: 660px;
                   margin: 1em auto;
               }
               .highcharts-data-table table {
                   font-family: Verdana, sans-serif;
                   border-collapse: collapse;
                   border: 1px solid #EBEBEB;
                   margin: 10px auto;
                   text-align: center;
                   width: 100%;
                   max-width: 500px;
               }
               .highcharts-data-table caption {
                   padding: 1em 0;
                   font-size: 1.2em;
                   color: #555;
               }
               .highcharts-data-table th {
                   font-weight: 600;
                   padding: 0.5em;
               }
               .highcharts-data-table td, .highcharts-data-table th,
               .highcharts-data-table caption {
                   padding: 0.5em;
               }
               .highcharts-data-table thead tr,
               .highcharts-data-table tr:nth-child(even) {
                   background: #f8f8f8;
               }
               .highcharts-data-table tr:hover {
                   background: #f1f7ff;
               }
               </style>
               """
        if not libs:
            chart_css = ""
        chart_description = ""
        chart_figure = """
               <figure class="highcharts-figure">
                   <div id="chartcontainer_num_%s"></div>
                   <p class="highcharts-description">%s</p>
               </figure>
               """ % (
            self._chart_count,
            chart_description,
        )
        min_zero = ""
        if zero:
            min_zero = "min: 0,"
        chart_init_1 = """
               <script>
               // Build the chart
               Highcharts.chart('chartcontainer_num_%s', {
               credits: {
                   enabled: false
               },
               title: {
                   text: '%s'
               },
               subtitle: {
                   text: '%s'
               },
               xAxis: { },
               yAxis: {
                   %s
                   title: {
                       text: '%s',
                       style: {
                           fontSize: '14px'
                       }
                   },
                   labels: {
                       useHTML: true,
                       style: {
                           fontSize: '14px'
                       }
                   }
               },
               chart: {
                   renderTo: 'statusChart',
                   plotBackgroundColor: null,
                   plotBorderWidth: null,
                   plotShadow: false,
                   type: '%s'
               },
               """ % (
            self._chart_count,
            title,
            subtitle,
            min_zero,
            unit,
            style,
        )
        #  "{series.name}:"
        point_format = (
            r"<b>{point.y}</b><br />" r"<b>{point.percentage:.1f}%</b>"
        )
        if chart_data.style != "pie":
            point_format = r"<b>{point.y}</b>"
        chart_init_2 = (
                """
                tooltip: {
                    enabled: true,
                    useHTML: true,
                    style: {
                        padding: '6px',
                        fontSize: '14px'
                    },
                    backgroundColor: {
                        linearGradient: {
                            x1: 0,
                            y1: 0,
                            x2: 0,
                            y2: 1
                        },
                        stops: [
                            [0, 'rgba(255, 255, 255, 0.78)'],
                            [0.5, 'rgba(235, 235, 235, 0.76)'],
                            [1, 'rgba(244, 252, 255, 0.74)']
                        ]
                    },
                    hideDelay: 40,
                    pointFormat: '%s'
                },
                """
                % point_format
        )
        chart_init_3 = """
               accessibility: {
                   point: {
                       valueSuffix: '%%'
                   }
               },
               plotOptions: {
                   series: {
                       states: {
                           inactive: {
                               opacity: 0.85
                           }
                       }
                   },
                   pie: {
                       size: "95%%",
                       allowPointSelect: true,
                       animation: false,
                       cursor: 'pointer',
                       dataLabels: {
                           enabled: %s,
                           formatter: function() {
                             if (this.y > 0) {
                               return this.point.name + ': ' + this.point.y
                             }
                           }
                       },
                       states: {
                           hover: {
                               enabled: true
                           }
                       },
                       showInLegend: %s
                   }
               },
               """ % (
            chart_data.labels,
            chart_data.legend,
        )
        if chart_data.style != "pie":
            chart_init_3 = """
                   allowPointSelect: true,
                   cursor: 'pointer',
                   legend: {
                       layout: 'vertical',
                       align: 'right',
                       verticalAlign: 'middle'
                   },
                   states: {
                       hover: {
                           enabled: true
                       }
                   },
                   plotOptions: {
                       series: {
                           dataLabels: {
                               enabled: %s
                           },
                           showInLegend: %s,
                           animation: false,
                           shadow: false,
                           lineWidth: 3,
                           fillOpacity: 0.5,
                           marker: {
                               enabled: true
                           }
                       }
                   },
                   """ % (
                chart_data.labels,
                chart_data.legend,
            )
        chart_init = chart_init_1 + chart_init_2 + chart_init_3
        color_by_point = "true"
        if chart_data.style != "pie":
            color_by_point = "false"
        series = """
               series: [{
               name: '%s',
               colorByPoint: %s,
               data: [
               """ % (
            data_name,
            color_by_point,
        )
        new_chart = chart_libs + chart_css + chart_figure + chart_init + series
        self._chart_data[chart_data.chart_name] = []
        self._chart_label[chart_data.chart_name] = []
        self._chart_data[chart_data.chart_name].append(new_chart)
        self._chart_first_series[chart_data.chart_name] = True
        self._chart_series_count[chart_data.chart_name] = 1

    def add_series_to_chart(self, data_name=None, chart_name=None):
        """Add a new data series to an existing chart.
        This allows charts to have multiple data sets.
        @Params
        data_name - Set the series name. Useful for multi-series charts.
        chart_name - If creating multiple charts,
                     use this to select which one.
        """
        if not chart_name:
            chart_name = "default"
        self._chart_series_count[chart_name] += 1
        if not data_name:
            data_name = "Series %s" % self._chart_series_count[chart_name]
        series = (
                """
                ]
                },
                {
                name: '%s',
                colorByPoint: false,
                data: [
                """
                % data_name
        )
        self._chart_data[chart_name].append(series)
        self._chart_first_series[chart_name] = False

    def add_data_point(self, label, value, color=None, chart_name=None):
        """Add a data point to a SeleniumBase-generated chart.
        @Params
        label - The label name for the data point.
        value - The numeric value of the data point.
        color - The HTML color of the data point.
                Can be an RGB color. Eg: "#55ACDC".
                Can also be a named color. Eg: "Teal".
        chart_name - If creating multiple charts,
                     use this to select which one.
        """
        if not chart_name:
            chart_name = "default"
        if chart_name not in self._chart_data:
            # Create a chart if it doesn't already exist
            self.create_pie_chart(chart_name=chart_name)
        if not value:
            value = 0
        if not type(value) is int and not type(value) is float:
            raise Exception('Expecting a numeric value for "value"!')
        if not color:
            color = ""
        label = label.replace("'", "\\'")
        color = color.replace("'", "\\'")
        data_point = """
               {
               name: '%s',
               y: %s,
               color: '%s'
               },
               """ % (
            label,
            value,
            color,
        )
        self._chart_data[chart_name].append(data_point)
        if self._chart_first_series[chart_name]:
            self._chart_label[chart_name].append(label)

    def save_chart(self, chart_name=None, filename=None, folder=None):
        """Saves a SeleniumBase-generated chart to a file for later use.
        @Params
        chart_name - If creating multiple charts at the same time,
                     use this to select the one you wish to use.
        filename - The name of the HTML file that you wish to
                   save the chart to. (filename must end in ".html")
        folder - The name of the folder where you wish to
                 save the HTML file. (Default: "./saved_charts/")
        """
        if not chart_name:
            chart_name = "default"
        if not filename:
            filename = "my_chart.html"
        if chart_name not in self._chart_data:
            raise Exception("Chart {%s} does not exist!" % chart_name)
        if not filename.endswith(".html"):
            raise Exception('Chart file must end in ".html"!')
        the_html = '<meta charset="utf-8">\n'
        the_html += '<meta http-equiv="Content-Type" content="text/html">\n'
        the_html += '<meta name="viewport" content="shrink-to-fit=no">\n'
        for chart_data_point in self._chart_data[chart_name]:
            the_html += chart_data_point
        the_html += """
               ]
                   }]
               });
               </script>
               """
        axis = "xAxis: {\n"
        axis += "                labels: {\n"
        axis += "                    useHTML: true,\n"
        axis += "                    style: {\n"
        axis += "                        fontSize: '14px',\n"
        axis += "                    },\n"
        axis += "                },\n"
        axis += "            categories: ["
        for label in self._chart_label[chart_name]:
            axis += "'%s'," % label
        axis += "], crosshair: false},"
        the_html = the_html.replace("xAxis: { },", axis)
        if not folder:
            saved_charts_folder = constants.Charts.SAVED_FOLDER
        else:
            saved_charts_folder = folder
        if saved_charts_folder.endswith("/"):
            saved_charts_folder = saved_charts_folder[:-1]
        if not os.path.exists(saved_charts_folder):
            try:
                os.makedirs(saved_charts_folder)
            except Exception:
                pass
        file_path = saved_charts_folder + "/" + filename
        out_file = codecs.open(file_path, "w+", encoding="utf-8")
        out_file.writelines(the_html)
        out_file.close()
        print("\n>>> [%s] was saved!" % file_path)
        return file_path

    def display_chart(self, chart_name=None, filename=None, interval=0):
        """Displays a SeleniumBase-generated chart in the browser window.
        @Params
        chart_name - If creating multiple charts at the same time,
                     use this to select the one you wish to use.
        filename - The name of the HTML file that you wish to
                   save the chart to. (filename must end in ".html")
        interval - The delay time for auto-advancing charts. (in seconds)
                   If set to 0 (default), auto-advancing is disabled.
        """
        if self.headless or self.xvfb:
            interval = 1  # Race through chart if running in headless mode
        if not chart_name:
            chart_name = "default"
        if not filename:
            filename = "my_chart.html"
        if not interval:
            interval = 0
        if interval == 0 and self.interval:
            interval = float(self.interval)
        if not type(interval) is int and not type(interval) is float:
            raise Exception('Expecting a numeric value for "interval"!')
        if interval < 0:
            raise Exception('The "interval" cannot be a negative number!')
        if chart_name not in self._chart_data:
            raise Exception("Chart {%s} does not exist!" % chart_name)
        if not filename.endswith(".html"):
            raise Exception('Chart file must end in ".html"!')
        file_path = self.save_chart(chart_name=chart_name, filename=filename)
        self.open_html_file(file_path)
        chart_folder = constants.Charts.SAVED_FOLDER
        if interval == 0:
            try:
                print("\n*** Close the browser window to continue ***")
                # Will also continue if manually navigating to a new page
                while len(self.driver.window_handles) > 0 and (
                        chart_folder in self.get_current_url()
                ):
                    time.sleep(0.05)
            except Exception:
                pass
        else:
            try:
                start_ms = time.time() * 1000.0
                stop_ms = start_ms + (interval * 1000.0)
                for x in range(int(interval * 10)):
                    now_ms = time.time() * 1000.0
                    if now_ms >= stop_ms:
                        break
                    if len(self.driver.window_handles) == 0:
                        break
                    if chart_folder not in self.get_current_url():
                        break
                    time.sleep(0.1)
            except Exception:
                pass

    def extract_chart(self, chart_name=None):
        """Extracts the HTML from a SeleniumBase-generated chart.
        @Params
        chart_name - If creating multiple charts at the same time,
                     use this to select the one you wish to use.
        """
        if not chart_name:
            chart_name = "default"
        if chart_name not in self._chart_data:
            raise Exception("Chart {%s} does not exist!" % chart_name)
        the_html = ""
        for chart_data_point in self._chart_data[chart_name]:
            the_html += chart_data_point
        the_html += """
               ]
                   }]
               });
               </script>
               """
        axis = "xAxis: {\n"
        axis += "                labels: {\n"
        axis += "                    useHTML: true,\n"
        axis += "                    style: {\n"
        axis += "                        fontSize: '14px',\n"
        axis += "                    },\n"
        axis += "                },\n"
        axis += "            categories: ["
        for label in self._chart_label[chart_name]:
            axis += "'%s'," % label
        axis += "], crosshair: false},"
        the_html = the_html.replace("xAxis: { },", axis)
        self._chart_xcount += 1
        the_html = the_html.replace(
            "chartcontainer_num_", "chartcontainer_%s_" % self._chart_xcount
        )
        return the_html


class ChartData(BaseModel):
    chart_name: str = "default",
    style: Literal["pie", "bar", "column", "line", "area"] = "pie"
    title: NoneStr = "",
    subtitle: NoneStr = "",
    data_name: str = "Series 1",
    unit: NoneStr = "Values",
    libs: bool = True,
    labels: bool = True,
    legend: bool = True,
    zero: bool = False,



class BasePytestUnitTestCase(unittest.UnitTestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._highlighter = ReprHighlighter()

        self._is_timeout_changed = False
        self._time_limit: OptionalFloat = None
        self._start_time_ms: OptionalInt = None

        self.__deferred_assert_count = 0
        self.__deferred_assert_failures = []
        self.__visual_baseline_copies = []




