import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

const PALETTE = {
    dark: { cpu: '#3b82f6', memory: '#22c55e', disk: '#f59e0b', network: '#ef4444', grid: '#27272a', text: '#71717a' },
    light: { cpu: '#2563eb', memory: '#16a34a', disk: '#d97706', network: '#dc2626', grid: '#e4e4e7', text: '#a1a1aa' },
};

function MetricsChart({ data, theme = 'dark' }) {
    const chartRef = useRef(null);
    const chartInstance = useRef(null);
    const colors = PALETTE[theme] || PALETTE.dark;

    useEffect(() => {
        if (!chartRef.current) return;

        if (!chartInstance.current) {
            chartInstance.current = echarts.init(chartRef.current, theme === 'dark' ? 'dark' : undefined);
        } else {
            chartInstance.current.dispose();
            chartInstance.current = echarts.init(chartRef.current, theme === 'dark' ? 'dark' : undefined);
        }

        const metricsByType = { cpu: [], memory: [], disk: [], network: [] };

        data.forEach((item) => {
            const metricType = item.data?.metric_type;
            const value = item.data?.value;
            const timestamp = item.data?.timestamp || item.timestamp;
            if (metricType && value !== undefined && timestamp && metricsByType[metricType]) {
                metricsByType[metricType].push({ time: new Date(timestamp).getTime(), value });
            }
        });

        const series = Object.entries(metricsByType)
            .filter(([, values]) => values.length > 0)
            .map(([type, values]) => ({
                name: type.toUpperCase(),
                type: 'line',
                smooth: 0.35,
                symbol: 'none',
                lineStyle: { width: 2, color: colors[type] },
                itemStyle: { color: colors[type] },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: colors[type] + '30' },
                        { offset: 1, color: colors[type] + '05' },
                    ]),
                },
                data: values.map((v) => [v.time, v.value]),
            }));

        chartInstance.current.setOption({
            backgroundColor: 'transparent',
            animation: true,
            animationDuration: 400,
            tooltip: {
                trigger: 'axis',
                backgroundColor: theme === 'dark' ? '#18181b' : '#fff',
                borderColor: colors.grid,
                textStyle: { color: theme === 'dark' ? '#fafafa' : '#09090b', fontSize: 12 },
                formatter(params) {
                    let out = `<span style="font-family:monospace;font-size:11px">${new Date(params[0].value[0]).toLocaleTimeString()}</span><br/>`;
                    params.forEach((p) => {
                        const unit = p.seriesName === 'NETWORK' ? ' MB/s' : '%';
                        out += `${p.marker} ${p.seriesName}: <b>${p.value[1].toFixed(1)}${unit}</b><br/>`;
                    });
                    return out;
                },
            },
            legend: {
                top: 0,
                right: 0,
                icon: 'roundRect',
                itemWidth: 12,
                itemHeight: 3,
                textStyle: { color: colors.text, fontSize: 11 },
            },
            grid: { left: 48, right: 16, bottom: 28, top: 36 },
            xAxis: {
                type: 'time',
                boundaryGap: false,
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: { color: colors.text, fontSize: 10, fontFamily: 'JetBrains Mono' },
                splitLine: { show: false },
            },
            yAxis: {
                type: 'value',
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: { color: colors.text, fontSize: 10, fontFamily: 'JetBrains Mono' },
                splitLine: { lineStyle: { color: colors.grid, type: 'dashed' } },
            },
            series,
        }, true);

        const onResize = () => chartInstance.current?.resize();
        window.addEventListener('resize', onResize);
        return () => window.removeEventListener('resize', onResize);
    }, [data, theme, colors]);

    return <div ref={chartRef} className="chart-canvas" />;
}

export default MetricsChart;
