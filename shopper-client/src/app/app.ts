// Copyright 2026 UCP Authors / GDG DevFest Milano 2026
import { Component, inject, effect, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  TravelerTicketCardComponent,
  TravelerContextModalComponent,
  TravelerLcmModalComponent,
  ProtocolInspectorComponent,
  TravelerProposalCardComponent,
  ScenarioPreset,
  TravelerContext,
  ProtocolStep,
  DEFAULT_SCENARIO_PRESETS
} from '@ucp/shared-frontend';
import { ShopperService } from './services/shopper.service';
import { AuthService } from './services/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TravelerTicketCardComponent,
    TravelerContextModalComponent,
    TravelerLcmModalComponent,
    ProtocolInspectorComponent,
    TravelerProposalCardComponent
  ],
  templateUrl: './app.html',
  styleUrls: ['./app.css']
})
export class App {
  readonly shopperService = inject(ShopperService);
  readonly authService = inject(AuthService);
  @ViewChild('messagesContainer') private messagesContainer?: ElementRef<HTMLDivElement>;
  @ViewChild(ProtocolInspectorComponent) private inspector?: ProtocolInspectorComponent;

  inputText: string = '';
  copiedStepIndex: number | null = null;
  highlightedMessageId: string | null = null;
  highlightedStepNumbers: number[] = [];

  constructor() {
    effect(() => {
      // Trigger when chat messages or proposal state updates
      this.shopperService.chatMessages();
      this.shopperService.pendingProposal();
      setTimeout(() => {
        if (this.messagesContainer?.nativeElement) {
          this.messagesContainer.nativeElement.scrollTo({
            top: this.messagesContainer.nativeElement.scrollHeight,
            behavior: 'smooth'
          });
        }
      }, 50);
    });
  }

  jumpToInspector(stepNumber: number, allStepNumbers?: number[]): void {
    if (!this.shopperService.inspectorExpanded()) {
      this.shopperService.inspectorExpanded.set(true);
    }
    const stepNums = allStepNumbers && allStepNumbers.length > 0 ? allStepNumbers : [stepNumber];
    this.highlightedStepNumbers = [...stepNums];

    setTimeout(() => {
      this.inspector?.scrollToStep(stepNumber, stepNums);
    }, 60);

    setTimeout(() => {
      this.highlightedStepNumbers = [];
    }, 3500);
  }

  onStepSelected(step: ProtocolStep): void {
    if (!step.related_message_id) return;
    const targetMsgId = step.related_message_id;
    this.highlightedMessageId = targetMsgId;

    setTimeout(() => {
      if (this.messagesContainer?.nativeElement) {
        const el = this.messagesContainer.nativeElement.querySelector('#chat-msg-' + targetMsgId) as HTMLElement;
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
    }, 60);

    setTimeout(() => {
      if (this.highlightedMessageId === targetMsgId) {
        this.highlightedMessageId = null;
      }
    }, 3500);
  }

  formatStepRange(stepNumbers: number[] | undefined): string {
    if (!stepNumbers || stepNumbers.length === 0) return '';
    if (stepNumbers.length === 1) return `Passo ${stepNumbers[0]}`;
    const min = Math.min(...stepNumbers);
    const max = Math.max(...stepNumbers);
    return min === max ? `Passo ${min}` : `Passi ${min}–${max}`;
  }

  readonly quickSuggestions = [
    {
      label: '🚆 Act I: Caffè e Focaccia in Carrozza 4 (Frecciarossa 9540)',
      query: 'Prendimi un caffè doppio e una focaccia ligure per la carrozza 4',
      mode: 'a2a' as const,
      presetId: 'scenario_departing_soon'
    },
    {
      label: '🧊 Act II: Snack sano & Caffè Specialty al Locker (20 min)',
      query: 'Ho 20 minuti di sosta: prendimi uno snack sano per il viaggio e un caffè specialty da ritirare al locker',
      mode: 'a2a' as const,
      presetId: 'scenario_fitness_specialty'
    },
    {
      label: '🌐 Demo 4: Snack allo Smart Locker con verifica RFC 9421',
      query: 'Preparami uno snack da ritirare subito allo Smart Locker con verifica RFC 9421',
      mode: 'ucp_rest' as const,
      presetId: 'scenario_transit_locker'
    }
  ];

  async sendPrompt(customText?: string, suggestion?: { mode?: 'a2a' | 'ucp_rest'; presetId?: string }): Promise<void> {
    const text = customText || this.inputText;
    if (!text.trim() || this.shopperService.isRunning()) return;

    if (suggestion) {
      if (suggestion.mode && suggestion.mode !== this.shopperService.protocolMode()) {
        this.shopperService.setProtocolMode(suggestion.mode);
      }
      if (suggestion.presetId) {
        const currentPresetId = this.shopperService.travelerContext()?.scenario_preset_id;
        if (currentPresetId !== suggestion.presetId) {
          const targetPreset = DEFAULT_SCENARIO_PRESETS.find(p => p.id === suggestion.presetId);
          if (targetPreset) {
            await this.shopperService.selectPreset(targetPreset);
          }
        }
      }
    }

    this.shopperService.runMission(text.trim());
    if (!customText) {
      this.inputText = '';
    }
  }

  setMode(mode: 'a2a' | 'ucp_rest'): void {
    this.shopperService.setProtocolMode(mode);
  }

  onPresetSelected(preset: ScenarioPreset): void {
    this.shopperService.selectPreset(preset);
  }

  onSaveContext(updated: TravelerContext): void {
    this.shopperService.saveContext(updated);
  }

  onConfirmProposal(event: { optionId: string; proposal: any }): void {
    this.shopperService.confirmProposalSelection(event.optionId, event.proposal);
  }

  copyPayload(step: ProtocolStep, index: number): void {
    const text = JSON.stringify(step.payload, null, 2);
    navigator.clipboard.writeText(text);
    this.copiedStepIndex = index;
    setTimeout(() => {
      this.copiedStepIndex = null;
    }, 2000);
  }

  formatCents(cents: number | undefined): string {
    if (cents === undefined || cents === null) return '0.00';
    return (cents / 100).toFixed(2);
  }

  resetSession(): void {
    if (this.shopperService.isRunning()) return;
    this.shopperService.clearSession();
    this.inputText = '';
    this.highlightedStepNumbers = [];
    this.highlightedMessageId = null;
  }
}
