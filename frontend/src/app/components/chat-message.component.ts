import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ChatMessage, Sender } from '../models';
import { ProductCardComponent } from './product-card.component';
import { CheckoutComponent } from './checkout.component';
import { ChatService } from '../services/chat.service';

export interface SuggestionAction {
  label: string;
  prompt: string;
  variant: 'express' | 'train' | 'locker' | 'default';
}

@Component({
  selector: 'app-chat-message',
  standalone: true,
  imports: [CommonModule, ProductCardComponent, CheckoutComponent],
  template: `
    <div class="message-container" [class.user-message]="isUser()" [class.model-message]="!isUser()">
      <!-- Avatar for Model -->
      @if (!isUser()) {
        <div class="avatar model-avatar" [class.notice-avatar]="isNotice()">
          <span>{{ isNotice() ? '⚠️' : '☕' }}</span>
        </div>
      }

      <div class="bubble-wrapper">
        <!-- Message Bubble -->
        @if (message.text || message.isLoading) {
          <div
            class="bubble"
            [class.user-bubble]="isUser()"
            [class.model-bubble]="!isUser()"
            [class.notice-bubble]="!isUser() && isNotice()"
          >
            @if (!isUser() && isNotice()) {
              <div class="notice-badge">
                <span class="notice-badge-icon">⏱️</span>
                <span>AVVISO OPERATIVO: PREAVVISO STAZIONE</span>
              </div>
            }

            @if (message.isLoading) {
              <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            } @else {
              <div class="message-text" [innerHTML]="formatMarkdown(message.text)"></div>
            }

            @if (message.stepNumbers && message.stepNumbers.length > 0) {
              <div class="msg-protocol-correlation">
                <button
                  type="button"
                  class="btn-corr-pill"
                  (click)="onJumpToInspector(message.stepNumbers[0], message.stepNumbers)"
                  title="Allinea l'Inspector ai passaggi di rete corrispondenti"
                >
                  <span class="pill-dot"></span>
                  <span class="pill-icon">📡</span>
                  <span class="pill-text">{{ formatStepRange(message.stepNumbers) }}</span>
                  <span class="pill-arrow">➔</span>
                </button>
              </div>
            }
          </div>
        }

        <!-- Interactive Quick Action Suggestions from Agent Notice -->
        @if (!isUser() && !message.isLoading && getQuickSuggestions().length > 0) {
          <div class="message-suggestions">
            <span class="suggestions-label">💡 Azioni rapide suggerite:</span>
            <div class="suggestions-chips">
              @for (s of getQuickSuggestions(); track s.label) {
                <button
                  type="button"
                  class="suggestion-btn"
                  [ngClass]="'btn-' + s.variant"
                  (click)="onSuggestionClick(s.prompt)"
                  [disabled]="chatService.isLoading()"
                >
                  {{ s.label }}
                </button>
              }
            </div>
          </div>
        }

        <!-- Product Cards Grid/Carousel -->
        @if (message.products && message.products.length > 0) {
          <div class="products-grid">
            @for (p of message.products; track p.productID) {
              <app-product-card [product]="p" />
            }
          </div>
        }

        <!-- Checkout Box -->
        @if (message.checkout) {
          <app-checkout [checkout]="message.checkout" />
        }
      </div>

      <!-- Avatar for User -->
      @if (isUser()) {
        <div class="avatar user-avatar">
          <span>👤</span>
        </div>
      }
    </div>
  `,
  styles: [`
    .message-container {
      display: flex;
      margin-bottom: 16px;
      gap: 10px;
      align-items: flex-start;
    }
    .user-message {
      justify-content: flex-end;
    }
    .model-message {
      justify-content: flex-start;
    }
    .avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.1rem;
      flex-shrink: 0;
      box-shadow: 0 2px 5px rgba(0,0,0,0.06);
    }
    .model-avatar {
      background: #fef3c7;
      border: 1px solid #fde68a;
    }
    .notice-avatar {
      background: #fef3c7;
      border: 1px solid #fde68a;
    }
    .user-avatar {
      background: #f5f5f4;
      border: 1px solid #e7e5e4;
    }
    .bubble-wrapper {
      display: flex;
      flex-direction: column;
      max-width: 82%;
      gap: 8px;
    }
    .user-message .bubble-wrapper {
      align-items: flex-end;
    }
    .bubble {
      padding: 12px 16px;
      border-radius: 14px;
      font-size: 0.9rem;
      line-height: 1.48;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      word-break: break-word;
    }
    .user-bubble {
      background: linear-gradient(135deg, #d97706, #b45309);
      color: #ffffff;
      border-bottom-right-radius: 2px;
      white-space: pre-line;
      box-shadow: 0 2px 8px rgba(180, 83, 9, 0.25);
    }
    .model-bubble {
      background: #ffffff;
      color: #1c1917;
      border: 1px solid #e7e5e4;
      border-bottom-left-radius: 2px;
    }
    .notice-bubble {
      background: #fffbeb;
      border: 1px solid #fde68a;
      box-shadow: 0 2px 8px rgba(245, 158, 11, 0.08);
    }
    .notice-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #fef3c7;
      color: #92400e;
      border: 1px solid #fde68a;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 0.68rem;
      font-weight: 800;
      letter-spacing: 0.04em;
      margin-bottom: 8px;
    }
    .message-text {
      color: inherit;
    }
    :host ::ng-deep .msg-heading {
      font-size: 0.95rem;
      font-weight: 700;
      color: #0f172a;
      margin: 10px 0 4px 0;
    }
    :host ::ng-deep .msg-heading.large {
      font-size: 1.05rem;
      font-weight: 800;
    }
    :host ::ng-deep .msg-bullet {
      padding-left: 6px;
      margin: 3px 0;
      color: #334155;
    }
    :host ::ng-deep .msg-code {
      background: #f1f5f9;
      color: #0f172a;
      padding: 2px 5px;
      border-radius: 4px;
      font-family: monospace;
      font-size: 0.85em;
    }
    :host ::ng-deep .msg-divider {
      height: 1px;
      background: #e2e8f0;
      margin: 8px 0;
    }
    :host ::ng-deep strong {
      color: #0f172a;
      font-weight: 700;
    }
    .notice-bubble :host ::ng-deep strong {
      color: #78350f;
    }

    /* Suggestion Chips */
    .message-suggestions {
      display: flex;
      flex-direction: column;
      gap: 6px;
      background: #f8fafc;
      border: 1px dashed #cbd5e1;
      border-radius: 10px;
      padding: 8px 12px;
      animation: fadeIn 0.2s ease;
    }
    .suggestions-label {
      font-size: 0.72rem;
      font-weight: 700;
      color: #475569;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    .suggestions-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .suggestion-btn {
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
      border: 1px solid transparent;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .btn-express {
      background: #dcfce7;
      color: #166534;
      border-color: #bbf7d0;
    }
    .btn-express:hover:not(:disabled) {
      background: #bbf7d0;
      border-color: #86efac;
    }
    .btn-train {
      background: #e0e7ff;
      color: #3730a3;
      border-color: #c7d2fe;
    }
    .btn-train:hover:not(:disabled) {
      background: #c7d2fe;
      border-color: #a5b4fc;
    }
    .btn-locker {
      background: #fef3c7;
      color: #92400e;
      border-color: #fde68a;
    }
    .btn-locker:hover:not(:disabled) {
      background: #fde68a;
      border-color: #fcd34d;
    }
    .btn-default {
      background: #f1f5f9;
      color: #334155;
      border-color: #e2e8f0;
    }
    .btn-default:hover:not(:disabled) {
      background: #e2e8f0;
    }
    .suggestion-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .products-grid {
      display: flex;
      gap: 12px;
      overflow-x: auto;
      padding: 4px 2px 10px 2px;
      max-width: 100%;
    }
    .typing-indicator {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 4px 6px;
    }
    .typing-indicator span {
      width: 8px;
      height: 8px;
      background: #94a3b8;
      border-radius: 50%;
      animation: bounce 1.2s infinite ease-in-out both;
    }
    .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
    .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
    @keyframes bounce {
      0%, 80%, 100% { transform: scale(0); }
      40% { transform: scale(1); }
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }

    :host.bubble-highlighted .bubble {
      border-color: #38bdf8 !important;
      box-shadow: 0 0 25px rgba(56, 189, 248, 0.6), inset 0 0 10px rgba(56, 189, 248, 0.2) !important;
      transform: scale(1.02);
      transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
      animation: pulseHighlight 1.5s infinite alternate;
    }

    .msg-protocol-correlation {
      margin-top: 6px;
      display: flex;
    }

    .btn-corr-pill {
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid rgba(56, 189, 248, 0.45);
      color: #38bdf8;
      font-size: 0.68rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 12px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
    }

    .btn-corr-pill:hover {
      background: rgba(14, 165, 233, 0.25);
      border-color: #38bdf8;
      color: #ffffff;
      transform: translateY(-1px);
      box-shadow: 0 2px 8px rgba(56, 189, 248, 0.4);
    }

    .btn-corr-pill .pill-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 4px #10b981;
    }

    .btn-corr-pill .pill-arrow {
      font-size: 0.62rem;
      transition: transform 0.2s;
    }

    .btn-corr-pill:hover .pill-arrow {
      transform: translateX(2px);
    }

    @keyframes pulseHighlight {
      0% {
        box-shadow: 0 0 18px rgba(56, 189, 248, 0.4), inset 0 0 8px rgba(56, 189, 248, 0.15);
      }
      100% {
        box-shadow: 0 0 30px rgba(56, 189, 248, 0.75), inset 0 0 14px rgba(56, 189, 248, 0.3);
      }
    }
  `]
})
export class ChatMessageComponent {
  @Input({ required: true }) message!: ChatMessage;

