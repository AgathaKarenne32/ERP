import { Routes } from '@angular/router';
import { authGuard, sellerGuard } from './core/auth.guard';

// Lazy standalone components keep the initial bundle small.
export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./features/home/home.component').then((m) => m.HomeComponent),
  },
  {
    path: 'search',
    loadComponent: () =>
      import('./features/search/search.component').then((m) => m.SearchComponent),
  },
  {
    path: 'product/:id',
    loadComponent: () =>
      import('./features/product/product.component').then((m) => m.ProductComponent),
  },
  {
    path: 'cart',
    canActivate: [authGuard],
    loadComponent: () => import('./features/cart/cart.component').then((m) => m.CartComponent),
  },
  {
    path: 'checkout',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/checkout/checkout.component').then((m) => m.CheckoutComponent),
  },
  {
    path: 'orders',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/orders/orders.component').then((m) => m.OrdersComponent),
  },
  {
    path: 'orders/:id',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/orders/order-detail.component').then((m) => m.OrderDetailComponent),
  },
  {
    path: 'track/:code',
    loadComponent: () =>
      import('./features/orders/track.component').then((m) => m.TrackComponent),
  },
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'register',
    loadComponent: () =>
      import('./features/auth/register.component').then((m) => m.RegisterComponent),
  },
  {
    path: 'seller',
    canActivate: [sellerGuard],
    loadComponent: () =>
      import('./features/seller/dashboard.component').then((m) => m.SellerDashboardComponent),
  },
  {
    path: 'seller/products',
    canActivate: [sellerGuard],
    loadComponent: () =>
      import('./features/seller/products.component').then((m) => m.SellerProductsComponent),
  },
  {
    path: 'seller/products/new',
    canActivate: [sellerGuard],
    loadComponent: () =>
      import('./features/seller/product-form.component').then((m) => m.ProductFormComponent),
  },
  { path: '**', redirectTo: '' },
];
