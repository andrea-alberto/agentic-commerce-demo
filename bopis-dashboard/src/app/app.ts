import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HeaderComponent } from './components/header.component';
import { AuthService } from './services/auth.service';
import { BopisService, BopisOrder, BopisOrderStatus } from './services/bopis.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, HeaderComponent],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  readonly authService = inject(AuthService);
  readonly bopisService = inject(BopisService);

  getOrdersByStatus(status: BopisOrderStatus): BopisOrder[] {
    return this.bopisService.filteredOrders().filter(o => o.status === status);
  }

  getChannelClass(channel: string): string {
    switch (channel) {
      case 'ucp_direct_a2a': return 'demo1';
      case 'web_mcp': return 'demo2';
      case 'two_agent_a2a': return 'demo3';
      case 'ucp_rest': return 'demo4';
      default: return 'demo1';
    }
  }

  formatPlacedAt(order: BopisOrder): string {
    if (order.placed_at_display) return order.placed_at_display;
    if (order.created_at) {
      try {
        const d = new Date(order.created_at);
        return d.toLocaleDateString('it-IT') + ' ' + d.toLocaleTimeString('it-IT');
      } catch {
        return order.created_at;
      }
    }
    return 'N/D';
  }

  formatRequestedDelivery(order: BopisOrder): string {
    const raw = order.requested_delivery_display || '';
    const details = order.fulfillment_details;

    // 1. Data di riferimento (priorità: data presente in raw string, altrimenti created_at, altrimenti oggi)
    let dateStr = '';
    const dateMatch = raw.match(/\b\d{2}\/\d{2}\/\d{4}\b/);
    if (dateMatch) {
      dateStr = dateMatch[0];
    } else if (order.created_at) {
      try {
        dateStr = new Date(order.created_at).toLocaleDateString('it-IT');
      } catch {
        dateStr = new Date().toLocaleDateString('it-IT');
      }
    } else {
      dateStr = new Date().toLocaleDateString('it-IT');
    }

    // 2. Estrazione orario (HH:mm oppure intervallo HH:mm - HH:mm)
    let timeStr = '';

    // Se nella stringa raw è già presente un orario valido, estraiamolo (escludendo note testuali aggiunte tra parentesi)
    const timeMatch = raw.match(/\b\d{1,2}:\d{2}(?:\s*[\-–]\s*\d{1,2}:\d{2})?\b/);
    if (timeMatch) {
      timeStr = timeMatch[0];
    }

    // Se non trovato nella stringa, cerchiamo nei dettagli di fulfillment
    if (!timeStr && details) {
      if (details.service_time && /\b\d{1,2}:\d{2}\b/.test(details.service_time)) {
        timeStr = details.service_time;
      } else if (details.delivery_time && /\b\d{1,2}:\d{2}\b/.test(details.delivery_time)) {
        timeStr = details.delivery_time;
      } else if (details.slot_start && /\b\d{1,2}:\d{2}\b/.test(details.slot_start)) {
        timeStr = details.slot_end ? `${details.slot_start} – ${details.slot_end}` : details.slot_start;
      } else if (details.window && /\b\d{1,2}:\d{2}\b/.test(details.window)) {
        timeStr = details.window;
      }
    }

    // Se ancora non trovato, calcoliamo l'orario a partire da created_at + lead_time_minutes (default 5 min)
    if (!timeStr) {
      try {
        const base = order.created_at ? new Date(order.created_at) : new Date();
        const leadMins = order.lead_time_minutes ?? 5;
        const target = new Date(base.getTime() + leadMins * 60 * 1000);
        timeStr = target.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
      } catch {
        timeStr = 'In orario';
      }
    }

    return `${dateStr} ${timeStr}`.trim();
  }
}
