export enum Sender {
  USER = 'user',
  MODEL = 'model',
}

export interface AdditionalProperty {
  '@type'?: string;
  name: string;
  value: string;
}

export interface Product {
  productID: string;
  sku: string;
  name: string;
  image?: string[] | string;
  brand?: { name: string };
  offers?: {
    price: string;
    priceCurrency: string;
  };
  description?: string;
  category?: string;
  additionalProperty?: AdditionalProperty[] | AdditionalProperty;
}

export interface Total {
  type: string;
  display_text: string;
  amount: number;
}

export interface LineItem {
  id: string;
  item: {
    id: string;
    price: number;
    title: string;
    image_url?: string;
  };
  quantity: number;
  totals: Total[];
}

export interface FulfillmentOption {
  id: string;
  title: string;
  description: string;
  carrier?: string;
  earliest_fulfillment_time?: string;
  latest_fulfillment_time?: string;
  totals: Total[];
}

export interface FulfillmentGroup {
  id: string;
  line_item_ids: string[];
  options: FulfillmentOption[];
  selected_option_id: string;
}

export interface FulfillmentMethod {
  id: string;
  type: string;
  line_item_ids: string[];
  groups?: FulfillmentGroup[];
  destinations?: any[];
  selected_destination_id?: string;
}

export interface Fulfillment {
  methods?: FulfillmentMethod[];
  root?: {
    methods: FulfillmentMethod[];
  };
}

export interface OrderConfirmation {
  id: string;
  permalink_url?: string;
}

export interface Checkout {
  id: string;
  status: 'incomplete' | 'ready_for_complete' | 'completed' | string;
  currency: string;
  line_items: LineItem[];
  totals: Total[];
  fulfillment?: Fulfillment;
  continue_url?: string;
  order?: OrderConfirmation;
  payment?: {
    handlers?: any[];
    selected_instrument_id?: string;
  };
}

export interface ChatMessage {
  id: string;
  sender: Sender;
  text?: string;
  products?: Product[];
  checkout?: Checkout;
  isAction?: boolean;
  isLoading?: boolean;
  timestamp?: Date;
  stepNumbers?: number[];
}
