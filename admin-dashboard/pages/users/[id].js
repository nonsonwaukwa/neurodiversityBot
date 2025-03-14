import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { doc, getDoc, collection, getDocs, query, orderBy, limit } from 'firebase/firestore';
import { db } from '../../lib/firebase';
import DashboardLayout from '../../components/DashboardLayout';
import { safeFormatDate, dateToMillis } from '../../utils/dateUtils';
import {
  Box,
  Button,
  Heading,
  Text,
  Badge,
  Flex,
  Icon,
  VStack,
  HStack,
  Divider,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  SimpleGrid,
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
  useToast,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { 
  FiUser, 
  FiArrowLeft, 
  FiCalendar, 
  FiPhone, 
  FiActivity, 
  FiMessageCircle, 
  FiClock, 
  FiCheckCircle
} from 'react-icons/fi';
import NextLink from 'next/link';
import { LineChart } from '../../components/Charts';

export default function UserDetail() {
  const router = useRouter();
  const { id } = router.query;
  const toast = useToast();
  
  const [user, setUser] = useState(null);
  const [recentMessages, setRecentMessages] = useState([]);
  const [stressHistory, setStressHistory] = useState([]);
  const [completionHistory, setCompletionHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    // Only fetch if id is available from the router
    if (!id) return;
    
    async function fetchUserData() {
      setLoading(true);
      try {
        // Get user data
        const userDoc = await getDoc(doc(db, 'instances/instance1/users', id));
        
        if (!userDoc.exists()) {
          setError('User not found');
          setLoading(false);
          return;
        }
        
        const userData = {
          id: userDoc.id,
          ...userDoc.data()
        };
        
        console.log('Fetched user data:', userData);
        setUser(userData);
        
        // Get recent messages
        try {
          const messagesQuery = query(
            collection(db, 'instances/instance1/users', id, 'conversations'),
            orderBy('timestamp', 'desc'),
            limit(10)
          );
          const messagesSnapshot = await getDocs(messagesQuery);
          const messagesData = messagesSnapshot.docs.map(doc => ({
            id: doc.id,
            ...doc.data()
          }));
          setRecentMessages(messagesData);
        } catch (msgError) {
          console.warn("Could not fetch messages:", msgError);
          // Don't fail completely if just messages fail to load
        }
        
        // Get stress and completion metrics (simulated for now)
        // In a real implementation, this would come from a metrics collection
        const mockStressData = [
          { date: '2023-05-01', value: 3 },
          { date: '2023-05-02', value: 4 },
          { date: '2023-05-03', value: 2 },
          { date: '2023-05-04', value: 3 },
          { date: '2023-05-05', value: 5 },
          { date: '2023-05-06', value: 4 },
          { date: '2023-05-07', value: 3 },
        ];
        
        const mockCompletionData = [
          { date: '2023-05-01', value: 80 },
          { date: '2023-05-02', value: 75 },
          { date: '2023-05-03', value: 85 },
          { date: '2023-05-04', value: 90 },
          { date: '2023-05-05', value: 65 },
          { date: '2023-05-06', value: 70 },
          { date: '2023-05-07', value: 80 },
        ];
        
        setStressHistory(mockStressData);
        setCompletionHistory(mockCompletionData);
        
        setLoading(false);
      } catch (error) {
        console.error("Error fetching user data:", error);
        setError('Failed to load user data');
        setLoading(false);
        
        toast({
          title: 'Error loading user data',
          description: error.message,
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      }
    }
    
    fetchUserData();
  }, [id, toast]);
  
  if (loading) {
    return (
      <DashboardLayout>
        <Box p={6} textAlign="center">
          <Text>Loading user data...</Text>
        </Box>
      </DashboardLayout>
    );
  }
  
  if (error) {
    return (
      <DashboardLayout>
        <Alert status="error" mb={6}>
          <AlertIcon />
          {error}
        </Alert>
        <Button
          leftIcon={<FiArrowLeft />}
          onClick={() => router.push('/users')}
          mb={6}
        >
          Back to Users
        </Button>
      </DashboardLayout>
    );
  }
  
  return (
    <DashboardLayout>
      <Flex justify="space-between" align="center" mb={6}>
        <NextLink href="/users" passHref>
          <Button as="a" leftIcon={<FiArrowLeft />} variant="outline">
            Back to Users
          </Button>
        </NextLink>
      </Flex>
      
      <Box bg="white" shadow="sm" borderRadius="lg" p={6} mb={6}>
        <Flex
          direction={{ base: 'column', md: 'row' }}
          align={{ base: 'flex-start', md: 'center' }}
          justify="space-between"
          mb={6}
        >
          <Flex align="center">
            <Icon as={FiUser} boxSize={10} p={2} bg="blue.50" color="blue.500" borderRadius="full" mr={4} />
            <Box>
              <Heading size="lg" display="flex" alignItems="center">
                User {user?.id}
                {user?.active && <Badge colorScheme="green" ml={2}>Active</Badge>}
              </Heading>
              <HStack mt={1} color="gray.600" spacing={4}>
                {user?.phone_number && (
                  <Flex align="center">
                    <Icon as={FiPhone} mr={1} />
                    <Text>{user.phone_number}</Text>
                  </Flex>
                )}
                {user?.created_at && (
                  <Flex align="center">
                    <Icon as={FiCalendar} mr={1} />
                    <Text>Joined {safeFormatDate(user.created_at, 'MMM dd, yyyy')}</Text>
                  </Flex>
                )}
              </HStack>
            </Box>
          </Flex>
        </Flex>
        
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
          <Stat>
            <StatLabel>Current State</StatLabel>
            <StatNumber>{user?.state || 'Unknown'}</StatNumber>
            <StatHelpText>User's current interaction state</StatHelpText>
          </Stat>
          
          <Stat>
            <StatLabel>Task Completion Rate</StatLabel>
            <StatNumber>
              <Badge
                fontSize="md"
                px={2}
                py={1}
                colorScheme={
                  !user?.metrics?.completion_rate ? 'gray' :
                  user.metrics.completion_rate >= 70 ? 'green' :
                  user.metrics.completion_rate >= 40 ? 'blue' : 'orange'
                }
              >
                {user?.metrics?.completion_rate?.toFixed(1) || 0}%
              </Badge>
            </StatNumber>
            <StatHelpText>Average task completion</StatHelpText>
          </Stat>
          
          <Stat>
            <StatLabel>Last Activity</StatLabel>
            <StatNumber>
              <Text fontSize="md" fontWeight="bold">
                {safeFormatDate(user?.last_interaction, 'MMM dd, h:mm a', 'Never')}
              </Text>
            </StatNumber>
            <StatHelpText>
              {user?.last_interaction
                ? `${Math.round((Date.now() - dateToMillis(user.last_interaction)) / (1000 * 60 * 60))} hours ago`
                : 'No activity recorded'
              }
            </StatHelpText>
          </Stat>
        </SimpleGrid>
      </Box>
      
      <Tabs variant="enclosed" colorScheme="blue" bg="white" shadow="sm" borderRadius="lg" mb={6}>
        <TabList>
          <Tab><Icon as={FiActivity} mr={2} /> Metrics</Tab>
          <Tab><Icon as={FiMessageCircle} mr={2} /> Conversations</Tab>
        </TabList>
        
        <TabPanels>
          <TabPanel>
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
              <Box p={4} borderWidth="1px" borderRadius="md" bg="white">
                <Heading size="sm" mb={4}>Stress Level History</Heading>
                <Box h="250px">
                  <LineChart 
                    data={stressHistory.map(item => ({
                      x: item.date,
                      y: item.value
                    }))}
                    color="orange.500"
                    yAxisLabel="Stress Level"
                  />
                </Box>
              </Box>
              
              <Box p={4} borderWidth="1px" borderRadius="md" bg="white">
                <Heading size="sm" mb={4}>Task Completion Rate</Heading>
                <Box h="250px">
                  <LineChart 
                    data={completionHistory.map(item => ({
                      x: item.date,
                      y: item.value
                    }))}
                    color="blue.500" 
                    yAxisLabel="Completion (%)"
                  />
                </Box>
              </Box>
            </SimpleGrid>
          </TabPanel>
          
          <TabPanel>
            <Heading size="sm" mb={4}>Recent Conversations</Heading>
            {recentMessages.length === 0 ? (
              <Text color="gray.500">No recent messages found</Text>
            ) : (
              <Box overflowX="auto">
                <Table variant="simple">
                  <Thead>
                    <Tr>
                      <Th>Timestamp</Th>
                      <Th>Message</Th>
                      <Th>Type</Th>
                      <Th>Response</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {recentMessages.map((message) => (
                      <Tr key={message.id}>
                        <Td whiteSpace="nowrap">
                          {safeFormatDate(message.timestamp, 'MMM dd, yyyy h:mm a', '-')}
                        </Td>
                        <Td maxW="200px" isTruncated>{message.content || '-'}</Td>
                        <Td>
                          <Badge>{message.type || 'unknown'}</Badge>
                        </Td>
                        <Td maxW="200px" isTruncated>{message.response || '-'}</Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Box>
            )}
          </TabPanel>
        </TabPanels>
      </Tabs>
    </DashboardLayout>
  );
} 