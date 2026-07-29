import { get } from './client';
import type { DashboardSummary } from '../types/dashboard';

export const getDashboardSummary = () => get<DashboardSummary>('/dashboard/summary');
