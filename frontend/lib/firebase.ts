import { initializeApp, getApps, getApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

// Initialize Firebase safely
const app = (firebaseConfig.apiKey && getApps().length === 0) 
  ? initializeApp(firebaseConfig) 
  : (getApps().length > 0 ? getApp() : null);

const auth = app ? getAuth(app) : null;
const googleProvider = new GoogleAuthProvider();

export { auth, googleProvider };
