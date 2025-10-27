import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { ExcelUploadComponent } from './modules/excel-upload/excel-upload.component';
import { SheetManagementComponent } from './modules/sheet-management/sheet-management.component';
import { ResultViewComponent } from './modules/result-view/result-view.component';
import { ExcelUploadService } from './services/excel-upload.service';

// Importar Chart.js
import { Chart, registerables } from 'chart.js';
Chart.register(...registerables);

@NgModule({
  declarations: [
    AppComponent,
    ExcelUploadComponent,
    SheetManagementComponent,
    ResultViewComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    HttpClientModule,
    FormsModule,
    ReactiveFormsModule,
    BrowserAnimationsModule
  ],
  providers: [ExcelUploadService],
  bootstrap: [AppComponent]
})
export class AppModule { }
