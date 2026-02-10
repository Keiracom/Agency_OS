/**
 * Mock data for Billing page
 * Will be replaced with real API calls
 */

export interface CurrentPlan {
  name: string;
  price: number;
  currency: string;
  period: string;
  renewalDate: string;
  status: 'active' | 'cancelled' | 'past_due';
}

export interface PlanMetrics {
  leads: number;
  meetingsMin: number;
  meetingsMax: number;
  clientsMin: number;
  clientsMax: number;
  channels: number;
}

export interface UsageData {
  leads: { current: number; max: number };
  meetings: { current: number; targetMin: number; targetMax: number };
  clients: { current: number; targetMin: number; targetMax: number };
}

export interface Invoice {
  id: string;
  date: string;
  description: string;
  amount: number;
  status: 'paid' | 'pending' | 'failed';
}

export interface PaymentMethod {
  type: 'mastercard' | 'visa' | 'amex';
  lastFour: string;
  expiryMonth: string;
  expiryYear: string;
}

export interface AvailablePlan {
  id: string;
  name: string;
  tagline: string;
  price: number;
  meetingsMin: number;
  meetingsMax: number;
  clientsMin: number;
  clientsMax: number;
  leads: number;
  features: string[];
  isCurrent: boolean;
  isPopular: boolean;
}

export const mockCurrentPlan: CurrentPlan = {
  name: 'Velocity',
  price: 5000,
  currency: '$',
  period: 'month',
  renewalDate: 'March 1, 2026',
  status: 'active',
};

export const mockPlanMetrics: PlanMetrics = {
  leads: 2500,
  meetingsMin: 15,
  meetingsMax: 16,
  clientsMin: 3,
  clientsMax: 4,
  channels: 5,
};

export const mockUsageData: UsageData = {
  leads: { current: 1847, max: 2500 },
  meetings: { current: 12, targetMin: 15, targetMax: 16 },
  clients: { current: 3, targetMin: 3, targetMax: 4 },
};

export const mockInvoices: Invoice[] = [
  {
    id: '1',
    date: 'Feb 1, 2026',
    description: 'Velocity Plan — Monthly',
    amount: 5000.0,
    status: 'paid',
  },
  {
    id: '2',
    date: 'Jan 1, 2026',
    description: 'Velocity Plan — Monthly',
    amount: 5000.0,
    status: 'paid',
  },
  {
    id: '3',
    date: 'Dec 1, 2025',
    description: 'Velocity Plan — Monthly',
    amount: 5000.0,
    status: 'paid',
  },
  {
    id: '4',
    date: 'Nov 1, 2025',
    description: 'Ignition Plan — Monthly',
    amount: 2500.0,
    status: 'paid',
  },
];

export const mockPaymentMethod: PaymentMethod = {
  type: 'mastercard',
  lastFour: '8492',
  expiryMonth: '09',
  expiryYear: '28',
};

export const mockAvailablePlans: AvailablePlan[] = [
  {
    id: 'ignition',
    name: 'Ignition',
    tagline: 'Launch your outbound engine',
    price: 2500,
    meetingsMin: 8,
    meetingsMax: 9,
    clientsMin: 1,
    clientsMax: 2,
    leads: 1250,
    features: [
      '1,250 leads per month',
      '5-channel outreach (Email, LinkedIn, SMS, Voice, Mail)',
      'AI-powered personalization',
      'Basic reporting dashboard',
      'Email support',
    ],
    isCurrent: false,
    isPopular: false,
  },
  {
    id: 'velocity',
    name: 'Velocity',
    tagline: 'Accelerate your growth',
    price: 5000,
    meetingsMin: 15,
    meetingsMax: 16,
    clientsMin: 3,
    clientsMax: 4,
    leads: 2500,
    features: [
      '2,500 leads per month',
      'Everything in Ignition',
      'Priority lead scoring',
      'Advanced analytics',
      'Dedicated success manager',
      'Weekly strategy calls',
    ],
    isCurrent: true,
    isPopular: false,
  },
  {
    id: 'dominance',
    name: 'Dominance',
    tagline: 'Own your market',
    price: 7500,
    meetingsMin: 31,
    meetingsMax: 32,
    clientsMin: 9,
    clientsMax: 10,
    leads: 5000,
    features: [
      '5,000 leads per month',
      'Everything in Velocity',
      'Custom integrations',
      'White-glove onboarding',
      'Direct Slack channel',
      'Quarterly business reviews',
    ],
    isCurrent: false,
    isPopular: true,
  },
];
