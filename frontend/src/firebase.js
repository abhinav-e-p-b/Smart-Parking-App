import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyCS_5sz7isu4lvEBMKyxnlpUgR8FPwTPoE",
  authDomain: "smart-parking-app-8cd2c.firebaseapp.com",
  projectId: "smart-parking-app-8cd2c",
  storageBucket: "smart-parking-app-8cd2c.firebasestorage.app",
  messagingSenderId: "37730632007",
  appId: "1:37730632007:web:1a75dafe319684569a0c62"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);