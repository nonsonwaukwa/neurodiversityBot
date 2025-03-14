import { useState, useEffect } from 'react';
import { collection, getDocs, query, orderBy, limit } from 'firebase/firestore';
import { db } from '../../lib/firebase';
import DashboardLayout from '../../components/DashboardLayout';
import {
  Box,
  Button,
  Heading,
  Text,
  Flex,
  SimpleGrid,
  Select,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Icon,
  HStack,
  Tag,
  Badge,
  useToast,
} from '@chakra-ui/react';
import { 
  FiBarChart2, 
  FiDownload, 
  FiUser, 
  FiMessageCircle, 
  FiCheck, 
  FiClock, 
  FiActivity 
} from 'react-icons/fi';
import { format, subDays } from 'date-fns';
import { LineChart, BarChart, PieChart } from '../../components/Charts';

export default function Analytics() {
  const [timeframe, setTimeframe] = useState('7d');
  const [metrics, setMetrics] = useState({
    totalUsers: 0,
    activeUsers: 0,
    messagesReceived: 0,
    messagesProcessed: 0,
    averageResponseTime: 0,
    completionRate: 0,
    userRetention: 0,
    activeSessions: 0,
  });
  const [userGrowth, setUserGrowth] = useState([]);
  const [messageVolume, setMessageVolume] = useState([]);
  const [completionRates, setCompletionRates] = useState([]);
  const [commonTopics, setCommonTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const toast = useToast();
  
  useEffect(() => {
    async function fetchAnalyticsData() {
      setLoading(true);
      try {
        // In a real implementation, this would fetch data from Firestore
        // Here we're generating mock data for demonstration
        
        // Simulate loading time
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Mock metrics based on timeframe
        let dayCount = 7;
        if (timeframe === '30d') dayCount = 30;
        if (timeframe === '90d') dayCount = 90;
        
        // Generate synthetic data for charts
        generateMockData(dayCount);
        
        // Update overall metrics
        const growthRate = getGrowthRate(userGrowth);
        const prevCompletionRate = 67.8; // Previous period for comparison
        
        setMetrics({
          totalUsers: 1240 + Math.floor(Math.random() * 100),
          activeUsers: 835 + Math.floor(Math.random() * 50),
          messagesReceived: 15230 + Math.floor(Math.random() * 1000),
          messagesProcessed: 15200 + Math.floor(Math.random() * 300),
          averageResponseTime: 1.8 + (Math.random() * 0.5),
          completionRate: 72.4 + (Math.random() * 5 - 2.5),
          userRetention: 81.2 + (Math.random() * 4 - 2),
          activeSessions: 125 + Math.floor(Math.random() * 20),
          userGrowthRate: growthRate,
          completionRateChange: metrics.completionRate - prevCompletionRate,
        });
        
        setLoading(false);
      } catch (error) {
        console.error("Error fetching analytics data:", error);
        setLoading(false);
        
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
  }, [timeframe, toast]);
  
  const generateMockData = (days) => {
    // Generate user growth data
    const userGrowthData = [];
    let cumulativeUsers = 1150;
    
    for (let i = days; i >= 0; i--) {
      const date = format(subDays(new Date(), i), 'yyyy-MM-dd');
      const newUsers = Math.floor(Math.random() * 15) + 5;
      cumulativeUsers += newUsers;
      
      userGrowthData.push({
        date,
        value: cumulativeUsers
      });
    }
    setUserGrowth(userGrowthData);
    
    // Generate message volume data
    const messageVolumeData = [];
    for (let i = days; i >= 0; i--) {
      const date = format(subDays(new Date(), i), 'yyyy-MM-dd');
      const value = Math.floor(Math.random() * 300) + 400;
      
      messageVolumeData.push({
        date,
        value
      });
    }
    setMessageVolume(messageVolumeData);
    
    // Generate completion rate data
    const completionRateData = [];
    for (let i = days; i >= 0; i--) {
      const date = format(subDays(new Date(), i), 'yyyy-MM-dd');
      const value = Math.floor(Math.random() * 15) + 65;
      
      completionRateData.push({
        date,
        value
      });
    }
    setCompletionRates(completionRateData);
    
    // Generate common topics data
    setCommonTopics([
      { name: 'Stress Management', count: Math.floor(Math.random() * 200) + 800 },
      { name: 'Mood Tracking', count: Math.floor(Math.random() * 150) + 650 },
      { name: 'Breathing Exercises', count: Math.floor(Math.random() * 100) + 500 },
      { name: 'Sleep Issues', count: Math.floor(Math.random() * 80) + 400 },
      { name: 'Physical Activity', count: Math.floor(Math.random() * 70) + 350 },
      { name: 'Meditation', count: Math.floor(Math.random() * 60) + 300 },
      { name: 'Diet & Nutrition', count: Math.floor(Math.random() * 50) + 250 },
      { name: 'Social Anxiety', count: Math.floor(Math.random() * 40) + 200 },
    ]);
  };
  
  const getGrowthRate = (data) => {
    if (!data || data.length < 2) return 0;
    
    const current = data[data.length - 1].value;
    const previous = data[0].value;
    const daysCount = data.length - 1;
    
    // Calculate daily growth rate percentage
    return ((Math.pow(current / previous, 1 / daysCount) - 1) * 100).toFixed(1);
  };
  
  const handleExportData = () => {
    toast({
      title: 'Export initiated',
      description: 'Analytics data is being prepared for download.',
      status: 'info',
      duration: 3000,
      isClosable: true,
    });
    
    // In a real implementation, this would generate and download a CSV or Excel file
    setTimeout(() => {
      toast({
        title: 'Export ready',
        description: 'Your data has been exported successfully.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    }, 2000);
  };
  
  return (
    <DashboardLayout>
      <Box mb={6}>
        <Heading mb={2} display="flex" alignItems="center">
          <Icon as={FiBarChart2} mr={2} />
          Analytics
        </Heading>
        <Text color="gray.600">View system usage statistics and trends</Text>
      </Box>
      
      <Flex 
        direction={{ base: 'column', md: 'row' }} 
        justify="space-between" 
        align={{ base: 'flex-start', md: 'center' }}
        mb={6}
        gap={4}
      >
        <Select
          value={timeframe}
          onChange={(e) => setTimeframe(e.target.value)}
          width={{ base: 'full', md: '200px' }}
          bg="white"
        >
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
          <option value="90d">Last 90 Days</option>
        </Select>
        
        <Button
          leftIcon={<FiDownload />}
          colorScheme="blue"
          variant="outline"
          onClick={handleExportData}
          isLoading={loading}
        >
          Export Data
        </Button>
      </Flex>
      
      {/* Key Metrics */}
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={6} mb={8}>
        <Box bg="white" p={6} borderRadius="lg" shadow="sm">
          <Stat>
            <Flex align="center" mb={2}>
              <Icon as={FiUser} color="blue.500" boxSize={5} mr={2} />
              <StatLabel>Active Users</StatLabel>
            </Flex>
            <StatNumber>{metrics.activeUsers}</StatNumber>
            <StatHelpText>
              <StatArrow type="increase" />
              {metrics.userGrowthRate}% growth
            </StatHelpText>
          </Stat>
        </Box>
        
        <Box bg="white" p={6} borderRadius="lg" shadow="sm">
          <Stat>
            <Flex align="center" mb={2}>
              <Icon as={FiMessageCircle} color="green.500" boxSize={5} mr={2} />
              <StatLabel>Messages</StatLabel>
            </Flex>
            <StatNumber>{metrics.messagesReceived.toLocaleString()}</StatNumber>
            <StatHelpText>
              <Text fontSize="sm">
                {(metrics.messagesProcessed / metrics.messagesReceived * 100).toFixed(1)}% processed
              </Text>
            </StatHelpText>
          </Stat>
        </Box>
        
        <Box bg="white" p={6} borderRadius="lg" shadow="sm">
          <Stat>
            <Flex align="center" mb={2}>
              <Icon as={FiCheck} color="purple.500" boxSize={5} mr={2} />
              <StatLabel>Task Completion</StatLabel>
            </Flex>
            <StatNumber>{metrics.completionRate.toFixed(1)}%</StatNumber>
            <StatHelpText>
              <StatArrow type={metrics.completionRateChange > 0 ? 'increase' : 'decrease'} />
              {Math.abs(metrics.completionRateChange).toFixed(1)}% from last period
            </StatHelpText>
          </Stat>
        </Box>
        
        <Box bg="white" p={6} borderRadius="lg" shadow="sm">
          <Stat>
            <Flex align="center" mb={2}>
              <Icon as={FiClock} color="orange.500" boxSize={5} mr={2} />
              <StatLabel>Response Time</StatLabel>
            </Flex>
            <StatNumber>{metrics.averageResponseTime.toFixed(1)}s</StatNumber>
            <StatHelpText>
              <Text fontSize="sm">Average system response time</Text>
            </StatHelpText>
          </Stat>
        </Box>
      </SimpleGrid>
      
      <Tabs colorScheme="blue" variant="enclosed" bg="white" shadow="sm" borderRadius="lg" mb={8}>
        <TabList px={4} pt={4}>
          <Tab>Trends</Tab>
          <Tab>Usage</Tab>
          <Tab>Topics</Tab>
        </TabList>
        
        <TabPanels>
          {/* Trends Tab */}
          <TabPanel>
            <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={8}>
              <Box>
                <Heading size="sm" mb={4}>User Growth</Heading>
                <Box height="300px">
                  <LineChart
                    data={userGrowth.map(item => ({
                      x: item.date,
                      y: item.value
                    }))}
                    color="blue.500"
                    yAxisLabel="Total Users"
                  />
                </Box>
              </Box>
              
              <Box>
                <Heading size="sm" mb={4}>Completion Rate Trends</Heading>
                <Box height="300px">
                  <LineChart
                    data={completionRates.map(item => ({
                      x: item.date,
                      y: item.value
                    }))}
                    color="green.500"
                    yAxisLabel="Completion (%)"
                  />
                </Box>
              </Box>
            </SimpleGrid>
          </TabPanel>
          
          {/* Usage Tab */}
          <TabPanel>
            <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={8}>
              <Box>
                <Heading size="sm" mb={4}>Daily Message Volume</Heading>
                <Box height="300px">
                  <BarChart
                    data={messageVolume.slice(-14).map(item => ({
                      x: item.date,
                      y: item.value
                    }))}
                    color="purple.500"
                    yAxisLabel="Message Count"
                  />
                </Box>
              </Box>
              
              <Box>
                <Heading size="sm" mb={4}>Active Sessions by Hour</Heading>
                <Box height="300px">
                  <BarChart
                    data={[
                      { x: '00:00', y: 12 },
                      { x: '03:00', y: 5 },
                      { x: '06:00', y: 8 },
                      { x: '09:00', y: 45 },
                      { x: '12:00', y: 78 },
                      { x: '15:00', y: 92 },
                      { x: '18:00', y: 65 },
                      { x: '21:00', y: 30 },
                    ]}
                    color="orange.500"
                    yAxisLabel="Active Sessions"
                  />
                </Box>
              </Box>
            </SimpleGrid>
          </TabPanel>
          
          {/* Topics Tab */}
          <TabPanel>
            <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={8}>
              <Box>
                <Heading size="sm" mb={4}>Common Conversation Topics</Heading>
                <Box height="300px">
                  <PieChart
                    data={commonTopics.map(topic => ({
                      id: topic.name,
                      label: topic.name,
                      value: topic.count,
                    }))}
                  />
                </Box>
              </Box>
              
              <Box>
                <Heading size="sm" mb={4}>Top Conversation Topics</Heading>
                <Table variant="simple">
                  <Thead bg="gray.50">
                    <Tr>
                      <Th>Topic</Th>
                      <Th isNumeric>Count</Th>
                      <Th>Trend</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {commonTopics.map((topic, index) => (
                      <Tr key={topic.name}>
                        <Td>
                          <HStack>
                            <Text fontWeight={index < 3 ? "medium" : "normal"}>
                              {topic.name}
                            </Text>
                            {index < 3 && (
                              <Badge colorScheme="green">Top</Badge>
                            )}
                          </HStack>
                        </Td>
                        <Td isNumeric>{topic.count}</Td>
                        <Td>
                          <Tag
                            size="sm"
                            colorScheme={
                              Math.random() > 0.5 ? "green" : 
                              Math.random() > 0.5 ? "red" : "gray"
                            }
                          >
                            {Math.random() > 0.5 ? "↑" : "↓"} 
                            {Math.floor(Math.random() * 30) + 1}%
                          </Tag>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Box>
            </SimpleGrid>
          </TabPanel>
        </TabPanels>
      </Tabs>
      
      <Box bg="white" p={6} borderRadius="lg" shadow="sm" mb={6}>
        <Heading size="md" mb={4}>
          <Flex align="center">
            <Icon as={FiActivity} mr={2} />
            System Health
          </Flex>
        </Heading>
        
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
          <Stat>
            <StatLabel>System Uptime</StatLabel>
            <StatNumber>99.9%</StatNumber>
            <StatHelpText>Last 30 days</StatHelpText>
          </Stat>
          
          <Stat>
            <StatLabel>API Latency</StatLabel>
            <StatNumber>124ms</StatNumber>
            <StatHelpText>Average response time</StatHelpText>
          </Stat>
          
          <Stat>
            <StatLabel>Error Rate</StatLabel>
            <StatNumber>0.03%</StatNumber>
            <StatHelpText>
              <StatArrow type="decrease" />
              0.01% from previous period
            </StatHelpText>
          </Stat>
        </SimpleGrid>
      </Box>
    </DashboardLayout>
  );
} 