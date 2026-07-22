import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ProductsService } from '../../core/api';

@Component({
  selector: 'app-product-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  template: `
    <a routerLink="/seller/products" class="text-sm text-brand-blue hover:underline">← Meus produtos</a>
    <h1 class="mb-4 mt-2 text-xl font-semibold text-gray-700">Novo produto</h1>

    <form [formGroup]="form" (ngSubmit)="submit()" class="max-w-lg space-y-4 rounded-lg bg-white p-6 shadow">
      <div>
        <label class="mb-1 block text-sm text-gray-500">Título</label>
        <input formControlName="title" class="w-full rounded border px-3 py-2" />
      </div>
      <div>
        <label class="mb-1 block text-sm text-gray-500">Descrição</label>
        <textarea formControlName="description" rows="3" class="w-full rounded border px-3 py-2"></textarea>
      </div>
      <div class="flex gap-4">
        <div class="flex-1">
          <label class="mb-1 block text-sm text-gray-500">Preço (R$)</label>
          <input formControlName="price" type="number" step="0.01" class="w-full rounded border px-3 py-2" />
        </div>
        <div class="flex-1">
          <label class="mb-1 block text-sm text-gray-500">Estoque</label>
          <input formControlName="stock" type="number" class="w-full rounded border px-3 py-2" />
        </div>
      </div>
      <div>
        <label class="mb-1 block text-sm text-gray-500">Categoria</label>
        <select formControlName="category" class="w-full rounded border px-3 py-2">
          <option value="eletronicos">Eletrônicos</option>
          <option value="casa">Casa</option>
          <option value="moda">Moda</option>
        </select>
      </div>
      <div>
        <label class="mb-1 block text-sm text-gray-500">URL da imagem</label>
        <input formControlName="image" placeholder="https://…" class="w-full rounded border px-3 py-2" />
        <!-- File upload is out of MVP scope; we accept URLs (see ROADMAP). -->
      </div>
      @if (error()) {
        <p class="text-sm text-red-600">{{ error() }}</p>
      }
      <button type="submit" [disabled]="form.invalid || saving()"
        class="rounded bg-brand-blue px-6 py-2 font-semibold text-white disabled:opacity-50">
        {{ saving() ? 'Salvando…' : 'Cadastrar produto' }}
      </button>
    </form>
  `,
})
export class ProductFormComponent {
  private fb = inject(FormBuilder);
  private api = inject(ProductsService);
  private router = inject(Router);

  saving = signal(false);
  error = signal('');

  form = this.fb.nonNullable.group({
    title: ['', Validators.required],
    description: [''],
    price: [0, [Validators.required, Validators.min(0.01)]],
    stock: [0, [Validators.required, Validators.min(0)]],
    category: ['eletronicos', Validators.required],
    image: [''],
  });

  submit(): void {
    if (this.form.invalid) return;
    this.saving.set(true);
    this.error.set('');
    const v = this.form.getRawValue();
    this.api
      .createProductApiProductsPost({
        title: v.title,
        description: v.description,
        price_cents: Math.round(v.price * 100), // convert reais -> cents
        stock: v.stock,
        category: v.category,
        images: v.image ? [v.image] : [],
      })
      .subscribe({
        next: () => this.router.navigate(['/seller/products']),
        error: (err) => {
          this.error.set(err?.error?.detail ?? 'Erro ao cadastrar');
          this.saving.set(false);
        },
      });
  }
}
