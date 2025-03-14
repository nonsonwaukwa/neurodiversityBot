import { useState, useEffect } from 'react';
import { Box, Text, Heading } from '@chakra-ui/react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { format, subDays } from 'date-fns';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

export default function CompletionRateChart({ userData, timeFrame }) {
  const [chartData, setChartData] = useState({
    labels: [],
    datasets: [],
  });

  useEffect(() => {
    if (!userData || userData.length === 0) return;

    // Calculate date range based on timeFrame
    const today = new Date();
    let daysToLookBack;
    
    switch (timeFrame) {
      case 'day':
        daysToLookBack = 7; // Last week daily
        break;
      case 'week':
        daysToLookBack = 28; // Last 4 weeks
        break;
      case 'month':
        daysToLookBack = 90; // Last 3 months
        break;
      default:
        daysToLookBack = 7;
    }

    // Generate date labels
    const dates = Array.from({ length: daysToLookBack }, (_, i) => {
      const date = subDays(today, daysToLookBack - i - 1);
      return format(date, 'MMM dd');
    });

    // Calculate completion rate per day
    // This is simulated data since we don't have real historical data
    // In a real implementation, you would aggregate actual user data
    const completionRates = dates.map(() => Math.floor(Math.random() * 40) + 60); // Random 60-100%

    setChartData({
      labels: dates,
      datasets: [
        {
          label: 'Task Completion Rate (%)',
          data: completionRates,
          fill: false,
          backgroundColor: 'rgba(66, 153, 225, 0.5)',
          borderColor: 'rgba(66, 153, 225, 1)',
          tension: 0.4,
        },
      ],
    });
  }, [userData, timeFrame]);

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            return `Completion rate: ${context.parsed.y}%`;
          }
        }
      }
    },
    scales: {
      y: {
        min: 0,
        max: 100,
        ticks: {
          callback: function(value) {
            return value + '%';
          }
        }
      }
    }
  };

  return (
    <Box p={5} bg="white" borderRadius="lg" boxShadow="sm" h="400px">
      <Heading size="md" mb={4}>Task Completion Rate Over Time</Heading>
      {userData.length > 0 ? (
        <Line data={chartData} options={options} />
      ) : (
        <Text mt={8} textAlign="center">No data available</Text>
      )}
    </Box>
  );
} 