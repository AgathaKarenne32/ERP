import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ProductOut, ProductsService } from '../../core/api';
import { ProductCardComponent } from '../../shared/product-card.component';

@Component({
  selector: 'app-search',
  standalone: true,
  imports: [CommonModule, FormsModule, ProductCardComponent],
  template: `
    <div class="flex gap-6">
      <!-- Filters -->
      <aside class="w-56 shrink-0 rounded-lg bg-white p-4 shadow">
        <h3 class="mb-3 font-semibold text-gray-700">Filtros</h3>
        <label class="mb-1 block text-xs text-gray-500">Categoria</label>
        <select [(ngModel)]="category" class="mb-3 w-full rounded border px-2 py-1">
          <option value="">Todas</option>
          <option value="eletronicos">Eletrônicos</option>
          <option value="casa">Casa</option>
          <option value="moda">Moda</option>
        </select>
        <label class="mb-1 block text-xs text-gray-500">Preço (R$)</label>
        <div class="mb-3 flex gap-2">
          <input [(ngModel)]="minPrice" type="number" placeholder="mín" class="w-full rounded border px-2 py-1" />
          <input [(ngModel)]="maxPrice" type="number" placeholder="máx" class="w-full rounded border px-2 py-1" />
        </div>
        <button (click)="apply()" class="w-full rounded bg-brand-blue py-2 text-sm text-white">
          Aplicar
        </button>
      </aside>

      <!-- Results -->
      <div class="flex-1">
        <p class="mb-3 text-sm text-gray-500">
          {{ total() }} resultado(s) @if (query()) { para “{{ query() }}” }
        </p>
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          @for (p of products(); track p.id) {
            <app-product-card [product]="p" />
          }
        </div>
        @if (!loading() && products().length === 0) {
          <p class="mt-8 text-center text-gray-500">Nenhum produto encontrado.</p>
        }

        @if (total() > pageSize) {
          <div class="mt-6 flex justify-center gap-2">
            <button (click)="prev()" [disabled]="offset === 0" class="rounded border px-3 py-1 disabled:opacity-40">
              Anterior
            </button>
            <button (click)="next()" [disabled]="offset + pageSize >= total()" class="rounded border px-3 py-1 disabled:opacity-40">
              Próxima
            </button>
          </div>
        }
      </div>
    </div>
  `,
})
export class SearchComponent {
  private api = inject(ProductsService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  products = signal<ProductOut[]>([]);
  total = signal(0);
  query = signal('');
  loading = signal(false);

  category = '';
  minPrice: number | null = null;
  maxPrice: number | null = null;
  offset = 0;
  pageSize = 12;

  constructor() {
    this.route.queryParams.subscribe((p) => {
      this.query.set(p['q'] ?? '');
      this.offset = 0;
      this.load();
    });
  }

  private load(): void {
    this.loading.set(true);
    this.api
      .listProductsApiProductsGet(
        this.query() || undefined,
        this.category || undefined,
        this.minPrice != null ? this.minPrice * 100 : undefined,
        this.maxPrice != null ? this.maxPrice * 100 : undefined,
        this.pageSize,
        this.offset,
      )
      .subscribe({
        next: (res) => {
          this.products.set(res.items);
          this.total.set(res.total);
          this.loading.set(false);
        },
        error: () => this.loading.set(false),
      });
  }

  apply(): void {
    this.offset = 0;
    this.load();
  }

  next(): void {
    this.offset += this.pageSize;
    this.load();
  }

  prev(): void {
    this.offset = Math.max(0, this.offset - this.pageSize);
    this.load();
  }
}
