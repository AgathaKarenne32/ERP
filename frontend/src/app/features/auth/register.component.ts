import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  template: `
    <div class="mx-auto max-w-sm rounded-lg bg-white p-8 shadow">
      <h1 class="mb-6 text-center text-xl font-semibold text-gray-700">Criar conta</h1>
      <form [formGroup]="form" (ngSubmit)="submit()" class="space-y-4">
        <input formControlName="name" placeholder="Nome" class="w-full rounded border px-3 py-2" />
        <input formControlName="email" type="email" placeholder="E-mail" class="w-full rounded border px-3 py-2" />
        <input formControlName="password" type="password" placeholder="Senha (mín. 6)" class="w-full rounded border px-3 py-2" />

        <div class="flex gap-4 text-sm">
          <label class="flex items-center gap-1">
            <input type="radio" formControlName="role" value="BUYER" /> Comprador
          </label>
          <label class="flex items-center gap-1">
            <input type="radio" formControlName="role" value="SELLER" /> Vendedor
          </label>
        </div>
        @if (form.value.role === 'SELLER') {
          <input formControlName="store_name" placeholder="Nome da loja" class="w-full rounded border px-3 py-2" />
        }

        @if (error()) {
          <p class="text-sm text-red-600">{{ error() }}</p>
        }
        <button type="submit" [disabled]="form.invalid || loading()"
          class="w-full rounded bg-brand-blue py-2 font-semibold text-white disabled:opacity-50">
          {{ loading() ? 'Criando…' : 'Criar conta' }}
        </button>
      </form>
      <p class="mt-4 text-center text-sm text-gray-500">
        Já tem conta? <a routerLink="/login" class="text-brand-blue hover:underline">Entrar</a>
      </p>
    </div>
  `,
})
export class RegisterComponent {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);

  loading = signal(false);
  error = signal('');

  form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
    role: ['BUYER' as 'BUYER' | 'SELLER', Validators.required],
    store_name: [''],
  });

  submit(): void {
    if (this.form.invalid) return;
    this.loading.set(true);
    this.error.set('');
    const v = this.form.getRawValue();
    this.auth.register(v).subscribe({
      next: () => {
        // Auto-login after registration.
        this.auth.login({ email: v.email, password: v.password }).subscribe(() => {
          this.auth.loadMe().subscribe();
          this.router.navigate(['/']);
        });
      },
      error: (err) => {
        this.error.set(err?.error?.detail ?? 'Erro ao criar conta');
        this.loading.set(false);
      },
    });
  }
}
