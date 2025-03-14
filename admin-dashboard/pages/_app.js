import { ChakraProvider } from '@chakra-ui/react';
import { AuthProvider } from '../lib/AuthContext';
import '../styles/globals.css';

function MyApp({ Component, pageProps }) {
  return (
    <ChakraProvider>
      <AuthProvider>
        <Component {...pageProps} />
      </AuthProvider>
    </ChakraProvider>
  );
}

export default MyApp; 