  sanitizer = inject(DomSanitizer);
  chatService = inject(ChatService);

  isUser(): boolean {
    return this.message.sender === Sender.USER;
  }

  isNotice(): boolean {
    if (this.isUser() || !this.message.text) return false;
    const txt = this.message.text.toLowerCase();
    return (
      txt.includes('⚠️') ||
      txt.includes('preavviso minimo') ||
      txt.includes('serve un preavviso') ||
      txt.includes('preavviso di almeno') ||
      txt.includes('non è possibile') ||
      txt.includes('non possiamo') ||
      txt.includes('non consentito') ||
      txt.includes('sicurezza alimentare') ||
      txt.includes('rifiuto')
    );
  }

  getSelectedOptionId(): string | null {
    const chk = this.message.checkout || this.chatService.latestCheckout();
    if (!chk?.fulfillment) return null;
    const f: any = chk.fulfillment;
    const methods: any[] = Array.isArray(f.methods) ? f.methods : (f.root?.methods || []);
    for (const m of methods) {
      if (m.groups && m.groups.length > 0) {
        return m.groups[0].selected_option_id || null;
      }
    }
    return null;
  }

  hasHotItems(): boolean {
    const chk = this.message.checkout || this.chatService.latestCheckout();
    if (!chk?.line_items) return false;
    return chk.line_items.some((li) => {
      const title = (li.item?.title || '').toLowerCase();
      return (
        title.includes('espresso') ||
        title.includes('cappuccino') ||
        title.includes('caldo') ||
        title.includes('calda') ||
        title.includes('toast')
      );
    });
  }

