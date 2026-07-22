import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { ProductOut, ProductsService } from '../../core/api';
import { ProductCardComponent } from '../../shared/product-card.component';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, ProductCardComponent],
  template: `
    <section class="mb-6 rounded-lg bg-brand-blue px-6 py-8 text-white">
      <h1 class="text-2xl font-bold">Bem-vindo ao MercadoMVP</h1>
      <p class="mt-1 text-brand-light">Os melhores produtos com entrega rastreada.</p>
    </section>

    <h2 class="mb-4 text-lg font-semibold text-gray-700">Destaques</h2>
    @if (loading()) {
      <p class="text-gray-500">Carregando…</p>
    } @else {
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        @for (p of products(); track p.id) {
          <app-product-card [product]="p" />
        }
      </div>
    }
  `,
})
export class HomeComponent {
  private api = inject(ProductsService);
  products = signal<ProductOut[]>([]);
  loading = signal(true);

  constructor() {
    this.api.listProductsApiProductsGet(undefined, undefined, undefined, undefined, 10).subscribe({
      next: (res) => {
        this.products.set(res.items);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}
