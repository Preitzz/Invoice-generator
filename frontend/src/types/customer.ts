export interface CustomerRead {
  id: string;
  name: string;
  email: string;
  phone: string | null;
  billing_address: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CustomerCreate {
  name: string;
  email: string;
  phone?: string | null;
  billing_address: string;
}

export interface CustomerUpdate {
  name?: string;
  email?: string;
  phone?: string | null;
  billing_address?: string;
}
