import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { HomeComponent } from './home.component';

describe('HomeComponent', () => {
  let fixture: ComponentFixture<HomeComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HomeComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
    fixture = TestBed.createComponent(HomeComponent);
    httpMock = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  it('renders the highlights heading and shows fetched products', () => {
    const req = httpMock.expectOne((r) => r.url.includes('/api/products'));
    req.flush({
      items: [
        {
          id: '1',
          seller_id: 's',
          title: 'Test Item',
          description: '',
          price_cents: 1000,
          currency: 'BRL',
          stock: 5,
          category: 'x',
          images: [],
          status: 'ACTIVE',
          created_at: '',
        },
      ],
      total: 1,
      limit: 10,
      offset: 0,
    });
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('Destaques');
    expect(el.textContent).toContain('Test Item');
    httpMock.verify();
  });
});
