import { useState, useEffect } from 'react';
import { Box } from '@chakra-ui/react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line, Bar, Pie } from 'react-chartjs-2';
import { format } from 'date-fns';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

// Line Chart Component
export function LineChart({ data, color = 'rgba(66, 153, 225, 1)', yAxisLabel = '' }) {
  const [chartData, setChartData] = useState({
    labels: [],
    datasets: [],
  });

  useEffect(() => {
    if (!data || data.length === 0) return;

    setChartData({
      labels: data.map(item => typeof item.x === 'string' ? item.x : format(new Date(item.x), 'MMM dd')),
      datasets: [
        {
          label: yAxisLabel,
          data: data.map(item => item.y),
          fill: false,
          backgroundColor: color.replace('1)', '0.2)'),
          borderColor: color,
          tension: 0.4,
        },
      ],
    });
  }, [data, color, yAxisLabel]);

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: !!yAxisLabel,
          text: yAxisLabel
        }
      }
    }
  };

  return <Line data={chartData} options={options} />;
}

// Bar Chart Component
export function BarChart({ data, color = 'rgba(66, 153, 225, 1)', yAxisLabel = '' }) {
  const [chartData, setChartData] = useState({
    labels: [],
    datasets: [],
  });

  useEffect(() => {
    if (!data || data.length === 0) return;

    setChartData({
      labels: data.map(item => typeof item.x === 'string' ? item.x : format(new Date(item.x), 'MMM dd')),
      datasets: [
        {
          label: yAxisLabel,
          data: data.map(item => item.y),
          backgroundColor: color.replace('1)', '0.6)'),
          borderColor: color,
          borderWidth: 1,
        },
      ],
    });
  }, [data, color, yAxisLabel]);

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: !!yAxisLabel,
          text: yAxisLabel
        }
      }
    }
  };

  return <Bar data={chartData} options={options} />;
}

// Pie Chart Component
export function PieChart({ data }) {
  const [chartData, setChartData] = useState({
    labels: [],
    datasets: [],
  });

  useEffect(() => {
    if (!data || data.length === 0) return;

    // Generate colors
    const generateColors = (count) => {
      const colors = [
        'rgba(255, 99, 132, 0.6)',
        'rgba(54, 162, 235, 0.6)',
        'rgba(255, 206, 86, 0.6)',
        'rgba(75, 192, 192, 0.6)',
        'rgba(153, 102, 255, 0.6)',
        'rgba(255, 159, 64, 0.6)',
        'rgba(199, 199, 199, 0.6)',
        'rgba(83, 102, 255, 0.6)',
      ];
      
      // If we need more colors than in our array, generate them
      if (count > colors.length) {
        for (let i = colors.length; i < count; i++) {
          const r = Math.floor(Math.random() * 255);
          const g = Math.floor(Math.random() * 255);
          const b = Math.floor(Math.random() * 255);
          colors.push(`rgba(${r}, ${g}, ${b}, 0.6)`);
        }
      }
      
      return colors.slice(0, count);
    };

    setChartData({
      labels: data.map(item => item.label || item.id),
      datasets: [
        {
          data: data.map(item => item.value),
          backgroundColor: generateColors(data.length),
          borderWidth: 1,
        },
      ],
    });
  }, [data]);

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right',
      },
    }
  };

  return <Pie data={chartData} options={options} />;
} 