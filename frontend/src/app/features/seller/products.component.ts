import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ProductOut, ProductsService, SellerService } from '../../core/api';
import { CentsPipe } from '../../shared/cents.pipe';

@Component({
  selector: 'app-seller-products',
  standalone: true,
  imports: [CommonModule, RouterLink, CentsPipe],
  template: `
    <div class="mb-4 flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-700">Meus produtos</h1>
      <a routerLink="/seller/products/new" class="rounded bg-brand-blue px-4 py-2 text-sm text-white">
        + Novo produto
      </a>
    </div>

    @if (products().length === 0) {
      <p class="text-gray-500">Você ainda não cadastrou produtos.</p>
    } @else {
      <div class="overflow-hidden rounded-lg bg-white shadow">
        @for (p of products(); track p.id) {
          <div class="flex items-center gap-4 border-b p-4">
            <img [src]="p.images?.[0] || placeholder" class="h-12 w-12 rounded object-cover" />
            <span class="flex-1">{{ p.title }}</span>
            <span class="text-gray-600">{{ p.price_cents | cents }}</span>
            <span class="text-sm text-gray-500">Estoque: {{ p.stock }}</span>
            <span
              class="rounded-full px-3 py-1 text-xs"
              [class]="p.status === 'ACTIVE' ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-600'"
              >{{ p.status }}</span
            >
            <button (click)="toggle(p)" class="text-sm text-brand-blue hover:underline">
              {{ p.status === 'ACTIVE' ? 'Pausar' : 'Ativar' }}
            </button>
          </div>
        }
      </div>
    }
  `,
})
export class SellerProductsComponent {
  private seller = inject(SellerService);
  private products_ = inject(ProductsService);
  products = signal<ProductOut[]>([]);
  placeholder = 'https://via.placeholder.com/80?text=P';

  constructor() {
    this.load();
  }

  private load(): void {
    this.seller.myProductsApiSellerProductsGet().subscribe((p) => this.products.set(p));
  }

  toggle(p: ProductOut): void {
    const status = p.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE';
    this.products_.updateProductApiProductsProductIdPatch(p.id, { status }).subscribe(() =>
      this.load(),
    );
  }
}
