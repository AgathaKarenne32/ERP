import { Injectable, computed, inject, signal } from '@angular/core';
import { CartOut, CartService } from './api';

/**
 * Thin signal wrapper over the generated CartService so the header badge and
 * cart page share one reactive source of truth for the current cart.
 */
@Injectable({ providedIn: 'root' })
export class CartStore {
  private api = inject(CartService);

  readonly cart = signal<CartOut | null>(null);
  readonly count = computed(() =>
    (this.cart()?.items ?? []).reduce((n, i) => n + i.quantity, 0),
  );

  refresh(): void {
    this.api.getCartApiCartGet().subscribe({
      next: (c) => this.cart.set(c),
      error: () => this.cart.set(null),
    });
  }

  set(cart: CartOut): void {
    this.cart.set(cart);
  }

  clear(): void {
    this.cart.set(null);
  }
}
