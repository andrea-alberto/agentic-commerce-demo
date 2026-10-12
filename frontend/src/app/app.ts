import {
  Component,
  ElementRef,
  ViewChild,
  effect,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ProtocolInspectorComponent } from '@ucp/shared-frontend';
import { HeaderComponent } from './components/header.component';
import { ChatMessageComponent } from './components/chat-message.component';
import { ChatInputComponent } from './components/chat-input.component';
import { ChatService } from './services/chat.service';
import { AuthService } from './services/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    HeaderComponent,
    ChatMessageComponent,
    ChatInputComponent,
    ProtocolInspectorComponent,
  ],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  readonly chatService = inject(ChatService);
  readonly authService = inject(AuthService);

  @ViewChild('messagesContainer') messagesContainer?: ElementRef<HTMLDivElement>;
  @ViewChild(ProtocolInspectorComponent) inspector?: ProtocolInspectorComponent;

  constructor() {
    effect(() => {
      this.chatService.messages();
      setTimeout(() => {
        if (this.messagesContainer?.nativeElement) {
          this.messagesContainer.nativeElement.scrollTop =
            this.messagesContainer.nativeElement.scrollHeight;
        }
      }, 50);
    });

    effect(() => {
      const stepNums = this.chatService.highlightedStepNumbers();
      if (stepNums.length > 0) {
        setTimeout(() => {
          if (this.inspector) {
            this.inspector.scrollToStep(stepNums[0], stepNums);
          }
        }, 100);
      }
    });
  }

  onStepSelected(step: any): void {
    if (!step.related_message_id) return;
    this.chatService.jumpToMessage(step.related_message_id);
    setTimeout(() => {
      if (this.messagesContainer?.nativeElement) {
        const el = this.messagesContainer.nativeElement.querySelector('#chat-msg-' + step.related_message_id) as HTMLElement;
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
    }, 100);
  }
}
