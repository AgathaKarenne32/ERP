import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { CartStore } from '../../core/cart.store';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  template: `
    <div class="mx-auto max-w-sm rounded-lg bg-white p-8 shadow">
      <h1 class="mb-6 text-center text-xl font-semibold text-gray-700">Entrar</h1>
      <form [formGroup]="form" (ngSubmit)="submit()" class="space-y-4">
        <div>
          <input formControlName="email" type="email" placeholder="E-mail"
            class="w-full rounded border px-3 py-2 focus:outline-none" />
        </div>
        <div>
          <input formControlName="password" type="password" placeholder="Senha"
            class="w-full rounded border px-3 py-2 focus:outline-none" />
        </div>
        @if (error()) {
          <p class="text-sm text-red-600">{{ error() }}</p>
        }
        <button type="submit" [disabled]="form.invalid || loading()"
          class="w-full rounded bg-brand-blue py-2 font-semibold text-white disabled:opacity-50">
          {{ loading() ? 'Entrando…' : 'Entrar' }}
        </button>
      </form>
      <p class="mt-4 text-center text-sm text-gray-500">
        Não tem conta? <a routerLink="/register" class="text-brand-blue hover:underline">Criar conta</a>
      </p>
      <div class="mt-4 rounded bg-gray-50 p-3 text-xs text-gray-500">
        <b>Demo:</b> buyer&#64;demo.com / seller1&#64;demo.com — senha <code>demo1234</code>
      </div>
    </div>
  `,
})
export class LoginComponent {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private cart = inject(CartStore);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  loading = signal(false);
  error = signal('');

  form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', Validators.required],
  });

  submit(): void {
    if (this.form.invalid) return;
    this.loading.set(true);
    this.error.set('');
    this.auth.login(this.form.getRawValue()).subscribe({
      next: () => {
        this.auth.loadMe().subscribe();
        this.cart.refresh();
        const redirect = this.route.snapshot.queryParams['redirect'] ?? '/';
        this.router.navigateByUrl(redirect);
      },
      error: (err) => {
        this.error.set(err?.error?.detail ?? 'Credenciais inválidas');
        this.loading.set(false);
      },
    });
  }
}
