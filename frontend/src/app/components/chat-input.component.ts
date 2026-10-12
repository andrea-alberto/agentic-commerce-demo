import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService } from '../services/chat.service';

@Component({
  selector: 'app-chat-input',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="input-container">
      <!-- Quick Suggestion Chips -->
      <div class="chips-container">
        @for (chip of suggestionChips; track chip.text) {
          <button
            class="chip"
            (click)="onChipClick(chip.prompt)"
            [disabled]="chatService.isLoading()"
          >
            {{ chip.text }}
          </button>
        }
      </div>

      <!-- Input Form -->
      <form class="input-form" (ngSubmit)="onSubmit()">
        <input
          type="text"
          [(ngModel)]="userInput"
          name="userInput"
          placeholder="Scrivi al Concierge del Bistrot (Binario 12)..."
          class="text-input"
          [disabled]="chatService.isLoading()"
        />
        <button
          type="submit"
          class="send-btn"
          [disabled]="chatService.isLoading() || !userInput.trim()"
        >
          Invia ↵
        </button>
      </form>
    </div>
  `,
  styles: [`
    .input-container {
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 12px 16px;
      background: #ffffff;
      border-top: 1px solid #e7e5e4;
    }
    .chips-container {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding-bottom: 4px;
    }
    .chip {
      background: #fffbeb;
      border: 1px solid #fde68a;
      border-radius: 9999px;
      padding: 6px 12px;
      font-size: 0.78rem;
      font-weight: 600;
      color: #92400e;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s ease;
    }
    .chip:hover:not(:disabled) {
      background: #fef3c7;
      color: #78350f;
      border-color: #fcd34d;
    }
    .chip:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .input-form {
      display: flex;
      gap: 8px;
    }
    .text-input {
      flex: 1;
      padding: 10px 14px;
      border: 1px solid #d6d3d1;
      border-radius: 10px;
      font-size: 0.9rem;
      outline: none;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    .text-input:focus {
      border-color: #d97706;
      box-shadow: 0 0 0 3px rgba(217, 119, 6, 0.18);
    }
    .send-btn {
      background: linear-gradient(135deg, #d97706, #b45309);
      color: #ffffff;
      border: none;
      border-radius: 10px;
      padding: 0 18px;
      font-size: 0.88rem;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 2px 6px rgba(180, 83, 9, 0.3);
      transition: all 0.15s ease;
    }
    .send-btn:hover:not(:disabled) {
      background: linear-gradient(135deg, #b45309, #92400e);
    }
    .send-btn:disabled {
      background: #e7e5e4;
      color: #a8a29e;
      box-shadow: none;
      cursor: not-allowed;
    }
  `]
})
export class ChatInputComponent {
  chatService = inject(ChatService);
  userInput = '';

  suggestionChips = [
    {
      text: '⚡ Demo 1: Espresso doppio e brioche al banco',
      prompt: 'Vorrei un espresso doppio caldo e una brioche al pistacchio da ritirare al banco prima della partenza',
    },
    {
      text: '⚠️ Test Regola Termica: Espresso caldo allo Smart Locker',
      prompt: 'Vorrei un espresso doppio caldo e una brioche al pistacchio da ritirare allo Smart Locker',
    },
    {
      text: '🛍️ Espresso, brioche e caricatore 65W (15 min)',
      prompt: 'Sto arrivando a Milano Centrale tra 15 minuti: ordinami un espresso doppio, una brioche al pistacchio da asporto e un caricatore USB-C 65W pronto per il ritiro immediato senza fare la fila.',
    },
    {
      text: '🚄 Frecciarossa 9540: Consegna a bordo (Carrozza 4)',
      prompt: 'Il mio treno Frecciarossa 9540 (Carrozza 4, Posto 12D) sosterà al Binario 14 tra 40 minuti. Vorrei un panino con crudo e un\'acqua con consegna diretta al mio posto.',
    },
    {
      text: '📦 Smart Locker: Panino freddo e bibita (Interrato)',
      prompt: 'Vorrei un panino con crudo e bufala freddo, un\'acqua minerale e un powerbank da ritirare allo Smart Locker del piano interrato tra 35 minuti.',
    },
  ];

  onSubmit(): void {
    const text = this.userInput.trim();
    if (!text) return;
    this.chatService.sendMessage(text);
    this.userInput = '';
  }

  onChipClick(prompt: string): void {
    this.chatService.sendMessage(prompt);
  }
}
