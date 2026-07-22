import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { CartService, OrdersService } from '../../core/api';
import { CartStore } from '../../core/cart.store';
import { CentsPipe } from '../../shared/cents.pipe';

@Component({
  selector: 'app-checkout',
  standalone: true,
  imports: [CommonModule, RouterLink, CentsPipe],
  template: `
    <h1 class="mb-4 text-xl font-semibold text-gray-700">Checkout</h1>
    @if (items().length === 0) {
      <p class="text-gray-500">Carrinho vazio. <a routerLink="/" class="text-brand-blue">Voltar</a></p>
    } @else {
      <div class="grid gap-6 md:grid-cols-3">
        <div class="rounded-lg bg-white p-6 shadow md:col-span-2">
          <h2 class="mb-3 font-semibold text-gray-700">Resumo do pedido</h2>
          @for (it of items(); track it.id) {
            <div class="flex justify-between border-b py-2 text-sm">
              <span>{{ it.product.title }} × {{ it.quantity }}</span>
              <span>{{ it.line_total_cents | cents }}</span>
            </div>
          }
          <!-- Payment is a mock gateway in the MVP (approves after ~1s). -->
          <div class="mt-4 rounded bg-gray-50 p-3 text-sm text-gray-500">
            💳 Pagamento simulado (gateway mock). Nenhuma cobrança real é feita.
          </div>
        </div>
        <div class="rounded-lg bg-white p-6 shadow">
          <div class="flex justify-between text-lg">
            <span>Total</span>
            <span class="font-bold">{{ total() | cents }}</span>
          </div>
          <button
            (click)="pay()"
            [disabled]="paying()"
            class="mt-4 w-full rounded bg-brand-blue py-3 font-semibold text-white hover:opacity-90 disabled:opacity-50"
          >
            {{ paying() ? 'Processando pagamento…' : 'Pagar agora' }}
          </button>
          @if (error()) {
            <p class="mt-2 text-sm text-red-600">{{ error() }}</p>
          }
        </div>
      </div>
    }
  `,
})
export class CheckoutComponent {
  private orders = inject(OrdersService);
  private cartApi = inject(CartService);
  private store = inject(CartStore);
  private router = inject(Router);

  items = computed(() => this.store.cart()?.items ?? []);
  total = computed(() => this.store.cart()?.total_cents ?? 0);
  paying = signal(false);
  error = signal('');

  constructor() {
    this.store.refresh();
  }

  pay(): void {
    this.paying.set(true);
    this.error.set('');
    this.orders.createCheckoutApiCheckoutPost().subscribe({
      next: (order) => {
        this.store.clear();
        this.router.navigate(['/orders', order.id]);
      },
      error: (err) => {
        this.error.set(err?.error?.detail ?? 'Falha no checkout');
        this.paying.set(false);
      },
    });
  }
}
