import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

function MetricsChart({ data }) {
    const chartRef = useRef(null);
    const chartInstance = useRef(null);

    useEffect(() => {
        if (!chartRef.current) return;

        // Initialize chart
        if (!chartInstance.current) {
            chartInstance.current = echarts.init(chartRef.current, 'dark');
        }

        // Process data by metric type
        const metricsByType = {
            cpu: [],
            memory: [],
            disk: [],
            network: []
        };

        data.forEach(item => {
            const metricType = item.data?.metric_type;
            const value = item.data?.value;
            const timestamp = item.data?.timestamp || item.timestamp;

            if (metricType && value !== undefined && timestamp) {
                metricsByType[metricType]?.push({
                    time: new Date(timestamp).getTime(),
                    value: value
                });
            }
        });

        // Prepare series data
        const series = [];
        const colors = {
            cpu: '#5470c6',
            memory: '#91cc75',
            disk: '#fac858',
            network: '#ee6666'
        };

        Object.entries(metricsByType).forEach(([type, values]) => {
            if (values.length > 0) {
                series.push({
                    name: type.toUpperCase(),
                    type: 'line',
                    smooth: true,
                    symbol: 'circle',
                    symbolSize: 6,
                    lineStyle: {
                        width: 2,
                        color: colors[type]
                    },
                    itemStyle: {
                        color: colors[type]
                    },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: colors[type] + '40' },
                            { offset: 1, color: colors[type] + '10' }
                        ])
                    },
                    data: values.map(v => [v.time, v.value])
                });
            }
        });

        // Chart options
        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross',
                    label: {
                        backgroundColor: '#6a7985'
                    }
                },
                formatter: function (params) {
                    let result = new Date(params[0].value[0]).toLocaleTimeString() + '<br/>';
                    params.forEach(param => {
                        const unit = param.seriesName === 'NETWORK' ? ' MB/s' : '%';
                        result += `${param.marker} ${param.seriesName}: ${param.value[1].toFixed(2)}${unit}<br/>`;
                    });
                    return result;
                }
            },
            legend: {
                data: ['CPU', 'MEMORY', 'DISK', 'NETWORK'],
                textStyle: {
                    color: '#ccc'
                },
                top: 10
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                top: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'time',
                boundaryGap: false,
                axisLine: {
                    lineStyle: {
                        color: '#555'
                    }
                },
                axisLabel: {
                    color: '#999',
                    formatter: function (value) {
                        return new Date(value).toLocaleTimeString();
                    }
                }
            },
            yAxis: {
                type: 'value',
                name: 'Value',
                nameTextStyle: {
                    color: '#999'
                },
                axisLine: {
                    lineStyle: {
                        color: '#555'
                    }
                },
                axisLabel: {
                    color: '#999'
                },
                splitLine: {
                    lineStyle: {
                        color: '#333'
                    }
                }
            },
            series: series
        };

        chartInstance.current.setOption(option);

        // Resize handler
        const handleResize = () => {
            chartInstance.current?.resize();
        };
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
        };
    }, [data]);

    return (
        <div
            ref={chartRef}
            style={{ width: '100%', height: '400px' }}
        />
    );
}

export default MetricsChart;
