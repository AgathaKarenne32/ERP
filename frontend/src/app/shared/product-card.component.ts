import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ProductOut } from '../core/api';
import { CentsPipe } from './cents.pipe';

/** Marketplace-style product card used across home and search grids. */
@Component({
  selector: 'app-product-card',
  standalone: true,
  imports: [CommonModule, RouterLink, CentsPipe],
  template: `
    <a
      [routerLink]="['/product', product.id]"
      class="flex flex-col rounded-lg bg-white p-3 shadow transition hover:shadow-lg"
    >
      <img
        [src]="product.images?.[0] || placeholder"
        [alt]="product.title"
        class="mb-3 h-40 w-full rounded object-cover"
        loading="lazy"
      />
      <span class="line-clamp-2 text-sm text-gray-700">{{ product.title }}</span>
      <span class="mt-1 text-lg font-semibold text-gray-900">{{
        product.price_cents | cents: product.currency
      }}</span>
      @if (product.seller) {
        <span class="mt-1 text-xs text-gray-500"
          >{{ product.seller.store_name }} · ⭐ {{ product.seller.reputation_score }}</span
        >
      }
    </a>
  `,
})
export class ProductCardComponent {
  @Input({ required: true }) product!: ProductOut;
  placeholder = 'https://via.placeholder.com/300x200?text=Produto';
}
