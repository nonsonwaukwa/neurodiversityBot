import { useState, useEffect } from 'react';
import { 
  Box, 
  Heading, 
  SimpleGrid, 
  Stat, 
  StatLabel, 
  StatNumber, 
  StatHelpText, 
  Tabs, 
  TabList, 
  TabPanels, 
  Tab, 
  TabPanel,
  Flex,
  Select,
  Button,
  useToast,
  Spinner,
  Text
} from '@chakra-ui/react';
import { FiUsers, FiMessageCircle, FiCheckCircle, FiPieChart } from 'react-icons/fi';
import DashboardLayout from '../components/DashboardLayout';
import { LineChart, BarChart, PieChart } from '../components/Charts';
import { collection, getDocs, query, where, orderBy } from 'firebase/firestore';
import { db } from '../lib/firebase';
import { safeFormatDate } from '../utils/dateUtils';

// Function to generate mock data for the charts
function generateMockData() {
  const userGrowth = [];
  const messageVolume = [];
  const completionRates = [];
  const daysOfWeek = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  
  // Generate last 30 days of data for user growth
  for (let i = 29; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    
    userGrowth.push({
      x: safeFormatDate(date, 'MMM dd'),
      y: Math.floor(100 + Math.random() * i * 4)
    });
  }
  
  // Generate data for daily message volume
  for (let i = 0; i < 7; i++) {
    messageVolume.push({
      x: daysOfWeek[i],
      y: Math.floor(50 + Math.random() * 100)
    });
  }
  
  // Generate data for completion rates over time
  for (let i = 29; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    
    completionRates.push({
      x: safeFormatDate(date, 'MMM dd'),
      y: Math.floor(60 + Math.random() * 30)
    });
  }
  
  // Topics data for pie chart
  const topicsData = [
    { name: 'Stress Management', value: 35 },
    { name: 'Routines', value: 25 },
    { name: 'School Work', value: 20 },
    { name: 'Social Interactions', value: 15 },
    { name: 'Other', value: 5 }
  ];
  
  return { userGrowth, messageVolume, completionRates, topicsData };
}

