import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';
import { LoginRequest, RegisterRequest, TokenResponse, UserOut } from './api';

const TOKEN_KEY = 'access_token';

/**
 * Central auth state. Holds the access token (in memory + localStorage so a
 * refresh survives reloads) and the current user as signals. The refresh token
 * lives only in an httpOnly cookie set by the backend and is never touched here.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private base = environment.apiBase + '/api/auth';

  readonly token = signal<string | null>(localStorage.getItem(TOKEN_KEY));
  readonly user = signal<UserOut | null>(null);
  readonly isLoggedIn = computed(() => this.token() !== null);
  readonly isSeller = computed(
    () => this.user()?.role === 'SELLER' || this.user()?.role === 'ADMIN',
  );

  login(payload: LoginRequest): Observable<TokenResponse> {
    return this.http
      .post<TokenResponse>(`${this.base}/login`, payload, { withCredentials: true })
      .pipe(tap((res) => this.setToken(res.access_token)));
  }

  register(payload: RegisterRequest): Observable<UserOut> {
    return this.http.post<UserOut>(`${this.base}/register`, payload);
  }

  /** Uses the httpOnly refresh cookie to mint a new access token. */
  refresh(): Observable<TokenResponse> {
    return this.http
      .post<TokenResponse>(`${this.base}/refresh`, {}, { withCredentials: true })
      .pipe(tap((res) => this.setToken(res.access_token)));
  }

  loadMe(): Observable<UserOut> {
    return this.http
      .get<UserOut>(`${environment.apiBase}/api/me`)
      .pipe(tap((u) => this.user.set(u)));
  }

  setToken(token: string): void {
    this.token.set(token);
    localStorage.setItem(TOKEN_KEY, token);
  }

  logout(): void {
    this.token.set(null);
    this.user.set(null);
    localStorage.removeItem(TOKEN_KEY);
  }
}
