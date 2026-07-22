import { CommonModule } from '@angular/common';
import { Component, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';
import { RouterLink } from '@angular/router';
import { OrderOut, OrdersService, ReviewsService } from '../../core/api';
import { CentsPipe } from '../../shared/cents.pipe';

@Component({
  selector: 'app-order-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, CentsPipe],
  template: `
    @if (order(); as o) {
      <a routerLink="/orders" class="text-sm text-brand-blue hover:underline">← Minhas compras</a>
      <h1 class="mb-4 mt-2 text-xl font-semibold text-gray-700">Pedido {{ o.id.slice(0, 8) }}…</h1>

      <div class="grid gap-6 md:grid-cols-3">
        <div class="rounded-lg bg-white p-6 shadow md:col-span-2">
          <h2 class="mb-3 font-semibold text-gray-700">Itens</h2>
          @for (it of o.items; track it.id) {
            <div class="flex justify-between border-b py-2">
              <span>{{ it.title_snapshot }} × {{ it.quantity }}</span>
              <span>{{ it.unit_price_cents * it.quantity | cents }}</span>
            </div>
          }
          <div class="flex justify-between pt-3 font-semibold">
            <span>Total</span><span>{{ o.total_cents | cents }}</span>
          </div>
        </div>

        <div class="rounded-lg bg-white p-6 shadow">
          <h2 class="mb-3 font-semibold text-gray-700">Status</h2>
          <p class="mb-1 text-sm">Pedido: <b>{{ o.status }}</b></p>
          <p class="mb-3 text-sm">Pagamento: <b>{{ o.payment_status }}</b></p>
          @if (o.shipment; as s) {
            <div class="rounded bg-gray-50 p-3 text-sm">
              <p>Rastreio: <b>{{ s.tracking_code }}</b></p>
              <p>Envio: {{ s.status }}</p>
              <a [routerLink]="['/track', s.tracking_code]" class="text-brand-blue hover:underline">
                Ver rastreamento
              </a>
            </div>
          }
        </div>
      </div>

      <!-- Review is only allowed once the order is DELIVERED. -->
      @if (o.status === 'DELIVERED') {
        <section class="mt-6 rounded-lg bg-white p-6 shadow">
          <h2 class="mb-3 font-semibold text-gray-700">Avaliar produto</h2>
          @if (reviewDone()) {
            <p class="text-green-600">Obrigado pela sua avaliação!</p>
          } @else {
            <label class="mb-1 block text-sm text-gray-500">Produto</label>
            <select [(ngModel)]="selectedProduct" class="mb-3 w-full rounded border px-2 py-2">
              @for (it of o.items; track it.id) {
                <option [value]="it.product_id">{{ it.title_snapshot }}</option>
              }
            </select>
            <label class="mb-1 block text-sm text-gray-500">Nota</label>
            <select [(ngModel)]="rating" class="mb-3 w-full rounded border px-2 py-2">
              @for (n of [5, 4, 3, 2, 1]; track n) {
                <option [value]="n">{{ n }} estrela(s)</option>
              }
            </select>
            <textarea
              [(ngModel)]="comment"
              rows="3"
              placeholder="Conte como foi sua experiência…"
              class="mb-3 w-full rounded border px-3 py-2"
            ></textarea>
            <button
              (click)="submitReview()"
              [disabled]="submitting()"
              class="rounded bg-brand-blue px-5 py-2 font-semibold text-white disabled:opacity-50"
            >
              Enviar avaliação
            </button>
          }
        </section>
      }
    } @else {
      <p class="text-gray-500">Carregando…</p>
    }
  `,
})
export class OrderDetailComponent {
  id = input.required<string>();

  private orders = inject(OrdersService);
  private reviews = inject(ReviewsService);
  private snack = inject(MatSnackBar);

  order = signal<OrderOut | null>(null);
  selectedProduct = '';
  rating = 5;
  comment = '';
  submitting = signal(false);
  reviewDone = signal(false);

  constructor() {
    queueMicrotask(() => {
      this.orders.getOrderApiOrdersOrderIdGet(this.id()).subscribe((o) => {
        this.order.set(o);
        this.selectedProduct = o.items[0]?.product_id ?? '';
      });
    });
  }

  submitReview(): void {
    if (!this.selectedProduct) return;
    this.submitting.set(true);
    this.reviews
      .createReviewApiProductsProductIdReviewsPost(this.selectedProduct, {
        rating: Number(this.rating),
        comment: this.comment,
      })
      .subscribe({
        next: () => {
          this.reviewDone.set(true);
          this.submitting.set(false);
          this.snack.open('Avaliação enviada!', 'OK', { duration: 2000 });
        },
        error: (err) => {
          this.submitting.set(false);
          this.snack.open(err?.error?.detail ?? 'Erro ao avaliar', 'OK', { duration: 3000 });
        },
      });
  }
}
