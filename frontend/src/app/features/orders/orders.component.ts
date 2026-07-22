import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { OrderOut, OrdersService } from '../../core/api';
import { CentsPipe } from '../../shared/cents.pipe';

const STATUS_LABELS: Record<string, string> = {
  PENDING: 'Pendente',
  PAID: 'Pago',
  SHIPPED: 'Enviado',
  DELIVERED: 'Entregue',
  CANCELLED: 'Cancelado',
};

@Component({
  selector: 'app-orders',
  standalone: true,
  imports: [CommonModule, RouterLink, CentsPipe],
  template: `
    <h1 class="mb-4 text-xl font-semibold text-gray-700">Minhas compras</h1>
    @if (orders().length === 0) {
      <p class="text-gray-500">Você ainda não fez nenhuma compra.</p>
    } @else {
      <div class="space-y-3">
        @for (o of orders(); track o.id) {
          <a
            [routerLink]="['/orders', o.id]"
            class="flex items-center justify-between rounded-lg bg-white p-4 shadow hover:shadow-md"
          >
            <div>
              <p class="text-sm text-gray-500">Pedido {{ o.id.slice(0, 8) }}…</p>
              <p class="font-medium">{{ o.items.length }} item(s)</p>
            </div>
            <span class="rounded-full bg-gray-100 px-3 py-1 text-sm">{{ label(o.status) }}</span>
            <span class="font-semibold">{{ o.total_cents | cents }}</span>
          </a>
        }
      </div>
    }
  `,
})
export class OrdersComponent {
  private api = inject(OrdersService);
  orders = signal<OrderOut[]>([]);

  constructor() {
    this.api.listOrdersApiOrdersGet().subscribe((o) => this.orders.set(o));
  }

  label(s: string): string {
    return STATUS_LABELS[s] ?? s;
  }
}
