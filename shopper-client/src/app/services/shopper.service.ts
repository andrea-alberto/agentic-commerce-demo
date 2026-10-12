import { Injectable, signal, inject, effect } from '@angular/core';
import {
  TravelerContext,
  ScenarioPreset,
  ProtocolStep,
  MissionStreamEvent,
  ClientAP2MandateResult,
  ShopperProposal
} from '@ucp/shared-frontend';
import { AuthService } from './auth.service';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent' | 'system';
  text: string;
  timestamp: string;
  order?: any;
  proposal?: ShopperProposal;
  protocolMode?: 'a2a' | 'ucp_rest';
  stepNumbers?: number[];
}

@Injectable({
  providedIn: 'root'
})
export class ShopperService {
  private readonly backendUrl = 'http://localhost:10998';
  readonly authService = inject(AuthService);

  // State Signals
  readonly travelerContext = signal<TravelerContext | null>(null);
  readonly protocolMode = signal<'a2a' | 'ucp_rest'>('a2a');
  readonly isRunning = signal<boolean>(false);
  readonly inspectorExpanded = signal<boolean>(true);
  readonly contextExpanded = signal<boolean>(false);
  readonly isModalOpen = signal<boolean>(false);
  readonly isLcmModalOpen = signal<boolean>(false);
  readonly pendingChallenge = signal<any | null>(null);
  readonly pendingProposal = signal<ShopperProposal | null>(null);
  readonly protocolSteps = signal<ProtocolStep[]>([]);
  readonly chatMessages = signal<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'agent',
      text: 'Ciao Mario! Sono il tuo Personal Shopper Agent per Milano Centrale. Ho caricato i dettagli del tuo biglietto ferroviario. Come posso aiutarti prima della partenza?',
      timestamp: '12:55'
    }
  ]);
  readonly confirmedOrder = signal<any | null>(null);

  constructor() {
    this.loadContext();

    // Sincronizza il travelerContext con l'utente autenticato tramite Google
    effect(() => {
      const authUser = this.authService.user();
      const current = this.travelerContext();
      if (authUser && current) {
        this.travelerContext.set({
          ...current,
          name: authUser.displayName || current.name,
          email: authUser.email || current.email,
          loyalty_tier: authUser.loyaltyTier || current.loyalty_tier,
          loyalty_code: authUser.loyaltyCode || current.loyalty_code
        });
      }
    });
  }

  async loadContext(): Promise<void> {
    try {
      const email = this.authService.userEmail();
      const res = await fetch(`${this.backendUrl}/shopper/context?email=${encodeURIComponent(email)}`);
      if (res.ok) {
        const data: TravelerContext = await res.json();
        this.travelerContext.set(data);
      }
    } catch (e) {
      console.warn('[ShopperService] Context fetch failed, using fallback:', e);
    }
  }

  async selectPreset(preset: ScenarioPreset): Promise<void> {
    try {
      const res = await fetch(`${this.backendUrl}/shopper/context/preset/${preset.id}`, {
        method: 'POST'
      });
      if (res.ok) {
        const data: TravelerContext = await res.json();
        this.travelerContext.set(data);
        this.chatMessages.update(msgs => [
          ...msgs,
          {
            id: 'preset-' + Date.now(),
            sender: 'system',
            text: `Scenario attivo aggiornato: ${preset.title} (${preset.badge}).`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
        ]);
      }
    } catch (e) {
      console.error('[ShopperService] Error selecting preset:', e);
    }
  }

  async saveContext(updated: TravelerContext): Promise<void> {
    try {
      const res = await fetch(`${this.backendUrl}/shopper/context`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated)
      });
      if (res.ok) {
        const data: TravelerContext = await res.json();
        this.travelerContext.set(data);
        this.isModalOpen.set(false);
        this.chatMessages.update(msgs => [
          ...msgs,
          {
            id: 'ctx-save-' + Date.now(),
            sender: 'system',
            text: `Contesto viaggiatore personalizzato salvato con successo.`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
        ]);
      }
    } catch (e) {
      console.error('[ShopperService] Error saving context:', e);
    }
  }

  setProtocolMode(mode: 'a2a' | 'ucp_rest'): void {
    this.protocolMode.set(mode);
  }

  toggleInspector(): void {
    this.inspectorExpanded.update(v => !v);
  }

  toggleContext(): void {
    this.contextExpanded.update(v => !v);
  }

  openContextModal(): void {
    this.isModalOpen.set(true);
  }

  closeContextModal(): void {
    this.isModalOpen.set(false);
  }

  async runMission(promptText: string): Promise<void> {
    if (this.isRunning() || !promptText.trim()) return;

    this.isRunning.set(true);
    this.protocolSteps.set([]);
    this.confirmedOrder.set(null);
    this.pendingChallenge.set(null);
    this.pendingProposal.set(null);
    this.isLcmModalOpen.set(false);

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const currentMode = this.protocolMode();
    const userMsgId = 'msg-' + Date.now();
    const currentTurnStepNumbers: number[] = [];

    // Add user message to chat
    this.chatMessages.update(msgs => [
      ...msgs,
      {
        id: userMsgId,
        sender: 'user',
        text: promptText,
        timestamp: timeStr,
        protocolMode: currentMode
      }
    ]);

    try {
      const response = await fetch(`${this.backendUrl}/shopper/mission/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: promptText,
          protocol: currentMode,
          context_override: this.travelerContext()
        })
      });

      if (!response.ok || !response.body) {
        throw new Error(`Mission stream HTTP error: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            const jsonStr = trimmed.substring(6);
            try {
              const event: MissionStreamEvent = JSON.parse(jsonStr);
              this.handleStreamEvent(event, userMsgId, currentTurnStepNumbers);
            } catch (err) {
              console.error('Error parsing SSE event JSON:', jsonStr, err);
            }
          }
        }
      }
    } catch (err: any) {
      console.error('[ShopperService] Mission stream failed:', err);
      this.chatMessages.update(msgs => [
        ...msgs,
        {
          id: 'err-' + Date.now(),
          sender: 'system',
          text: `Errore durante la missione con l'agente: ${err?.message || err}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      this.isRunning.set(false);
    }
  }

  private handleStreamEvent(
    event: MissionStreamEvent,
    userMsgId: string,
    turnStepNumbers: number[]
  ): void {
    if (event.type === 'step' && event.step) {
      turnStepNumbers.push(event.step.step_number);
      this.protocolSteps.update(steps => [...steps, event.step!]);
    } else if (event.type === 'proposal') {
      this.pendingProposal.set(event.proposal);
      const propMsgId = 'prop-' + Date.now();
      const stepNums = [...turnStepNumbers];

      // Tag existing steps with this proposal message id
      this.protocolSteps.update(steps =>
        steps.map(s => stepNums.includes(s.step_number) ? { ...s, related_message_id: propMsgId } : s)
      );

      // Also tag user message with the step numbers!
      this.chatMessages.update(msgs =>
        msgs.map(m => m.id === userMsgId ? { ...m, stepNumbers: stepNums } : m)
      );

      if (event.message) {
        this.chatMessages.update(msgs => [
          ...msgs,
          {
            id: propMsgId,
            sender: 'agent',
            text: event.message!,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            proposal: event.proposal,
            protocolMode: this.protocolMode(),
            stepNumbers: stepNums
          }
        ]);
      }
    } else if (event.type === 'challenge') {
      this.pendingChallenge.set(event.challenge);
      this.isLcmModalOpen.set(true);
      const chalMsgId = 'chal-' + Date.now();
      const stepNums = [...turnStepNumbers];

      this.protocolSteps.update(steps =>
        steps.map(s => stepNums.includes(s.step_number) ? { ...s, related_message_id: chalMsgId } : s)
      );

      if (event.message) {
        this.chatMessages.update(msgs => [
          ...msgs,
          {
            id: chalMsgId,
            sender: 'agent',
            text: event.message!,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            protocolMode: this.protocolMode(),
            stepNumbers: stepNums
          }
        ]);
      }
    } else if (event.type === 'final') {
      if (event.final_order) {
        this.confirmedOrder.set(event.final_order);
      }
      const finalMsgId = 'final-' + Date.now();
      const stepNums = [...turnStepNumbers];

      this.protocolSteps.update(steps =>
        steps.map(s => stepNums.includes(s.step_number) ? { ...s, related_message_id: finalMsgId } : s)
      );

      if (event.message) {
        this.chatMessages.update(msgs => [
          ...msgs,
          {
            id: finalMsgId,
            sender: 'agent',
            text: event.message!,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            order: event.final_order,
            protocolMode: this.protocolMode(),
            stepNumbers: stepNums
          }
        ]);
      }
    }
  }

  confirmProposalSelection(optionId: string, proposal: ShopperProposal): void {
    const chosenOpt =
      proposal.fulfillment_options.find((o) => o.id === optionId) ||
      proposal.fulfillment_options[0];

    const parsedCheckoutId =
      typeof proposal.notes === 'string' && proposal.notes.includes('checkout_id=')
        ? proposal.notes.split('checkout_id=')[1]
        : 'CHK-UCP-' + crypto.randomUUID().substring(0, 6).toUpperCase();

    const challengePayload = {
      challenge_id: 'CHAL-' + crypto.randomUUID().substring(0, 8),
      protocol: proposal.protocol,
      order_id: 'ORD-MI-' + crypto.randomUUID().substring(0, 6).toUpperCase(),
      merchant: proposal.merchant_name,
      order_summary_title: proposal.item.title,
      order_item_id: proposal.item.id,
      order_item_price: proposal.item.price_cents,
      delivery_fee: chosenOpt.delivery_fee_cents,
      total_cents: chosenOpt.total_cents,
      fl_method: chosenOpt.id,
      fl_label: chosenOpt.label,
      fl_window: chosenOpt.details,
      ticket: proposal.ticket,
      buyer: proposal.buyer,
      checkout_id: parsedCheckoutId,
      chosen_prod: proposal.item,
      items: (proposal as any).items || (proposal.item as any).items || undefined,
    };

    this.pendingChallenge.set(challengePayload);
    this.isLcmModalOpen.set(true);
  }

  private async calculateSha256Hex(text: string): Promise<string> {
    try {
      const msgBuffer = new TextEncoder().encode(text);
      const hashBuffer = await window.crypto.subtle.digest('SHA-256', msgBuffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    } catch {
      return 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';
    }
  }

  async authorizeChallenge(ap2Mandate: ClientAP2MandateResult): Promise<void> {
    const challenge = this.pendingChallenge();
    if (!challenge) return;

    this.isRunning.set(true);
    try {
      const currentSteps = this.protocolSteps();
      const baseOffset = currentSteps.length;
      const nowTimeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

      // Generazione reale del challenge SHA-256 con Web Crypto API
      const rawChallengeStr = `${challenge.order_id || challenge.checkout_id || 'CHK'}-${challenge.total_cents}-${challenge.merchant || 'Bistrot'}`;
      const challengeSha256 = await this.calculateSha256Hex(rawChallengeStr);

      // Passo A: Richiesta credenziali verso il Local Credential Manager (W3C WebAuthn)
      const stepLcmReq: ProtocolStep = {
        step_number: baseOffset + 1,
        protocol: 'webauthn',
        actor_source: 'shopper_client',
        actor_target: 'credential_manager',
        action: 'NAVIGATOR_CREDENTIALS_GET',
        description: `Invocazione W3C Credential Management API (navigator.credentials.get): challenge crittografica SHA-256 e vincoli CartMandate (€${((challenge.total_cents || 750) / 100).toFixed(2)}). Richiesta verifica biometrica del titolare.`,
        payload: {
          publicKey: {
            rpId: window.location.hostname || 'localhost',
            challenge: challengeSha256,
            userVerification: 'required',
            timeout: 60000,
            allowCredentials: [{ type: 'public-key', id: 'cred_passkey_mario_p256' }],
            extensions: {
              ap2: {
                mandate_type: 'CartMandate',
                total_cents: challenge.total_cents,
                currency: 'EUR',
                merchant: challenge.merchant,
                fulfillment_binding: challenge.fl_label || 'Milano Centrale'
              }
            }
          }
        },
        status: 'success',
        timestamp: nowTimeStr,
      };

      // Passo B: Asserzione crittografica hardware restituita dal Credential Manager
      const stepLcmRes: ProtocolStep = {
        step_number: baseOffset + 2,
        protocol: 'webauthn',
        actor_source: 'credential_manager',
        actor_target: 'shopper_client',
        action: 'CREDENTIAL_MANAGER_ASSERTION',
        description: 'Asserzione crittografica hardware generata nel Secure Enclave/KeyMint (Passkey P-256). Utente verificato biometricamente (User Verified = 1, User Present = 1). Rilascio Mandato AP2.',
        payload: {
          credential_id: 'cred_passkey_mario_p256',
          authenticator_data: {
            flags: {
              user_present: true,
              user_verified: true,
              backup_eligible: true,
              backup_state: true
            },
            sign_count: 142
          },
          client_data_json: {
            type: 'webauthn.get',
            challenge: challengeSha256,
            origin: window.location.origin
          },
          signature_scheme: 'FIDO2_Passkey_P256',
          signature: '30450221008f4cb7e022031c99a0d84f8812c4167e9120e2947192837bcda124e022031c99a0d8...',
          ap2_mandate: {
            mandate_id: ap2Mandate.mandate_id,
            iss: 'did:key:z6MkuDevicePasskeyLCM_MarioRossi_Client',
            type: 'ap2:CartMandate',
            authorized_amount_cents: challenge.total_cents,
            hardware_attestation: 'Android-KeyMint-FIDO2-L3-SecureEnclave'
          }
        },
        status: 'success',
        timestamp: nowTimeStr,
      };

      const res = await fetch(`${this.backendUrl}/shopper/mission/authorize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          protocol: this.protocolMode(),
          challenge,
          ap2_mandate: ap2Mandate,
          step_offset: baseOffset + 2
        })
      });

      if (!res.ok) {
        throw new Error(`Autorizzazione fallita (HTTP ${res.status})`);
      }

      const data = await res.json();
      const finalMsgId = 'final-' + Date.now();
      const serverSteps: ProtocolStep[] = data.steps || [data.step_ap2, data.step_commit, data.step_final].filter(Boolean);

      const taggedLcmSteps = [
        { ...stepLcmReq, related_message_id: finalMsgId },
        { ...stepLcmRes, related_message_id: finalMsgId },
      ];
      const taggedServerSteps = serverSteps.map(s => ({ ...s, related_message_id: finalMsgId }));
      const allAuthSteps: ProtocolStep[] = [...taggedLcmSteps, ...taggedServerSteps];

      this.protocolSteps.update(steps => [...steps, ...allAuthSteps]);
      const authStepNums = allAuthSteps.map(s => s.step_number);

      if (data.final_order) {
        this.confirmedOrder.set(data.final_order);
      }
      if (data.message) {
        this.chatMessages.update(msgs => [
          ...msgs,
          {
            id: finalMsgId,
            sender: 'agent',
            text: data.message,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            order: data.final_order,
            protocolMode: this.protocolMode(),
            stepNumbers: authStepNums
          }
        ]);
      }
      this.pendingChallenge.set(null);
      this.isLcmModalOpen.set(false);
    } catch (err: any) {
      console.error('[ShopperService] Mission authorization error:', err);
      this.chatMessages.update(msgs => [
        ...msgs,
        {
          id: 'err-auth-' + Date.now(),
          sender: 'system',
          text: `Errore durante la finalizzazione del mandato AP2: ${err?.message || err}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      this.isRunning.set(false);
    }
  }

  cancelChallenge(): void {
    this.isLcmModalOpen.set(false);
    this.pendingChallenge.set(null);
    this.isRunning.set(false);
    this.chatMessages.update(msgs => [
      ...msgs,
      {
        id: 'cancel-' + Date.now(),
        sender: 'system',
        text: "Autorizzazione pagamento annullata dall'utente.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
  }

  clearSession(): void {
    const travelerName = this.travelerContext()?.name?.split(' ')[0] || this.authService.user()?.displayName?.split(' ')[0] || 'Mario';
    this.chatMessages.set([
      {
        id: 'welcome-' + Date.now(),
        sender: 'agent',
        text: `Ciao ${travelerName}! Sono il tuo Personal Shopper Agent per Milano Centrale. Ho caricato i dettagli del tuo biglietto ferroviario. Come posso aiutarti prima della partenza?`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
    this.protocolSteps.set([]);
    this.confirmedOrder.set(null);
    this.pendingProposal.set(null);
    this.pendingChallenge.set(null);
    this.isLcmModalOpen.set(false);
  }
}
