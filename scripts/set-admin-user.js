const { initializeApp } = require('firebase-admin/app');
const { getAuth } = require('firebase-admin/auth');
const admin = require('firebase-admin');

// Initialize Firebase admin with your service account
const serviceAccount = require('../serviceAccountKey.json');

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});

const auth = getAuth();

// Replace with the email of the user you want to make an admin
const userEmail = 'your-admin-email@example.com';

async function setAdminClaim() {
  try {
    // Get the user by email
    const user = await auth.getUserByEmail(userEmail);
    
    // Set custom claims
    await auth.setCustomUserClaims(user.uid, { admin: true });
    
    console.log(`Successfully set admin claim for user: ${userEmail}`);
    console.log('User UID:', user.uid);
    console.log('This user now has admin privileges in your application');
    
  } catch (error) {
    console.error('Error setting admin claim:', error);
  }
}

// Run the function
setAdminClaim()
  .then(() => {
    console.log('Script completed');
    process.exit(0);
  })
  .catch((error) => {
    console.error('Script failed:', error);
    process.exit(1);
  }); 