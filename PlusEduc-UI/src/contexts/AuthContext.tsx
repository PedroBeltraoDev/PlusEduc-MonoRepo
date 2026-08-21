import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { authService } from '@/services';
import type {
  AuthResponse,
  LoadingState,
  LoginRequest,
  ProfileUpdateRequest,
  StudentRegistrationRequest,
  User,
} from '@/types';

interface AuthContextType {
  isAuthenticated: boolean;
  role: User['role'] | null;
  userName: string | null;
  userEmail: string | null;
  userId: string | null;
  studentId: string | null;
  isStudent: boolean;
  isEducator: boolean;
  loadingState: LoadingState;
  login: (credentials: LoginRequest) => Promise<string>;
  registerStudent: (data: StudentRegistrationRequest) => Promise<string>;
  updateProfile: (data: ProfileUpdateRequest) => Promise<AuthResponse>;
  logout: () => void;
  getToken: () => string | null;
  getHomePath: () => string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [role, setRole] = useState<User['role'] | null>(null);
  const [userName, setUserName] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [studentId, setStudentId] = useState<string | null>(null);
  const [loadingState, setLoadingState] = useState<LoadingState>('loading');

  const syncFromStorage = () => {
    setIsAuthenticated(authService.isAuthenticated());
    setRole(authService.getRole());
    setUserName(authService.getUserName());
    setUserEmail(authService.getUserEmail());
    setUserId(authService.getUserId());
    setStudentId(authService.getStudentId());
  };

  useEffect(() => {
    try {
      setLoadingState('loading');
      syncFromStorage();
      setLoadingState('success');
    } catch (error) {
      console.error('Erro ao verificar autenticação:', error);
      authService.logout();
      setIsAuthenticated(false);
      setRole(null);
      setUserName(null);
      setUserEmail(null);
      setUserId(null);
      setStudentId(null);
      setLoadingState('error');
    }
  }, []);

  const login = async (credentials: LoginRequest) => {
    try {
      setLoadingState('loading');
      const response = await authService.login(credentials);
      syncFromStorage();
      setLoadingState('success');
      return response.role === 'STUDENT' ? '/aluno' : '/dashboard';
    } catch (error) {
      setIsAuthenticated(false);
      setRole(null);
      setUserName(null);
      setUserEmail(null);
      setUserId(null);
      setStudentId(null);
      setLoadingState('error');
      throw error;
    }
  };

  const registerStudent = async (data: StudentRegistrationRequest) => {
    try {
      setLoadingState('loading');
      const response = await authService.registerStudent(data);
      syncFromStorage();
      setLoadingState('success');
      return response.role === 'STUDENT' ? '/aluno' : '/dashboard';
    } catch (error) {
      setIsAuthenticated(false);
      setRole(null);
      setUserName(null);
      setUserEmail(null);
      setUserId(null);
      setStudentId(null);
      setLoadingState('error');
      throw error;
    }
  };

  const updateProfile = async (data: ProfileUpdateRequest) => {
    const response = await authService.updateProfile(data);
    syncFromStorage();
    return response;
  };

  const logout = () => {
    authService.logout();
    setIsAuthenticated(false);
    setRole(null);
    setUserName(null);
    setUserEmail(null);
    setStudentId(null);
    setLoadingState('idle');
  };

  const value: AuthContextType = {
    isAuthenticated,
    role,
    userName,
    userEmail,
    userId,
    studentId,
    isStudent: role === 'STUDENT',
    isEducator: role === 'TEACHER' || role === 'ADMIN',
    loadingState,
    login,
    registerStudent,
    updateProfile,
    logout,
    getToken: () => authService.getAccessToken(),
    getHomePath: () => authService.getHomePath(),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth deve ser usado dentro de um AuthProvider');
  }
  return context;
}
