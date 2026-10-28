// Chaves do localStorage onde a sessão do usuário fica guardada (compartilhadas por auth.ts e api.ts).
export const AUTH_KEYS = {
  accessToken: 'accessToken',
  refreshToken: 'refreshToken',
  tokenType: 'tokenType',
  expiresIn: 'expiresIn',
  loginTime: 'loginTime',
  userId: 'userId',
  userEmail: 'userEmail',
  role: 'role',
  studentId: 'studentId',
  userName: 'userName',
} as const;

// Marca, no sessionStorage, que a sessão acabou para a tela de login avisar o usuário.
export const SESSION_EXPIRED_FLAG = 'pluseduc:sessionExpired';
