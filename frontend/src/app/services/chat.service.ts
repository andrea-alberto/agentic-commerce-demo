import { Injectable, signal, inject } from '@angular/core';
import { ProtocolStep } from '@ucp/shared-frontend';
import {
  ChatMessage,
  Checkout,
  Product,
  Sender,
} from '../models';
import { AuthService } from './auth.service';

export interface RequestPart {
  type: 'text' | 'data';
  text?: string;
  data?: Record<string, unknown>;
}

@Injectable({
  providedIn: 'root',
})
export class ChatService {
  private readonly authService = inject(AuthService);

  messages = signal<ChatMessage[]>([
    {
      id: 'welcome',
      sender: Sender.MODEL,
      text: '👋 Benvenuto all\'Hub di Milano Centrale! Sono il tuo assistente shopping e travel concierge per il GDG DevFest 2026.\n\nPuoi ordinare caffè, colazione calda, sandwich freschi o accessori tech da ritirare al volo o ricevere direttamente a bordo del tuo treno!',
      timestamp: new Date(),
    },
  ]);

  isLoading = signal<boolean>(false);
  contextId = signal<string | null>(null);
  taskId = signal<string | null>(null);
  latestCheckout = signal<Checkout | null>(null);

  // Live Protocol Inspector state
  protocolSteps = signal<ProtocolStep[]>([]);
  inspectorExpanded = signal<boolean>(false);
  highlightedStepNumbers = signal<number[]>([]);
  highlightedMessageId = signal<string | null>(null);
  private stepSeq = 0;

  toggleInspector(): void {
    this.inspectorExpanded.update((v) => !v);
  }

  jumpToInspector(stepNumber: number, allStepNumbers?: number[]): void {
    if (!this.inspectorExpanded()) {
      this.inspectorExpanded.set(true);
    }
    const stepNums = allStepNumbers && allStepNumbers.length > 0 ? allStepNumbers : [stepNumber];
    this.highlightedStepNumbers.set(stepNums);
    setTimeout(() => {
      this.highlightedStepNumbers.set([]);
    }, 3500);
  }

  jumpToMessage(messageId: string): void {
    this.highlightedMessageId.set(messageId);
    setTimeout(() => {
      if (this.highlightedMessageId() === messageId) {
        this.highlightedMessageId.set(null);
      }
    }, 3500);
  }

  async sendMessage(
    messageContent: string | RequestPart[],
    options: { isUserAction?: boolean } = {}
  ): Promise<void> {
    if (this.isLoading()) return;

    // Add user message to UI
    const userText =
      typeof messageContent === 'string'
        ? messageContent
        : options.isUserAction
        ? 'Azione Utente'
        : 'Dati inviati';

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      sender: Sender.USER,
      text: userText,
      isAction: options.isUserAction,
      timestamp: new Date(),
    };

    const loadingMessage: ChatMessage = {
      id: 'loading-' + crypto.randomUUID(),
      sender: Sender.MODEL,
      text: '',
      isLoading: true,
      timestamp: new Date(),
    };

    this.messages.update((msgs) => [...msgs, userMessage, loadingMessage]);
    this.isLoading.set(true);