  formatMarkdown(rawText?: string): SafeHtml {
    if (!rawText) return '';
    let text = rawText
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Headings
    text = text.replace(/^### (.*$)/gim, '<div class="msg-heading">$1</div>');
    text = text.replace(/^## (.*$)/gim, '<div class="msg-heading large">$1</div>');

    // Bold & italic
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Code
    text = text.replace(/`([^`]+)`/g, '<code class="msg-code">$1</code>');

    // Dividers
    text = text.replace(/^---$/gim, '<div class="msg-divider"></div>');

    // Bullets
    text = text.replace(/^[*-] (.*$)/gim, '<div class="msg-bullet">• $1</div>');
    text = text.replace(/^\d+\.\s+(.*$)/gim, '<div class="msg-bullet"><strong>•</strong> $1</div>');

    // Line breaks
    text = text.replace(/\n/g, '<br/>');

    return this.sanitizer.bypassSecurityTrustHtml(text);
  }

  getQuickSuggestions(): SuggestionAction[] {
    if (this.isUser() || !this.message.text) return [];

    // Suggestions are only relevant if there's an operational warning/constraint (isNotice)
    // or if the assistant is explicitly prompting the user to choose an alternative method.
    const text = this.message.text.toLowerCase();
    const isChoosingMethod =
      text.includes('quale modalità preferisci') ||
      text.includes('come preferisci ricevere') ||
      text.includes('puoi scegliere tra');

    if (!this.isNotice() && !isChoosingMethod) {
      return [];
    }

    const suggestions: SuggestionAction[] = [];
    const currentOptionId = this.getSelectedOptionId();

    // 1. Proponi Ritiro Express al Banco SOLO se non è già il metodo selezionato nel carrello
    if (currentOptionId !== 'pickup_express') {
      if (
        text.includes('ritiro express') ||
        text.includes('al banco') ||
        text.includes('bistrot binario 12') ||
        text.includes('pronto in soli 5 minuti') ||
        text.includes('in soli 5 minuti') ||
        text.includes('alternativa')
      ) {
        suggestions.push({
          label: '⚡ Passa a Ritiro Express al Banco (5 min)',
          prompt: 'Vorrei passare al Ritiro Express al Banco presso il Bistrot Binario 12 (pronto in 5 minuti).',
          variant: 'express',
        });
      }
    }

    // 2. Proponi Consegna al Treno SOLO se non è già il metodo selezionato,
    // e se il messaggio fa effettivo riferimento al servizio treno (escludendo il semplice nome del bistrot)
    if (currentOptionId !== 'in_seat_train') {
      const mentionsTrainDelivery =
        text.includes('consegna al posto') ||
        text.includes('a bordo treno') ||
        text.includes('consegna al treno') ||
        text.includes('frecciarossa') ||
        text.includes('italo');

      if (mentionsTrainDelivery) {
        suggestions.push({
          label: '🚆 Consegna al Treno al primo orario valido (+35 min)',
          prompt: 'Va bene, programma la consegna a bordo treno per il primo orario utile con almeno 35 minuti di preavviso.',
          variant: 'train',
        });
      }
    }

    // 3. Proponi Smart Locker SOLO se non è già selezionato E non ci sono alimenti/bevande calde nel carrello
    if (currentOptionId !== 'pickup_locker' && !this.hasHotItems()) {
      if (
        text.includes('locker') &&
        (text.includes('slot') || text.includes('preavviso') || text.includes('freddi'))
      ) {
        suggestions.push({
          label: '📦 Imposta primo slot Locker utile (+30 min)',
          prompt: 'Va bene, programma il ritiro allo Smart Locker per il primo slot utile con preavviso di 30 minuti.',
          variant: 'locker',
        });
      }
    }

    return suggestions;
  }

  onSuggestionClick(prompt: string): void {
    this.chatService.sendMessage(prompt);
  }

  onJumpToInspector(stepNum: number, allStepNums?: number[]): void {
    this.chatService.jumpToInspector(stepNum, allStepNums);
  }

  formatStepRange(stepNumbers: number[] | undefined): string {
    if (!stepNumbers || stepNumbers.length === 0) return '';
    if (stepNumbers.length === 1) return `Passo ${stepNumbers[0]}`;
    const min = Math.min(...stepNumbers);
    const max = Math.max(...stepNumbers);
    return min === max ? `Passo ${min}` : `Passi ${min}–${max}`;
  }
}
