import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '../api/client';

interface User {
  user_id: string;
  username: string;
  role: string;
  auth_type: string;
  can_review: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Load user from localStorage on mount
  useEffect(() => {
    const loadUser = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          // Validate token is still valid by fetching fresh user info
          const userInfo = await api.getCurrentUser();
          setUser(userInfo);
          localStorage.setItem('user', JSON.stringify(userInfo));
        } catch (err) {
          console.error('Failed to validate token:', err);
          // Token is invalid, clear it
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          setUser(null);
        }
      } else {
        setUser(null);
      }

      setLoading(false);
    };

    loadUser();
  }, []);

  const login = async (username: string, password: string) => {
    const response = await api.login(username, password);
    
    // Store token and user info
    localStorage.setItem('token', response.access_token);
    localStorage.setItem('user', JSON.stringify(response.user));
    
    setUser(response.user);
  };

  const logout = () => {
    // Call logout endpoint (for logging/auditing)
    api.logout().catch((err: any) => console.error('Logout error:', err));
    
    // Clear local storage
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    
    setUser(null);
  };

  const refreshUser = async () => {
    try {
      const userInfo = await api.getCurrentUser();
      setUser(userInfo);
      localStorage.setItem('user', JSON.stringify(userInfo));
    } catch (err) {
      console.error('Failed to refresh user:', err);
      logout();
    }
  };

  const value: AuthContextType = {
    user,
    loading,
    login,
    logout,
    refreshUser,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
