import { TestBed } from '@angular/core/testing';

import { Radicado } from './radicado';

describe('Radicado', () => {
  let service: Radicado;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Radicado);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
