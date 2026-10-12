import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../services/auth.service';
import { ChatService } from '../services/chat.service';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule],
  template: `
    <header class="app-header">
      <div class="header-left">
        <div class="logo-circle">
          <span>☕</span>
        </div>
        <div class="title-group">
          <h2>Bistrot Milano Centrale (Binario 12)</h2>
          <span class="sub-title">AI Concierge Chat · Direct A2A (Demo 1) · DevFest Milano 2026</span>
        </div>
      </div>

      <!-- HEADER RIGHT CONTROLS -->
      <div class="header-right">
        @if (authService.isAuthenticated()) {
          <button
            type="button"
            class="inspector-toggle-btn"
            [class.active]="chatService.inspectorExpanded()"
            (click)="chatService.toggleInspector()"
            title="Mostra / Nascondi il pannello del Protocol Inspector (Demo 1)">
            <span class="icon">🔍</span>
            <span class="text">{{ chatService.inspectorExpanded() ? 'Nascondi Inspector' : 'Mostra Inspector' }}</span>
          </button>

          <a
            href="http://localhost:4201"
            target="_blank"
            class="bopis-link-btn"
            title="Apri la Dashboard Operativa della Stazione su un monitor separato (porta 4201)">
            🏪 Dashboard BOPIS (4201) ↗️
          </a>

          <div class="user-pill">
            @if (authService.userAvatar()) {
              <img [src]="authService.userAvatar()!" class="user-avatar" alt="Avatar" />
            } @else {
              <span class="user-avatar-placeholder">👤</span>
            }
            <span class="user-name">{{ authService.userDisplayName() }}</span>
            <button class="logout-btn" (click)="authService.logout()" title="Disconnetti account Google">
              Esci
            </button>
          </div>
        } @else {
          <button class="login-google-btn" (click)="authService.loginWithGoogle()">
            <svg class="google-icon" viewBox="0 0 24 24" width="16" height="16">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
            </svg>
            Accedi con Google
          </button>
        }
      </div>
    </header>
  `,
  styles: [`
    .app-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 20px;
      background: #1c1917;
      border-bottom: 1px solid #292524;
      box-shadow: 0 2px 10px rgba(0,0,0,0.18);
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .logo-circle {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: linear-gradient(135deg, #d97706, #b45309);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.3rem;
      color: #ffffff;
      box-shadow: 0 2px 8px rgba(217, 119, 6, 0.4);
    }

    .title-group h2 {
      margin: 0;
      font-size: 1.15rem;
      font-weight: 700;
      color: #fef3c7;
      letter-spacing: -0.01em;
    }

    .sub-title {
      font-size: 0.76rem;
      color: #f59e0b;
      font-weight: 600;
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .bopis-link-btn {
      background: #292524;
      border: 1px solid #44403c;
      color: #fbbf24;
      font-size: 0.78rem;
      font-weight: 700;
      padding: 6px 12px;
      border-radius: 8px;
      text-decoration: none;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .bopis-link-btn:hover {
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

    .user-avatar-placeholder {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: #e2e8f0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.9rem;
    }

    .user-name {
      font-size: 0.8rem;
      font-weight: 600;
      color: #f5f5f4;
      max-width: 140px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .logout-btn {
      background: transparent;
      border: 1px solid #57534e;
      border-radius: 6px;
      padding: 3px 8px;
      font-size: 0.72rem;
      font-weight: 600;
      color: #a8a29e;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .logout-btn:hover {
      background: #7f1d1d;
      border-color: #991b1b;
      color: #fecaca;
    }

    .login-google-btn {
      display: flex;
      align-items: center;
      gap: 8px;
      background: #ffffff;
      border: 1px solid #dadce0;
      color: #3c4043;
      font-size: 0.82rem;
      font-weight: 600;
      padding: 8px 14px;
      border-radius: 8px;
      cursor: pointer;
      box-shadow: 0 1px 2px rgba(60,64,67,0.15);
      transition: all 0.2s ease;
    }

    .login-google-btn:hover {
      background: #f8f9fa;
      border-color: #c6c9cc;
      box-shadow: 0 1px 3px rgba(60,64,67,0.25);
    }

    .inspector-toggle-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #292524;
      color: #d6d3d1;
      border: 1px solid #44403c;
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 0.75rem;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .inspector-toggle-btn:hover {
      background: #3d3835;
      color: #ffffff;
      border-color: #d97706;
    }

    .inspector-toggle-btn.active {
      background: rgba(217, 119, 6, 0.25);
      color: #fef3c7;
      border-color: #d97706;
    }

    @media (max-width: 640px) {
      .sub-title { display: none; }
    }
  `]
})
export class HeaderComponent {
  readonly authService = inject(AuthService);
  readonly chatService = inject(ChatService);
}
