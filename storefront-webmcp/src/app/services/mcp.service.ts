import { Injectable, signal, computed, inject, effect } from '@angular/core';
import { environment } from '../../environments/environment';
import { setActiveMcpService, webMcpTools } from '../webmcp.tools';
import { AuthService } from './auth.service';

export interface McpTool {
  name: string;
  description: string;
  inputSchema: any;
}

export interface UserProfile {
  uid?: string;
  name: string;
  email: string;
  loyaltyTier: string;
  loyaltyCode: string;
  photoURL?: string | null;
}

import {
  NutritionalInfo,
  ProcessingLevel,
  DietaryProfile,
  CoffeeProfile,
  TravelProfile,
  TechSpecs,
} from '@ucp/shared-frontend';

export interface StoreProduct {
  id: string;
  name: string;
  price: number;
  price_cents: number;
  currency: string;
  description: string;
  category: string;
  is_hot: boolean;
  image_url: string;
  packaging_type?: 'prepackaged' | 'fresh_service';
  net_weight_g?: number;
  nutrition?: NutritionalInfo;
  processing_level?: ProcessingLevel;
  dietary_profile?: DietaryProfile;
  coffee_profile?: CoffeeProfile;
  travel_profile?: TravelProfile;
  tech_specs?: TechSpecs;
}

export interface CartItem {
  product_id: string;
  name: string;
  price: number;
  price_cents: number;
  quantity: number;
  is_hot: boolean;
  image_url: string;
}

export interface CartFulfillment {
  method: 'pickup_locker' | 'pickup_express' | 'in_seat_train' | 'table_service';
  label: string;
  location?: string;
  window?: string;
  lead_time_minutes?: number;
  box_number?: string;
  pin_code?: string;
  delivery_time?: string;
  service_time?: string;
  train_number?: string;
  platform?: string;
  carriage?: string;
  seat?: string;
  table_number?: string;
  delivery_fee_cents?: number;
}

export interface CartState {
  cart_id: string;
  items: CartItem[];
  subtotal_cents: number;
  delivery_fee_cents: number;
  total_cents: number;
  contains_hot_items: boolean;
  fulfillment?: CartFulfillment;
}

export interface McpTraceStep {
  step: number;
  tool: string;
  arguments: any;
  result: any;
  mcp_request: any;
  mcp_response: any;
  timestamp: string;
}

