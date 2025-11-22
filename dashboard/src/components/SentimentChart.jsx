import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

function SentimentChart({ data }) {
    const chartRef = useRef(null);
    const chartInstance = useRef(null);

    useEffect(() => {
        if (!chartRef.current) return;

        // Initialize chart
        if (!chartInstance.current) {
            chartInstance.current = echarts.init(chartRef.current, 'dark');
        }

        // Count sentiments
        const sentimentCounts = {
            positive: 0,
            negative: 0,
            neutral: 0
        };

        data.forEach(item => {
            const sentiment = item.data?.sentiment;
            if (sentiment && sentimentCounts.hasOwnProperty(sentiment)) {
                sentimentCounts[sentiment]++;
            }
        });

        // Prepare chart data
        const chartData = [
            { value: sentimentCounts.positive, name: 'Positive', itemStyle: { color: '#91cc75' } },
            { value: sentimentCounts.negative, name: 'Negative', itemStyle: { color: '#ee6666' } },
            { value: sentimentCounts.neutral, name: 'Neutral', itemStyle: { color: '#fac858' } }
        ];

        // Chart options
        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'item',
                formatter: '{a} <br/>{b}: {c} ({d}%)'
            },
            legend: {
                orient: 'vertical',
                left: 'left',
                textStyle: {
                    color: '#ccc'
                },
                data: ['Positive', 'Negative', 'Neutral']
            },
            series: [
                {
                    name: 'Sentiment',
                    type: 'pie',
                    radius: ['40%', '70%'],
                    center: ['60%', '50%'],
                    avoidLabelOverlap: false,
                    itemStyle: {
                        borderRadius: 10,
                        borderColor: '#1a1a1a',
                        borderWidth: 2
                    },
                    label: {
                        show: true,
                        formatter: '{b}\n{d}%',
                        color: '#ccc'
                    },
                    emphasis: {
                        label: {
                            show: true,
                            fontSize: 16,
                            fontWeight: 'bold'
                        },
                        itemStyle: {
                            shadowBlur: 10,
                            shadowOffsetX: 0,
                            shadowColor: 'rgba(0, 0, 0, 0.5)'
                        }
                    },
                    labelLine: {
                        show: true,
                        lineStyle: {
                            color: '#555'
                        }
                    },
                    data: chartData
                }
            ]
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

export default SentimentChart;
