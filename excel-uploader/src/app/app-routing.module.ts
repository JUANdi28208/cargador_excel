import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ExcelUploadComponent } from './modules/excel-upload/excel-upload.component';
import { SheetManagementComponent } from './modules/sheet-management/sheet-management.component';
import { ResultViewComponent } from './modules/result-view/result-view.component';

const routes: Routes = [
  { path: '', component: ExcelUploadComponent },
  { path: 'sheet-management', component: SheetManagementComponent },
  { path: 'result-view', component: ResultViewComponent },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }