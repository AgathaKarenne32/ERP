import { CommonModule } from '@angular/common';
import { Component, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, RouterOutlet } from '@angular/router';
import { AuthService } from './core/auth.service';
import { CartStore } from './core/cart.store';
import { ChatWidgetComponent } from './features/chat/chat-widget.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterOutlet, RouterLink, ChatWidgetComponent],
  template: `
    <header class="bg-brand-yellow shadow">
      <div class="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
        <a routerLink="/" class="text-xl font-bold text-brand-blue">🛒 MercadoMVP</a>
        <form (ngSubmit)="search()" class="flex flex-1">
          <input
            [(ngModel)]="query"
            name="q"
            placeholder="Buscar produtos, marcas e muito mais…"
            class="w-full rounded-l bg-white px-4 py-2 focus:outline-none"
            autocomplete="off"
          />
          <button type="submit" class="rounded-r bg-white px-4 text-gray-500">🔍</button>
        </form>
        <nav class="flex items-center gap-4 text-sm text-brand-blue">
          @if (auth.isSeller()) {
            <a routerLink="/seller" class="hover:underline">Vender</a>
          }
          <a routerLink="/cart" class="relative hover:underline">
            Carrinho
            @if (cart.count() > 0) {
              <span
                class="absolute -right-4 -top-2 rounded-full bg-brand-blue px-1.5 text-xs text-white"
                >{{ cart.count() }}</span
              >
            }
          </a>
          @if (auth.isLoggedIn()) {
            <a routerLink="/orders" class="hover:underline">Compras</a>
            <button (click)="logout()" class="hover:underline">Sair</button>
          } @else {
            <a routerLink="/login" class="hover:underline">Entrar</a>
            <a routerLink="/register" class="hover:underline">Criar conta</a>
          }
        </nav>
      </div>
    </header>

    <main class="mx-auto max-w-6xl px-4 py-6">
      <router-outlet />
    </main>

    <app-chat-widget />
  `,
})
export class AppComponent {
  auth = inject(AuthService);
  cart = inject(CartStore);
  private router = inject(Router);
  query = '';

  constructor() {
    // When a token is present (fresh load or after login), hydrate user + cart.
    effect(() => {
      if (this.auth.isLoggedIn() && !this.auth.user()) {
        this.auth.loadMe().subscribe({ error: () => this.auth.logout() });
        this.cart.refresh();
      }
    });
  }

  search(): void {
    this.router.navigate(['/search'], { queryParams: { q: this.query } });
  }

  logout(): void {
    this.auth.logout();
    this.cart.clear();
    this.router.navigate(['/']);
  }
}
