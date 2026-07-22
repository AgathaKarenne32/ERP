import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ChatMessageOut, ChatService } from '../../core/api';
import { AuthService } from '../../core/auth.service';

/**
 * Floating AI customer-support widget. Visible to logged-in buyers; the backend
 * grounds every answer in real order data. Uses single-response (no streaming)
 * per the MVP scope.
 */
@Component({
  selector: 'app-chat-widget',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    @if (auth.isLoggedIn()) {
      <div class="fixed bottom-4 right-4 z-50">
        @if (open()) {
          <div class="flex h-[28rem] w-80 flex-col rounded-xl bg-white shadow-2xl">
            <div class="flex items-center justify-between rounded-t-xl bg-brand-blue px-4 py-3 text-white">
              <span class="font-semibold">Atendimento</span>
              <button (click)="open.set(false)" aria-label="Fechar">✕</button>
            </div>
            <div class="flex-1 space-y-2 overflow-y-auto p-3 text-sm">
              @for (m of messages(); track m.id) {
                <div [class]="m.role === 'USER' ? 'text-right' : 'text-left'">
                  <span
                    class="inline-block max-w-[85%] whitespace-pre-line rounded-lg px-3 py-2"
                    [class]="m.role === 'USER' ? 'bg-brand-light text-gray-800' : 'bg-gray-100 text-gray-800'"
                    >{{ m.content }}</span
                  >
                </div>
              }
              @if (loading()) {
                <div class="text-left text-gray-400">digitando…</div>
              }
            </div>
            <form (ngSubmit)="send()" class="flex gap-2 border-t p-2">
              <input
                [(ngModel)]="draft"
                name="draft"
                placeholder="Digite sua dúvida…"
                class="flex-1 rounded border px-3 py-2 text-sm focus:outline-none"
                autocomplete="off"
              />
              <button
                type="submit"
                [disabled]="loading() || !draft.trim()"
                class="rounded bg-brand-blue px-3 py-2 text-sm text-white disabled:opacity-50"
              >
                Enviar
              </button>
            </form>
          </div>
        } @else {
          <button
            (click)="openChat()"
            class="rounded-full bg-brand-blue px-5 py-3 font-semibold text-white shadow-lg hover:opacity-90"
          >
            💬 Ajuda
          </button>
        }
      </div>
    }
  `,
})
export class ChatWidgetComponent {
  auth = inject(AuthService);
  private api = inject(ChatService);

  open = signal(false);
  loading = signal(false);
  messages = signal<ChatMessageOut[]>([]);
  draft = '';

  openChat(): void {
    this.open.set(true);
    if (this.messages().length === 0) {
      this.api.historyApiChatHistoryGet().subscribe((h) => this.messages.set(h));
    }
  }

  send(): void {
    const text = this.draft.trim();
    if (!text || this.loading()) return;
    this.draft = '';
    this.loading.set(true);
    // Optimistically show the user's message.
    this.messages.update((m) => [
      ...m,
      { id: 'tmp-' + Date.now(), role: 'USER', content: text, order_id: null, created_at: '' },
    ]);
    this.api.chatApiChatPost({ message: text }).subscribe({
      next: (res) => {
        this.messages.update((m) => [...m, res.reply]);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}