export default function AnalyticsPage() {
  const toast = useToast();
  const [activeUserCount, setActiveUserCount] = useState(0);
  const [totalMessageCount, setTotalMessageCount] = useState(0);
  const [avgCompletionRate, setAvgCompletionRate] = useState(0);
  const [instanceFilter, setInstanceFilter] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  
  // Charts data
  const [chartData, setChartData] = useState(() => generateMockData());
  
  useEffect(() => {
    async function fetchAnalyticsData() {
      setIsLoading(true);
      try {
        // Query users collection with instance filter if not "all"
        let usersQuery;
        
        if (instanceFilter === 'all') {
          usersQuery = query(collection(db, 'users'));
        } else {
          usersQuery = query(
            collection(db, 'users'),
            where('instance', '==', instanceFilter)
          );
        }
        
        const usersSnapshot = await getDocs(usersQuery);
        const users = usersSnapshot.docs.map(doc => ({
          id: doc.id,
          ...doc.data()
        }));
        
        // Count active users
        const activeUsers = users.filter(user => user.active);
        setActiveUserCount(activeUsers.length);
        
        // Calculate average completion rate
        let totalCompletionRate = 0;
        let usersWithCompletionRate = 0;
        
        users.forEach(user => {
          if (user.metrics && typeof user.metrics.completion_rate === 'number') {
            totalCompletionRate += user.metrics.completion_rate;
            usersWithCompletionRate++;
          }
        });
        
        const avgRate = usersWithCompletionRate > 0
          ? totalCompletionRate / usersWithCompletionRate
          : 0;
        
        setAvgCompletionRate(avgRate);
        
        // For message count, we would typically query a messages collection
        // For now, let's use a mock value
        setTotalMessageCount(users.length * 12); // Just an estimate
        
        // In a real implementation, we would fetch time-series data
        // For the demo, we'll use the mock data from generateMockData
        setChartData(generateMockData());
        
        setIsLoading(false);
      } catch (error) {
        console.error('Error fetching analytics data:', error);
        setIsLoading(false);
        
        toast({
          title: 'Error loading analytics',
          description: error.message,
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      }
    }
    
    fetchAnalyticsData();
  }, [toast, instanceFilter]);
  
  return (
    <DashboardLayout>
      <Box p={4}>
        <Flex justify="space-between" align="center" mb={6}>
          <Heading size="lg">Analytics Dashboard</Heading>
          <Flex>
            <Select 
              value={instanceFilter}
              onChange={(e) => setInstanceFilter(e.target.value)}
              w="200px"
              mr={3}
            >
              <option value="all">All Instances</option>
              <option value="instance1">Instance 1</option>
              <option value="instance2">Instance 2</option>
            </Select>
            <Button
              onClick={() => fetchAnalyticsData()}
              isLoading={isLoading}
              loadingText="Refreshing"
            >
              Refresh
            </Button>
          </Flex>
        </Flex>
        
        {isLoading ? (
          <Flex justify="center" align="center" h="200px">
            <Spinner mr={3} />
            <Text>Loading analytics data...</Text>
          </Flex>
        ) : (
          <>
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6} mb={6}>
              <Stat bg="white" p={4} borderRadius="lg" shadow="sm">
                <Flex align="center">
                  <Box
                    bg="blue.50"
                    p={2}
                    borderRadius="md"
                    color="blue.500"
                    mr={3}
                  >
                    <FiUsers size={24} />
                  </Box>
                  <Box>
                    <StatLabel>Active Users</StatLabel>
                    <StatNumber>{activeUserCount}</StatNumber>
                    <StatHelpText>From {instanceFilter === 'all' ? 'all instances' : instanceFilter}</StatHelpText>
                  </Box>
                </Flex>
              </Stat>
              
              <Stat bg="white" p={4} borderRadius="lg" shadow="sm">
                <Flex align="center">
                  <Box
                    bg="green.50"
                    p={2}
                    borderRadius="md"
                    color="green.500"
                    mr={3}
                  >
                    <FiMessageCircle size={24} />
                  </Box>
                  <Box>
                    <StatLabel>Total Messages</StatLabel>
                    <StatNumber>{totalMessageCount.toLocaleString()}</StatNumber>
                    <StatHelpText>Messages exchanged</StatHelpText>
                  </Box>
                </Flex>
              </Stat>
              
              <Stat bg="white" p={4} borderRadius="lg" shadow="sm">
                <Flex align="center">
                  <Box
                    bg="purple.50"
                    p={2}
                    borderRadius="md"
                    color="purple.500"
                    mr={3}
                  >
                    <FiCheckCircle size={24} />
                  </Box>
                  <Box>
                    <StatLabel>Avg. Completion Rate</StatLabel>
                    <StatNumber>{avgCompletionRate.toFixed(1)}%</StatNumber>
                    <StatHelpText>Tasks completed</StatHelpText>
                  </Box>
                </Flex>
              </Stat>
            </SimpleGrid>
            
            <Tabs variant="enclosed" colorScheme="blue" bg="white" p={4} borderRadius="lg" shadow="sm">
              <TabList>
                <Tab>Trends</Tab>
                <Tab>Usage</Tab>
                <Tab>Topics</Tab>
              </TabList>
              
              <TabPanels>
                <TabPanel>
                  <Box h="400px">
                    <Heading size="md" mb={4}>User Growth Over Time</Heading>
                    <LineChart
                      data={chartData.userGrowth}
                      color="blue.500"
                      yAxisLabel="User Count"
                    />
                  </Box>
                </TabPanel>
                
                <TabPanel>
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                    <Box h="300px">
                      <Heading size="md" mb={4}>Daily Message Volume</Heading>
                      <BarChart
                        data={chartData.messageVolume}
                        color="green.400"
                        yAxisLabel="Message Count"
                      />
                    </Box>
                    
                    <Box h="300px">
                      <Heading size="md" mb={4}>Completion Rates Over Time</Heading>
                      <LineChart
                        data={chartData.completionRates}
                        color="purple.500"
                        yAxisLabel="Completion Rate (%)"
                      />
                    </Box>
                  </SimpleGrid>
                </TabPanel>
                
                <TabPanel>
                  <Box h="400px" display="flex" justifyContent="center">
                    <Box maxW="500px" w="100%">
                      <Heading size="md" mb={4} textAlign="center">Common Conversation Topics</Heading>
                      <PieChart data={chartData.topicsData} />
                    </Box>
                  </Box>
                </TabPanel>
              </TabPanels>
            </Tabs>
          </>
        )}
      </Box>
    </DashboardLayout>
  );
} 