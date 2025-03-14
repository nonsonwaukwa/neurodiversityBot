import { useState, useEffect } from 'react';
import { collection, getDocs, query, orderBy, limit } from 'firebase/firestore';
import { db } from '../../lib/firebase';
import DashboardLayout from '../../components/DashboardLayout';
import NextLink from 'next/link';
import { safeFormatDate, dateToMillis } from '../../utils/dateUtils';
import {
  Box,
  Button,
  Heading,
  Text,
  Input,
  InputGroup,
  InputLeftElement,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Select,
  HStack,
  Badge,
  Flex,
  IconButton,
  useToast,
  Spinner,
  Center,
  Alert,
  AlertIcon,
  Code,
  Tag,
} from '@chakra-ui/react';
import { 
  FiSearch, 
  FiFilter, 
  FiUser, 
  FiEye, 
  FiChevronUp, 
  FiChevronDown,
  FiRefreshCw,
  FiServer
} from 'react-icons/fi';

export default function Users() {
  const [users, setUsers] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [debugInfo, setDebugInfo] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState('created_at');
  const [sortDirection, setSortDirection] = useState('desc');
  const [statusFilter, setStatusFilter] = useState('all');
  const [instanceFilter, setInstanceFilter] = useState('all');
  const toast = useToast();

  useEffect(() => {
    fetchUsers();
  }, []);

  useEffect(() => {
    try {
      // Apply filters and sorting when dependencies change
      if (users.length === 0) {
        setFilteredUsers([]);
        return;
      }
      
      // Deep clone to avoid mutation issues
      let result = JSON.parse(JSON.stringify(users));
      
      // Apply status filter
      if (statusFilter !== 'all') {
        result = result.filter(user => user.active === (statusFilter === 'active'));
      }
      
      // Apply instance filter
      if (instanceFilter !== 'all') {
        result = result.filter(user => user.instance === instanceFilter);
      }
      
      // Apply search filter (on id, phone number, or state)
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        result = result.filter(user => 
          (user.id && user.id.toLowerCase().includes(query)) ||
          (user.phone_number && typeof user.phone_number === 'string' && user.phone_number.toLowerCase().includes(query)) ||
          (user.state && user.state.toLowerCase().includes(query)) ||
          (user.instance && user.instance.toLowerCase().includes(query))
        );
      }
      
      // Apply sorting
      result.sort((a, b) => {
        let valueA, valueB;
        
        try {
          // Handle dates with our utility function
          if (sortField === 'created_at' || sortField === 'last_interaction') {
            valueA = dateToMillis(a[sortField]);
            valueB = dateToMillis(b[sortField]);
          }
          // Handle numbers
          else if (sortField === 'metrics.completion_rate') {
            valueA = a.metrics?.completion_rate || 0;
            valueB = b.metrics?.completion_rate || 0;
          }
          // For strings
          else if (typeof a[sortField] === 'string' && typeof b[sortField] === 'string') {
            valueA = a[sortField].toLowerCase();
            valueB = b[sortField].toLowerCase();
          }
          else {
            // Default values if properties don't exist
            valueA = a[sortField] || '';
            valueB = b[sortField] || '';
          }
        } catch (error) {
          console.error('Error during sorting:', error, 'field:', sortField, 'values:', a[sortField], b[sortField]);
          // Use safe defaults
          valueA = '';
          valueB = '';
        }
        
        if (valueA === valueB) {
          return 0;
        }
        
        const direction = sortDirection === 'asc' ? 1 : -1;
        return valueA < valueB ? -1 * direction : 1 * direction;
      });
      
      setFilteredUsers(result);
    } catch (err) {
      console.error("Error filtering/sorting users:", err);
      setDebugInfo(JSON.stringify({ error: err.message, stack: err.stack }));
    }
  }, [users, searchQuery, statusFilter, instanceFilter, sortField, sortDirection]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      // Fetch from the new unified users collection
      const usersSnapshot = await getDocs(collection(db, 'users'));
      
      if (usersSnapshot.empty) {
        console.log('No users found in collection');
        setUsers([]);
        setLoading(false);
        return;
      }
      
      const userData = usersSnapshot.docs.map(doc => {
        const data = doc.data();
        console.log(`User ${doc.id} data:`, data);
        console.log(`User ${doc.id} instance:`, data.instance);
        return {
          id: doc.id,
          ...data
        };
      });
      
      // Log instance information
      const instancesFound = [...new Set(userData.map(user => user.instance).filter(Boolean))];
      console.log('Instances found:', instancesFound);
      console.log('Users without instance field:', userData.filter(user => !user.instance).length);
      console.log('All fetched users:', userData);
      
      setUsers(userData);
      setLoading(false);
    } catch (err) {
      console.error("Error fetching users:", err);
      setError("Failed to fetch users. Please try again.");
      setDebugInfo(JSON.stringify({ error: err.message, stack: err.stack }));
      setLoading(false);
      
      toast({
        title: 'Error fetching users',
        description: err.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const handleRefresh = () => {
    fetchUsers();
    toast({
      title: 'Refreshing user data',
      status: 'info',
      duration: 2000,
      isClosable: true,
    });
  };

  // Helper function to safely render dates
  const renderDate = (dateValue, format, fallback) => {
    try {
      return safeFormatDate(dateValue, format, fallback);
    } catch (error) {
      console.error('Error formatting date:', dateValue, error);
      return fallback || 'Error';
    }
  };

  // Get unique instances for the filter dropdown
  const instances = [...new Set(users.map(user => user.instance).filter(Boolean))];

  return (
    <DashboardLayout>
      <Box mb={6}>
        <Heading mb={2}>Users</Heading>
        <Text color="gray.600">Manage and monitor all users in the system</Text>
      </Box>
      
      {/* Filters and Search */}
      <Flex
        direction={{ base: 'column', md: 'row' }}
        justify="space-between"
        align={{ base: 'flex-start', md: 'center' }}
        mb={6}
        gap={4}
      >
        <HStack spacing={4} width={{ base: '100%', md: 'auto' }}>
          <InputGroup maxW="300px">
            <InputLeftElement pointerEvents="none">
              <FiSearch color="gray.300" />
            </InputLeftElement>
            <Input
              placeholder="Search users..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </InputGroup>
          
          <Select
            icon={<FiFilter />}
            width="150px"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </Select>
          
          <Select
            icon={<FiServer />}
            width="150px"
            value={instanceFilter}
            onChange={(e) => setInstanceFilter(e.target.value)}
          >
            <option value="all">All Instances</option>
            {instances.map(instance => (
              <option key={instance} value={instance}>
                {instance}
              </option>
            ))}
          </Select>
        </HStack>
        
        <Button
          leftIcon={<FiRefreshCw />}
          onClick={handleRefresh}
          size="md"
          variant="outline"
          isLoading={loading}
        >
          Refresh
        </Button>
      </Flex>
      
      {/* Error Alert */}
      {error && (
        <Alert status="error" mb={6} borderRadius="md">
          <AlertIcon />
          {error}
        </Alert>
      )}
      
      {/* Debug Info */}
      {debugInfo && (
        <Alert status="warning" mb={6} borderRadius="md">
          <AlertIcon />
          <Box>
            <Text mb={2}>Debug Information:</Text>
            <Code p={2} maxH="200px" overflow="auto" w="100%" fontSize="xs">
              {debugInfo}
            </Code>
          </Box>
        </Alert>
      )}
      
      {/* Users Table */}
      <Box bg="white" shadow="sm" borderRadius="lg" overflow="hidden">
        {loading ? (
          <Center p={10}>
            <Spinner size="xl" color="blue.500" thickness="4px" />
          </Center>
        ) : filteredUsers.length === 0 ? (
          <Box p={8} textAlign="center">
            <Text fontSize="lg" fontWeight="medium">No users found</Text>
            <Text color="gray.500" mt={2}>Try adjusting your search or filters</Text>
            {users.length > 0 && (
              <Text color="blue.500" mt={4} fontSize="sm">
                There are {users.length} users in the database but none match your filters
              </Text>
            )}
          </Box>
        ) : (
          <Box overflowX="auto">
            <Table variant="simple">
              <Thead bg="gray.50">
                <Tr>
                  <Th cursor="pointer" onClick={() => handleSort('id')}>
                    <Flex align="center">
                      User ID
                      {sortField === 'id' && (
                        <Box ml={1}>
                          {sortDirection === 'asc' ? <FiChevronUp /> : <FiChevronDown />}
                        </Box>
                      )}
                    </Flex>
                  </Th>
                  <Th cursor="pointer" onClick={() => handleSort('phone_number')}>
                    <Flex align="center">
                      Phone
                      {sortField === 'phone_number' && (
                        <Box ml={1}>
                          {sortDirection === 'asc' ? <FiChevronUp /> : <FiChevronDown />}
                        </Box>
                      )}
                    </Flex>
                  </Th>
                  <Th cursor="pointer" onClick={() => handleSort('instance')}>
                    <Flex align="center">
                      Instance
                      {sortField === 'instance' && (
                        <Box ml={1}>
                          {sortDirection === 'asc' ? <FiChevronUp /> : <FiChevronDown />}
                        </Box>
                      )}
                    </Flex>
                  </Th>
                  <Th cursor="pointer" onClick={() => handleSort('state')}>
                    <Flex align="center">
                      State
                      {sortField === 'state' && (
                        <Box ml={1}>
                          {sortDirection === 'asc' ? <FiChevronUp /> : <FiChevronDown />}
                        </Box>
                      )}
                    </Flex>
                  </Th>
                  <Th cursor="pointer" onClick={() => handleSort('metrics.completion_rate')}>
                    <Flex align="center">
                      Completion Rate
                      {sortField === 'metrics.completion_rate' && (
                        <Box ml={1}>
                          {sortDirection === 'asc' ? <FiChevronUp /> : <FiChevronDown />}
                        </Box>
                      )}
                    </Flex>
                  </Th>
                  <Th cursor="pointer" onClick={() => handleSort('last_interaction')}>
                    <Flex align="center">
                      Last Active
                      {sortField === 'last_interaction' && (
                        <Box ml={1}>
                          {sortDirection === 'asc' ? <FiChevronUp /> : <FiChevronDown />}
                        </Box>
                      )}
                    </Flex>
                  </Th>
                  <Th cursor="pointer" onClick={() => handleSort('created_at')}>
                    <Flex align="center">
                      Joined
                      {sortField === 'created_at' && (
                        <Box ml={1}>
                          {sortDirection === 'asc' ? <FiChevronUp /> : <FiChevronDown />}
                        </Box>
                      )}
                    </Flex>
                  </Th>
                  <Th>Actions</Th>
                </Tr>
              </Thead>
              <Tbody>
                {filteredUsers.map((user) => (
                  <Tr key={user.id}>
                    <Td>
                      <Flex align="center">
                        <Box
                          mr={2}
                          w="8px"
                          h="8px"
                          borderRadius="full"
                          bg={user.active ? "green.400" : "gray.300"}
                        />
                        {user.id.substring(0, 8)}...
                      </Flex>
                    </Td>
                    <Td>{user.phone_number || 'N/A'}</Td>
                    <Td>
                      <Tag
                        size="sm"
                        colorScheme={user.instance === 'instance1' ? 'blue' : 'purple'}
                        variant="solid"
                      >
                        {user.instance || 'unknown'}
                      </Tag>
                    </Td>
                    <Td>
                      <Badge colorScheme={
                        user.state === 'onboarding' ? 'purple' :
                        user.state === 'active' ? 'green' :
                        user.state === 'inactive' ? 'gray' : 'blue'
                      }>
                        {user.state || 'N/A'}
                      </Badge>
                    </Td>
                    <Td>
                      {user.metrics?.completion_rate ? 
                        `${user.metrics.completion_rate.toFixed(1)}%` : 
                        'N/A'
                      }
                    </Td>
                    <Td>
                      {renderDate(user.last_interaction, 'MMM dd, yyyy', 'Never')}
                    </Td>
                    <Td>
                      {renderDate(user.created_at, 'MMM dd, yyyy', 'Unknown')}
                    </Td>
                    <Td>
                      <NextLink href={`/users/${user.id}`} passHref>
                        <IconButton
                          as="a"
                          icon={<FiEye />}
                          size="sm"
                          aria-label="View user"
                          title="View user details"
                        />
                      </NextLink>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        )}
      </Box>
    </DashboardLayout>
  );
} 