    try {
      const requestParts: RequestPart[] =
        typeof messageContent === 'string'
          ? [{ type: 'text', text: messageContent }]
          : messageContent;

      const profileUrl =
        typeof window !== 'undefined'
          ? `${window.location.origin}/profile/agent_profile.json`
          : 'http://localhost:4200/profile/agent_profile.json';

      const requestParams: any = {
        message: {
          role: 'user',
          parts: requestParts,
          messageId: crypto.randomUUID(),
          kind: 'message',
        },
        configuration: {
          historyLength: 0,
        },
      };

      if (this.contextId()) {
        requestParams.message.contextId = this.contextId();
      }
      if (this.taskId()) {
        requestParams.message.taskId = this.taskId();
      }

      // Determine action name and description for Inspector
      let actionName = 'A2A_PROMPT_SEND';
      let actionDesc = typeof messageContent === 'string'
        ? `Richiesta utente: "${messageContent.length > 55 ? messageContent.slice(0, 52) + '...' : messageContent}"`
        : 'Azione utente interattiva inviata all\'agente.';

      if (options.isUserAction && Array.isArray(messageContent)) {
        for (const p of messageContent) {
          const act = (p.data as any)?.action;
          if (act === 'add_to_checkout') {
            actionName = 'A2A_ADD_TO_CHECKOUT';
            actionDesc = 'Aggiunta articolo al carrello della sessione UCP.';
          } else if (act === 'select_delivery_method') {
            actionName = 'A2A_SELECT_FULFILLMENT';
            actionDesc = 'Selezione modalità di consegna/ritiro di stazione.';
          } else if (act === 'set_train_delivery_details') {
            actionName = 'A2A_SET_TRAIN_DETAILS';
            actionDesc = 'Configurazione consegna al posto treno (Frecciarossa/Italo).';
          } else if (act === 'set_locker_pickup_details') {
            actionName = 'A2A_SET_LOCKER_DETAILS';
            actionDesc = 'Configurazione Smart Locker e slot di ritiro.';
          } else if (act === 'set_table_service_details') {
            actionName = 'A2A_SET_TABLE_DETAILS';
            actionDesc = 'Configurazione servizio al tavolo / banco Bistrot.';
          } else if (act === 'start_payment') {
            actionName = 'A2A_START_PAYMENT';
            actionDesc = 'Avvio checkout e richiesta mandato di pagamento.';
          } else if (act === 'complete_checkout') {
            actionName = 'A2A_COMPLETE_PAYMENT_AP2';
            actionDesc = 'Conferma transazione con Mandato AP2 e firma hardware TPM/FIDO2.';
          }
        }
      } else if (options.isUserAction && typeof messageContent === 'string') {
        try {
          const parsed = JSON.parse(messageContent);
          if (parsed.action === 'add_to_checkout') {
            actionName = 'A2A_ADD_TO_CHECKOUT';
            actionDesc = `Aggiunta articolo (${parsed.product_id || ''}) al carrello UCP.`;
          } else if (parsed.action === 'select_delivery_method') {
            actionName = 'A2A_SELECT_FULFILLMENT';
            actionDesc = `Selezione modalità di consegna/ritiro: ${parsed.option_id || ''}.`;
          } else if (parsed.action === 'set_train_delivery_details') {
            actionName = 'A2A_SET_TRAIN_DETAILS';
            actionDesc = `Configurazione consegna treno: ${parsed.train_number || ''}, Posto ${parsed.seat || ''}.`;
          } else if (parsed.action === 'set_locker_pickup_details') {
            actionName = 'A2A_SET_LOCKER_DETAILS';
            actionDesc = `Configurazione Smart Locker: slot ${parsed.slot_time || ''}.`;
          } else if (parsed.action === 'set_table_service_details') {
            actionName = 'A2A_SET_TABLE_DETAILS';
            actionDesc = `Configurazione servizio al tavolo: ${parsed.table_number || ''}.`;
          } else if (parsed.action === 'start_payment') {
            actionName = 'A2A_START_PAYMENT';
            actionDesc = 'Avvio checkout e richiesta mandato di pagamento.';
          }
        } catch {}
      }

      this.stepSeq++;
      const currStepNum = this.stepSeq;
      this.messages.update((msgs) =>
        msgs.map((m) => (m.id === userMessage.id ? { ...m, stepNumbers: [currStepNum] } : m))
      );
      const startTime = performance.now();
      const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

      const currentUser = this.authService.user();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'X-A2A-Extensions': 'https://ucp.dev/2026-01-23/specification/overview?v=2026-01-23',
        'UCP-Agent': `profile="${profileUrl}"`,
      };
      if (currentUser?.email) {
        headers['X-User-Email'] = currentUser.email;
        if (currentUser.displayName) {
          headers['X-User-Name'] = currentUser.displayName;
        }
      }

      const outgoingStep: ProtocolStep = {
        step_number: currStepNum,
        protocol: 'a2a_direct',
        actor_source: 'client_browser',
        actor_target: 'merchant_agent',
        action: actionName,
        description: actionDesc,
        headers,
        payload: {
          jsonrpc: '2.0',
          method: 'message/send',
          params: requestParams,
        },
        status: 'pending',
        timestamp: timeStr,
        related_message_id: userMessage.id,
      };
      this.protocolSteps.update((steps) => [...steps, outgoingStep]);