export interface ShopperMissionResult {
  status: string;
  prompt: string;
  steps: McpTraceStep[];
  total_steps: number;
  order?: any;
  final_answer: string;
  completed_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class McpService {
  private readonly baseUrl = environment.mcpApiUrl;

  readonly tools = signal<McpTool[]>([]);
  readonly products = signal<StoreProduct[]>([]);
  readonly isLoading = signal<boolean>(false);
  readonly selectedCategory = signal<string>('all');
  readonly searchQuery = signal<string>('');
  readonly missionResult = signal<ShopperMissionResult | null>(null);
  readonly isMcpConnected = signal<boolean>(true);

  // Authentication & Traveler Profile (Google + Firebase Auth)
  readonly authService = inject(AuthService);
  readonly currentUser = computed<UserProfile | null>(() => {
    const u = this.authService.user();
    if (!u) return null;
    return {
      uid: u.uid,
      name: u.displayName || u.email || 'Viaggiatore Google',
      email: u.email || 'viaggiatore@devfest.it',
      loyaltyTier: u.loyaltyTier || 'FrecciaClub Gold',
      loyaltyCode: u.loyaltyCode || (u.uid ? 'FF-' + u.uid.slice(-6).toUpperCase() : 'FF-884920'),
      photoURL: u.photoURL || null
    };
  });

  // Human-Present Payment State
  readonly selectedPaymentMethod = signal<'gpay' | 'card' | 'ap2'>('gpay');
  readonly isProcessingPayment = signal<boolean>(false);

  // Human & WebMCP In-Page E-Commerce Shopping State
  readonly currentCart = signal<CartState | null>(null);
  readonly isCartOpen = signal<boolean>(false);
  readonly orderSuccessBanner = signal<any | null>(null);

  // View Navigation & Authenticated User Orders
  readonly activeView = signal<'catalog' | 'orders' | 'about'>('catalog');
  readonly allOrders = signal<any[]>([]);
  readonly isOrdersLoading = signal<boolean>(false);

  readonly userOrders = computed(() => {
    const u = this.currentUser();
    if (!u) return [];
    // Gli ordini sono già filtrati dal backend tramite il parametro buyer_email (Modalità 1: Matching per Email)
    return this.allOrders();
  });

  // Fulfillment Selection Signals (Synchronized with WebMCP Agent Tools)
  readonly selectedFulfillment = signal<'pickup_locker' | 'pickup_express' | 'in_seat_train' | 'table_service'>('pickup_express');
  readonly lockerSlotTime = signal<string>(this.computeDefaultLockerSlot());
  readonly lockerPin = signal<string>('8492');
  readonly trainNumber = signal<string>('Frecciarossa 9540');
  readonly trainPlatform = signal<string>('Binario 14');
  readonly trainCarriage = signal<string>('Carrozza 4');
  readonly trainSeat = signal<string>('Posto 12D');
  readonly trainDeliveryTime = signal<string>(this.computeDefaultTrainTime());
  readonly tableNumber = signal<string>('Tavolo 5');

  readonly cartItemsCount = computed(() => {
    const c = this.currentCart();
    if (!c) return 0;
    return c.items.reduce((acc, i) => acc + i.quantity, 0);
  });
  readonly hasHotItems = computed(() => {
    return this.currentCart()?.contains_hot_items ?? false;
  });
  readonly fulfillmentError = signal<string | null>(null);
  readonly lastHumanOrder = signal<any | null>(null);

  // REACTIVE LIVE FILTERED PRODUCTS (Updated synchronously by WebMCP tools)
  readonly filteredProducts = computed(() => {
    let list = this.products();
    const cat = this.selectedCategory();
    const query = this.searchQuery().trim().toLowerCase();

    // 1. Filter by category
    if (cat === 'hot') {
      list = list.filter(p => p.is_hot);
    } else if (cat === 'cold') {
      list = list.filter(p => !p.is_hot && !p.category.includes('Tech') && !p.category.includes('Audio') && !p.category.includes('Elettronica'));
    } else if (cat === 'tech') {
      list = list.filter(p => p.category.includes('Tech') || p.category.includes('Audio') || p.category.includes('Elettronica'));
    } else if (cat === 'sandwiches') {
      list = list.filter(p => {
        const text = `${p.name} ${p.category} ${p.description}`.toLowerCase();
        return text.includes('panin') || text.includes('toast') || text.includes('ciabatta') || text.includes('focaccia') || text.includes('sandwich');
      });
    } else if (cat === 'vegan') {
      list = list.filter(p => {
        const tags = (p.dietary_profile?.dietary_tags || []).join(' ').toLowerCase();
        return tags.includes('vegan') || p.name.toLowerCase().includes('vegan');
      });
    } else if (cat === 'coffee') {
      list = list.filter(p => {
        const text = `${p.name} ${p.category}`.toLowerCase();
        return text.includes('caff') || text.includes('espresso') || text.includes('cappuccino');
      });
    } else if (cat === 'drinks') {
      list = list.filter(p => {
        const text = `${p.name} ${p.category}`.toLowerCase();
        return text.includes('bevand') || text.includes('spremuta') || text.includes('acqua');
      });
    } else if (cat === 'specialty') {
      list = list.filter(p => p.coffee_profile?.is_specialty_grade || p.id === 'COFFEE-017');
    } else if (cat === 'gluten_free') {
      list = list.filter(p => p.dietary_profile?.aic_gluten_free_certified || p.dietary_profile?.allergens_free_claim?.includes('Glutine'));
    } else if (cat === 'lactose_free') {
      list = list.filter(p => p.dietary_profile?.lactose_free || p.dietary_profile?.allergens_free_claim?.includes('Lattosio'));
    } else if (cat === 'high_protein') {
      list = list.filter(p => {
        const p100 = p.nutrition?.per_100g?.protein_g ?? 0;
        const pserv = p.nutrition?.per_serving?.protein_g ?? 0;
        return p100 >= 10 || pserv >= 15;
      });
    } else if (cat === 'low_salt') {
      list = list.filter(p => {
        const s100 = p.nutrition?.per_100g?.salt_g;
        const sserv = p.nutrition?.per_serving?.salt_g;
        return (s100 !== undefined && s100 <= 0.5) || (sserv !== undefined && sserv <= 1.0);
      });
    } else if (cat === 'clean_nova') {
      list = list.filter(p => p.processing_level?.nova_group === 1 || p.processing_level?.nova_group === 3);
    }

    // 2. Filter by search query (free-text search matching name, description, category, tags)
    if (query) {
      // Ignora stopword colloquiali e verbi d'azione per supportare query naturali (es. "aggiungi al carrello il panino vegano")
      const stopwords = new Set([
        'mostrami', 'fammi', 'vedere', 'cerca', 'trova', 'vorrei', 'prendimi', 'dammi', 'per', 'favore',
        'aggiungi', 'aggiugi', 'aggiungimi', 'metti', 'inserisci', 'prendi', 'carrello',
        'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una', 'dei', 'degli', 'delle',
        'al', 'allo', 'alla', 'ai', 'agli', 'alle', 'nel', 'nello', 'nella', 'nei', 'negli', 'nelle'
      ]);
      const rawWords = query.split(/\s+/).filter(w => w.length > 0);
      const searchWords = rawWords.filter(w => !stopwords.has(w));
      const wordsToMatch = searchWords.length > 0 ? searchWords : rawWords;

      list = list.filter(p => {
        const tags = (p.dietary_profile?.dietary_tags || []).join(' ');
        const flavor = (p.coffee_profile?.flavor_notes || []).join(' ');
        const text = `${p.name} ${p.description} ${p.category} ${p.id} ${tags} ${flavor}`.toLowerCase();

        return wordsToMatch.every(w => {
          if (text.includes(w)) return true;
          if (w.length > 4 && 'oiea'.includes(w[w.length - 1])) {
            const stem = w.slice(0, -1);
            if (text.includes(stem)) return true;
          }
          return false;
        });
      });
    }

    return list;
  });

  constructor() {
    setActiveMcpService(this);
    this.restoreCartFromSession();
    this.initData();

    // Automatically synchronize currentCart with sessionStorage
    effect(() => {
      const cart = this.currentCart();
      if (typeof window !== 'undefined' && window.sessionStorage) {
        if (cart && cart.items && cart.items.length > 0) {
          window.sessionStorage.setItem('mcp_storefront_cart', JSON.stringify(cart));
        } else {
          window.sessionStorage.removeItem('mcp_storefront_cart');
        }
      }
    });
  }

  private async restoreCartFromSession(): Promise<void> {
    if (typeof window === 'undefined' || !window.sessionStorage) return;
    try {
      const saved = window.sessionStorage.getItem('mcp_storefront_cart');
      if (!saved) return;
      const parsed: CartState = JSON.parse(saved);
      if (!parsed || !parsed.cart_id || !parsed.items || parsed.items.length === 0) return;

      // Immediately restore local state so UI updates without flicker
      this.currentCart.set(parsed);
      if (parsed.fulfillment?.method) {
        this.selectedFulfillment.set(parsed.fulfillment.method);
        if (parsed.fulfillment.delivery_time) {
          this.lockerSlotTime.set(parsed.fulfillment.delivery_time);
        }
      }

      // Verify / re-sync with backend to ensure the cart is still alive on the server
      const res = await fetch(`${this.baseUrl}/mcp/cart/${parsed.cart_id}`);
      if (res.ok) {
        const serverCart = await res.json();
        this.currentCart.set(serverCart);
      } else {
        // If server was restarted and lost in-memory cart, re-create and re-add items
        await this.recreateCartOnServer(parsed);
      }
    } catch (err) {
      console.warn('Errore ripristino carrello da sessione:', err);
    }
  }

  private async recreateCartOnServer(localCart: CartState): Promise<void> {
    try {
      const res = await this.callMcpToolDirect('create_cart', {});
      const newCartId = res.cart?.cart_id;
      if (!newCartId) return;

      let updatedCart: any = res.cart;
      for (const item of localCart.items) {
        const addRes = await this.callMcpToolDirect('add_to_cart', {
          cart_id: newCartId,
          product_id: item.product_id,
          quantity: item.quantity
        });
        if (addRes.cart) updatedCart = addRes.cart;
      }

      if (localCart.fulfillment?.method) {
        try {
          const fulRes = await this.callMcpToolDirect('configure_fulfillment', {
            cart_id: newCartId,
            method: localCart.fulfillment.method,
            details: {
              slot_time: this.lockerSlotTime(),
              pin_code: this.lockerPin(),
              table_number: this.tableNumber(),
              train_number: this.trainNumber(),
              carriage: this.trainCarriage(),
              seat: this.trainSeat(),
              platform: this.trainPlatform(),
              delivery_time: this.trainDeliveryTime()
            }
          });
          if (fulRes.cart) updatedCart = fulRes.cart;
        } catch {
          // ignore
        }
      }

      this.currentCart.set(updatedCart);
    } catch (e) {
      console.warn('Impossibile ricreare carrello sul server:', e);
    }
  }

  async loginWithGoogle(): Promise<void> {
    await this.authService.loginWithGoogle();
  }

  async logout(): Promise<void> {
    await this.authService.logout();
  }

  loginDemoUser(): void {
    this.authService.loginDemoUser();
  }

  toggleLogin(): void {
    if (this.authService.isAuthenticated()) {
      this.authService.logout();
    } else {
      this.authService.loginDemoUser();
    }
  }

  computeDefaultLockerSlot(): string {
    const now = new Date();
    now.setMinutes(now.getMinutes() + 35);
    const rem = now.getMinutes() % 10;
    if (rem !== 0) {
      now.setMinutes(now.getMinutes() + (10 - rem));
    }
    return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  }

  computeDefaultTrainTime(): string {
    const now = new Date();
    now.setMinutes(now.getMinutes() + 35);
    return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  }

  // --- IN-BROWSER AI CONTEXT EXPORTER (MARKDOWN SNAPSHOT) ---

  getPageContextMarkdown(): string {
    const visible = this.filteredProducts();
    const cart = this.currentCart();
    const cartItems = cart?.items || [];
    const cat = this.selectedCategory();
    const q = this.searchQuery();
    const ful = this.selectedFulfillment();

    const lines: string[] = [];
    lines.push('# [CONTESTO VISTA ATTUALE - Milano Centrale Storefront]');
    lines.push(`• Filtro attivo: ${cat !== 'all' ? cat : 'Tutti i prodotti'}${q ? ` | Ricerca: "${q}"` : ''}`);
    lines.push('');
    lines.push(`## Prodotti visibili a video (${visible.length}):`);
    if (visible.length === 0) {
      lines.push('*(Nessun prodotto corrisponde ai filtri correnti)*');
    } else {
      visible.forEach(p => {
        const lockerSafe = !p.is_hot && !p.category.includes('Tech') && !p.category.includes('Audio');
        const tags = (p.dietary_profile?.dietary_tags || []).join(', ');
        lines.push(`- **ID:** \`${p.id}\` | **Nome:** ${p.name} | **Prezzo:** €${p.price.toFixed(2)} | **Smart Locker:** ${lockerSafe ? 'Idoneo (Freddo)' : 'Non Idoneo (Caldo)'}${tags ? ` | **Tag:** ${tags}` : ''}`);
      });
    }
    lines.push('');
    lines.push('## Stato del Carrello:');
    if (cartItems.length === 0) {
      lines.push('• Carrello vuoto (0 articoli, totale €0.00)');
    } else {
      lines.push(`• Articoli nel carrello (${cartItems.length}):`);
      cartItems.forEach(i => {
        lines.push(`  - ${i.quantity}x ${i.name} (€${((i.price_cents * i.quantity) / 100).toFixed(2)})`);
      });
      lines.push(`• Totale carrello: €${((cart?.total_cents || 0) / 100).toFixed(2)}`);
    }
    lines.push('');
    lines.push(`## Ritiro Stazione Selezionato: ${ful ? ful : 'Nessuno'}`);
    lines.push('');
    lines.push('## Comandi WebMCP disponibili sulla pagina:');
    lines.push('- `searchCatalog({ query: "..." })` -> compila la search bar e filtra i prodotti a video');
    lines.push('- `addToCart({ product_id: "..." })` -> aggiunge il prodotto scelto al carrello');
    lines.push('- `configureFulfillment({ method: "pickup_locker" | "pickup_express" })` -> imposta il ritiro allo Smart Locker o Banco');
    lines.push('- `prepareCheckout()` -> apre il cassetto di checkout a video per autorizzazione Human-Present');

    return lines.join('\n');
  }

  async copyPageContextToClipboard(): Promise<boolean> {
    if (typeof navigator === 'undefined' || !navigator.clipboard) return false;
    try {
      const md = this.getPageContextMarkdown();
      await navigator.clipboard.writeText(md);
      return true;
    } catch (e) {
      console.warn('Errore copia contesto negli appunti:', e);
      return false;
    }
  }

  async initData(): Promise<void> {
    try {
      await Promise.all([this.loadTools(), this.loadProducts(), this.fetchUserOrders()]);
      this.isMcpConnected.set(true);
      this.registerBrowserWebMcpTools();
    } catch (e) {
      console.warn('Errore connessione MCP:', e);
      this.isMcpConnected.set(false);
    }
  }

  async loadTools(): Promise<void> {
    const res = await fetch(`${this.baseUrl}/mcp/tools`);
    if (res.ok) {
      const data = await res.json();
      this.tools.set(data.tools || []);
    }
  }

  async loadProducts(): Promise<void> {
    const res = await fetch(`${this.baseUrl}/mcp/products`);
    if (res.ok) {
      const data = await res.json();
      this.products.set(data || []);
    }
  }

  async fetchUserOrders(): Promise<void> {
    this.isOrdersLoading.set(true);
    try {
      const userEmail = this.currentUser()?.email || 'alex.traveler@example.com';
      const res = await fetch(`${this.baseUrl}/bopis/orders?buyer_email=${encodeURIComponent(userEmail)}`, {
        headers: {
          'X-User-Email': userEmail
        }
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          data.sort((a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime());
          this.allOrders.set(data);
        }
      }
    } catch (err) {
      console.warn('Errore recupero ordini utente:', err);
    } finally {
      this.isOrdersLoading.set(false);
    }
  }

  // --- HUMAN SHOPPING METHODS VIA MCP TOOLS ---

  async ensureCart(): Promise<string> {
    const current = this.currentCart();
    if (current?.cart_id) {
      return current.cart_id;
    }
    const res = await this.callMcpToolDirect('create_cart', {});
    const cart: CartState = res.cart;
    this.currentCart.set(cart);
    return cart.cart_id;
  }

  async addItemToCart(product: StoreProduct, qty = 1): Promise<void> {
    this.isLoading.set(true);
    this.fulfillmentError.set(null);
    try {
      const cartId = await this.ensureCart();
      const res = await this.callMcpToolDirect('add_to_cart', {
        cart_id: cartId,
        product_id: product.id,
        quantity: qty
      });
      const updatedCart: CartState = res.cart;
      this.currentCart.set(updatedCart);
    } finally {
      this.isLoading.set(false);
    }
  }

  async updateItemQuantity(productId: string, delta: number): Promise<void> {
    const cart = this.currentCart();
    if (!cart) return;
    const item = cart.items.find(i => i.product_id === productId);
    if (!item) return;

    this.isLoading.set(true);
    try {
      if (delta > 0) {
        const res = await this.callMcpToolDirect('add_to_cart', {
          cart_id: cart.cart_id,
          product_id: productId,
          quantity: 1
        });
        const updatedCart: CartState = res.cart;
        this.currentCart.set(updatedCart);
      } else if (delta < 0) {
        const res = await this.callMcpToolDirect('remove_from_cart', {
          cart_id: cart.cart_id,
          product_id: productId,
          quantity: 1
        });
        const updatedCart: CartState = res.cart;
        this.currentCart.set(updatedCart);
      }

      // Check if thermal restriction is now cleared
      const current = this.currentCart();
      if (current && !current.contains_hot_items) {
        if (this.fulfillmentError() && (this.fulfillmentError()!.includes('Termica') || this.fulfillmentError()!.includes('caldi'))) {
          this.fulfillmentError.set(null);
        }
        // If Smart Locker was previously selected, re-configure it now that hot items are gone
        if (this.selectedFulfillment() === 'pickup_locker') {
          await this.applyFulfillment('pickup_locker', {
            slot_time: this.lockerSlotTime(),
            pin_code: this.lockerPin(),
            box_number: 'Box #14'
          });
        }
      }
    } catch (err: any) {
      console.warn('Errore chiamata MCP per aggiornamento carrello, applico fallback locale:', err);
      if (delta < 0 && item.quantity > 1) {
        item.quantity -= 1;
      } else if (delta < 0 && item.quantity <= 1) {
        cart.items = cart.items.filter(i => i.product_id !== productId);
      } else if (delta > 0) {
        item.quantity += 1;
      }
      this._refreshLocalCartCalculations(cart);
      if (!cart.contains_hot_items && this.fulfillmentError() && this.fulfillmentError()!.includes('Termica')) {
        this.fulfillmentError.set(null);
      }
    } finally {
      this.isLoading.set(false);
    }
  }

  private _refreshLocalCartCalculations(cart: CartState): void {
    const subtotal = cart.items.reduce((acc, i) => acc + (i.price_cents * i.quantity), 0);
    cart.subtotal_cents = subtotal;
    cart.contains_hot_items = cart.items.some(i => i.is_hot);
    cart.total_cents = subtotal + cart.delivery_fee_cents;
    this.currentCart.set({ ...cart });
  }

  async applyFulfillment(method: string, details: any): Promise<boolean> {
    const cart = this.currentCart();
    if (!cart) return false;
    this.isLoading.set(true);
    this.fulfillmentError.set(null);
    try {
      const res = await this.callMcpToolDirect('configure_fulfillment', {
        cart_id: cart.cart_id,
        method,
        details
      });
      const updatedCart: CartState = res.cart;
      this.currentCart.set(updatedCart);
      this.fulfillmentError.set(null);
      return true;
    } catch (err: any) {
      let msg = err.message || String(err);
      try {
        const p = JSON.parse(msg);
        if (p && typeof p === 'object' && p.error) msg = p.error;
      } catch {}
      this.fulfillmentError.set(msg);
      return false;
    } finally {
      this.isLoading.set(false);
    }
  }

  // --- HUMAN-PRESENT SIMULATED PAYMENT & ORDER AUTHORIZATION ---

  async authorizeAndPay(): Promise<any> {
    const user = this.currentUser();
    if (!user) {
      throw new Error('Accesso viaggiatore richiesto per autorizzare il pagamento.');
    }
    const cart = this.currentCart();
    if (!cart || cart.items.length === 0) {
      throw new Error('Il carrello è vuoto.');
    }

    this.isProcessingPayment.set(true);
    this.fulfillmentError.set(null);
    try {
      // 1. Simulate authentication and secure payment verification (PSD2 SCA / AP2 Protocol)
      await new Promise(r => setTimeout(r, 800));

      // 2. Submit order to backend BOPIS engine
      const paymentMethod = this.selectedPaymentMethod();
      const res = await this.callMcpToolDirect('checkout_cart', {
        cart_id: cart.cart_id,
        buyer_name: user.name,
        buyer_email: user.email,
        payment_method: paymentMethod
      });
      const order = res.order || res;
      order.payment_method = paymentMethod;
      if (paymentMethod !== 'ap2') {
        order.ap2_mandate_id = null;
        order.ap2_verification = null;
      }
      this.lastHumanOrder.set(order);
      this.orderSuccessBanner.set(order);
      this.currentCart.set(null);
      this.isCartOpen.set(false);
      this.fetchUserOrders();
      return order;
    } catch (err: any) {
      this.fulfillmentError.set(err.message || String(err));
      throw err;
    } finally {
      this.isProcessingPayment.set(false);
    }
  }

  // --- REACTIVE WEBMCP EXECUTION BRIDGE (UPDATES ANGULAR SIGNALS & DOM IN REAL-TIME) ---

  async executeWebMcpTool(name: string, args: any = {}): Promise<any> {
    console.log(`%c[WebMCP In-Page Execution] Invoked Tool: ${name}`, 'color: #38bdf8; font-weight: bold;', args);
    try {
      switch (name) {
        case 'searchCatalog':
        case 'search_catalog': {
          const q = (args.query || '').trim();
          this.searchQuery.set(q);

          if (args.category) {
            const cat = String(args.category).toLowerCase();
            if (cat.includes('panin') || cat.includes('sand')) this.selectedCategory.set('sandwiches');
            else if (cat.includes('veg')) this.selectedCategory.set('vegan');
            else if (cat.includes('caff') || cat.includes('coff')) this.selectedCategory.set('coffee');
            else if (cat.includes('bevand') || cat.includes('drink')) this.selectedCategory.set('drinks');
            else if (cat.includes('cald') || cat.includes('hot')) this.selectedCategory.set('hot');
            else if (cat.includes('fredd') || cat.includes('cold') || cat.includes('locker')) this.selectedCategory.set('cold');
            else if (cat.includes('tech') || cat.includes('elettronica') || cat.includes('audio')) this.selectedCategory.set('tech');
            else if (cat.includes('glutin') || cat.includes('aic')) this.selectedCategory.set('gluten_free');
            else if (cat.includes('lattos')) this.selectedCategory.set('lactose_free');
            else if (cat.includes('protein')) this.selectedCategory.set('high_protein');
            else if (cat.includes('spec')) this.selectedCategory.set('specialty');
            else this.selectedCategory.set('all');
          } else {
            // Se la query è libera senza categoria esplicita, non vincoliamo a una categoria ristretta
            this.selectedCategory.set('all');
          }

          // Call backend MCP tool for protocol compliance
          const res = await this.callMcpToolDirect('search_catalog', args);
          if (res && Array.isArray(res.results) && res.results.length > 0) {
            return res;
          }

          // Resilient Fallback: se il backend non trova risultati (o differisce per stemming/filtri),
          // restituisce i prodotti corrispondenti filtrati reattivamente nel catalogo locale
          const localResults = this.filteredProducts();
          if (localResults.length > 0) {
            return {
              results: localResults.map(p => ({
                id: p.id,
                name: p.name,
                price: p.price,
                price_cents: p.price_cents,
                category: p.category,
                is_hot: p.is_hot,
                locker_compatible: !p.is_hot && !p.category.includes('Tech')
              })),
              count: localResults.length
            };
          }

          return res;
        }

        case 'selectCategory':
        case 'filterCategory':
        case 'select_category':
        case 'filter_category': {
          let cat = String(args.category || 'all').toLowerCase();
          if (cat.includes('panin') || cat.includes('sand')) cat = 'sandwiches';
          else if (cat.includes('veg')) cat = 'vegan';
          else if (cat.includes('caff') || cat.includes('coff')) cat = 'coffee';
          else if (cat.includes('bevand') || cat.includes('drink')) cat = 'drinks';
          else if (cat.includes('cald') || cat.includes('hot')) cat = 'hot';
          else if (cat.includes('fredd') || cat.includes('cold') || cat.includes('locker')) cat = 'cold';
          else if (cat.includes('tech') || cat.includes('elettronica') || cat.includes('audio')) cat = 'tech';
          else if (cat.includes('glutin') || cat.includes('aic')) cat = 'gluten_free';
          else if (cat.includes('lattos')) cat = 'lactose_free';
          else if (cat.includes('protein')) cat = 'high_protein';
          else if (cat.includes('spec')) cat = 'specialty';
          else cat = 'all';

          this.searchQuery.set('');
          this.selectedCategory.set(cat);
          const results = this.filteredProducts();
          return {
            success: true,
            category: cat,
            count: results.length,
            results: results.map(p => ({
              id: p.id,
              name: p.name,
              price: p.price,
              price_cents: p.price_cents,
              category: p.category,
              is_hot: p.is_hot,
              locker_compatible: !p.is_hot && !p.category.includes('Tech')
            }))
          };
        }

        case 'filterHotFood': {
          this.searchQuery.set('');
          this.selectedCategory.set('hot');
          const results = this.filteredProducts();
          return { success: true, category: 'hot', count: results.length, results };
        }

        case 'filterLockerSafe': {
          this.searchQuery.set('');
          this.selectedCategory.set('cold');
          const results = this.filteredProducts();
          return { success: true, category: 'cold', count: results.length, results };
        }

        case 'filterTech': {
          this.searchQuery.set('');
          this.selectedCategory.set('tech');
          const results = this.filteredProducts();
          return { success: true, category: 'tech', count: results.length, results };
        }

        case 'getProductDetails':
        case 'get_product_details': {
          return await this.callMcpToolDirect('get_product_details', args);
        }

        case 'createCart':
        case 'create_cart': {
          const cartId = await this.ensureCart();
          return { cart_id: cartId, cart: this.currentCart() };
        }

        case 'addToCart':
        case 'add_to_cart': {
          const rawTarget = String(args.product_id || args.product_name || args.name || args.query || '').trim().toLowerCase();
          const qty = Number(args.quantity) || 1;
          
          // 1. Match per ID esatto (es. VEG-012, BEV-007)
          let found = this.products().find(p => p.id.toLowerCase() === rawTarget);
          
          // 2. Se non è un ID esatto, risolvi per nome del prodotto o parole chiave
          if (!found && rawTarget) {
            found = this.products().find(p => {
              const pName = p.name.toLowerCase();
              return pName.includes(rawTarget) || rawTarget.includes(pName);
            });
            
            // 3. Risoluzione semantica per prodotti chiave della demo
            if (!found) {
              if (rawTarget.includes('veg') && (rawTarget.includes('panin') || rawTarget.includes('hummus'))) {
                found = this.products().find(p => p.id === 'VEG-012');
              } else if (rawTarget.includes('spremut') || rawTarget.includes('aranc')) {
                found = this.products().find(p => p.id === 'BEV-007');
              } else if (rawTarget.includes('brioche') || rawTarget.includes('croissant') || rawTarget.includes('pistacch')) {
                found = this.products().find(p => p.id === 'PAST-002');
              } else if (rawTarget.includes('focaccia') || rawTarget.includes('toast')) {
                found = this.products().find(p => p.id === 'TOAST-003');
              } else if (rawTarget.includes('caff') || rawTarget.includes('espresso')) {
                found = this.products().find(p => p.id === 'CAFFE-001');
              } else if (rawTarget.includes('cold brew')) {
                found = this.products().find(p => p.id === 'COFFEE-017');
              }
            }
          }

          const prod = found || {
            id: args.product_id || 'PROD-GENERIC',
            name: args.product_id || 'Articolo Selezionato',
            price: 5.0,
            price_cents: 500,
            currency: 'EUR',
            description: '',
            category: 'Gastronomia',
            is_hot: false,
            image_url: ''
          };

          await this.addItemToCart(prod, qty);
          return {
            success: true,
            product_id: prod.id,
            product_name: prod.name,
            quantity: qty,
            message: `Aggiunto ${qty}x ${prod.name} al carrello.`,
            cart_id: this.currentCart()?.cart_id,
            cart: this.currentCart()
          };
        }

        case 'configureFulfillment':
        case 'configure_fulfillment': {
          const method = args.method || 'pickup_locker';
          const details = args.details || {};
          
          if (['pickup_locker', 'pickup_express', 'in_seat_train', 'table_service'].includes(method)) {
            this.selectedFulfillment.set(method as any);
          }
          if (method === 'pickup_locker') {
            if (!details.slot_time) details.slot_time = this.computeDefaultLockerSlot();
            if (!details.pin_code) details.pin_code = '8492';
            if (!details.box_number) details.box_number = 'Box #14';
            this.lockerSlotTime.set(details.slot_time);
            this.lockerPin.set(details.pin_code);
          }
          if (details.train_number) this.trainNumber.set(details.train_number);
          if (details.platform) this.trainPlatform.set(details.platform);
          if (details.carriage) this.trainCarriage.set(details.carriage);
          if (details.seat) this.trainSeat.set(details.seat);
          if (details.delivery_time) this.trainDeliveryTime.set(details.delivery_time);
          if (details.table_number) this.tableNumber.set(details.table_number);

          const ok = await this.applyFulfillment(method, details);
          const fulLabel = method === 'pickup_locker' 
            ? `Smart Locker Contactless (${details.slot_time || '12:30'}, Box #14, PIN 8492)`
            : 'Ritiro Rapido al Banco Bistrot';
          return {
            success: ok,
            method,
            label: fulLabel,
            message: `Modalità di ritiro '${method}' configurata con successo sulla pagina web.`,
            fulfillment: this.currentCart()?.fulfillment,
            cart: this.currentCart(),
            error: this.fulfillmentError()
          };
        }

        case 'prepareCheckout':
        case 'prepare_checkout':
        case 'checkoutCart':
        case 'checkout_cart': {
          // Open checkout drawer for Human-Present verification and payment authorization
          this.isCartOpen.set(true);
          const user = this.currentUser();
          const buyerName = args.buyer_name || user?.name || 'Mario Rossi';
          const buyerEmail = args.buyer_email || user?.email || 'mario.rossi@devfest.it';
          const cart = this.currentCart();

          return {
            success: true,
            status: 'human_present_authorization_required',
            message: 'Cassetto di checkout aperto a video per la verifica e autorizzazione del pagamento (Human-Present).',
            buyer_name: buyerName,
            buyer_email: buyerEmail,
            total_cents: cart?.total_cents || 0,
            fulfillment: cart?.fulfillment,
            cart
          };
        }

        default:
          return await this.callMcpToolDirect(name, args);
      }
    } catch (err: any) {
      console.error(`[WebMCP Execution Error] ${name}:`, err);
      return { isError: true, error: err.message || String(err) };
    }
  }

  registerBrowserWebMcpTools(): void {
    if (typeof window === 'undefined') return;
    const win = window as any;

    const toolsToRegister = webMcpTools;

    // 1. Hook or create navigator.modelContext
    if (!win.navigator.modelContext) {
      const registry = new Map<string, any>();
      const mc = {
        registerTool: async (tool: any) => {
          registry.set(tool.name, tool);
        },
        unregisterTool: async (name: string) => {
          registry.delete(name);
        },
        getTools: () => Array.from(registry.values()),
        listTools: async () => Array.from(registry.values()),
        callTool: async (name: string, args: any) => {
          return await this.executeWebMcpTool(name, args);
        }
      };
      win.navigator.modelContext = mc;
      win.modelContext = mc;
    }

    // 2. Register tools into any available modelContext object (deduplicated)
    const targets = Array.from(new Set([win.navigator?.modelContext, win.modelContext].filter(Boolean)));
    targets.forEach((mc: any) => {
      if (mc && typeof mc.registerTool === 'function') {
        toolsToRegister.forEach((tool) => {
          try {
            const res = mc.registerTool(tool);
            if (res && typeof res.catch === 'function') {
              res.catch(() => {});
            }
          } catch (e) {
            // ignore duplicate tool registration gracefully
          }
        });
      }
    });

    // 3. Expose global window.__webmcp helper for easy verification & testing
    win.__webmcp = {
      listTools: () => webMcpTools,
      callTool: (name: string, args: any) => this.executeWebMcpTool(name, args),
      getCart: () => this.currentCart(),
      getOrder: () => this.orderSuccessBanner(),
      getUser: () => this.currentUser(),
      loginWithGoogle: () => this.loginWithGoogle(),
      loginDemoUser: () => this.loginDemoUser(),
      logout: () => this.logout(),
      toggleLogin: () => this.toggleLogin(),
      search: (q: string, cat?: string) => this.executeWebMcpTool('searchCatalog', { query: q, category: cat }),
      add: (id: string, qty = 1) => this.executeWebMcpTool('addToCart', { product_id: id, quantity: qty }),
      fulfillment: (method: string, details: any = {}) => this.executeWebMcpTool('configureFulfillment', { method, details }),
      checkout: () => this.executeWebMcpTool('prepareCheckout', {})
    };
    console.log('%c[WebMCP Live Bridge Ready] 5 Tools linked to Angular UI Signals', 'color: #10b981; font-weight: bold;');
  }

  // --- CORE MCP JSON-RPC 2.0 BRIDGE CALL ---

  async callMcpToolDirect(name: string, args: any): Promise<any> {
    const rpcPayload = {
      jsonrpc: '2.0',
      id: Date.now(),
      method: 'tools/call',
      params: {
        name,
        arguments: args
      }
    };

    const res = await fetch(`${this.baseUrl}/mcp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(rpcPayload)
    });

    if (!res.ok) throw new Error(`Errore HTTP MCP: ${res.status}`);
    const json = await res.json();
    if (json.error) {
      throw new Error(json.error.message || 'Errore server MCP');
    }
    const result = json.result;
    if (result?.isError) {
      let errMsg = result.content?.[0]?.text || 'Errore esecuzione tool MCP';
      try {
        const parsed = JSON.parse(errMsg);
        if (parsed && typeof parsed === 'object' && parsed.error) {
          errMsg = parsed.error;
        }
      } catch {}
      throw new Error(errMsg);
    }
    const text = result?.content?.[0]?.text;
    if (text) {
      try {
        const parsed = JSON.parse(text);
        if (parsed && typeof parsed === 'object' && parsed.error) {
          throw new Error(parsed.error);
        }
        return parsed;
      } catch (err: any) {
        if (err.message && !err.message.includes('JSON')) {
          throw err;
        }
        return text;
      }
    }
    return result;
  }
}
