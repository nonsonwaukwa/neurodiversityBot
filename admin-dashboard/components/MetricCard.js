import {
  Box,
  Flex,
  Stat,
  StatLabel,
  StatNumber,
  useColorModeValue,
  Icon,
} from '@chakra-ui/react';
import { FiUsers, FiCheckCircle, FiActivity, FiUserCheck } from 'react-icons/fi';

// Map of icon names to their components
const iconMap = {
  users: FiUsers,
  userActive: FiUserCheck,
  checkCircle: FiCheckCircle,
  activity: FiActivity,
};

export default function MetricCard({ title, value, icon, change }) {
  return (
    <Stat
      px={{ base: 2, md: 4 }}
      py="5"
      shadow="sm"
      border="1px solid"
      borderColor={useColorModeValue('gray.200', 'gray.500')}
      rounded="lg"
      bg={useColorModeValue('white', 'gray.700')}
    >
      <Flex justifyContent="space-between">
        <Box pl={{ base: 2, md: 4 }}>
          <StatLabel fontWeight="medium" isTruncated>
            {title}
          </StatLabel>
          <StatNumber fontSize="2xl" fontWeight="bold">
            {value}
          </StatNumber>
          {change && (
            <Box
              fontSize="sm"
              color={change > 0 ? 'green.500' : change < 0 ? 'red.500' : 'gray.500'}
              fontWeight="medium"
              mt={1}
            >
              {change > 0 ? `+${change}%` : `${change}%`}
            </Box>
          )}
        </Box>
        <Box
          my="auto"
          color={useColorModeValue('gray.800', 'gray.200')}
          alignContent="center"
        >
          <Icon as={iconMap[icon] || FiActivity} w={8} h={8} />
        </Box>
      </Flex>
    </Stat>
  );
} 