"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { onAuthStateChanged, User, signOut } from "firebase/auth";
import { auth } from "@/lib/firebase";

interface UserProfile {
  id: string;
  org_id: string;
  role_id: number;
  role: string;
  allowed_pages: string[];
  email: string;
}

interface AuthContextType {
  user: User | null;
  profile: UserProfile | null;
  loading: boolean;
  idToken: string | null;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  profile: null,
  loading: true,
  idToken: null,
  logout: async () => {},
});

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [idToken, setIdToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch internal user data:
  useEffect(() => {
    if (idToken) {
        fetch("/api/auth/me", {
            headers: { Authorization: `Bearer ${idToken}` }
        })
        .then(res => res.json())
        .then(data => {
            if (data && data.role) setProfile(data);
        })
        .catch(err => console.error("Profile sync fail:", err));
    } else {
        setProfile(null);
    }
  }, [idToken]);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        const token = await user.getIdToken();
        setUser(user);
        setIdToken(token);
        localStorage.setItem("fincore_token", token);
      } else {
        setUser(null);
        setProfile(null);
        setIdToken(null);
        localStorage.removeItem("fincore_token");
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const logout = async () => {
    await signOut(auth);
  };

  return (
    <AuthContext.Provider value={{ user, profile, loading, idToken, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
