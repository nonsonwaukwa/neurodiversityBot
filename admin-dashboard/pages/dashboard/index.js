import { useEffect, useState } from 'react';
import { collection, getDocs, query, where } from 'firebase/firestore';
import { db } from '../../lib/firebase';
import DashboardLayout from '../../components/DashboardLayout';
import MetricCard from '../../components/MetricCard';
import CompletionRateChart from '../../components/charts/CompletionRateChart';
import StressLevelChart from '../../components/charts/StressLevelChart';
import { 
  Box, 
  Heading, 
  SimpleGrid, 
  Text, 
  Flex,
  Select,
  useColorModeValue,
} from '@chakra-ui/react';

export default function Dashboard() {
  const [metrics, setMetrics] = useState({
    totalUsers: 0,
    activeUsers: 0,
    averageCompletionRate: 0,
    averageStressLevel: 3.2, // Default value
  });
  
  const [userData, setUserData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeFrame, setTimeFrame] = useState('week');
  
  useEffect(() => {
    async function fetchDashboardData() {
      try {
        // Fetch all users
        const usersSnapshot = await getDocs(collection(db, 'instances/instance1/users'));
        const users = usersSnapshot.docs.map(doc => ({
          id: doc.id,
          ...doc.data()
        }));
        
        setUserData(users);
        
        // Calculate metrics
        const totalUsers = users.length;
        
        // Calculate active users (active in last 24 hours)
        const activeUsers = users.filter(user => {
          if (!user.last_interaction) return false;
          const lastActivity = new Date(user.last_interaction);
          const oneDayAgo = new Date();
          oneDayAgo.setDate(oneDayAgo.getDate() - 1);
          return lastActivity > oneDayAgo;
        }).length;
        
        // Calculate average completion rate
        let completionRateSum = 0;
        let completionRateCount = 0;
        
        users.forEach(user => {
          if (user.metrics && typeof user.metrics.completion_rate === 'number') {
            completionRateSum += user.metrics.completion_rate;
            completionRateCount++;
          }
        });
        
        const averageCompletionRate = completionRateCount > 0 ? 
          (completionRateSum / completionRateCount).toFixed(1) : 0;
        
        setMetrics({
          totalUsers,
          activeUsers,
          averageCompletionRate,
          averageStressLevel: 3.2 // Placeholder for survey data
        });
        
        setLoading(false);
      } catch (error) {
        console.error("Error fetching dashboard data:", error);
        setLoading(false);
      }
    }
    
    fetchDashboardData();
  }, []);

  const handleTimeFrameChange = (e) => {
    setTimeFrame(e.target.value);
  };

  return (
    <DashboardLayout>
      <Box mb={8}>
        <Heading mb={2}>Dashboard Overview</Heading>
        <Text color="gray.600">Monitor key metrics from your WhatsApp accountability system</Text>
      </Box>
      
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={6} mb={8}>
        <MetricCard 
          title="Total Users" 
          value={metrics.totalUsers} 
          icon="users" 
        />
        <MetricCard 
          title="Active Users (24h)" 
          value={metrics.activeUsers} 
          icon="userActive" 
        />
        <MetricCard 
          title="Avg. Completion Rate" 
          value={`${metrics.averageCompletionRate}%`} 
          icon="checkCircle" 
        />
        <MetricCard 
          title="Avg. Stress Level" 
          value={metrics.averageStressLevel} 
          icon="activity" 
        />
      </SimpleGrid>
      
      <Flex justifyContent="flex-end" mb={4}>
        <Box>
          <Select
            value={timeFrame}
            onChange={handleTimeFrameChange}
            size="sm"
            width="200px"
            bg="white"
          >
            <option value="day">Daily</option>
            <option value="week">Weekly</option>
            <option value="month">Monthly</option>
          </Select>
        </Box>
      </Flex>
      
      <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6} mb={8}>
        <CompletionRateChart userData={userData} timeFrame={timeFrame} />
        <StressLevelChart userData={userData} timeFrame={timeFrame} />
      </SimpleGrid>
      
      <Box
        p={5}
        bg="white"
        borderRadius="lg"
        boxShadow="sm"
        mb={8}
      >
        <Heading size="md" mb={4}>Recent Activity</Heading>
        {loading ? (
          <Text>Loading activity data...</Text>
        ) : userData.length === 0 ? (
          <Text>No recent activity found</Text>
        ) : (
          <Box>
            {/* Here you would map through recent user activities, but it's just a placeholder */}
            <Text color="gray.600">Recent user check-ins and task completions would appear here.</Text>
          </Box>
        )}
      </Box>
    </DashboardLayout>
  );
} 