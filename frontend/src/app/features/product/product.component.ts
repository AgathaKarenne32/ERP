import { CommonModule } from '@angular/common';
import { Component, inject, input, signal } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router } from '@angular/router';
import {
  ProductOut,
  ProductsService,
  ReviewOut,
  ReviewsService,
} from '../../core/api';
import { AuthService } from '../../core/auth.service';
import { CartStore } from '../../core/cart.store';
import { CartService } from '../../core/api';
import { CentsPipe } from '../../shared/cents.pipe';

@Component({
  selector: 'app-product',
  standalone: true,
  imports: [CommonModule, CentsPipe],
  template: `
    @if (product(); as p) {
      <div class="grid gap-6 rounded-lg bg-white p-6 shadow md:grid-cols-2">
        <img
          [src]="p.images?.[0] || placeholder"
          [alt]="p.title"
          class="h-80 w-full rounded object-cover"
        />
        <div>
          <h1 class="text-2xl font-semibold text-gray-800">{{ p.title }}</h1>
          @if (p.seller) {
            <p class="mt-1 text-sm text-gray-500">
              {{ p.seller.store_name }} · ⭐ {{ p.seller.reputation_score }} ·
              {{ p.seller.sales_count }} vendas
            </p>
          }
          <p class="mt-4 text-3xl font-bold text-gray-900">
            {{ p.price_cents | cents: p.currency }}
          </p>
          <p class="mt-1 text-sm" [class]="p.stock > 0 ? 'text-green-600' : 'text-red-600'">
            {{ p.stock > 0 ? p.stock + ' em estoque' : 'Sem estoque' }}
          </p>
          <p class="mt-4 whitespace-pre-line text-gray-700">{{ p.description }}</p>
          <button
            (click)="addToCart(p)"
            [disabled]="p.stock === 0 || adding()"
            class="mt-6 rounded bg-brand-blue px-6 py-3 font-semibold text-white hover:opacity-90 disabled:opacity-50"
          >
            Adicionar ao carrinho
          </button>
        </div>
      </div>

      <section class="mt-6 rounded-lg bg-white p-6 shadow">
        <h2 class="mb-4 text-lg font-semibold text-gray-700">Avaliações</h2>
        @if (reviews().length === 0) {
          <p class="text-gray-500">Ainda não há avaliações.</p>
        } @else {
          <ul class="space-y-3">
            @for (r of reviews(); track r.id) {
              <li class="border-b pb-2">
                <span class="text-brand-blue">{{ stars(r.rating) }}</span>
                <p class="text-gray-700">{{ r.comment }}</p>
              </li>
            }
          </ul>
        }
      </section>
    } @else {
      <p class="text-gray-500">Carregando…</p>
    }
  `,
})
export class ProductComponent {
  // Route param bound via withComponentInputBinding().
  id = input.required<string>();

  private products = inject(ProductsService);
  private reviewsApi = inject(ReviewsService);
  private cartApi = inject(CartService);
  private cartStore = inject(CartStore);
  private auth = inject(AuthService);
  private router = inject(Router);
  private snack = inject(MatSnackBar);

  product = signal<ProductOut | null>(null);
  reviews = signal<ReviewOut[]>([]);
  adding = signal(false);
  placeholder = 'https://via.placeholder.com/600x400?text=Produto';

  constructor() {
    // input() is available synchronously here in the constructor's microtask.
    queueMicrotask(() => {
      const pid = this.id();
      this.products.getProductApiProductsProductIdGet(pid).subscribe((p) => this.product.set(p));
      this.reviewsApi
        .listReviewsApiProductsProductIdReviewsGet(pid)
        .subscribe((r) => this.reviews.set(r));
    });
  }

  stars(n: number): string {
    return '★'.repeat(n) + '☆'.repeat(5 - n);
  }

  addToCart(p: ProductOut): void {
    if (!this.auth.isLoggedIn()) {
      this.router.navigate(['/login'], { queryParams: { redirect: '/product/' + p.id } });
      return;
    }
    this.adding.set(true);
    this.cartApi.addItemApiCartItemsPost({ product_id: p.id, quantity: 1 }).subscribe({
      next: (cart) => {
        this.cartStore.set(cart);
        this.adding.set(false);
        this.snack.open('Adicionado ao carrinho', 'OK', { duration: 2000 });
      },
      error: () => {
        this.adding.set(false);
        this.snack.open('Erro ao adicionar', 'OK', { duration: 2000 });
      },
    });
  }
}
