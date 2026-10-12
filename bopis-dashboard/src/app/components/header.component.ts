import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../services/auth.service';
import { BopisService } from '../services/bopis.service';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule],
  template: `
    <header class="station-header">
      <div class="header-left">
        <div class="station-logo">
          <span>📦</span>
        </div>
        <div class="header-titles">
          <div class="station-badge">
            <span class="live-pulse"></span>
            <span>BISTROT MILANO CENTRALE (BINARIO 12) • KDS & DISPATCHER HUB • ULTIME 24H</span>
          </div>
          <h1 class="main-title">Dashboard Operativa Ordini & Consegne</h1>
        </div>
      </div>

      <div class="header-right">
        <!-- SYNC INDICATOR -->
        <div class="sync-status" [class.firestore-active]="bopisService.isConnectedToFirestore()">
          <span class="sync-dot">{{ bopisService.isConnectedToFirestore() ? '⚡' : '🔄' }}</span>
          <span>{{ bopisService.isConnectedToFirestore() ? 'Firestore Live Sync' : 'Live Polling (REST)' }}</span>
        </div>

        <button class="refresh-btn" (click)="bopisService.fetchOrdersRest()" title="Forza sincronizzazione">
          ↻ Sincronizza
        </button>

        <!-- USER PILL -->
        @if (authService.isAuthenticated()) {
          <div class="user-pill">
            @if (authService.userAvatar()) {
              <img [src]="authService.userAvatar()!" class="user-avatar" alt="Avatar" />
            } @else {
              <span class="user-placeholder">👤</span>
            }
            <span class="user-name">{{ authService.userDisplayName() }}</span>
            <button class="logout-btn" (click)="authService.logout()" title="Disconnetti account Google">
              Esci
            </button>
          </div>
        }
      </div>
    </header>
  `,
  styles: [`
    .station-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem 1.75rem;
      background: #1c1917;
      border-bottom: 1px solid #292524;
      position: sticky;
      top: 0;
      z-index: 50;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .station-logo {
      width: 44px;
      height: 44px;
      border-radius: 12px;
      background: linear-gradient(135deg, #f59e0b, #ea580c);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.5rem;
      box-shadow: 0 4px 12px rgba(234, 88, 12, 0.45);
    }

    .station-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 0.72rem;
      font-weight: 700;
      color: #fbbf24;
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.3);
      padding: 3px 10px;
      border-radius: 20px;
      letter-spacing: 0.06em;
      margin-bottom: 3px;
    }

    .live-pulse {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #22c55e;
      box-shadow: 0 0 8px #22c55e;
    }

    .main-title {
      margin: 0;
      font-size: 1.25rem;
      font-weight: 800;
      color: #fef3c7;
      letter-spacing: -0.01em;
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .sync-status {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.3);
      border-radius: 8px;
      font-size: 0.75rem;
      color: #fbbf24;
      font-weight: 600;
    }

    .sync-status.firestore-active {
      background: rgba(34, 197, 94, 0.15);
      border-color: rgba(34, 197, 94, 0.3);
      color: #4ade80;
    }

    .refresh-btn {
      background: #292524;
      color: #fbbf24;
      border: 1px solid #44403c;
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .refresh-btn:hover {
      background: #3d3835;
      border-color: #d97706;
      color: #fef3c7;
    }

    .user-pill {
      display: flex;
      align-items: center;
      gap: 8px;
      background: #292524;
      border: 1px solid #44403c;
      padding: 4px 10px 4px 4px;
      border-radius: 24px;
    }

    .user-avatar {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      object-fit: cover;
    }

    .user-placeholder {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: #334155;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.85rem;
    }

    .user-name {
      font-size: 0.8rem;
      font-weight: 600;
      color: #e2e8f0;
      max-width: 140px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .logout-btn {
      background: transparent;
      border: 1px solid #475569;
      border-radius: 6px;
      padding: 2px 8px;
      font-size: 0.72rem;
      font-weight: 600;
      color: #94a3b8;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .logout-btn:hover {
      background: #ef4444;
      border-color: #ef4444;
      color: #fff;
    }
  `]
})
export class HeaderComponent {
  readonly authService = inject(AuthService);
  readonly bopisService = inject(BopisService);
}
