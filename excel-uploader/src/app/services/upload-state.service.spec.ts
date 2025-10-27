import { TestBed } from '@angular/core/testing';

import { UploadStateService } from './upload-state.service';

describe('UploadStateService', () => {
  let service: UploadStateService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(UploadStateService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
