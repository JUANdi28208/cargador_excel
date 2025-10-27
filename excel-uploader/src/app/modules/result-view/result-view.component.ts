import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { UploadResponse } from '../../models/excel-file';

@Component({
  selector: 'app-result-view',
  templateUrl: './result-view.component.html',
  styleUrls: []
})
export class ResultViewComponent implements OnInit {
  uploadResult: UploadResponse | null = null;

  constructor(private router: Router) { }

  ngOnInit() {
    const navigation = this.router.getCurrentNavigation();
    if (navigation?.extras.state) {
      this.uploadResult = navigation.extras.state['uploadResult'];
    }
  }

  // Métodos para mostrar los resultados
  getObjectKeys(obj: any): string[] {
    return Object.keys(obj);
  }

  getObjectValues(obj: any): any[] {
    return Object.values(obj);
  }
}

