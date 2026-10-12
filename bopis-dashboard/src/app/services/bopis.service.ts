import { Injectable, signal, computed, inject } from '@angular/core';
import { initializeApp, getApps } from 'firebase/app';
import {
  getFirestore,
  collection,
  onSnapshot,
  Firestore
} from 'firebase/firestore';
import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

export type BopisOrderStatus = 'pending' | 'preparing' | 'ready_for_pickup' | 'completed' | 'cancelled';
export type BopisFulfillmentType = 'in_seat_train' | 'pickup_locker' | 'dine_in_table' | 'pickup_express';

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
  created_at: string;
  updated_at: string;
  placed_at_display?: string;
  requested_delivery_display?: string;
  lead_time_minutes?: number;
  channel_source: string;
  channel_label: string;
  status: BopisOrderStatus;
  fulfillment_type: BopisFulfillmentType;
  fulfillment_details: {
    train_number?: string;
    platform?: string;
    carriage?: string;
    seat?: string;
    delivery_time?: string;
    window?: string;
    delivery_fee_cents?: number;
    passenger_name?: string;

    location?: string;
    box_number?: string;
    pin_code?: string;
    slot_start?: string;
    slot_end?: string;

    table_number?: string;
    service_time?: string;
  };
  items: BopisOrderItem[];
  totals: BopisOrderTotals;
  buyer: {
    name: string;
    email: string;
  };
  payment_method?: string;
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
}

export interface BopisStats {
  total_orders: number;
  preparing: number;
  ready_for_pickup: number;
  completed: number;
  by_channel: Record<string, number>;
  by_fulfillment: Record<string, number>;
}

@Injectable({
  providedIn: 'root'
})
export class BopisService {
  private authService = inject(AuthService);
  private firestore: Firestore | null = null;
  private pollInterval: any = null;

  readonly orders = signal<BopisOrder[]>([]);
  readonly isLoading = signal<boolean>(true);
  readonly selectedChannelFilter = signal<string>('all');
  readonly selectedStatusFilter = signal<string>('all');
  readonly isConnectedToFirestore = signal<boolean>(false);

  readonly filteredOrders = computed(() => {
    let list = this.orders();
    const ch = this.selectedChannelFilter();
    const st = this.selectedStatusFilter();

    // Filtra per mostrare esclusivamente gli ordini delle ultime 24 ore (qualsiasi stato)
    const now = Date.now();
    const twentyFourHoursMs = 24 * 60 * 60 * 1000;
    list = list.filter(o => {
      const orderDate = new Date(o.created_at || o.updated_at).getTime();
      return isNaN(orderDate) || (now - orderDate) <= twentyFourHoursMs;
    });

    if (ch !== 'all') {
      list = list.filter(o => o.channel_source === ch);
    }
    if (st !== 'all') {
      list = list.filter(o => o.status === st);
    }
    return list;
  });

  readonly stats = computed<BopisStats>(() => {
    const now = Date.now();
    const twentyFourHoursMs = 24 * 60 * 60 * 1000;
    const list = this.orders().filter(o => {
      const orderDate = new Date(o.created_at || o.updated_at).getTime();
      return isNaN(orderDate) || (now - orderDate) <= twentyFourHoursMs;
    });

    const stats: BopisStats = {
      total_orders: list.length,
      preparing: list.filter(o => o.status === 'preparing').length,
      ready_for_pickup: list.filter(o => o.status === 'ready_for_pickup').length,
      completed: list.filter(o => o.status === 'completed').length,
      by_channel: {},
      by_fulfillment: {}
    };

    for (const o of list) {
      stats.by_channel[o.channel_source] = (stats.by_channel[o.channel_source] || 0) + 1;
      stats.by_fulfillment[o.fulfillment_type] = (stats.by_fulfillment[o.fulfillment_type] || 0) + 1;
    }
    return stats;
  });

  constructor() {
    this.initFirestoreListener();
    this.fetchOrdersRest();

    this.pollInterval = setInterval(() => {
      this.fetchOrdersRest();
    }, 4000);
  }

  private initFirestoreListener(): void {
    try {
      const app = getApps().length === 0 ? initializeApp(environment.firebase) : getApps()[0];
      this.firestore = getFirestore(app);
      const ordersCol = collection(this.firestore, 'bopis_orders');

      onSnapshot(
        ordersCol,
        (snapshot) => {
          this.isConnectedToFirestore.set(true);
          const firestoreOrders: BopisOrder[] = [];
          snapshot.forEach((doc) => {
            firestoreOrders.push(doc.data() as BopisOrder);
          });
          if (firestoreOrders.length > 0) {
            firestoreOrders.sort(
              (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
            );
            this.orders.set(firestoreOrders);
            this.isLoading.set(false);
          }
        },
        (error) => {
          console.warn('Firestore snapshot listener non disponibile (fallback REST):', error.message);
          this.isConnectedToFirestore.set(false);
        }
      );
    } catch (e) {
      console.warn('Inizializzazione Firestore saltata, uso REST:', e);
      this.isConnectedToFirestore.set(false);
    }
  }

  async fetchOrdersRest(): Promise<void> {
    try {
      const email = this.authService.user()?.email || 'merchant@agentic-commerce.demo';
      const res = await fetch(`${environment.bopisApiUrl}/bopis/orders?hours=24`, {
        headers: {
          'X-User-Email': email
        }
      });
      if (res.ok) {
        const data: BopisOrder[] = await res.json();
        if (!this.isConnectedToFirestore() || data.length >= this.orders().length) {
          data.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
          this.orders.set(data);
        }
        this.isLoading.set(false);
      }
    } catch (err) {
      console.warn('Fetch ordini REST fallito:', err);
    }
  }

  async updateOrderStatus(orderId: string, newStatus: BopisOrderStatus): Promise<void> {
    this.orders.update((list) =>
      list.map((o) =>
        o.order_id === orderId
          ? { ...o, status: newStatus, updated_at: new Date().toISOString() }
          : o
      )
    );

    try {
      const email = this.authService.user()?.email || 'merchant@agentic-commerce.demo';
      const res = await fetch(`${environment.bopisApiUrl}/bopis/orders/${orderId}/status`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Email': email
        },
        body: JSON.stringify({ status: newStatus })
      });
      if (res.ok) {
        const updated = await res.json();
        this.orders.update((list) =>
          list.map((o) => (o.order_id === orderId ? updated : o))
        );
      }
    } catch (err) {
      console.error('Errore aggiornamento stato ordine:', err);
    }
  }
}
