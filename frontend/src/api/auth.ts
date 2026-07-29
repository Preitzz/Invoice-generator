import { post } from './client';
import type { LoginRequest, LoginResponse } from '../types/user';

export const login = (payload: LoginRequest) => post<LoginResponse>('/auth/login', payload);

export const logout = () => post<{ status: string }>('/auth/logout');
