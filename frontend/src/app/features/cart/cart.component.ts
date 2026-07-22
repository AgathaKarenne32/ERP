import { CommonModule } from '@angular/common';
import { Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CartService } from '../../core/api';
import { CartStore } from '../../core/cart.store';
import { CentsPipe } from '../../shared/cents.pipe';

@Component({
  selector: 'app-cart',
  standalone: true,
  imports: [CommonModule, RouterLink, CentsPipe],
  template: `
    <h1 class="mb-4 text-xl font-semibold text-gray-700">Meu carrinho</h1>
    @if (items().length === 0) {
      <div class="rounded-lg bg-white p-8 text-center shadow">
        <p class="text-gray-500">Seu carrinho está vazio.</p>
        <a routerLink="/" class="mt-3 inline-block text-brand-blue hover:underline">Ver produtos</a>
      </div>
    } @else {
      <div class="rounded-lg bg-white shadow">
        @for (it of items(); track it.id) {
          <div class="flex items-center gap-4 border-b p-4">
            <img [src]="it.product.images?.[0] || placeholder" class="h-16 w-16 rounded object-cover" />
            <div class="flex-1">
              <p class="text-gray-800">{{ it.product.title }}</p>
              <p class="text-sm text-gray-500">{{ it.product.price_cents | cents }}</p>
            </div>
            <div class="flex items-center gap-2">
              <button (click)="setQty(it.id, it.quantity - 1)" [disabled]="it.quantity <= 1"
                class="h-8 w-8 rounded border disabled:opacity-40">−</button>
              <span class="w-6 text-center">{{ it.quantity }}</span>
              <button (click)="setQty(it.id, it.quantity + 1)" class="h-8 w-8 rounded border">+</button>
            </div>
            <p class="w-24 text-right font-semibold">{{ it.line_total_cents | cents }}</p>
            <button (click)="remove(it.id)" class="text-red-500 hover:underline">Remover</button>
          </div>
        }
        <div class="flex items-center justify-between p-4">
          <span class="text-lg">Total</span>
          <span class="text-xl font-bold">{{ total() | cents }}</span>
        </div>
      </div>
      <div class="mt-4 text-right">
        <a routerLink="/checkout" class="rounded bg-brand-blue px-6 py-3 font-semibold text-white hover:opacity-90">
          Finalizar compra
        </a>
      </div>
    }
  `,
})
export class CartComponent {
  private api = inject(CartService);
  store = inject(CartStore);
  placeholder = 'https://via.placeholder.com/100?text=P';

  items = computed(() => this.store.cart()?.items ?? []);
  total = computed(() => this.store.cart()?.total_cents ?? 0);

  constructor() {
    this.store.refresh();
  }

  setQty(id: string, qty: number): void {
    if (qty < 1) return;
    this.api.updateItemApiCartItemsItemIdPatch(id, { quantity: qty }).subscribe((c) => this.store.set(c));
  }

  remove(id: string): void {
    this.api.removeItemApiCartItemsItemIdDelete(id).subscribe((c) => this.store.set(c));
  }
}