      const response = await fetch('/api', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          jsonrpc: '2.0',
          id: crypto.randomUUID(),
          method: 'message/send',
          params: requestParams,
        }),
      });

      if (!response.ok) {
        throw new Error(`Errore HTTP API: ${response.status}`);
      }

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error.message || 'Errore JSON-RPC dal server');
      }

      // Update context and task IDs
      if (data.result?.contextId) {
        this.contextId.set(data.result.contextId);
      }
      if (
        data.result?.id &&
        ['working', 'submitted', 'input-required'].includes(
          data.result?.status?.state
        )
      ) {
        this.taskId.set(data.result.id);
      } else {
        this.taskId.set(null);
      }

      const responseParts =
        data.result?.parts || data.result?.status?.message?.parts || [];

      let modelText = '';
      let products: Product[] | undefined;
      let checkout: Checkout | undefined;

      for (const part of responseParts) {
        if (part.text) {
          modelText += (modelText ? '\n\n' : '') + part.text;
        } else if (part.data?.['a2a.product_results']) {
          const resultsObj = part.data['a2a.product_results'];
          if (resultsObj.content) {
            modelText += (modelText ? '\n\n' : '') + resultsObj.content;
          }
          if (resultsObj.results) {
            products = resultsObj.results;
          }
        } else if (part.data?.['a2a.ucp.checkout']) {
          checkout = part.data['a2a.ucp.checkout'];
          this.latestCheckout.set(checkout ?? null);
        }
      }

      // Record successful response in protocol steps
      const latency = Math.round(performance.now() - startTime);
      this.protocolSteps.update((steps) =>
        steps.map((s) =>
          s.step_number === currStepNum
            ? { ...s, status: 'success', latency_ms: latency }
            : s
        )
      );

      this.stepSeq++;
      const respStepNum = this.stepSeq;
      const respTimeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

      let respAction = 'A2A_MESSAGE_RESPONSE';
      let respDesc = 'Risposta semantica JSON-RPC 2.0 ricevuta dal Merchant Agent di Milano Centrale.';
      if (checkout) {
        const totalAmount = checkout.totals?.find((t) => t.type === 'total')?.amount;
        const formattedTotal = totalAmount !== undefined ? ` (Totale: €${(totalAmount / 100).toFixed(2)})` : '';
        respAction = 'A2A_UCP_CHECKOUT_EVENT';
        respDesc = `Sessione di checkout UCP aggiornata${formattedTotal} (Stato: ${checkout.status || 'in_progress'}).`;
      } else if (products && products.length > 0) {
        respAction = 'A2A_PRODUCT_CATALOG_EVENT';
        respDesc = `Risultati semantici del catalogo: ${products.length} articoli disponibili trovati.`;
      }

      const botMsgId = crypto.randomUUID();
      const stepNums = [currStepNum, respStepNum];

      const respStep: ProtocolStep = {
        step_number: respStepNum,
        protocol: 'a2a_direct',
        actor_source: 'merchant_agent',
        actor_target: 'client_browser',
        action: respAction,
        description: respDesc,
        payload: data.result,
        status: 'success',
        timestamp: respTimeStr,
        latency_ms: latency,
        related_message_id: botMsgId,
      };

      this.protocolSteps.update((steps) => [...steps, respStep]);

      const botMessage: ChatMessage = {
        id: botMsgId,
        sender: Sender.MODEL,
        text: modelText,
        products,
        checkout,
        timestamp: new Date(),
        stepNumbers: stepNums,
      };

      // Replace loading message with actual response
      this.messages.update((msgs) => [
        ...msgs.filter((m) => !m.isLoading),
        botMessage,
      ]);
    } catch (err: any) {
      console.error('ChatService error:', err);
      this.protocolSteps.update((steps) =>
        steps.map((s) =>
          s.status === 'pending'
            ? { ...s, status: 'error', description: s.description + ' (Errore: ' + (err.message || 'Chiamata fallita') + ')' }
            : s
        )
      );
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        sender: Sender.MODEL,
        text: `⚠️ Si è verificato un errore: ${err.message || 'Impossibile contattare l\'agente'}. Assicurati che il backend A2A sia attivo su porta 10999.`,
        timestamp: new Date(),
      };
      this.messages.update((msgs) => [
        ...msgs.filter((m) => !m.isLoading),
        errorMessage,
      ]);
    } finally {
      this.isLoading.set(false);
    }
  }

  addToCheckout(product: Product, quantity = 1): void {
    const actionPayload = JSON.stringify({
      action: 'add_to_checkout',
      product_id: product.productID,
      quantity,
    });
    this.sendMessage(actionPayload, { isUserAction: true });
  }

  selectDeliveryOption(optionId: string, slotTime?: string): void {
    const actionPayload = JSON.stringify({
      action: 'select_delivery_method',
      option_id: optionId,
      ...(slotTime ? { slot_time: slotTime } : {}),
    });
    this.sendMessage(actionPayload, { isUserAction: true });
  }

  setLockerPickup(slotTime: string): void {
    const actionPayload = JSON.stringify({
      action: 'set_locker_pickup_details',
      slot_time: slotTime,
    });
    this.sendMessage(actionPayload, { isUserAction: true });
  }

  setTrainDelivery(details: {
    trainNumber: string;
    carriage: string;
    seat: string;
    deliveryTime?: string;
    platform?: string;
  }): void {
    const actionPayload = JSON.stringify({
      action: 'set_train_delivery_details',
      train_number: details.trainNumber,
      carriage: details.carriage,
      seat: details.seat,
      delivery_time: details.deliveryTime,
      platform: details.platform,
    });
    this.sendMessage(actionPayload, { isUserAction: true });
  }

  setTableService(tableNumber: string, serviceTime?: string): void {
    const actionPayload = JSON.stringify({
      action: 'set_table_service_details',
      table_number: tableNumber,
      service_time: serviceTime,
    });
    this.sendMessage(actionPayload, { isUserAction: true });
  }

  startPayment(): void {
    const actionPayload = JSON.stringify({ action: 'start_payment' });
    this.sendMessage(actionPayload, { isUserAction: true });
  }

  async completePayment(
    checkout: Checkout,
    mandates?: { mandateId: string; cartMandateJwt: string; paymentMandateJwt: string }
  ): Promise<void> {
    const handlerId = checkout.payment?.handlers?.[0]?.id || 'example_payment_provider';
    const mockPaymentInstrument = {
      id: 'instr_devfest_card_01',
      handler_id: handlerId,
      type: 'card',
      brand: 'Mastercard',
      last_digits: '4242',
      display: {
        brand: 'Mastercard',
        last_digits: '4242',
      },
    };

    const parts: RequestPart[] = [
      { type: 'data', data: { action: 'complete_checkout' } },
      {
        type: 'data',
        data: {
          'a2a.ucp.checkout.payment_data': mockPaymentInstrument,
          'a2a.ucp.checkout.risk_signals': {
            ap2_mandate_id: mandates?.mandateId || 'mandate_milano_centrale_2026',
            device_verification: 'hardware_backed_tpm',
            cart_mandate_jwt: mandates?.cartMandateJwt,
            payment_mandate_jwt: mandates?.paymentMandateJwt,
          },
        },
      },
    ];

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    this.stepSeq++;
    const totalCents = (checkout as any).total_cents || (checkout.totals?.find(t => t.type === 'total')?.amount ?? 750);
    const stepLcmReq: ProtocolStep = {
      step_number: this.stepSeq,
      protocol: 'webauthn',
      actor_source: 'client_browser',
      actor_target: 'credential_manager',
      action: 'NAVIGATOR_CREDENTIALS_GET',
      description: `Invocazione W3C Credential Management API (navigator.credentials.get): challenge crittografica SHA-256 e vincoli CartMandate (€${(totalCents / 100).toFixed(2)}).`,
      payload: {
        publicKey: {
          rpId: window.location.hostname || 'localhost',
          challenge: 'a89f30b912c984210fd6192837bcda124e...',
          userVerification: 'required',
          timeout: 60000,
          allowCredentials: [{ type: 'public-key', id: 'cred_passkey_milano_centrale' }],
          extensions: {
            ap2: {
              mandate_type: 'CartMandate',
              checkout_id: checkout.id,
              total_cents: totalCents,
            },
          },
        },
      },
      status: 'success',
      timestamp: timeStr,
    };

    this.stepSeq++;
    const stepLcmRes: ProtocolStep = {
      step_number: this.stepSeq,
      protocol: 'webauthn',
      actor_source: 'credential_manager',
      actor_target: 'client_browser',
      action: 'CREDENTIAL_MANAGER_ASSERTION',
      description: 'Asserzione crittografica hardware generata nel Secure Enclave/KeyMint (Passkey P-256). Utente verificato biometricamente (User Verified = 1, User Present = 1). Rilascio Mandato AP2.',
      payload: {
        credential_id: 'cred_passkey_milano_centrale',
        authenticator_data: {
          flags: { user_present: true, user_verified: true, backup_eligible: true },
          sign_count: 88,
        },
        client_data_json: {
          type: 'webauthn.get',
          challenge: 'a89f30b912c984210fd6192837bcda124e...',
          origin: window.location.origin,
        },
        signature_scheme: 'FIDO2_Passkey_P256',
        ap2_mandate: {
          mandate_id: mandates?.mandateId || 'mandate_milano_centrale_2026',
          iss: 'did:key:z6MkuDevicePasskeyLCM_Milano_Centrale',
          type: 'ap2:CartMandate',
          hardware_attestation: 'Android-KeyMint-FIDO2-L3-SecureEnclave',
        },
      },
      status: 'success',
      timestamp: timeStr,
    };

    this.protocolSteps.update((steps) => [...steps, stepLcmReq, stepLcmRes]);

    await this.sendMessage(parts, { isUserAction: true });
  }
}
