import { useState, useEffect } from 'react';
import { doc, getDoc, updateDoc } from 'firebase/firestore';
import { db } from '../../lib/firebase';
import DashboardLayout from '../../components/DashboardLayout';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  FormHelperText,
  Input,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Heading,
  Text,
  Switch,
  VStack,
  Divider,
  useToast,
  Flex,
  Textarea,
  Select,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  IconButton,
  SimpleGrid,
  Badge,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  useDisclosure,
} from '@chakra-ui/react';
import { FiSave, FiAlertTriangle, FiSettings, FiMessageSquare, FiClock, FiInfo } from 'react-icons/fi';
import { useRef } from 'react';

export default function Settings() {
  const [settings, setSettings] = useState({
    general: {
      systemName: 'Odinma AI',
      activeHours: {
        start: '09:00',
        end: '17:00',
      },
      timezone: 'Africa/Lagos',
      isActive: true,
    },
    ai: {
      model: 'gpt-4',
      temperature: 0.7,
      maxTokens: 1000,
      systemPrompt: 'You are Odinma AI, a mental health accountability chatbot. Be supportive, encouraging, and help users complete their daily mental health exercises.',
    },
    notifications: {
      reminderEnabled: true,
      reminderFrequency: 'daily',
      reminderTime: '08:00',
      missedSessionAlertEnabled: true,
      missedSessionThreshold: 2,
    },
    privacy: {
      dataDeletionPeriod: 90,
      anonymizeUserData: false,
      collectAnalytics: true,
    }
  });
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const toast = useToast();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const cancelRef = useRef();
  
  useEffect(() => {
    async function fetchSettings() {
      try {
        const settingsDoc = await getDoc(doc(db, 'instances/instance1/config', 'settings'));
        
        if (settingsDoc.exists()) {
          setSettings({
            ...settings,
            ...settingsDoc.data()
          });
        }
        
        setLoading(false);
      } catch (error) {
        console.error("Error fetching settings:", error);
        setLoading(false);
        
        toast({
          title: 'Error loading settings',
          description: error.message,
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      }
    }
    
    fetchSettings();
  }, [toast]);
  
  const handleGeneralChange = (field, value) => {
    setSettings({
      ...settings,
      general: {
        ...settings.general,
        [field]: value
      }
    });
  };
  
  const handleAiChange = (field, value) => {
    setSettings({
      ...settings,
      ai: {
        ...settings.ai,
        [field]: value
      }
    });
  };
  
  const handleNotificationsChange = (field, value) => {
    setSettings({
      ...settings,
      notifications: {
        ...settings.notifications,
        [field]: value
      }
    });
  };
  
  const handlePrivacyChange = (field, value) => {
    setSettings({
      ...settings,
      privacy: {
        ...settings.privacy,
        [field]: value
      }
    });
  };
  
  const handleActiveHoursChange = (field, value) => {
    setSettings({
      ...settings,
      general: {
        ...settings.general,
        activeHours: {
          ...settings.general.activeHours,
          [field]: value
        }
      }
    });
  };
  
  const handleSaveSettings = async () => {
    setSaving(true);
    try {
      await updateDoc(doc(db, 'instances/instance1/config', 'settings'), settings);
      
      toast({
        title: 'Settings saved',
        description: 'Your settings have been updated successfully.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      console.error("Error saving settings:", error);
      
      toast({
        title: 'Error saving settings',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setSaving(false);
    }
  };
  
  const handleSystemReset = async () => {
    onClose();
    setSaving(true);
    
    try {
      // In a real implementation, this would reset to default settings
      // and potentially clear user data or reset certain system states
      
      toast({
        title: 'System reset',
        description: 'System has been reset to default settings.',
        status: 'info',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      console.error("Error resetting system:", error);
      
      toast({
        title: 'Error resetting system',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setSaving(false);
    }
  };
  
  if (loading) {
    return (
      <DashboardLayout>
        <Box p={6} textAlign="center">
          <Text>Loading settings...</Text>
        </Box>
      </DashboardLayout>
    );
  }
  
  return (
    <DashboardLayout>
      <Box mb={6}>
        <Heading mb={2} display="flex" alignItems="center">
          <FiSettings size={24} style={{ marginRight: '12px' }} />
          Settings
        </Heading>
        <Text color="gray.600">
          Configure system behavior and AI parameters
        </Text>
      </Box>
      
      <Flex justify="flex-end" mb={6}>
        <Button
          colorScheme="blue"
          leftIcon={<FiSave />}
          onClick={handleSaveSettings}
          isLoading={saving}
          loadingText="Saving"
        >
          Save Settings
        </Button>
      </Flex>
      
      <Box bg="white" shadow="sm" borderRadius="lg" mb={6}>
        <Tabs colorScheme="blue" isLazy>
          <TabList px={4} pt={4}>
            <Tab><FiInfo size={18} style={{ marginRight: '8px' }} /> General</Tab>
            <Tab><FiMessageSquare size={18} style={{ marginRight: '8px' }} /> AI Configuration</Tab>
            <Tab><FiClock size={18} style={{ marginRight: '8px' }} /> Notifications</Tab>
            <Tab><FiAlertTriangle size={18} style={{ marginRight: '8px' }} /> Privacy & Data</Tab>
          </TabList>
          
          <TabPanels>
            {/* General Settings */}
            <TabPanel>
              <VStack spacing={6} align="stretch">
                <FormControl>
                  <FormLabel>System Name</FormLabel>
                  <Input
                    value={settings.general.systemName}
                    onChange={(e) => handleGeneralChange('systemName', e.target.value)}
                  />
                  <FormHelperText>The name of the AI system as seen by users</FormHelperText>
                </FormControl>
                
                <FormControl display="flex" alignItems="center">
                  <FormLabel htmlFor="system-active" mb="0">
                    System Active
                  </FormLabel>
                  <Switch
                    id="system-active"
                    isChecked={settings.general.isActive}
                    onChange={(e) => handleGeneralChange('isActive', e.target.checked)}
                  />
                </FormControl>
                
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                  <FormControl>
                    <FormLabel>Active Hours Start</FormLabel>
                    <Input
                      type="time"
                      value={settings.general.activeHours.start}
                      onChange={(e) => handleActiveHoursChange('start', e.target.value)}
                    />
                    <FormHelperText>When the system begins responding to users</FormHelperText>
                  </FormControl>
                  
                  <FormControl>
                    <FormLabel>Active Hours End</FormLabel>
                    <Input
                      type="time"
                      value={settings.general.activeHours.end}
                      onChange={(e) => handleActiveHoursChange('end', e.target.value)}
                    />
                    <FormHelperText>When the system stops responding to users</FormHelperText>
                  </FormControl>
                </SimpleGrid>
                
                <FormControl>
                  <FormLabel>Timezone</FormLabel>
                  <Select
                    value={settings.general.timezone}
                    onChange={(e) => handleGeneralChange('timezone', e.target.value)}
                  >
                    <option value="Africa/Lagos">Africa/Lagos</option>
                    <option value="Europe/London">Europe/London</option>
                    <option value="America/New_York">America/New_York</option>
                    <option value="Asia/Tokyo">Asia/Tokyo</option>
                    <option value="Australia/Sydney">Australia/Sydney</option>
                  </Select>
                  <FormHelperText>System timezone for scheduling and logs</FormHelperText>
                </FormControl>
                
                <Divider />
                
                <Box>
                  <Heading size="sm" mb={4}>System Reset</Heading>
                  <Text mb={4} color="gray.600">
                    Reset the system to default settings. This will not delete user data.
                  </Text>
                  <Button
                    colorScheme="red"
                    variant="outline"
                    leftIcon={<FiAlertTriangle />}
                    onClick={onOpen}
                  >
                    Reset System
                  </Button>
                </Box>
              </VStack>
            </TabPanel>
            
            {/* AI Configuration */}
            <TabPanel>
              <VStack spacing={6} align="stretch">
                <FormControl>
                  <FormLabel>AI Model</FormLabel>
                  <Select
                    value={settings.ai.model}
                    onChange={(e) => handleAiChange('model', e.target.value)}
                  >
                    <option value="gpt-4">GPT-4</option>
                    <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                    <option value="gpt-4-32k">GPT-4 32k</option>
                    <option value="claude-3-opus">Claude 3 Opus</option>
                    <option value="claude-3-sonnet">Claude 3 Sonnet</option>
                  </Select>
                  <FormHelperText>Select the AI model to use for responses</FormHelperText>
                </FormControl>
                
                <FormControl>
                  <FormLabel>Temperature</FormLabel>
                  <NumberInput
                    value={settings.ai.temperature}
                    onChange={(valueString) => handleAiChange('temperature', parseFloat(valueString))}
                    step={0.1}
                    min={0}
                    max={1}
                    precision={1}
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                  <FormHelperText>Controls randomness: 0 is deterministic, 1 is creative</FormHelperText>
                </FormControl>
                
                <FormControl>
                  <FormLabel>Maximum Tokens per Response</FormLabel>
                  <NumberInput
                    value={settings.ai.maxTokens}
                    onChange={(valueString) => handleAiChange('maxTokens', parseInt(valueString))}
                    step={100}
                    min={100}
                    max={4000}
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                  <FormHelperText>Maximum length of AI responses</FormHelperText>
                </FormControl>
                
                <FormControl>
                  <FormLabel>System Prompt</FormLabel>
                  <Textarea
                    value={settings.ai.systemPrompt}
                    onChange={(e) => handleAiChange('systemPrompt', e.target.value)}
                    minH="200px"
                  />
                  <FormHelperText>
                    Sets the AI's behavior and personality. This prompt is sent at the beginning of each conversation.
                  </FormHelperText>
                </FormControl>
              </VStack>
            </TabPanel>
            
            {/* Notifications */}
            <TabPanel>
              <VStack spacing={6} align="stretch">
                <FormControl display="flex" alignItems="center">
                  <FormLabel htmlFor="reminder-enabled" mb="0">
                    Enable Daily Reminders
                  </FormLabel>
                  <Switch
                    id="reminder-enabled"
                    isChecked={settings.notifications.reminderEnabled}
                    onChange={(e) => handleNotificationsChange('reminderEnabled', e.target.checked)}
                  />
                </FormControl>
                
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                  <FormControl>
                    <FormLabel>Reminder Frequency</FormLabel>
                    <Select
                      value={settings.notifications.reminderFrequency}
                      onChange={(e) => handleNotificationsChange('reminderFrequency', e.target.value)}
                      isDisabled={!settings.notifications.reminderEnabled}
                    >
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="custom">Custom</option>
                    </Select>
                    <FormHelperText>How often to send reminders</FormHelperText>
                  </FormControl>
                  
                  <FormControl>
                    <FormLabel>Reminder Time</FormLabel>
                    <Input
                      type="time"
                      value={settings.notifications.reminderTime}
                      onChange={(e) => handleNotificationsChange('reminderTime', e.target.value)}
                      isDisabled={!settings.notifications.reminderEnabled}
                    />
                    <FormHelperText>When to send reminders (in system timezone)</FormHelperText>
                  </FormControl>
                </SimpleGrid>
                
                <Divider />
                
                <FormControl display="flex" alignItems="center">
                  <FormLabel htmlFor="missed-session-alert" mb="0">
                    Missed Session Alerts
                  </FormLabel>
                  <Switch
                    id="missed-session-alert"
                    isChecked={settings.notifications.missedSessionAlertEnabled}
                    onChange={(e) => handleNotificationsChange('missedSessionAlertEnabled', e.target.checked)}
                  />
                </FormControl>
                
                <FormControl>
                  <FormLabel>Missed Session Threshold</FormLabel>
                  <NumberInput
                    value={settings.notifications.missedSessionThreshold}
                    onChange={(valueString) => handleNotificationsChange('missedSessionThreshold', parseInt(valueString))}
                    step={1}
                    min={1}
                    max={10}
                    isDisabled={!settings.notifications.missedSessionAlertEnabled}
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                  <FormHelperText>
                    Number of consecutive missed sessions before sending an alert
                  </FormHelperText>
                </FormControl>
              </VStack>
            </TabPanel>
            
            {/* Privacy & Data */}
            <TabPanel>
              <VStack spacing={6} align="stretch">
                <FormControl>
                  <FormLabel>Data Retention Period (days)</FormLabel>
                  <NumberInput
                    value={settings.privacy.dataDeletionPeriod}
                    onChange={(valueString) => handlePrivacyChange('dataDeletionPeriod', parseInt(valueString))}
                    step={30}
                    min={30}
                    max={365}
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                  <FormHelperText>
                    Number of days to keep user data before automatic deletion
                  </FormHelperText>
                </FormControl>
                
                <FormControl display="flex" alignItems="center">
                  <FormLabel htmlFor="anonymize-data" mb="0">
                    Anonymize User Data in Analytics
                  </FormLabel>
                  <Switch
                    id="anonymize-data"
                    isChecked={settings.privacy.anonymizeUserData}
                    onChange={(e) => handlePrivacyChange('anonymizeUserData', e.target.checked)}
                  />
                </FormControl>
                
                <FormControl display="flex" alignItems="center">
                  <FormLabel htmlFor="collect-analytics" mb="0">
                    Collect Anonymous Usage Analytics
                  </FormLabel>
                  <Switch
                    id="collect-analytics"
                    isChecked={settings.privacy.collectAnalytics}
                    onChange={(e) => handlePrivacyChange('collectAnalytics', e.target.checked)}
                  />
                </FormControl>
                
                <Box mt={4} p={4} bg="yellow.50" borderRadius="md">
                  <Heading size="sm" mb={2} display="flex" alignItems="center">
                    <FiAlertTriangle color="orange" style={{ marginRight: '8px' }} />
                    Data Privacy Notice
                  </Heading>
                  <Text fontSize="sm">
                    All user data is encrypted at rest and in transit. Changing these settings may affect compliance
                    with GDPR, HIPAA, and other data protection regulations. Make sure your settings comply with
                    your organization's privacy policy.
                  </Text>
                </Box>
              </VStack>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </Box>
      
      {/* Reset Confirmation Dialog */}
      <AlertDialog
        isOpen={isOpen}
        leastDestructiveRef={cancelRef}
        onClose={onClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Reset System
            </AlertDialogHeader>

            <AlertDialogBody>
              Are you sure you want to reset all system settings to their defaults?
              This will not delete user data but will reset all configuration options.
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onClose}>
                Cancel
              </Button>
              <Button colorScheme="red" onClick={handleSystemReset} ml={3} isLoading={saving}>
                Reset
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </DashboardLayout>
  );
} 