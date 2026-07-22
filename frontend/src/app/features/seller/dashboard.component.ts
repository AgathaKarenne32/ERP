import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { RouterLink } from '@angular/router';
import {
  OrderOut,
  SellerDashboard,
  SellerService,
  ShippingService,
} from '../../core/api';
import { CentsPipe } from '../../shared/cents.pipe';

@Component({
  selector: 'app-seller-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, CentsPipe],
  template: `
    <div class="mb-4 flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-700">Painel do vendedor</h1>
      <div class="flex gap-2">
        <a routerLink="/seller/products" class="rounded border px-4 py-2 text-sm">Meus produtos</a>
        <a routerLink="/seller/products/new" class="rounded bg-brand-blue px-4 py-2 text-sm text-white">
          + Novo produto
        </a>
      </div>
    </div>

    @if (metrics(); as m) {
      <div class="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <div class="rounded-lg bg-white p-4 shadow">
          <p class="text-sm text-gray-500">Produtos ativos</p>
          <p class="text-2xl font-bold">{{ m.active_products }}</p>
        </div>
        <div class="rounded-lg bg-white p-4 shadow">
          <p class="text-sm text-gray-500">Pedidos recebidos</p>
          <p class="text-2xl font-bold">{{ m.total_orders }}</p>
        </div>
        <div class="rounded-lg bg-white p-4 shadow">
          <p class="text-sm text-gray-500">Faturamento</p>
          <p class="text-2xl font-bold">{{ m.revenue_cents | cents }}</p>
        </div>
        <div class="rounded-lg bg-white p-4 shadow">
          <p class="text-sm text-gray-500">Reputação</p>
          <p class="text-2xl font-bold">⭐ {{ m.reputation_score }}</p>
        </div>
      </div>
    }

    <h2 class="mb-3 font-semibold text-gray-700">Pedidos recebidos</h2>
    @if (orders().length === 0) {
      <p class="text-gray-500">Nenhum pedido ainda.</p>
    } @else {
      <div class="space-y-3">
        @for (o of orders(); track o.id) {
          <div class="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-white p-4 shadow">
            <div>
              <p class="text-sm text-gray-500">Pedido {{ o.id.slice(0, 8) }}…</p>
              <p class="font-medium">{{ o.total_cents | cents }} · {{ o.status }}</p>
            </div>
            @if (o.shipment; as s) {
              <div class="text-sm text-gray-600">
                Envio: <b>{{ s.status }}</b> · {{ s.tracking_code }}
              </div>
              @if (s.status !== 'DELIVERED') {
                <button
                  (click)="advance(s.id)"
                  class="rounded bg-brand-blue px-4 py-2 text-sm text-white hover:opacity-90"
                >
                  Avançar envio
                </button>
              } @else {
                <span class="rounded-full bg-green-100 px-3 py-1 text-sm text-green-700">Entregue</span>
              }
            }
          </div>
        }
      </div>
    }
  `,
})
export class SellerDashboardComponent {
  private seller = inject(SellerService);
  private shipping = inject(ShippingService);
  private snack = inject(MatSnackBar);

  metrics = signal<SellerDashboard | null>(null);
  orders = signal<OrderOut[]>([]);

  constructor() {
    this.load();
  }

  private load(): void {
    this.seller.dashboardApiSellerDashboardGet().subscribe((m) => this.metrics.set(m));
    this.seller
      .receivedOrdersApiSellerOrdersGet()
      .subscribe((res: { items: OrderOut[] }) => this.orders.set(res.items));
  }

  advance(shipmentId: string): void {
    this.shipping.advanceShipmentApiShipmentsShipmentIdAdvancePatch(shipmentId).subscribe({
      next: () => {
        this.snack.open('Envio avançado', 'OK', { duration: 1500 });
        this.load();
      },
      error: (err) => this.snack.open(err?.error?.detail ?? 'Erro', 'OK', { duration: 2000 }),
    });
  }
}
