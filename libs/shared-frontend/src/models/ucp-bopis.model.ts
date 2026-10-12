// Copyright 2026 UCP Authors / GDG DevFest Milano 2026

export interface NutritionalValues {
  energy_kcal?: number;
  fat_g?: number;
  saturates_g?: number;
  carbohydrates_g?: number;
  sugars_g?: number;
  fiber_g?: number;
  protein_g?: number;
  salt_g?: number;
}

export interface NutritionalInfo {
  nutri_score?: 'A' | 'B' | 'C' | 'D' | 'E';
  reference_quantity?: string;
  per_100g?: NutritionalValues;
  per_serving?: NutritionalValues;
}

export interface ProcessingLevel {
  nova_group?: 1 | 2 | 3 | 4;
  nova_name?: string;
  is_ultra_processed?: boolean;
  description?: string;
}

export interface DietaryProfile {
  allergens?: string[];
  allergens_free_claim?: string[];
  dietary_tags?: string[];
  aic_gluten_free_certified?: boolean;
  lactose_free?: boolean;
}

export interface CoffeeProfile {
  species?: string;
  origin_country?: string;
  region_estate?: string;
  altitude_masl?: number;
  process_method?: string;
  roast_profile?: string;
  brew_method?: string;
  extraction_time_hours?: number;
  flavor_notes?: string[];
  is_specialty_grade?: boolean;
}

export interface TravelProfile {
  shelf_life_hours?: number;
  temperature_stability?: string;
  mess_free_rating?: number;
  smart_locker_suitable?: boolean;
}

export interface TechSpecs {
  wattage_w?: number;
  technology?: string;
  ports?: string[];
  fast_charge_protocols?: string[];
  cable_included?: boolean;
}

export interface UcpProduct {
  id: string;
  name: string;
  category: string;
  price_cents: number;
  price: number;
  is_hot: boolean;
  image_url: string;
  description: string;
  packaging_type?: 'prepackaged' | 'fresh_service';
  net_weight_g?: number;
  nutrition?: NutritionalInfo;
  processing_level?: ProcessingLevel;
  dietary_profile?: DietaryProfile;
  coffee_profile?: CoffeeProfile;
  travel_profile?: TravelProfile;
  tech_specs?: TechSpecs;
}

export interface BopisOrderItem {
  id: string;
  title: string;
  quantity: number;
  price_cents: number;
  image_url?: string;
}

export interface BopisOrderTotals {
  subtotal_cents: number;
  delivery_fee_cents: number;
  total_cents: number;
  currency: string;
}

export interface BopisOrder {
  order_id: string;
  channel_source: 'ucp_direct_a2a' | 'web_mcp' | 'two_agent_a2a' | 'ucp_rest';
  channel_label: string;
  status: 'preparing' | 'ready_for_pickup' | 'completed' | 'cancelled';
  fulfillment_type: 'pickup_locker' | 'in_seat_train' | 'pickup_express' | 'table_service';
  fulfillment_details: {
    location?: string;
    box_number?: string;
    pin_code?: string;
    slot_start?: string;
    slot_end?: string;
    train_number?: string;
    platform?: string;
    carriage?: string;
    seat?: string;
    delivery_time?: string;
    window?: string;
    table_number?: string;
    service_time?: string;
    delivery_fee_cents?: number;
    lead_time_minutes?: number;
  };
  items: BopisOrderItem[];
  totals: BopisOrderTotals;
  buyer: {
    name: string;
    email: string;
  };
  payment_method?: 'gpay' | 'card' | 'ap2';
  payment_info?: {
    method: string;
    label: string;
  };
  ap2_verification?: {
    verified: boolean;
    mandate_type: string;
    credential_manager: string;
    token_id?: string;
  };
  placed_at_display?: string;
  requested_delivery_display?: string;
  lead_time_minutes?: number;
  created_at?: string;
  updated_at?: string;
}

export interface ProposalFulfillmentOption {
  id: string; // 'in_seat_train' | 'pickup_express' | 'pickup_locker'
  label: string; // '🚆 Consegna al Posto Treno'
  badge?: string; // 'Consigliato' | 'Più veloce (5 min)' | 'Contactless'
  details: string; // 'Carrozza 6, Posto 21B • Binario 18 • Finestra 1 min (13:50)'
  delivery_fee_cents: number;
  total_cents: number;
  estimated_time?: string;
  is_recommended?: boolean;
}

export interface ProposalItemDetail {
  id: string;
  title: string;
  name?: string;
  price_cents: number;
  quantity?: number;
  description?: string;
  image_url?: string;
  is_hot?: boolean;
  category?: string;
  dietary?: string;
  packaging_type?: 'prepackaged' | 'fresh_service';
  net_weight_g?: number;
  nutri_score?: 'A' | 'B' | 'C' | 'D' | 'E';
  nova_group?: 1 | 2 | 3 | 4;
  salt_g?: number;
  protein_g?: number;
  dietary_tags?: string[];
  allergens_free?: string[];
  coffee_profile?: CoffeeProfile;
}

export interface ShopperProposal {
  proposal_id: string;
  protocol: 'a2a' | 'ucp_rest';
  merchant_name: string;
  item: {
    id: string;
    title: string;
    price_cents: number;
    description: string;
    image_url: string;
    is_hot: boolean;
    category?: string;
    dietary?: string;
    packaging_type?: 'prepackaged' | 'fresh_service';
    nutri_score?: 'A' | 'B' | 'C' | 'D' | 'E';
    nova_group?: 1 | 2 | 3 | 4;
    salt_g?: number;
    protein_g?: number;
    coffee_profile?: CoffeeProfile;
    items?: ProposalItemDetail[];
  };
  items?: ProposalItemDetail[];
  fulfillment_options: ProposalFulfillmentOption[];
  selected_option_id: string;
  ticket?: any;
  buyer?: {
    name: string;
    email: string;
  };
  notes?: string;
}
