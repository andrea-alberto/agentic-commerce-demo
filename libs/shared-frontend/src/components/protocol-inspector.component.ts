import {
  Component,
  Input,
  Output,
  EventEmitter,
  ViewChild,
  ElementRef,
  OnChanges,
  SimpleChanges,
  AfterViewInit
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ProtocolStep } from '../models/protocol-trace.model';

@Component({
  selector: 'lib-protocol-inspector',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div
      class="inspector-card"
      [class.theme-shopper]="theme === 'shopper'"
      [class.theme-merchant]="theme === 'merchant'"
    >
      <!-- INSPECTOR HEADER -->
      <div class="inspector-header">
        <div class="inspector-header-left">
          <span class="insp-icon">📡</span>
          <div>
            <h3 class="card-title">{{ title }}</h3>
            <span class="card-sub">{{ subtitle }}</span>
          </div>
        </div>

        <div class="inspector-header-right">
          <button
            *ngIf="steps && steps.length > 1"
            type="button"
            class="btn-header-scroll"
            (click)="scrollToBottom(true)"
            title="Scorri all'ultimo passaggio"
          >
            ⬇️ In fondo
          </button>
          <span class="live-pill" [class.active]="isLive">
            <span class="dot"></span>
            {{ isLive ? 'ATTIVO' : 'IDLE' }}
          </span>
          <span class="proto-badge" [ngClass]="protocolClass">
            {{ protocolBadge }}
          </span>
        </div>
      </div>

      <!-- INSPECTOR BODY -->
      <div class="inspector-body" #inspectorBody (scroll)="onScroll()">
        <!-- EMPTY STATE -->
        <div *ngIf="steps.length === 0 && !isLive" class="empty-inspector">
          <span class="empty-icon">🛰️</span>
          <p>{{ emptyMessage }}</p>
          <small>{{ emptySub }}</small>
        </div>

        <!-- TIMELINE OF STEPS -->
        <div class="step-timeline" *ngIf="steps.length > 0">
          <div
            *ngFor="let step of steps; let i = index"
            class="step-card"
            [id]="'step-card-' + step.step_number"
            [class.step-success]="step.status === 'success'"
            [class.step-pending]="step.status === 'pending'"
            [class.step-error]="step.status === 'error'"
            [class.step-highlighted]="isStepHighlighted(step.step_number)"
          >
            <!-- TOP LINE -->
            <div class="step-top-line">
              <div class="step-num-badge">Passo {{ step.step_number }}</div>
              <div class="actors-chain">
                <span class="actor-pill" [ngClass]="getActorBadgeClass(step.actor_source)" [title]="getActorTooltip(step.actor_source)">
                  <span class="actor-ico">{{ getActorIcon(step.actor_source) }}</span>
                  <span class="actor-name">{{ formatActorName(step.actor_source) }}</span>
                  <span *ngIf="getActorRoleBadge(step.actor_source)" class="actor-role-tag">{{ getActorRoleBadge(step.actor_source) }}</span>
                </span>
                <span class="arrow-dir">➔</span>
                <span class="actor-pill" [ngClass]="getActorBadgeClass(step.actor_target)" [title]="getActorTooltip(step.actor_target)">
                  <span class="actor-ico">{{ getActorIcon(step.actor_target) }}</span>
                  <span class="actor-name">{{ formatActorName(step.actor_target) }}</span>
                  <span *ngIf="getActorRoleBadge(step.actor_target)" class="actor-role-tag">{{ getActorRoleBadge(step.actor_target) }}</span>
                </span>
              </div>
              <div class="meta-right">
                <button
                  *ngIf="step.related_message_id"
                  type="button"
                  class="btn-step-jump-chat"
                  (click)="onStepClick(step)"
                  title="Allinea la chat al messaggio corrispondente"
                >
                  <span class="chat-icon">💬</span>
                  <span class="jump-txt">Chat</span>
                  <span class="jump-arr">➔</span>
                </button>
                <span *ngIf="step.latency_ms" class="latency-badge">⚡ {{ step.latency_ms }}ms</span>
                <span class="step-timestamp">{{ step.timestamp }}</span>
              </div>
            </div>

            <!-- ACTION & STATUS -->
            <div class="step-action-row">
              <strong class="action-name">{{ step.action }}</strong>
              <span
                class="action-status-tag"
                [class.tag-ok]="step.status === 'success'"
                [class.tag-pending]="step.status === 'pending'"
                [class.tag-err]="step.status === 'error'"
              >
                {{ step.status === 'success' ? '✓ OK' : (step.status === 'pending' ? '⏳ ATTESA' : '⚠️ ' + step.status) }}
              </span>
            </div>

            <!-- DESCRIPTION -->
            <p class="step-desc">{{ step.description }}</p>

            <!-- RFC 9421 HEADERS (FOR REST SIGNED STEPS) -->
            <div *ngIf="isRfc9421(step)" class="rfc9421-box">
              <div class="rfc-title">
                <span>🔐 RFC 9421 HTTP Message Signature</span>
                <span class="rfc-valid-badge">Verified ECDSA-P256</span>
              </div>
              <div class="rfc-headers-list">
                <div class="rfc-header-item" *ngIf="getHeader(step, 'signature-input')">
                  <span class="h-name">Signature-Input:</span>
                  <code>{{ getHeader(step, 'signature-input') }}</code>
                </div>
                <div class="rfc-header-item" *ngIf="getHeader(step, 'signature')">
                  <span class="h-name">Signature:</span>
                  <code class="sig-val">{{ getHeader(step, 'signature') }}</code>
                </div>
                <div class="rfc-header-item" *ngIf="getHeader(step, 'content-digest')">
                  <span class="h-name">Content-Digest:</span>
                  <code>{{ getHeader(step, 'content-digest') }}</code>
                </div>
              </div>
            </div>

            <!-- A2A HEADERS (FOR JSON-RPC / A2A DIRECT STEPS) -->
            <div *ngIf="isA2AHeaders(step)" class="a2a-headers-box">
              <div class="a2a-title">
                <span>🌐 Specifiche di Rete A2A & Profilo UCP</span>
                <span class="a2a-valid-badge">A2A Compliant</span>
              </div>
              <div class="a2a-headers-list">
                <div class="a2a-header-item" *ngIf="getHeader(step, 'x-a2a-extensions')">
                  <span class="h-name">X-A2A-Extensions:</span>
                  <code>{{ getHeader(step, 'x-a2a-extensions') }}</code>
                </div>
                <div class="a2a-header-item" *ngIf="getHeader(step, 'ucp-agent')">
                  <span class="h-name">UCP-Agent:</span>
                  <code>{{ getHeader(step, 'ucp-agent') }}</code>
                </div>
              </div>
            </div>

            <!-- JSON PAYLOAD VIEWER -->
            <div class="payload-box" *ngIf="step.payload">
              <div class="payload-header">
                <span>Carico Utile (Payload JSON):</span>
                <button type="button" class="btn-copy-json" (click)="copyPayload(step, i)">
                  {{ copiedStepIndex === i ? 'Copiato! ✓' : 'Copia JSON' }}
                </button>
              </div>
              <pre class="json-code"><code>{{ formatPayload(step.payload) }}</code></pre>
            </div>
          </div>
        </div>
      </div>

      <!-- FLOATING SCROLL TO BOTTOM BUTTON -->
      <button
        *ngIf="userScrolledUp && steps && steps.length > 0"
        type="button"
        class="float-scroll-bottom"
        (click)="scrollToBottomClick()"
        title="Scorri verso l'ultimo passaggio"
      >
        <span>Nuovi passaggi</span>
        <span class="arrow">⬇️</span>
      </button>
    </div>
  `,
  styles: [`
    :host {
      display: flex;
      flex-direction: column;
      flex: 1;
      height: 100%;
      min-height: 0;
      max-height: 100%;
      overflow: hidden;
      width: 100%;
      position: relative;
    }

    .inspector-card {
      background: #090d16;
      border: 1px solid #1e293b;
      border-radius: 14px;
      display: flex;
      flex-direction: column;
      flex: 1;
      height: 100%;
      min-height: 0;
      max-height: 100%;
      overflow: hidden;
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.45);
      font-family: inherit;
      position: relative;
    }

    .inspector-header {
      padding: 0.9rem 1.1rem;
      background: #0f172a;
      border-bottom: 1px solid #1e293b;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }

    .inspector-header-left {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .insp-icon {
      font-size: 1.3rem;
    }

    .card-title {
      font-size: 0.95rem;
      font-weight: 700;
      color: #f8fafc;
      margin: 0;
    }

    .card-sub {
      font-size: 0.72rem;
      color: #64748b;
      display: block;
      margin-top: 2px;
    }

    .inspector-header-right {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .live-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 3px 8px;
      border-radius: 12px;
      background: #1e293b;
      color: #94a3b8;
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.5px;
    }

    .live-pill .dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #64748b;
    }

    .live-pill.active {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .live-pill.active .dot {
      background: #10b981;
      box-shadow: 0 0 8px #10b981;
      animation: pulse-dot 1.5s infinite;
    }

    @keyframes pulse-dot {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }

    .proto-badge {
      font-size: 0.72rem;
      font-weight: 800;
      padding: 3px 10px;
      border-radius: 6px;
      letter-spacing: 0.4px;
    }

    .proto-badge.a2a {
      background: linear-gradient(135deg, rgba(79, 70, 229, 0.2), rgba(99, 102, 241, 0.3));
      color: #a5b4fc;
      border: 1px solid rgba(99, 102, 241, 0.4);
    }

    .proto-badge.rest {
      background: linear-gradient(135deg, rgba(6, 182, 212, 0.2), rgba(14, 165, 233, 0.3));
      color: #38bdf8;
      border: 1px solid rgba(6, 182, 212, 0.4);
    }

    .proto-badge.mcp {
      background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.3));
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.4);
    }

    /* DEMO-SPECIFIC PROTOCOL BADGES (SYNCED WITH BOPIS DISPATCHER) */
    .proto-badge.demo1,
    .proto-badge.a2a-direct {
      background: rgba(59, 130, 246, 0.2) !important;
      color: #60a5fa !important;
      border: 1px solid rgba(59, 130, 246, 0.45) !important;
    }

    .proto-badge.demo3,
    .proto-badge.a2a-federation {
      background: rgba(245, 158, 11, 0.2) !important;
      color: #fbbf24 !important;
      border: 1px solid rgba(245, 158, 11, 0.45) !important;
    }

    .proto-badge.demo4,
    .proto-badge.rest-signed {
      background: rgba(168, 85, 247, 0.2) !important;
      color: #c084fc !important;
      border: 1px solid rgba(168, 85, 247, 0.45) !important;
    }

    /* THEME: SHOPPER (PERSONAL AGENT COCKPIT - GEMINI DEEP VIOLET) */
    .inspector-card.theme-shopper {
      background: #120e24;
      border: 1px solid #2d1f4e;
      border-radius: 12px;
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.5);
    }

    .inspector-card.theme-shopper .inspector-header {
      background: #1a1435;
      border-bottom: 1px solid #2d1f4e;
      padding: 0.75rem 1rem;
    }

    .inspector-card.theme-shopper .card-title {
      font-size: 0.95rem;
      font-weight: 700;
      color: #f3e8ff;
    }

    .inspector-card.theme-shopper .card-sub {
      font-size: 0.72rem;
      color: #c084fc;
    }

    .inspector-card.theme-shopper .step-card {
      background: #181230;
      border: 1px solid #2d1f4e;
      border-radius: 10px;
    }

    .inspector-card.theme-shopper .step-num-badge {
      background: #281e52;
      color: #d8b4fe;
      border: 1px solid rgba(168, 85, 247, 0.3);
    }

    /* THEME: MERCHANT (BISTROT MILANO CENTRALE - ESPRESSO & AMBER) */
    .inspector-card.theme-merchant {
      background: #1c1917;
      border: 1px solid #292524;
      border-radius: 14px;
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
    }

    .inspector-card.theme-merchant .inspector-header {
      background: #24201e;
      border-bottom: 1px solid #292524;
      padding: 0.85rem 1.15rem;
    }

    .inspector-card.theme-merchant .card-title {
      color: #fef3c7;
      font-weight: 700;
      font-size: 0.95rem;
    }

    .inspector-card.theme-merchant .card-sub {
      color: #f59e0b;
      font-size: 0.72rem;
    }

    .inspector-card.theme-merchant .step-card {
      background: #24201e;
      border: 1px solid #3d3835;
      border-radius: 12px;
    }

    .inspector-card.theme-merchant .step-num-badge {
      background: #1c1917;
      color: #fbbf24;
      border: 1px solid rgba(217, 119, 6, 0.4);
    }

    .inspector-body {
      flex: 1;
      min-height: 0;
      padding: 1rem;
      overflow-y: auto;
      overflow-x: hidden;
      display: flex;
      flex-direction: column;
      gap: 1rem;
      scroll-behavior: smooth;
    }

    .inspector-body::-webkit-scrollbar {
      width: 8px;
    }

    .inspector-body::-webkit-scrollbar-track {
      background: #090d16;
    }

    .inspector-body::-webkit-scrollbar-thumb {
      background: #334155;
      border-radius: 4px;
    }

    .inspector-body::-webkit-scrollbar-thumb:hover {
      background: #475569;
    }

    .empty-inspector {
      text-align: center;
      padding: 3rem 1.5rem;
      color: #64748b;
    }

    .empty-icon {
      font-size: 2.2rem;
      display: block;
      margin-bottom: 0.8rem;
      opacity: 0.8;
    }

    .empty-inspector p {
      font-size: 0.92rem;
      font-weight: 600;
      color: #94a3b8;
      margin: 0 0 4px 0;
    }

    .empty-inspector small {
      font-size: 0.75rem;
      color: #64748b;
    }

    .step-timeline {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .step-card {
      background: #0f172a;
      border: 1px solid #1e293b;
      border-radius: 10px;
      padding: 0.9rem;
      display: flex;
      flex-direction: column;
      gap: 0.55rem;
      transition: border-color 0.2s ease;
    }

    .step-card.step-success {
      border-color: #334155;
    }

    .step-card.step-pending {
      border-color: rgba(99, 102, 241, 0.5);
      background: #111827;
    }

    .step-card.step-highlighted {
      border-color: #38bdf8 !important;
      background: linear-gradient(135deg, rgba(14, 165, 233, 0.15) 0%, rgba(15, 23, 42, 0.98) 100%) !important;
      box-shadow: 0 0 25px rgba(56, 189, 248, 0.5), inset 0 0 12px rgba(56, 189, 248, 0.2) !important;
      transform: scale(1.02);
      transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
      z-index: 5;
    }

    .btn-step-jump-chat {
      background: rgba(99, 102, 241, 0.2);
      border: 1px solid rgba(99, 102, 241, 0.45);
      color: #c7d2fe;
      font-size: 0.65rem;
      font-weight: 700;
      padding: 1px 7px;
      border-radius: 4px;
      display: inline-flex;
      align-items: center;
      gap: 3px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .btn-step-jump-chat:hover {
      background: #4f46e5;
      color: #ffffff;
      border-color: #6366f1;
      transform: translateY(-1px);
      box-shadow: 0 2px 8px rgba(79, 70, 229, 0.4);
    }

    .btn-step-jump-chat .jump-arr {
      font-size: 0.62rem;
      transition: transform 0.2s;
    }

    .btn-step-jump-chat:hover .jump-arr {
      transform: translateX(2px);
    }

    .step-top-line {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }

    .step-num-badge {
      background: #1e293b;
      color: #38bdf8;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.68rem;
      font-weight: 800;
      padding: 2px 7px;
      border-radius: 4px;
      border: 1px solid #334155;
    }

    .actors-chain {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 0.72rem;
      font-family: 'JetBrains Mono', monospace;
      flex-wrap: wrap;
    }

    .actor-pill {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.68rem;
      font-weight: 600;
      border: 1px solid transparent;
      line-height: 1.2;
      transition: all 0.2s ease;
    }

    .actor-pill .actor-ico {
      font-size: 0.75rem;
      line-height: 1;
    }

    .actor-pill .actor-name {
      color: inherit;
    }

    .actor-pill .actor-role-tag {
      font-size: 0.55rem;
      font-weight: 800;
      letter-spacing: 0.4px;
      padding: 1px 4px;
      border-radius: 3px;
      text-transform: uppercase;
      line-height: 1;
    }

    .actor-pill.actor-client {
      background: rgba(56, 189, 248, 0.12);
      border-color: rgba(56, 189, 248, 0.35);
      color: #7dd3fc;
    }
    .actor-pill.actor-client .actor-role-tag {
      background: rgba(56, 189, 248, 0.25);
      color: #38bdf8;
    }

    .actor-pill.actor-shopper-server {
      background: rgba(168, 85, 247, 0.12);
      border-color: rgba(168, 85, 247, 0.35);
      color: #d8b4fe;
    }
    .actor-pill.actor-shopper-server .actor-role-tag {
      background: rgba(168, 85, 247, 0.28);
      color: #c084fc;
    }

    .actor-pill.actor-merchant {
      background: rgba(245, 158, 11, 0.12);
      border-color: rgba(245, 158, 11, 0.35);
      color: #fcd34d;
    }
    .actor-pill.actor-merchant .actor-role-tag {
      background: rgba(245, 158, 11, 0.25);
      color: #fbbf24;
    }

    .actor-pill.actor-rest {
      background: rgba(16, 185, 129, 0.12);
      border-color: rgba(16, 185, 129, 0.35);
      color: #6ee7b7;
    }
    .actor-pill.actor-rest .actor-role-tag {
      background: rgba(16, 185, 129, 0.25);
      color: #34d399;
    }

    .actor-pill.actor-lcm {
      background: rgba(20, 184, 166, 0.15);
      border-color: rgba(20, 184, 166, 0.45);
      color: #2dd4bf;
    }
    .actor-pill.actor-lcm .actor-role-tag {
      background: rgba(20, 184, 166, 0.3);
      color: #14b8a6;
    }

    .actor-pill.actor-processor {
      background: rgba(236, 72, 153, 0.15);
      border-color: rgba(236, 72, 153, 0.45);
      color: #f472b6;
    }
    .actor-pill.actor-processor .actor-role-tag {
      background: rgba(236, 72, 153, 0.3);
      color: #ec4899;
    }

    .actor-pill.actor-bopis {
      background: rgba(249, 115, 22, 0.15);
      border-color: rgba(249, 115, 22, 0.45);
      color: #fb923c;
    }
    .actor-pill.actor-bopis .actor-role-tag {
      background: rgba(249, 115, 22, 0.3);
      color: #f97316;
    }

    .actor-pill.actor-generic {
      background: rgba(148, 163, 184, 0.12);
      border-color: rgba(148, 163, 184, 0.25);
      color: #cbd5e1;
    }

    .arrow-dir {
      color: #6366f1;
      font-weight: 800;
      font-size: 0.72rem;
    }

    .meta-right {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .latency-badge {
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.65rem;
      font-weight: 700;
      padding: 1px 6px;
      border-radius: 4px;
    }

    .step-timestamp {
      font-size: 0.68rem;
      color: #64748b;
      font-family: 'JetBrains Mono', monospace;
    }

    .step-action-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }

    .action-name {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.82rem;
      color: #f1f5f9;
      word-break: break-all;
    }

    .action-status-tag {
      font-size: 0.68rem;
      font-weight: 800;
      padding: 2px 7px;
      border-radius: 4px;
      letter-spacing: 0.3px;
    }

    .action-status-tag.tag-ok {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
    }

    .action-status-tag.tag-pending {
      background: rgba(99, 102, 241, 0.15);
      color: #a5b4fc;
    }

    .action-status-tag.tag-err {
      background: rgba(239, 68, 68, 0.15);
      color: #f87171;
    }

    .step-desc {
      font-size: 0.78rem;
      color: #94a3b8;
      line-height: 1.4;
      margin: 0;
    }

    /* RFC 9421 BOX */
    .rfc9421-box {
      background: #020617;
      border: 1px solid #1e293b;
      border-left: 3px solid #06b6d4;
      border-radius: 6px;
      padding: 0.6rem 0.8rem;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }

    .rfc-title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.7rem;
      font-weight: 700;
      color: #38bdf8;
    }

    .rfc-valid-badge {
      background: rgba(6, 182, 212, 0.2);
      color: #67e8f9;
      font-size: 0.62rem;
      padding: 1px 6px;
      border-radius: 3px;
    }

    .rfc-headers-list, .a2a-headers-list {
      display: flex;
      flex-direction: column;
      gap: 0.3rem;
    }

    .rfc-header-item, .a2a-header-item {
      display: flex;
      flex-direction: column;
      gap: 1px;
    }

    .h-name {
      font-size: 0.66rem;
      color: #64748b;
      font-weight: 600;
      font-family: 'JetBrains Mono', monospace;
    }

    code {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.7rem;
      color: #cbd5e1;
      word-break: break-all;
      background: rgba(255, 255, 255, 0.04);
      padding: 2px 4px;
      border-radius: 3px;
    }

    code.sig-val {
      color: #a78bfa;
    }

    /* A2A HEADERS BOX */
    .a2a-headers-box {
      background: #020617;
      border: 1px solid #1e293b;
      border-left: 3px solid #6366f1;
      border-radius: 6px;
      padding: 0.6rem 0.8rem;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }

    .a2a-title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.7rem;
      font-weight: 700;
      color: #818cf8;
    }

    .a2a-valid-badge {
      background: rgba(99, 102, 241, 0.2);
      color: #c7d2fe;
      font-size: 0.62rem;
      padding: 1px 6px;
      border-radius: 3px;
    }

    /* PAYLOAD BOX */
    .payload-box {
      background: #020617;
      border: 1px solid #1e293b;
      border-radius: 6px;
      overflow: hidden;
    }

    .payload-header {
      padding: 0.35rem 0.7rem;
      background: rgba(255, 255, 255, 0.02);
      border-bottom: 1px solid #1e293b;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.68rem;
      color: #64748b;
      font-weight: 600;
    }

    .btn-copy-json {
      background: transparent;
      border: 1px solid #334155;
      color: #94a3b8;
      font-size: 0.65rem;
      padding: 2px 6px;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .btn-copy-json:hover {
      background: #1e293b;
      color: #f8fafc;
      border-color: #64748b;
    }

    .btn-header-scroll {
      background: #1e293b;
      border: 1px solid #334155;
      color: #cbd5e1;
      font-size: 0.68rem;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: all 0.2s;
    }

    .btn-header-scroll:hover {
      background: #334155;
      color: #38bdf8;
      border-color: #64748b;
    }

    .float-scroll-bottom {
      position: absolute;
      bottom: 1rem;
      right: 1.25rem;
      background: #4f46e5;
      color: #ffffff;
      border: 1px solid #6366f1;
      border-radius: 20px;
      padding: 6px 12px;
      font-size: 0.72rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5), 0 0 10px rgba(99, 102, 241, 0.4);
      z-index: 10;
      animation: fadeInBottom 0.2s ease-out;
      transition: all 0.2s ease;
    }

    .float-scroll-bottom:hover {
      background: #4338ca;
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.6), 0 0 14px rgba(99, 102, 241, 0.6);
    }

    @keyframes fadeInBottom {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .json-code {
      margin: 0;
      padding: 0.6rem 0.8rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.7rem;
      line-height: 1.4;
      color: #38bdf8;
      max-height: 220px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }
  `]
})
export class ProtocolInspectorComponent implements OnChanges, AfterViewInit {
  @Input() steps: ProtocolStep[] = [];
  @Input() isLive: boolean = false;
  @Input() theme: 'merchant' | 'shopper' | 'auto' = 'auto';
  @Input() protocolBadge: string = 'A2A Direct (JSON-RPC 2.0)';
  @Input() protocolClass: string = 'a2a';
  @Input() title: string = 'Live Protocol Inspector';
  @Input() subtitle: string = 'Traccia dei messaggi di rete e conformità alle specifiche UCP & AP2';
  @Input() emptyMessage: string = 'Nessuna transazione in corso.';
  @Input() emptySub: string = 'Invia una richiesta nella chat per vedere i messaggi scambiati in tempo reale.';
  @Input() highlightedStepNumbers: number[] = [];
  @Output() stepSelected = new EventEmitter<ProtocolStep>();

  @ViewChild('inspectorBody') private inspectorBody?: ElementRef<HTMLDivElement>;

  copiedStepIndex: number | null = null;
  userScrolledUp: boolean = false;
  localHighlightedSteps: number[] = [];
  private lastStepCount: number = 0;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['protocolBadge'] || changes['protocolClass']) {
      this.userScrolledUp = false;
    }
    if (changes['steps']) {
      const currentCount = this.steps?.length ?? 0;
      if (currentCount < this.lastStepCount) {
        // Steps were cleared/reset
        this.userScrolledUp = false;
      }
      if (!this.userScrolledUp || currentCount > this.lastStepCount) {
        this.scheduleScrollToBottom();
      }
      this.lastStepCount = currentCount;
    }
    if (changes['isLive'] && !this.userScrolledUp) {
      this.scheduleScrollToBottom();
    }
  }

  ngAfterViewInit(): void {
    this.scheduleScrollToBottom(false);
  }

  onScroll(): void {
    if (!this.inspectorBody?.nativeElement) return;
    const el = this.inspectorBody.nativeElement;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    this.userScrolledUp = distanceFromBottom > 80;
  }

  scheduleScrollToBottom(smooth = true): void {
    setTimeout(() => {
      this.scrollToBottom(smooth);
    }, 60);
  }

  scrollToBottom(smooth = true): void {
    if (!this.inspectorBody?.nativeElement) return;
    const el = this.inspectorBody.nativeElement;
    el.scrollTo({
      top: el.scrollHeight,
      behavior: smooth ? 'smooth' : 'auto'
    });
  }

  scrollToBottomClick(): void {
    this.userScrolledUp = false;
    this.scrollToBottom(true);
  }

  scrollToStep(stepNumber: number, allStepNumbers?: number[]): void {
    if (allStepNumbers && allStepNumbers.length > 0) {
      this.localHighlightedSteps = [...allStepNumbers];
    } else {
      this.localHighlightedSteps = [stepNumber];
    }

    setTimeout(() => {
      if (!this.inspectorBody?.nativeElement) return;
      const targetEl = this.inspectorBody.nativeElement.querySelector('#step-card-' + stepNumber) as HTMLElement;
      if (targetEl) {
        targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 60);

    setTimeout(() => {
      this.localHighlightedSteps = [];
    }, 3000);
  }

  isStepHighlighted(stepNumber: number): boolean {
    return (
      (this.highlightedStepNumbers && this.highlightedStepNumbers.includes(stepNumber)) ||
      this.localHighlightedSteps.includes(stepNumber)
    );
  }

  onStepClick(step: ProtocolStep): void {
    this.stepSelected.emit(step);
  }

  isRfc9421(step: ProtocolStep): boolean {
    if (!step.headers) return false;
    return !!(
      this.getHeader(step, 'signature') ||
      this.getHeader(step, 'signature-input')
    );
  }

  isA2AHeaders(step: ProtocolStep): boolean {
    if (!step.headers) return false;
    return !!(
      this.getHeader(step, 'x-a2a-extensions') ||
      this.getHeader(step, 'ucp-agent')
    );
  }

  getHeader(step: ProtocolStep, key: string): string | null {
    if (!step.headers) return null;
    const lowerKey = key.toLowerCase();
    for (const [k, v] of Object.entries(step.headers)) {
      if (k.toLowerCase() === lowerKey) return v;
    }
    return null;
  }

  formatPayload(payload: any): string {
    if (typeof payload === 'string') return payload;
    try {
      return JSON.stringify(payload, null, 2);
    } catch {
      return String(payload);
    }
  }

  copyPayload(step: ProtocolStep, index: number): void {
    const text = this.formatPayload(step.payload);
    navigator.clipboard.writeText(text);
    this.copiedStepIndex = index;
    setTimeout(() => {
      this.copiedStepIndex = null;
    }, 2000);
  }

  getActorIcon(actor: string): string {
    switch (actor) {
      case 'shopper_client':
      case 'client_browser':
        return '💻';
      case 'credential_manager':
      case 'local_credential_manager':
        return '🔐';
      case 'shopper_agent':
      case 'shopper_server':
        return '🤖';
      case 'merchant_agent':
        return '🏪';
      case 'payment_processor':
      case 'mpp':
        return '💳';
      case 'bopis_engine':
        return '📦';
      case 'ucp_rest_server':
      case 'merchant_server':
        return '🌐';
      default:
        return '📡';
    }
  }

  getActorRoleBadge(actor: string): string {
    switch (actor) {
      case 'shopper_client':
      case 'client_browser':
        return 'CLIENT';
      case 'credential_manager':
      case 'local_credential_manager':
        return 'OS TRUSTED SURFACE';
      case 'shopper_agent':
      case 'shopper_server':
        return 'SERVER';
      case 'merchant_agent':
        return 'MERCHANT';
      case 'payment_processor':
      case 'mpp':
        return 'PAYMENT GATEWAY';
      case 'bopis_engine':
        return 'STORE LOGISTICS';
      case 'ucp_rest_server':
      case 'merchant_server':
        return 'REST API';
      default:
        return '';
    }
  }

  getActorBadgeClass(actor: string): string {
    switch (actor) {
      case 'shopper_client':
      case 'client_browser':
        return 'actor-client';
      case 'credential_manager':
      case 'local_credential_manager':
        return 'actor-lcm';
      case 'shopper_agent':
      case 'shopper_server':
        return 'actor-shopper-server';
      case 'merchant_agent':
        return 'actor-merchant';
      case 'payment_processor':
      case 'mpp':
        return 'actor-processor';
      case 'bopis_engine':
        return 'actor-bopis';
      case 'ucp_rest_server':
      case 'merchant_server':
        return 'actor-rest';
      default:
        return 'actor-generic';
    }
  }

  getActorTooltip(actor: string): string {
    switch (actor) {
      case 'shopper_client':
        return 'Client Web / Passkey LCM dell\'Utente Viaggiatore';
      case 'client_browser':
        return 'Browser Web Client (Frontend)';
      case 'credential_manager':
      case 'local_credential_manager':
        return 'Local Credential Manager (LCM) • Superficie Fidata del Sistema Operativo (FIDO2 / KeyMint)';
      case 'shopper_agent':
        return 'Personal Shopper AI Agent (Server Backend)';
      case 'merchant_agent':
        return 'Merchant Agent di Stazione (Bistrot Milano Centrale)';
      case 'payment_processor':
      case 'mpp':
        return 'Merchant Payment Processor (MPP) • Gateway Acquirer Bancario / Verifica Mandati AP2';
      case 'bopis_engine':
        return 'BOPIS Engine di Stazione • Gestione Preparazione Cucina, Smart Locker e Consegna Binario';
      case 'ucp_rest_server':
        return 'UCP Standard REST Gateway Server';
      default:
        return actor;
    }
  }

  formatActorName(actor: string): string {
    return actor || '';
  }
}
