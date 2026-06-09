import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

function SentimentChart({ data, theme = 'dark' }) {
    const chartRef = useRef(null);
    const chartInstance = useRef(null);

    useEffect(() => {
        if (!chartRef.current) return;

        if (!chartInstance.current) {
            chartInstance.current = echarts.init(chartRef.current, theme === 'dark' ? 'dark' : undefined);
        } else {
            chartInstance.current.dispose();
            chartInstance.current = echarts.init(chartRef.current, theme === 'dark' ? 'dark' : undefined);
        }

        const counts = { positive: 0, negative: 0, neutral: 0 };
        data.forEach((item) => {
            const s = item.data?.sentiment;
            if (s && Object.hasOwn(counts, s)) counts[s]++;
        });

        const total = Object.values(counts).reduce((a, b) => a + b, 0);
        const chartData = [
            { value: counts.positive, name: 'Positive', itemStyle: { color: '#22c55e' } },
            { value: counts.negative, name: 'Negative', itemStyle: { color: '#ef4444' } },
            { value: counts.neutral, name: 'Neutral', itemStyle: { color: '#71717a' } },
        ].filter((d) => d.value > 0);

        const borderColor = theme === 'dark' ? '#18181b' : '#ffffff';
        const textColor = theme === 'dark' ? '#a1a1aa' : '#52525b';

        chartInstance.current.setOption({
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'item',
                formatter: '{b}: {c} ({d}%)',
                backgroundColor: theme === 'dark' ? '#18181b' : '#fff',
                borderColor: '#27272a',
            },
            legend: {
                bottom: 0,
                left: 'center',
                icon: 'circle',
                itemWidth: 8,
                itemHeight: 8,
                textStyle: { color: textColor, fontSize: 11 },
            },
            series: [{
                name: 'Sentiment',
                type: 'pie',
                radius: ['52%', '72%'],
                center: ['50%', '44%'],
                avoidLabelOverlap: true,
                itemStyle: { borderRadius: 4, borderColor, borderWidth: 2 },
                label: { show: false },
                emphasis: {
                    scaleSize: 6,
                    itemStyle: { shadowBlur: 12, shadowColor: 'rgba(0,0,0,0.25)' },
                },
                data: chartData.length ? chartData : [{ value: 1, name: 'No data', itemStyle: { color: '#27272a' } }],
            }],
            graphic: total > 0 ? [{
                type: 'text',
                left: 'center',
                top: '38%',
                style: {
                    text: `${total}`,
                    fontSize: 28,
                    fontWeight: 700,
                    fill: theme === 'dark' ? '#fafafa' : '#09090b',
                    fontFamily: 'Inter',
                },
            }, {
                type: 'text',
                left: 'center',
                top: '48%',
                style: {
                    text: 'events',
                    fontSize: 11,
                    fill: textColor,
                    fontFamily: 'Inter',
                },
            }] : [],
        }, true);

        const onResize = () => chartInstance.current?.resize();
        window.addEventListener('resize', onResize);
        return () => window.removeEventListener('resize', onResize);
    }, [data, theme]);

    return <div ref={chartRef} className="chart-canvas" />;
}

export default SentimentChart;
