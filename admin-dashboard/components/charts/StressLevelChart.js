import { useState, useEffect } from 'react';
import { Box, Text, Heading } from '@chakra-ui/react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export default function StressLevelChart({ userData, timeFrame }) {
  const [chartData, setChartData] = useState({
    labels: [],
    datasets: [],
  });

  useEffect(() => {
    if (!userData || userData.length === 0) return;

    // For this chart, we're looking at survey data that includes stress levels
    // This is simulated data since we don't have real surveys yet
    const userIds = userData.slice(0, 10).map(user => user.id.substring(0, 8) + '...'); // Get first 10 users
    
    // Randomly generate stress levels (1-5 scale) for before and after
    const beforeStressLevels = userIds.map(() => Math.floor(Math.random() * 3) + 3); // 3-5 range (higher stress)
    const afterStressLevels = userIds.map(() => Math.floor(Math.random() * 2) + 1); // 1-3 range (lower stress)

    setChartData({
      labels: userIds,
      datasets: [
        {
          label: 'Stress Level Before',
          data: beforeStressLevels,
          backgroundColor: 'rgba(237, 100, 166, 0.6)',
        },
        {
          label: 'Stress Level After',
          data: afterStressLevels,
          backgroundColor: 'rgba(72, 187, 120, 0.6)',
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
            return `Stress level: ${context.parsed.y} (1-5 scale)`;
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 5,
        title: {
          display: true,
          text: 'Stress Level (1-5)'
        },
        ticks: {
          stepSize: 1
        }
      },
      x: {
        title: {
          display: true,
          text: 'Users'
        }
      }
    }
  };

  return (
    <Box p={5} bg="white" borderRadius="lg" boxShadow="sm" h="400px">
      <Heading size="md" mb={4}>User Stress Levels: Before vs. After</Heading>
      {userData.length > 0 ? (
        <Bar data={chartData} options={options} />
      ) : (
        <Text mt={8} textAlign="center">No survey data available</Text>
      )}
    </Box>
  );
} 