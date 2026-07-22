import { Pipe, PipeTransform } from '@angular/core';

/** Formats integer cents as BRL currency, e.g. 19900 -> "R$ 199,00". */
@Pipe({ name: 'cents', standalone: true })
export class CentsPipe implements PipeTransform {
  transform(cents: number | null | undefined, currency = 'BRL'): string {
    const value = (cents ?? 0) / 100;
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency }).format(value);
  }
}
