import { useState, useEffect } from 'react';
import { collection, getDocs, query, orderBy, limit } from 'firebase/firestore';
import { db } from '../../lib/firebase';
import DashboardLayout from '../../components/DashboardLayout';
import NextLink from 'next/link';
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
} from '@chakra-ui/react';
import { 
  FiSearch, 
  FiFilter, 
  FiUser, 
  FiEye, 
  FiChevronUp, 
  FiChevronDown,
  FiRefreshCw
} from 'react-icons/fi';
import { format } from 'date-fns';

export default function Users() {
  const [users, setUsers] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState('created_at');
  const [sortDirection, setSortDirection] = useState('desc');
  const [statusFilter, setStatusFilter] = useState('all');
  const toast = useToast();

  useEffect(() => {
    fetchUsers();
  }, []);

  useEffect(() => {
    // Apply filters and sorting when dependencies change
    let result = [...users];
    
    // Apply status filter
    if (statusFilter !== 'all') {
      result = result.filter(user => user.active === (statusFilter === 'active'));
    }
    
    // Apply search filter (on id, phone number, or state)
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(user => 
        (user.id && user.id.toLowerCase().includes(query)) ||
        (user.phone_number && user.phone_number.toLowerCase().includes(query)) ||
        (user.state && user.state.toLowerCase().includes(query))
      );
    }
    
    // Apply sorting
    result.sort((a, b) => {
      let valueA = a[sortField];
      let valueB = b[sortField];
      
      // Handle dates
      if (sortField === 'created_at' || sortField === 'last_interaction') {
        valueA = valueA ? new Date(valueA).getTime() : 0;
        valueB = valueB ? new Date(valueB).getTime() : 0;
      }
      
      // Handle numbers
      else if (sortField === 'metrics.completion_rate') {
        valueA = a.metrics?.completion_rate || 0;
        valueB = b.metrics?.completion_rate || 0;
      }
      
      // For strings
      else if (typeof valueA === 'string' && typeof valueB === 'string') {
        valueA = valueA.toLowerCase();
        valueB = valueB.toLowerCase();
      }
      
      if (valueA === valueB) {
        return 0;
      }
      
      const direction = sortDirection === 'asc' ? 1 : -1;
      return valueA < valueB ? -1 * direction : 1 * direction;
    });
    
    setFilteredUsers(result);
  }, [users, searchQuery, statusFilter, sortField, sortDirection]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const usersSnapshot = await getDocs(collection(db, 'instances/instance1/users'));
      const userData = usersSnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));
      
      setUsers(userData);
      setLoading(false);
    } catch (err) {
      console.error("Error fetching users:", err);
      setError("Failed to fetch users. Please try again.");
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
            <option value="all">All Users</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
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
                      {user.last_interaction ? 
                        format(new Date(user.last_interaction), 'MMM dd, yyyy') :
                        'Never'
                      }
                    </Td>
                    <Td>
                      {user.created_at ?
                        format(new Date(user.created_at), 'MMM dd, yyyy') :
                        'Unknown'
                      }
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