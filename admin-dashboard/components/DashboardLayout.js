import { Box, Flex, useColorModeValue, Stack, Text, Icon, Link } from '@chakra-ui/react';
import { useRouter } from 'next/router';
import NextLink from 'next/link';
import { FiHome, FiUsers, FiBarChart2, FiSettings, FiLogOut } from 'react-icons/fi';
import { signOut } from 'firebase/auth';
import { auth } from '../lib/firebase';
import ProtectedRoute from './ProtectedRoute';

// Navigation items for sidebar
const NavItems = [
  { name: 'Dashboard', icon: FiHome, path: '/dashboard' },
  { name: 'Users', icon: FiUsers, path: '/users' },
  { name: 'Analytics', icon: FiBarChart2, path: '/analytics' },
  { name: 'Settings', icon: FiSettings, path: '/settings' },
];

export default function DashboardLayout({ children }) {
  const router = useRouter();

  const handleSignOut = async () => {
    try {
      await signOut(auth);
      router.push('/login');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  return (
    <ProtectedRoute>
      <Flex minH="100vh" bg={useColorModeValue('gray.50', 'gray.900')}>
        {/* Sidebar */}
        <Box
          bg={useColorModeValue('white', 'gray.800')}
          borderRight="1px"
          borderRightColor={useColorModeValue('gray.200', 'gray.700')}
          w={{ base: 'full', md: 60 }}
          pos="fixed"
          h="full"
          boxShadow="sm"
        >
          <Flex h="20" alignItems="center" mx="8" justifyContent="space-between">
            <Text fontSize="2xl" fontWeight="bold" color={useColorModeValue('blue.600', 'blue.400')}>
              Odinma Admin
            </Text>
          </Flex>

          {/* Nav Items */}
          <Stack spacing={4} mt={8} px={4}>
            {NavItems.map((navItem) => (
              <NavItem
                key={navItem.name}
                icon={navItem.icon}
                path={navItem.path}
                active={router.pathname === navItem.path}
              >
                {navItem.name}
              </NavItem>
            ))}

            {/* Logout */}
            <Box 
              cursor="pointer" 
              onClick={handleSignOut}
              p={2}
              borderRadius="md"
              _hover={{
                bg: 'red.50',
                color: 'red.600',
              }}
              mt={8}
              color="gray.600"
              fontWeight="medium"
            >
              <Flex align="center">
                <Icon as={FiLogOut} mr={3} />
                <Text>Sign Out</Text>
              </Flex>
            </Box>
          </Stack>
        </Box>

        {/* Main Content */}
        <Box ml={{ base: 0, md: 60 }} p={4} width="full">
          <Box maxW="7xl" mx="auto" pt={5} px={{ base: 2, sm: 12, md: 17 }}>
            {children}
          </Box>
        </Box>
      </Flex>
    </ProtectedRoute>
  );
}

// Individual navigation item component
function NavItem({ icon, children, path, active, ...rest }) {
  return (
    <NextLink href={path} passHref>
      <Link
        style={{ textDecoration: 'none' }}
        _focus={{ boxShadow: 'none' }}
      >
        <Flex
          align="center"
          p="4"
          mx="4"
          borderRadius="lg"
          role="group"
          cursor="pointer"
          bg={active ? 'blue.50' : 'transparent'}
          color={active ? 'blue.600' : 'gray.600'}
          _hover={{
            bg: 'blue.50',
            color: 'blue.600',
          }}
          fontWeight={active ? 'bold' : 'medium'}
          {...rest}
        >
          {icon && (
            <Icon
              mr="4"
              fontSize="16"
              as={icon}
            />
          )}
          {children}
        </Flex>
      </Link>
    </NextLink>
  );
} 