import { CommonModule } from '@angular/common';
import { Component, inject, input, signal } from '@angular/core';
import { ShippingService, TrackingOut } from '../../core/api';

@Component({
  selector: 'app-track',
  standalone: true,
  imports: [CommonModule],
  template: `
    <h1 class="mb-4 text-xl font-semibold text-gray-700">Rastreamento</h1>
    @if (tracking(); as t) {
      <div class="rounded-lg bg-white p-6 shadow">
        <p class="mb-1 text-sm text-gray-500">Código</p>
        <p class="mb-6 font-mono text-lg">{{ t.tracking_code }}</p>

        <ol class="relative border-l-2 border-gray-200 pl-6">
          @for (ev of t.timeline; track ev.status) {
            <li class="mb-6">
              <span
                class="absolute -left-[9px] h-4 w-4 rounded-full"
                [class]="ev.reached ? 'bg-brand-blue' : 'bg-gray-300'"
              ></span>
              <p [class]="ev.reached ? 'font-semibold text-gray-800' : 'text-gray-400'">
                {{ ev.label }}
              </p>
            </li>
          }
        </ol>

        @if (t.estimated_delivery) {
          <p class="mt-2 text-sm text-gray-500">
            Previsão de entrega: {{ t.estimated_delivery | date: 'dd/MM/yyyy' }}
          </p>
        }
      </div>
    } @else if (error()) {
      <p class="text-red-600">{{ error() }}</p>
    } @else {
      <p class="text-gray-500">Carregando…</p>
    }
  `,
})
export class TrackComponent {
  code = input.required<string>();
  private api = inject(ShippingService);
  tracking = signal<TrackingOut | null>(null);
  error = signal('');

  constructor() {
    queueMicrotask(() => {
      this.api.trackApiShipmentsTrackCodeGet(this.code()).subscribe({
        next: (t) => this.tracking.set(t),
        error: () => this.error.set('Código de rastreio não encontrado.'),
      });
    });
  }
}
