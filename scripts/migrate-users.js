const { initializeApp } = require('firebase-admin/app');
const { getFirestore } = require('firebase-admin/firestore');
const admin = require('firebase-admin');

// Initialize Firebase admin with your service account
// You'll need to download your service account key from Firebase console
const serviceAccount = require('../config/neurodiversitybot-firebase-adminsdk-fbsvc-e442ab6d6a.json');

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});

const db = getFirestore();

async function migrateUsers() {
  console.log('Starting user migration...');
  
  try {
    // Check if the users collection already exists
    const usersCollectionRef = db.collection('users');
    const usersSnapshot = await usersCollectionRef.get();
    console.log(`Current users in unified collection: ${usersSnapshot.size}`);
    
    // Output existing users if any
    if (usersSnapshot.size > 0) {
      console.log('Existing users in unified collection:');
      usersSnapshot.docs.forEach(doc => {
        console.log(`- User ID: ${doc.id}, Instance: ${doc.data().instance || 'Not set'}`);
      });
    }
    
    // Get all users from instance1
    console.log('Fetching users from instance1...');
    const instance1Snapshot = await db.collection('instances/instance1/users').get();
    
    // Get all users from instance2
    console.log('Fetching users from instance2...');
    const instance2Snapshot = await db.collection('instances/instance2/users').get();
    
    console.log(`Found ${instance1Snapshot.size} users in instance1`);
    console.log(`Found ${instance2Snapshot.size} users in instance2`);
    
    // Output user IDs from each instance
    if (instance1Snapshot.size > 0) {
      console.log('Users in instance1:');
      instance1Snapshot.docs.forEach((doc, index) => {
        if (index < 5) console.log(`- User ID: ${doc.id}`);
      });
      if (instance1Snapshot.size > 5) console.log(`... and ${instance1Snapshot.size - 5} more`);
    }
    
    if (instance2Snapshot.size > 0) {
      console.log('Users in instance2:');
      instance2Snapshot.docs.forEach((doc, index) => {
        if (index < 5) console.log(`- User ID: ${doc.id}`);
      });
      if (instance2Snapshot.size > 5) console.log(`... and ${instance2Snapshot.size - 5} more`);
    }
    
    // Track migrated users
    let migratedCount = 0;
    let errorCount = 0;
    let skippedCount = 0;
    
    // Create a batch write for instance1 users
    const migrateInstance = async (snapshot, instanceName) => {
      // Use multiple batches if needed (Firestore has a limit of 500 operations per batch)
      const batchSize = 450;
      const batches = [];
      let currentBatch = db.batch();
      let operationCount = 0;
      
      for (const doc of snapshot.docs) {
        const userData = doc.data();
        const userId = doc.id;
        
        // Check if user already exists in unified collection
        const existingUserDoc = await usersCollectionRef.doc(userId).get();
        if (existingUserDoc.exists) {
          console.log(`User ${userId} already exists in unified collection, skipping...`);
          skippedCount++;
          continue;
        }
        
        // Add instance field to identify source
        userData.instance = instanceName;
        
        // Add timestamp for the migration
        userData.migratedAt = admin.firestore.FieldValue.serverTimestamp();
        
        try {
          // Create reference to new user document in unified collection
          const newUserRef = db.collection('users').doc(userId);
          
          // Add to batch
          currentBatch.set(newUserRef, userData);
          operationCount++;
          
          // If we reach batch size limit, add the current batch to our batches array
          // and create a new batch
          if (operationCount >= batchSize) {
            batches.push(currentBatch);
            currentBatch = db.batch();
            operationCount = 0;
          }
        } catch (error) {
          console.error(`Error preparing migration for user ${userId}:`, error);
          errorCount++;
        }
      }
      
      // Add the last batch if it has operations
      if (operationCount > 0) {
        batches.push(currentBatch);
      }
      
      // Commit all batches
      console.log(`Committing ${batches.length} batches for ${instanceName}...`);
      for (const [index, batch] of batches.entries()) {
        try {
          await batch.commit();
          migratedCount += (index === batches.length - 1 ? operationCount : batchSize);
          console.log(`Batch ${index + 1}/${batches.length} committed successfully`);
        } catch (error) {
          console.error(`Error committing batch ${index + 1}:`, error);
          errorCount += (index === batches.length - 1 ? operationCount : batchSize);
        }
      }
    };
    
    // Migrate both instances
    await migrateInstance(instance1Snapshot, 'instance1');
    await migrateInstance(instance2Snapshot, 'instance2');
    
    // Verify the results
    const finalUsersSnapshot = await usersCollectionRef.get();
    console.log(`\nFinal users count in unified collection: ${finalUsersSnapshot.size}`);
    
    // Count users by instance
    const instanceCounts = {};
    finalUsersSnapshot.docs.forEach(doc => {
      const instance = doc.data().instance || 'unknown';
      instanceCounts[instance] = (instanceCounts[instance] || 0) + 1;
    });
    
    console.log('Users count by instance:');
    Object.entries(instanceCounts).forEach(([instance, count]) => {
      console.log(`- ${instance}: ${count} users`);
    });
    
    console.log(`\nMigration summary: ${migratedCount} users migrated successfully`);
    console.log(`Skipped: ${skippedCount} users (already exist in unified collection)`);
    if (errorCount > 0) {
      console.log(`Warning: ${errorCount} users encountered errors during migration`);
    }
    
    // Optional: Create an index on the instance field for better query performance
    console.log('Completed! Remember to create an index on the instance field if needed.');
    
  } catch (error) {
    console.error('Migration failed:', error);
  }
}

// Run the migration
migrateUsers()
  .then(() => {
    console.log('Migration script completed');
    process.exit(0);
  })
  .catch((error) => {
    console.error('Migration script failed:', error);
    process.exit(1);
  }); 