<template>
  <div class="insurance-foundation-view">
    <div class="page-header insurance-header">
      <div>
        <h2>Cấu hình BHXH dùng chung</h2>
        <span class="subtitle">Foundation cho policy, tỷ lệ đóng mặc định và vùng BHXH công ty</span>
      </div>
      <div class="insurance-header-actions">
        <Button v-can:edit="'insurance'" label="Cập nhật vùng công ty" icon="pi pi-map-marker" severity="secondary" @click="openRegionDialog" />
        <Button v-can:create="'insurance'" label="Tạo policy mới" icon="pi pi-plus" @click="openCreatePolicyDialog" />
        <Button
          v-if="activePolicy"
          label="Tạo nháp từ policy hiện hành"
          icon="pi pi-copy"
          severity="secondary"
          v-can:edit="'insurance'"
          @click="openCloneDialog"
        />
        <Button
          label="Về tổng quan danh mục"
          icon="pi pi-th-large"
          severity="secondary"
          outlined
          @click="router.push('/catalog')"
        />
        <Button
          label="Mở module BHXH nhân viên"
          icon="pi pi-users"
          severity="secondary"
          @click="router.push('/insurance')"
        />
      </div>
    </div>

    <div class="insurance-note">
      <strong>Lưu ý quan trọng:</strong>
      <ul>
        <li>Thay đổi policy chỉ áp dụng cho cấu hình mới sau khi activate.</li>
        <li>Vùng BHXH của công ty hiện đang được seed mặc định là Vùng III.</li>
        <li>Seeder tỷ lệ là mặc định vận hành; trước khi thay đổi production cần đối chiếu lại văn bản pháp lý hiện hành.</li>
      </ul>
    </div>

    <div class="insurance-summary-grid">
      <div class="card insurance-summary-card">
        <div class="insurance-card-label">Policy đang active</div>
        <div v-if="activePolicy" class="insurance-card-main">{{ activePolicy.name }}</div>
        <div v-if="activePolicy" class="insurance-card-sub">
          {{ activePolicy.code }} · Hiệu lực từ {{ formatDate(activePolicy.effective_from) }}
        </div>
        <div v-else class="insurance-card-empty">Chưa có policy đang active</div>
      </div>

      <div class="card insurance-summary-card">
        <div class="insurance-card-label">Vùng BHXH công ty</div>
        <div v-if="companyRegion.current" class="insurance-card-main">{{ regionLabel(companyRegion.current.region) }}</div>
        <div v-if="companyRegion.current" class="insurance-card-sub">
          Hiệu lực từ {{ formatDate(companyRegion.current.effective_from) }}
        </div>
        <div v-else class="insurance-card-empty">Chưa có vùng hiệu lực</div>
      </div>

      <div class="card insurance-summary-card">
        <div class="insurance-card-label">LTTV vùng công ty</div>
        <div v-if="currentRegionMinimumWage" class="insurance-card-main">
          {{ formatCurrency(currentRegionMinimumWage.amount) }}
        </div>
        <div v-if="currentRegionMinimumWage" class="insurance-card-sub">
          {{ regionLabel(currentRegionMinimumWage.region) }} · {{ currentRegionMinimumWage.decree_number }}
        </div>
        <div v-else class="insurance-card-empty">Chưa có cấu hình hiệu lực</div>
      </div>

      <div class="card insurance-summary-card">
        <div class="insurance-card-label">Rule thâm niên BHXH</div>
        <div v-if="senioritySettings.current" class="insurance-card-main">
          {{ senioritySettings.current.years_per_grade }} năm / 1 bậc
        </div>
        <div v-if="senioritySettings.current" class="insurance-card-sub">
          Nâng bậc ngày {{ formatMonthDay(senioritySettings.current.raise_month, senioritySettings.current.raise_day) }}
          · Cutoff {{ formatMonthDay(senioritySettings.current.first_year_cutoff_month, senioritySettings.current.first_year_cutoff_day) }}
        </div>
        <div v-else class="insurance-card-empty">Chưa có rule hiệu lực</div>
      </div>

      <div class="card insurance-summary-card">
        <div class="insurance-card-label">Nhóm vị trí BHXH</div>
        <div v-if="positionGroups.length" class="insurance-card-main">{{ positionGroups.length }} nhóm</div>
        <div v-if="currentPositionScale" class="insurance-card-sub">
          {{ currentPositionScale.name }} · từ {{ formatDate(currentPositionScale.effective_from) }}
        </div>
        <div v-else class="insurance-card-empty">Chưa có scale hiệu lực</div>
      </div>
    </div>

    <div class="insurance-section-grid">
      <div class="card insurance-policy-list-card">
        <div class="section-heading">
          <h3>Danh sách policy version</h3>
          <Button icon="pi pi-refresh" severity="secondary" text rounded :loading="loading" @click="loadAll" />
        </div>

        <DataTable :value="policyVersions" :loading="loading" stripedRows responsive-layout="scroll">
          <Column field="code" header="Mã" style="min-width: 160px" />
          <Column field="name" header="Tên" style="min-width: 240px" />
          <Column header="Hiệu lực" style="width: 190px">
            <template #body="{ data }">
              <div class="range-cell">
                <span>{{ formatDate(data.effective_from) }}</span>
                <span>{{ data.effective_to ? `→ ${formatDate(data.effective_to)}` : '→ hiện tại' }}</span>
              </div>
            </template>
          </Column>
          <Column header="Vùng" style="width: 110px">
            <template #body="{ data }">{{ regionLabel(data.company_region) }}</template>
          </Column>
          <Column header="Trạng thái" style="width: 110px">
            <template #body="{ data }">
              <Tag
                :value="data.is_active ? 'Đang dùng' : (data.effective_to ? 'Lịch sử' : 'Nháp')"
                :severity="data.is_active ? 'success' : (data.effective_to ? 'contrast' : 'secondary')"
              />
            </template>
          </Column>
          <Column header="" style="width: 156px">
            <template #body="{ data }">
              <div class="action-cell">
                <Button
                  v-if="!data.is_active && !data.effective_to"
                  icon="pi pi-pencil"
                  severity="secondary"
                  text
                  rounded
                  size="small"
                  v-can:edit="'insurance'"
                  @click="openEditPolicyDialog(data)"
                />
                <Button
                  v-if="!data.is_active && !data.effective_to"
                  icon="pi pi-check"
                  severity="success"
                  text
                  rounded
                  size="small"
                  :loading="activatingPolicyId === data.id"
                  v-can:edit="'insurance'"
                  @click="activatePolicy(data)"
                />
                <Button
                  v-if="!data.is_active && !data.effective_to"
                  icon="pi pi-trash"
                  severity="danger"
                  text
                  rounded
                  size="small"
                  v-can:delete="'insurance'"
                  @click="confirmDeletePolicy(data)"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </div>

      <div class="card insurance-active-rates-card">
        <div class="section-heading">
          <h3>Tỷ lệ đóng mặc định đang áp dụng</h3>
          <span v-if="activePolicy" class="section-hint">{{ activePolicy.code }}</span>
        </div>

        <div v-if="!activePolicy" class="empty-state">Chưa có policy active</div>
        <div v-else class="ins-rates-table">
          <div class="ins-rates-head">
            <span>Thành phần</span>
            <span>NLĐ %</span>
            <span>NSDLĐ %</span>
            <span>Tổng %</span>
            <span>Nộp hộ</span>
          </div>
          <template v-for="group in groupedRates" :key="group.kind">
            <div class="ins-rates-group-header">{{ group.label }}</div>
            <div v-for="item in group.items" :key="item.component_code" class="ins-rates-row">
              <span>{{ item.component_name }}</span>
              <span>{{ formatPercent(item.employee_rate_percent) }}</span>
              <span>{{ formatPercent(item.employer_rate_percent) }}</span>
              <span>{{ formatPercent(totalRate(item)) }}</span>
              <Tag :value="item.employer_advances_employee_part ? 'Có' : 'Không'" :severity="item.employer_advances_employee_part ? 'warn' : 'contrast'" size="small" />
            </div>
            <div class="ins-rates-subtotal">
              <span>Tổng {{ group.label.split('—')[0].trim() }}</span>
              <span>{{ formatPercent(group.empTotal) }}</span>
              <span>{{ formatPercent(group.erTotal) }}</span>
              <span>{{ formatPercent(group.empTotal + group.erTotal) }}</span>
              <span></span>
            </div>
          </template>
          <div class="ins-rates-total">
            <span>Tổng tất cả</span>
            <span>{{ formatPercent(grandTotals.emp) }}</span>
            <span>{{ formatPercent(grandTotals.er) }}</span>
            <span>{{ formatPercent(grandTotals.emp + grandTotals.er) }}</span>
            <span></span>
          </div>
        </div>
      </div>
    </div>

    <div class="card insurance-region-history-card">
      <div class="section-heading">
        <h3>Rule thâm niên BHXH</h3>
        <Button v-can:create="'insurance'" label="Thêm rule thâm niên" icon="pi pi-plus" size="small" @click="openCreateSeniorityDialog" />
      </div>

      <DataTable :value="senioritySettings.history" stripedRows responsive-layout="scroll">
        <Column header="Ngày nâng bậc" style="width: 160px">
          <template #body="{ data }">{{ formatMonthDay(data.raise_month, data.raise_day) }}</template>
        </Column>
        <Column header="Chu kỳ" style="width: 170px">
          <template #body="{ data }">{{ data.years_per_grade }} năm / 1 bậc</template>
        </Column>
        <Column header="Cutoff năm đầu" style="width: 170px">
          <template #body="{ data }">{{ formatMonthDay(data.first_year_cutoff_month, data.first_year_cutoff_day) }}</template>
        </Column>
        <Column header="Hiệu lực" style="width: 200px">
          <template #body="{ data }">
            <div class="range-cell">
              <span>{{ formatDate(data.effective_from) }}</span>
              <span>{{ data.effective_to ? `→ ${formatDate(data.effective_to)}` : '→ hiện tại' }}</span>
            </div>
          </template>
        </Column>
        <Column field="note" header="Ghi chú" style="min-width: 220px" />
        <Column header="" style="width: 120px">
          <template #body="{ data }">
            <div class="action-cell">
              <Button v-can:edit="'insurance'" icon="pi pi-pencil" severity="secondary" text rounded size="small" @click="openEditSeniorityDialog(data)" />
              <Button v-can:delete="'insurance'" icon="pi pi-trash" severity="danger" text rounded size="small" @click="confirmDeleteSeniority(data)" />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <div class="card insurance-region-history-card">
      <div class="section-heading">
        <h3>Lịch sử vùng BHXH công ty</h3>
      </div>

      <DataTable :value="companyRegion.history" stripedRows responsive-layout="scroll">
        <Column header="Vùng" style="width: 140px">
          <template #body="{ data }">{{ regionLabel(data.region) }}</template>
        </Column>
        <Column header="Hiệu lực từ" style="width: 140px">
          <template #body="{ data }">{{ formatDate(data.effective_from) }}</template>
        </Column>
        <Column header="Hiệu lực đến" style="width: 140px">
          <template #body="{ data }">{{ data.effective_to ? formatDate(data.effective_to) : 'Hiện tại' }}</template>
        </Column>
        <Column field="note" header="Ghi chú" style="min-width: 240px" />
      </DataTable>
    </div>

    <div class="card insurance-region-history-card">
      <div class="section-heading">
        <h3>Lương tối thiểu vùng</h3>
        <Button v-can:create="'insurance'" label="Thêm cấu hình LTTV" icon="pi pi-plus" size="small" @click="openCreateMinimumWageDialog" />
      </div>

      <DataTable :value="minimumWages" stripedRows responsive-layout="scroll">
        <Column header="Vùng" style="width: 140px">
          <template #body="{ data }">{{ regionLabel(data.region) }}</template>
        </Column>
        <Column field="amount" header="Mức lương" style="width: 180px">
          <template #body="{ data }">{{ formatCurrency(data.amount) }}</template>
        </Column>
        <Column field="decree_number" header="Nghị định" style="width: 180px" />
        <Column header="Hiệu lực" style="width: 200px">
          <template #body="{ data }">
            <div class="range-cell">
              <span>{{ formatDate(data.effective_from) }}</span>
              <span>{{ data.effective_to ? `→ ${formatDate(data.effective_to)}` : '→ hiện tại' }}</span>
            </div>
          </template>
        </Column>
        <Column field="note" header="Ghi chú" style="min-width: 220px" />
        <Column header="" style="width: 120px">
          <template #body="{ data }">
            <div class="action-cell">
              <Button v-can:edit="'insurance'" icon="pi pi-pencil" severity="secondary" text rounded size="small" @click="openEditMinimumWageDialog(data)" />
              <Button v-can:delete="'insurance'" icon="pi pi-trash" severity="danger" text rounded size="small" @click="confirmDeleteMinimumWage(data)" />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Card Danh sách Thang bảng lương -->
    <div class="card insurance-region-history-card">
      <div class="section-heading">
        <h3>Thang bảng lương</h3>
        <Button v-can:create="'insurance'" label="Thêm thang bảng lương" icon="pi pi-plus" size="small" @click="openCreateSalaryScaleDialog" />
      </div>

      <DataTable :value="salaryScales" stripedRows responsive-layout="scroll">
        <Column field="name" header="Tên thang bảng lương" style="min-width: 260px" />
        <Column header="Thời gian hiệu lực" style="width: 220px">
          <template #body="{ data }">
            <div class="range-cell">
              <span>{{ formatDate(data.effective_from) }}</span>
              <span>{{ data.effective_to ? `→ ${formatDate(data.effective_to)}` : '→ hiện tại' }}</span>
            </div>
          </template>
        </Column>
        <Column header="Trạng thái" style="width: 140px">
          <template #body="{ data }">
            <Tag
              :value="data.is_active ? 'Đang dùng' : (data.effective_to ? 'Lịch sử' : 'Nháp')"
              :severity="data.is_active ? 'success' : (data.effective_to ? 'contrast' : 'secondary')"
            />
          </template>
        </Column>
        <Column field="note" header="Ghi chú" style="min-width: 220px" />
        <Column header="" style="width: 240px">
          <template #body="{ data }">
            <div class="action-cell">
              <Button
                icon="pi pi-cog"
                v-tooltip.top="'Cấu hình hệ số'"
                severity="secondary"
                text
                rounded
                size="small"
                v-can:edit="'insurance'"
                @click="openCoefficientsDialog(data)"
              />
              <Button
                v-if="!data.is_active"
                icon="pi pi-check"
                v-tooltip.top="'Kích hoạt'"
                severity="success"
                text
                rounded
                size="small"
                :loading="activatingScaleId === data.id"
                v-can:edit="'insurance'"
                @click="activateSalaryScale(data)"
              />
              <Button
                icon="pi pi-copy"
                v-tooltip.top="'Nhân bản'"
                severity="secondary"
                text
                rounded
                size="small"
                v-can:edit="'insurance'"
                @click="openCloneSalaryScaleDialog(data)"
              />
              <Button
                v-if="!data.is_active && !data.effective_to"
                icon="pi pi-pencil"
                v-tooltip.top="'Chỉnh sửa'"
                severity="secondary"
                text
                rounded
                size="small"
                v-can:edit="'insurance'"
                @click="openEditSalaryScaleDialog(data)"
              />
              <Button
                v-if="!data.is_active && !data.effective_to"
                icon="pi pi-trash"
                v-tooltip.top="'Xóa'"
                severity="danger"
                text
                rounded
                size="small"
                v-can:delete="'insurance'"
                @click="confirmDeleteSalaryScale(data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <div class="card insurance-region-history-card">
      <div class="section-heading">
        <h3>Nhóm vị trí BHXH + hệ số 7 bậc</h3>
        <Button
          v-can:create="'insurance'"
          label="Thêm nhóm vị trí BHXH"
          icon="pi pi-plus"
          size="small"
          :disabled="!currentPositionScale"
          @click="openCreatePositionGroupDialog"
        />
      </div>

      <div v-if="currentPositionScale" class="section-hint insurance-inline-hint">
        Scale hiện hành: {{ currentPositionScale.name }} · hiệu lực từ {{ formatDate(currentPositionScale.effective_from) }}
      </div>
      <div v-else class="empty-state">Chưa có thang bảng lương hiệu lực để cấu hình hệ số nhóm vị trí.</div>

      <DataTable v-if="currentPositionScale" :value="positionGroups" stripedRows responsive-layout="scroll">
        <Column field="code" header="Mã nhóm" style="width: 160px" />
        <Column field="name" header="Tên nhóm" style="min-width: 280px" />
        <Column header="Vị trí đã gán" style="min-width: 260px">
          <template #body="{ data }">
            <span v-if="data.members.length">
              {{ positionGroupMemberNames(data) }}
            </span>
            <span v-else>—</span>
          </template>
        </Column>
        <Column header="7 bậc hệ số" style="min-width: 260px">
          <template #body="{ data }">
            {{ positionGroupCoefficientSummary(data) }}
          </template>
        </Column>
        <Column header="Trạng thái" style="width: 120px">
          <template #body="{ data }">
            <Tag :value="data.is_active ? 'Hoạt động' : 'Tắt'" :severity="data.is_active ? 'success' : 'secondary'" />
          </template>
        </Column>
        <Column header="" style="width: 120px">
          <template #body="{ data }">
            <div class="action-cell">
              <Button v-can:edit="'insurance'" icon="pi pi-pencil" severity="secondary" text rounded size="small" @click="openEditPositionGroupDialog(data)" />
              <Button v-can:delete="'insurance'" icon="pi pi-trash" severity="danger" text rounded size="small" @click="confirmDeletePositionGroup(data)" />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <div class="card ins-date-checker">
      <div class="section-heading">
        <h3>Kiểm tra cấu hình theo ngày</h3>
      </div>
      <div class="field-row-2">
        <div class="field">
          <label>Ngày kiểm tra</label>
          <input v-model="checkDate" class="p-inputtext p-component w-full" type="date" />
        </div>
        <div class="field ins-check-action">
          <Button label="Kiểm tra" icon="pi pi-search" :loading="checkingDate" :disabled="!checkDate" @click="checkEffectiveConfig" />
        </div>
      </div>
      <div v-if="checkResult" class="ins-check-result">
        <div>Policy: <strong>{{ checkResult.policy_version.code }} — {{ checkResult.policy_version.name }}</strong></div>
        <div>Vùng công ty: <strong>{{ regionLabel(checkResult.company_region.region) }}</strong> (từ {{ formatDate(checkResult.company_region.effective_from) }})</div>
      </div>
      <div v-if="checkError" class="ins-check-error">{{ checkError }}</div>
    </div>

    <Dialog
      v-model:visible="policyDialogVisible"
      :header="editingPolicy ? 'Cập nhật policy version' : 'Tạo policy version mới'"
      :style="{ width: '960px' }"
      modal
      :close-on-escape="!submitting"
      :closable="!submitting"
    >
      <form class="insurance-policy-form" @submit.prevent="submitPolicy">
        <div class="field-row-3">
          <div class="field">
            <label>Mã policy <span class="req">*</span></label>
            <InputText v-model="policyForm.code" class="w-full" :disabled="!!editingPolicy" />
          </div>
          <div class="field">
            <label>Ngày hiệu lực <span class="req">*</span></label>
            <input v-model="policyForm.effective_from" class="p-inputtext p-component w-full" type="date" />
          </div>
          <div class="field">
            <label>Vùng công ty snapshot <span class="req">*</span></label>
            <Select
              v-model="policyForm.company_region"
              :options="regionOptions"
              option-label="label"
              option-value="value"
              filter
              class="w-full"
            />
          </div>
        </div>

        <div class="field">
          <label>Tên policy <span class="req">*</span></label>
          <InputText v-model="policyForm.name" class="w-full" />
        </div>

        <div class="field">
          <label>Căn cứ pháp lý</label>
          <Textarea v-model="policyForm.legal_basis_summary" class="w-full" rows="3" auto-resize />
        </div>

        <div class="field">
          <label>Ghi chú</label>
          <Textarea v-model="policyForm.note" class="w-full" rows="2" auto-resize />
        </div>

        <div class="policy-components-editor">
          <div class="section-heading">
            <h3>Component rates</h3>
            <span class="section-hint">Đủ 5 component active mới được activate policy</span>
          </div>

          <DataTable :value="policyForm.components" responsive-layout="scroll" stripedRows>
            <Column field="component_code" header="Mã" style="width: 180px" />
            <Column field="component_name" header="Tên" style="min-width: 260px" />
            <Column header="NLĐ %" style="width: 130px">
              <template #body="{ data }">
                <InputNumber v-model="data.employee_rate_percent_n" :min="0" :min-fraction-digits="0" :max-fraction-digits="4" class="w-full" />
              </template>
            </Column>
            <Column header="NSDLĐ %" style="width: 130px">
              <template #body="{ data }">
                <InputNumber v-model="data.employer_rate_percent_n" :min="0" :min-fraction-digits="0" :max-fraction-digits="4" class="w-full" />
              </template>
            </Column>
            <Column header="Công ty nộp hộ" style="width: 160px">
              <template #body="{ data }">
                <Checkbox v-model="data.employer_advances_employee_part" binary />
              </template>
            </Column>
          </DataTable>
        </div>

        <div class="dialog-actions">
          <Button type="button" label="Hủy" severity="secondary" text :disabled="submitting" @click="policyDialogVisible = false" />
          <Button v-can="editingPolicy ? 'insurance:edit' : 'insurance:create'" type="submit" :label="editingPolicy ? 'Lưu thay đổi' : 'Tạo policy'" icon="pi pi-check" :loading="submitting" />
        </div>
      </form>
    </Dialog>

    <Dialog
      v-model:visible="regionDialogVisible"
      header="Cập nhật vùng BHXH công ty"
      :style="{ width: '520px' }"
      modal
      :close-on-escape="!submittingRegion"
      :closable="!submittingRegion"
    >
      <form class="insurance-region-form" @submit.prevent="submitRegion">
        <div class="field">
          <label>Vùng mới <span class="req">*</span></label>
          <Select v-model="regionForm.region" :options="regionOptions" option-label="label" option-value="value" filter class="w-full" />
        </div>
        <div class="field">
          <label>Ngày hiệu lực <span class="req">*</span></label>
          <input v-model="regionForm.effective_from" class="p-inputtext p-component w-full" type="date" />
        </div>
        <div class="field">
          <label>Ghi chú</label>
          <Textarea v-model="regionForm.note" class="w-full" rows="3" auto-resize />
        </div>

        <div class="dialog-actions">
          <Button type="button" label="Hủy" severity="secondary" text :disabled="submittingRegion" @click="regionDialogVisible = false" />
          <Button v-can:edit="'insurance'" type="submit" label="Lưu vùng công ty" icon="pi pi-check" :loading="submittingRegion" />
        </div>
      </form>
    </Dialog>

    <Dialog
      v-model:visible="minimumWageDialogVisible"
      :header="editingMinimumWage ? 'Cập nhật lương tối thiểu vùng' : 'Thêm cấu hình lương tối thiểu vùng'"
      :style="{ width: '560px' }"
      modal
      :close-on-escape="!submittingMinimumWage"
      :closable="!submittingMinimumWage"
    >
      <form class="insurance-region-form" @submit.prevent="submitMinimumWage">
        <div class="field-row-2">
          <div class="field">
            <label>Vùng <span class="req">*</span></label>
            <Select v-model="minimumWageForm.region" :options="regionOptions" option-label="label" option-value="value" filter class="w-full" :disabled="!!editingMinimumWage" />
          </div>
          <div class="field">
            <label>Ngày hiệu lực <span class="req">*</span></label>
            <input v-model="minimumWageForm.effective_from" class="p-inputtext p-component w-full" type="date" :disabled="!!editingMinimumWage" />
          </div>
        </div>
        <div class="field-row-2">
          <div class="field">
            <label>Mức lương tối thiểu <span class="req">*</span></label>
            <InputNumber v-model="minimumWageForm.amount" class="w-full" :min="1" mode="currency" currency="VND" locale="vi-VN" />
          </div>
          <div class="field">
            <label>Nghị định <span class="req">*</span></label>
            <InputText v-model="minimumWageForm.decree_number" class="w-full" />
          </div>
        </div>
        <div class="field">
          <label>Ghi chú</label>
          <Textarea v-model="minimumWageForm.note" class="w-full" rows="3" auto-resize />
        </div>
        <div class="dialog-actions">
          <Button type="button" label="Hủy" severity="secondary" text :disabled="submittingMinimumWage" @click="minimumWageDialogVisible = false" />
          <Button v-can="editingMinimumWage ? 'insurance:edit' : 'insurance:create'" type="submit" :label="editingMinimumWage ? 'Lưu thay đổi' : 'Thêm cấu hình'" icon="pi pi-check" :loading="submittingMinimumWage" />
        </div>
      </form>
    </Dialog>

    <Dialog
      v-model:visible="seniorityDialogVisible"
      :header="editingSeniority ? 'Cập nhật rule thâm niên BHXH' : 'Thêm rule thâm niên BHXH'"
      :style="{ width: '640px' }"
      modal
      :close-on-escape="!submittingSeniority"
      :closable="!submittingSeniority"
    >
      <form class="insurance-region-form" @submit.prevent="submitSeniority">
        <div class="field-row-3">
          <div class="field">
            <label>Tháng nâng bậc <span class="req">*</span></label>
            <InputNumber v-model="seniorityForm.raise_month" class="w-full" :min="1" :max="12" />
          </div>
          <div class="field">
            <label>Ngày nâng bậc <span class="req">*</span></label>
            <InputNumber v-model="seniorityForm.raise_day" class="w-full" :min="1" :max="31" />
          </div>
          <div class="field">
            <label>Số năm / bậc <span class="req">*</span></label>
            <InputNumber v-model="seniorityForm.years_per_grade" class="w-full" :min="1" />
          </div>
        </div>
        <div class="field-row-3">
          <div class="field">
            <label>Tháng cutoff năm đầu <span class="req">*</span></label>
            <InputNumber v-model="seniorityForm.first_year_cutoff_month" class="w-full" :min="1" :max="12" />
          </div>
          <div class="field">
            <label>Ngày cutoff năm đầu <span class="req">*</span></label>
            <InputNumber v-model="seniorityForm.first_year_cutoff_day" class="w-full" :min="1" :max="31" />
          </div>
          <div class="field">
            <label>Ngày hiệu lực <span class="req">*</span></label>
            <input v-model="seniorityForm.effective_from" class="p-inputtext p-component w-full" type="date" :disabled="!!editingSeniority" />
          </div>
        </div>
        <div class="field">
          <label>Ghi chú</label>
          <Textarea v-model="seniorityForm.note" class="w-full" rows="3" auto-resize />
        </div>
        <div class="dialog-actions">
          <Button type="button" label="Hủy" severity="secondary" text :disabled="submittingSeniority" @click="seniorityDialogVisible = false" />
          <Button v-can="editingSeniority ? 'insurance:edit' : 'insurance:create'" type="submit" :label="editingSeniority ? 'Lưu thay đổi' : 'Thêm rule'" icon="pi pi-check" :loading="submittingSeniority" />
        </div>
      </form>
    </Dialog>

    <Dialog
      v-model:visible="positionGroupDialogVisible"
      :header="editingPositionGroup ? 'Cập nhật nhóm vị trí BHXH' : 'Thêm nhóm vị trí BHXH'"
      :style="{ width: '1040px' }"
      modal
      :close-on-escape="!submittingPositionGroup"
      :closable="!submittingPositionGroup"
    >
      <form class="insurance-region-form" @submit.prevent="submitPositionGroup">
        <div class="field-row-3">
          <div class="field">
            <label>Mã nhóm <span class="req">*</span></label>
            <InputText v-model="positionGroupForm.code" class="w-full" />
          </div>
          <div class="field">
            <label>Tên nhóm <span class="req">*</span></label>
            <InputText v-model="positionGroupForm.name" class="w-full" />
          </div>
          <div class="field">
            <label>Trạng thái</label>
            <Select
              v-model="positionGroupForm.is_active"
              :options="[
                { label: 'Hoạt động', value: true },
                { label: 'Tắt', value: false },
              ]"
              option-label="label"
              option-value="value"
              class="w-full"
            />
          </div>
        </div>

        <div class="field">
          <label>Mô tả</label>
          <Textarea v-model="positionGroupForm.description" class="w-full" rows="2" auto-resize />
        </div>

        <div class="field">
          <label>Vị trí công việc thuộc nhóm</label>
          <MultiSelect
            v-model="positionGroupForm.position_ids"
            :options="positionOptions"
            option-label="label"
            option-value="value"
            filter
            display="chip"
            class="w-full"
            :max-selected-labels="6"
          />
        </div>

        <div class="section-heading">
          <h3>7 bậc hệ số</h3>
          <span class="section-hint">Phải cấu hình đủ bậc I → VII</span>
        </div>
        <DataTable :value="positionGroupForm.coefficients" stripedRows responsive-layout="scroll">
          <Column header="Bậc" style="width: 100px">
            <template #body="{ data }">Bậc {{ data.grade_no }}</template>
          </Column>
          <Column header="Hệ số" style="width: 180px">
            <template #body="{ data }">
              <InputNumber v-model="data.coefficient" class="w-full" :min="0.01" :min-fraction-digits="2" :max-fraction-digits="4" />
            </template>
          </Column>
          <Column header="Số tháng xét nâng" style="width: 180px">
            <template #body="{ data }">
              <InputNumber v-model="data.promotion_months" class="w-full" :min="1" />
            </template>
          </Column>
          <Column header="Tiêu chí" style="min-width: 320px">
            <template #body="{ data }">
              <InputText v-model="data.criteria" class="w-full" />
            </template>
          </Column>
        </DataTable>

        <div class="dialog-actions">
          <Button type="button" label="Hủy" severity="secondary" text :disabled="submittingPositionGroup" @click="positionGroupDialogVisible = false" />
          <Button v-can="editingPositionGroup ? 'insurance:edit' : 'insurance:create'" type="submit" :label="editingPositionGroup ? 'Lưu thay đổi' : 'Thêm nhóm'" icon="pi pi-check" :loading="submittingPositionGroup" />
        </div>
      </form>
    </Dialog>

    <!-- Dialog Thêm/Sửa Thang bảng lương -->
    <Dialog
      v-model:visible="salaryScaleDialogVisible"
      :header="editingSalaryScale ? 'Cập nhật thông tin thang bảng lương' : 'Thêm thang bảng lương mới'"
      :style="{ width: '540px' }"
      modal
      :close-on-escape="!submittingSalaryScale"
      :closable="!submittingSalaryScale"
    >
      <form @submit.prevent="submitSalaryScale">
        <div class="field">
          <label>Tên thang lương <span class="req">*</span></label>
          <InputText v-model="salaryScaleForm.name" class="w-full" placeholder="Ví dụ: Thang bảng lương năm 2026" />
        </div>
        
        <div class="field">
          <label>Ngày hiệu lực <span class="req">*</span></label>
          <input v-model="salaryScaleForm.effective_from" class="p-inputtext p-component w-full" type="date" />
        </div>

        <div class="field">
          <label>Ghi chú</label>
          <Textarea v-model="salaryScaleForm.note" class="w-full" rows="3" auto-resize placeholder="Nhập ghi chú thêm..." />
        </div>

        <div class="dialog-actions">
          <Button type="button" label="Hủy" severity="secondary" text :disabled="submittingSalaryScale" @click="salaryScaleDialogVisible = false" />
          <Button v-can="editingSalaryScale ? 'insurance:edit' : 'insurance:create'" type="submit" :label="editingSalaryScale ? 'Lưu thay đổi' : 'Tạo thang lương'" icon="pi pi-check" :loading="submittingSalaryScale" />
        </div>
      </form>
    </Dialog>

    <!-- Dialog Nhân bản (Clone) Thang bảng lương -->
    <Dialog
      v-model:visible="salaryScaleCloneDialogVisible"
      header="Nhân bản thang bảng lương"
      :style="{ width: '540px' }"
      modal
      :close-on-escape="!submittingSalaryScale"
      :closable="!submittingSalaryScale"
    >
      <form @submit.prevent="submitCloneSalaryScale">
        <div class="field">
          <label>Thang bảng lương nguồn</label>
          <InputText v-if="cloneSourceScale" :model-value="cloneSourceScale.name" class="w-full" disabled />
        </div>

        <div class="field">
          <label>Tên thang lương mới <span class="req">*</span></label>
          <InputText v-model="cloneForm.name" class="w-full" placeholder="Ví dụ: Thang bảng lương năm 2026" />
        </div>
        
        <div class="field">
          <label>Ngày hiệu lực mới <span class="req">*</span></label>
          <input v-model="cloneForm.effective_from" class="p-inputtext p-component w-full" type="date" />
        </div>

        <div class="field">
          <label>Ghi chú</label>
          <Textarea v-model="cloneForm.note" class="w-full" rows="3" auto-resize />
        </div>

        <div class="dialog-actions">
          <Button type="button" label="Hủy" severity="secondary" text :disabled="submittingSalaryScale" @click="salaryScaleCloneDialogVisible = false" />
          <Button v-can:edit="'insurance'" type="submit" label="Nhân bản & Sao chép hệ số" icon="pi pi-copy" :loading="submittingSalaryScale" />
        </div>
      </form>
    </Dialog>

    <!-- Dialog Cấu hình hệ số 7 bậc -->
    <Dialog
      v-model:visible="coefficientsDialogVisible"
      :header="configuringScale ? `Cấu hình hệ số: ${configuringScale.name}` : 'Cấu hình hệ số'"
      :style="{ width: '1100px' }"
      modal
      :close-on-escape="!submittingCoefficients"
      :closable="!submittingCoefficients"
    >
      <div v-if="!configuringScale" class="flex justify-center p-4">
        <i class="pi pi-spin pi-spinner text-3xl" />
      </div>
      <div v-else-if="!coefficientsForm.length" class="empty-state">
        Chưa có nhóm vị trí BHXH nào. Hãy tạo nhóm vị trí BHXH trước khi cấu hình hệ số.
      </div>
      <form v-else @submit.prevent="submitScaleCoefficients">
        <div class="scale-coefficients-editor">
          <!-- Left sidebar: groups list -->
          <div class="scale-groups-sidebar">
            <div
              v-for="(group, idx) in coefficientsForm"
              :key="group.bhxh_position_group_id"
              class="scale-group-item"
              :class="{ active: activeTabGroupIndex === idx }"
              @click="activeTabGroupIndex = idx"
            >
              <div class="font-semibold">{{ group.name }}</div>
              <div class="text-sm opacity-80">{{ group.code }}</div>
            </div>
          </div>

          <!-- Right content: 7 grades for active group -->
          <div class="scale-coefficients-content">
            <div class="scale-group-name">
              Nhóm: {{ coefficientsForm[activeTabGroupIndex].name }} ({{ coefficientsForm[activeTabGroupIndex].code }})
            </div>

            <DataTable :value="coefficientsForm[activeTabGroupIndex].coefficients" responsive-layout="scroll" stripedRows>
              <Column header="Bậc" style="width: 100px">
                <template #body="{ data }">Bậc {{ data.grade_no }}</template>
              </Column>
              <Column header="Hệ số *" style="width: 160px">
                <template #body="{ data }">
                  <InputNumber v-model="data.coefficient" class="w-full" :min="0.01" :min-fraction-digits="2" :max-fraction-digits="4" />
                </template>
              </Column>
              <Column header="Số tháng xét nâng *" style="width: 160px">
                <template #body="{ data }">
                  <InputNumber v-model="data.promotion_months" class="w-full" :min="1" />
                </template>
              </Column>
              <Column header="Tiêu chí xét" style="min-width: 320px">
                <template #body="{ data }">
                  <InputText v-model="data.criteria" class="w-full" />
                </template>
              </Column>
            </DataTable>
          </div>
        </div>

        <div class="dialog-actions">
          <Button type="button" label="Hủy" severity="secondary" text :disabled="submittingCoefficients" @click="coefficientsDialogVisible = false" />
          <Button v-can:edit="'insurance'" type="submit" label="Lưu hệ số" icon="pi pi-check" :loading="submittingCoefficients" />
        </div>
      </form>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'
import jobPositionService, { type JobPositionListItem } from '@/services/jobPositionService'
import insuranceService, {
  type BhxhPositionGroupCatalogRead,
  type BhxhPositionGroupRead,
  type BhxhSenioritySettingCreate,
  type BhxhSenioritySettingRead,
  type BhxhSenioritySettingsRead,
  type BhxhSenioritySettingUpdate,
  type CompanyRegionRead,
  type InsuranceContributionComponentRead,
  type InsuranceEffectiveContributionConfigRead,
  type InsurancePolicyVersionCreate,
  type InsurancePolicyVersionRead,
  type InsurancePolicyVersionUpdate,
  type RegionalMinimumWageCreate,
  type RegionalMinimumWageRead,
  type RegionalMinimumWageUpdate,
  type SalaryScaleRead,
  type SalaryScaleDetailRead,
  type SalaryScaleCoefficientsUpdateInput,
} from '@/services/insuranceService'

type PolicyFormComponent = {
  component_code: string
  component_name: string
  employee_rate_percent_n: number
  employer_rate_percent_n: number
  employer_advances_employee_part: boolean
}

type PositionGroupFormCoefficient = {
  grade_no: number
  coefficient: number
  promotion_months: number
  criteria: string
}

const router = useRouter()
const confirm = useConfirm()
const toast = useToast()

const loading = ref(false)
const submitting = ref(false)
const submittingRegion = ref(false)
const activatingPolicyId = ref<number | null>(null)
const submittingMinimumWage = ref(false)
const submittingSeniority = ref(false)

const policyVersions = ref<InsurancePolicyVersionRead[]>([])
const components = ref<InsuranceContributionComponentRead[]>([])
const companyRegion = ref<CompanyRegionRead>({ current: null, history: [] })
const minimumWages = ref<RegionalMinimumWageRead[]>([])
const senioritySettings = ref<BhxhSenioritySettingsRead>({ current: null, history: [] })
const positionGroupCatalog = ref<BhxhPositionGroupCatalogRead>({ current_scale: null, groups: [] })
const jobPositions = ref<JobPositionListItem[]>([])

const salaryScales = ref<SalaryScaleRead[]>([])
const salaryScaleDialogVisible = ref(false)
const salaryScaleCloneDialogVisible = ref(false)
const editingSalaryScale = ref<SalaryScaleRead | null>(null)
const submittingSalaryScale = ref(false)
const activatingScaleId = ref<number | null>(null)

const cloneForm = ref({
  source_scale_id: null as number | null,
  name: '',
  effective_from: '',
  note: '',
})
const cloneSourceScale = ref<SalaryScaleRead | null>(null)

const coefficientsDialogVisible = ref(false)
const configuringScale = ref<SalaryScaleDetailRead | null>(null)
const submittingCoefficients = ref(false)
const activeTabGroupIndex = ref(0)

const salaryScaleForm = ref({
  name: '',
  effective_from: '',
  note: '',
})

const coefficientsForm = ref<{
  bhxh_position_group_id: number
  code: string
  name: string
  coefficients: {
    grade_no: number
    coefficient: number
    promotion_months: number
    criteria: string
  }[]
}[]>([])

const policyDialogVisible = ref(false)
const regionDialogVisible = ref(false)
const minimumWageDialogVisible = ref(false)
const seniorityDialogVisible = ref(false)
const positionGroupDialogVisible = ref(false)
const editingPolicy = ref<InsurancePolicyVersionRead | null>(null)
const editingMinimumWage = ref<RegionalMinimumWageRead | null>(null)
const editingSeniority = ref<BhxhSenioritySettingRead | null>(null)
const editingPositionGroup = ref<BhxhPositionGroupRead | null>(null)

const policyForm = ref({
  code: '',
  name: '',
  legal_basis_summary: '',
  effective_from: '',
  company_region: 3,
  note: '',
  components: [] as PolicyFormComponent[],
})

const regionForm = ref({
  region: 3,
  effective_from: '',
  note: '',
})

const minimumWageForm = ref({
  decree_number: '',
  region: 3,
  amount: 4_140_000,
  effective_from: '',
  note: '',
})

const seniorityForm = ref({
  raise_month: 1,
  raise_day: 1,
  years_per_grade: 3,
  first_year_cutoff_month: 4,
  first_year_cutoff_day: 30,
  effective_from: '',
  note: '',
})

const positionGroupForm = ref({
  code: '',
  name: '',
  description: '',
  is_active: true,
  position_ids: [] as number[],
  coefficients: [] as PositionGroupFormCoefficient[],
})

const regionOptions = [
  { label: 'Vùng I', value: 1 },
  { label: 'Vùng II', value: 2 },
  { label: 'Vùng III', value: 3 },
  { label: 'Vùng IV', value: 4 },
]

const checkDate = ref('')
const checkResult = ref<InsuranceEffectiveContributionConfigRead | null>(null)
const checkError = ref('')
const checkingDate = ref(false)
const submittingPositionGroup = ref(false)

const activePolicy = computed(() => policyVersions.value.find((item) => item.is_active) ?? null)
const currentRegionMinimumWage = computed(() => {
  const region = companyRegion.value.current?.region
  if (!region) return null
  return minimumWages.value.find((item) => item.region === region && item.effective_to === null) ?? null
})
const currentPositionScale = computed(() => positionGroupCatalog.value.current_scale)
const positionGroups = computed(() => positionGroupCatalog.value.groups)
const positionOptions = computed(() =>
  jobPositions.value
    .filter((item) => item.is_active)
    .sort((a, b) => a.name.localeCompare(b.name, 'vi'))
    .map((item) => ({
      label: `${item.name} (${item.code})${item.department_name ? ` — ${item.department_name}` : ''}`,
      value: item.id,
    })),
)

const _kindOrder = ['bhxh', 'bhyt', 'bhtn']
const _kindLabels: Record<string, string> = {
  bhxh: 'BHXH — Bảo hiểm xã hội',
  bhyt: 'BHYT — Bảo hiểm y tế',
  bhtn: 'BHTN — Bảo hiểm thất nghiệp',
}

const groupedRates = computed(() => {
  if (!activePolicy.value) return []
  const sorted = [...activePolicy.value.components].sort((a, b) => a.sort_order - b.sort_order)
  return _kindOrder
    .map((kind) => {
      const items = sorted.filter((c) => c.insurance_kind.toLowerCase() === kind)
      const empTotal = items.reduce((s: number, c) => s + Number(c.employee_rate_percent), 0)
      const erTotal = items.reduce((s: number, c) => s + Number(c.employer_rate_percent), 0)
      return { kind, label: _kindLabels[kind] ?? kind.toUpperCase(), items, empTotal, erTotal }
    })
    .filter((g) => g.items.length > 0)
})

const grandTotals = computed(() => {
  if (!activePolicy.value) return { emp: 0, er: 0 }
  const comps = activePolicy.value.components
  return {
    emp: comps.reduce((s, c) => s + Number(c.employee_rate_percent), 0),
    er: comps.reduce((s, c) => s + Number(c.employer_rate_percent), 0),
  }
})

function regionLabel(region: number) {
  return regionOptions.find((item) => item.value === region)?.label ?? `Vùng ${region}`
}

function formatDate(value: string | null) {
  if (!value) return '—'
  const [year, month, day] = value.slice(0, 10).split('-')
  return `${day}/${month}/${year}`
}

function formatPercent(value: string | number) {
  const n = Number(value)
  return `${n.toFixed(n % 1 === 0 ? 0 : 2)}%`
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(value)
}

function formatMonthDay(month: number, day: number) {
  return `${String(day).padStart(2, '0')}/${String(month).padStart(2, '0')}`
}

function totalRate(item: { employee_rate_percent: string; employer_rate_percent: string }) {
  return Number(item.employee_rate_percent) + Number(item.employer_rate_percent)
}

function positionGroupMemberNames(group: BhxhPositionGroupRead) {
  return group.members.map((member) => member.job_position_name).join(', ')
}

function positionGroupCoefficientSummary(group: BhxhPositionGroupRead) {
  return group.coefficients.map((item) => `B${item.grade_no}: ${item.coefficient}`).join(' · ')
}

function apiError(error: unknown): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  return 'Đã xảy ra lỗi không xác định'
}

function buildDefaultComponentFormRows() {
  return components.value
    .filter((item) => item.is_active)
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((item) => ({
      component_code: item.code,
      component_name: item.name_vi,
      employee_rate_percent_n: 0,
      employer_rate_percent_n: 0,
      employer_advances_employee_part: false,
    }))
}

function buildDefaultPositionGroupCoefficients(): PositionGroupFormCoefficient[] {
  return Array.from({ length: 7 }, (_, index) => ({
    grade_no: index + 1,
    coefficient: 1,
    promotion_months: 12,
    criteria: '',
  }))
}

async function loadAll() {
  loading.value = true
  try {
    const [componentsResp, policyResp, regionResp, minimumWagesResp, seniorityResp, positionGroupResp, jobPositionResp, salaryScalesResp] = await Promise.all([
      insuranceService.getComponents(),
      insuranceService.getPolicyVersions(),
      insuranceService.getCompanyRegion(),
      insuranceService.getMinimumWages(),
      insuranceService.getSenioritySettings(),
      insuranceService.getPositionGroups(),
      jobPositionService.getList(),
      insuranceService.listSalaryScales(),
    ])
    components.value = componentsResp.data
    policyVersions.value = policyResp.data
    companyRegion.value = regionResp.data
    minimumWages.value = minimumWagesResp.data
    senioritySettings.value = seniorityResp.data
    positionGroupCatalog.value = positionGroupResp.data
    jobPositions.value = jobPositionResp.data
    salaryScales.value = salaryScalesResp.data
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  } finally {
    loading.value = false
  }
}

function resetPolicyForm() {
  policyForm.value = {
    code: '',
    name: '',
    legal_basis_summary: '',
    effective_from: '',
    company_region: companyRegion.value.current?.region ?? 3,
    note: '',
    components: buildDefaultComponentFormRows(),
  }
}

function openCreatePolicyDialog() {
  editingPolicy.value = null
  resetPolicyForm()
  policyDialogVisible.value = true
}

function openCloneDialog() {
  if (!activePolicy.value) return
  editingPolicy.value = null
  policyForm.value = {
    code: '',
    name: `[NHÁP] ${activePolicy.value.name}`,
    legal_basis_summary: activePolicy.value.legal_basis_summary ?? '',
    effective_from: '',
    company_region: activePolicy.value.company_region,
    note: activePolicy.value.note ?? '',
    components: activePolicy.value.components
      .slice()
      .sort((a: { sort_order: number }, b: { sort_order: number }) => a.sort_order - b.sort_order)
      .map((item: typeof activePolicy.value.components[number]) => ({
        component_code: item.component_code,
        component_name: item.component_name,
        employee_rate_percent_n: Number(item.employee_rate_percent),
        employer_rate_percent_n: Number(item.employer_rate_percent),
        employer_advances_employee_part: item.employer_advances_employee_part,
      })),
  }
  policyDialogVisible.value = true
}

function openEditPolicyDialog(policy: InsurancePolicyVersionRead) {
  editingPolicy.value = policy
  policyForm.value = {
    code: policy.code,
    name: policy.name,
    legal_basis_summary: policy.legal_basis_summary ?? '',
    effective_from: policy.effective_from,
    company_region: policy.company_region,
    note: policy.note ?? '',
    components: policy.components
      .slice()
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((item) => ({
        component_code: item.component_code,
        component_name: item.component_name,
        employee_rate_percent_n: Number(item.employee_rate_percent),
        employer_rate_percent_n: Number(item.employer_rate_percent),
        employer_advances_employee_part: item.employer_advances_employee_part,
      })),
  }
  policyDialogVisible.value = true
}

function openRegionDialog() {
  regionForm.value = {
    region: companyRegion.value.current?.region ?? 3,
    effective_from: '',
    note: '',
  }
  regionDialogVisible.value = true
}

function resetMinimumWageForm() {
  minimumWageForm.value = {
    decree_number: '',
    region: companyRegion.value.current?.region ?? 3,
    amount: currentRegionMinimumWage.value?.amount ?? 4_140_000,
    effective_from: '',
    note: '',
  }
}

function openCreateMinimumWageDialog() {
  editingMinimumWage.value = null
  resetMinimumWageForm()
  minimumWageDialogVisible.value = true
}

function openEditMinimumWageDialog(item: RegionalMinimumWageRead) {
  editingMinimumWage.value = item
  minimumWageForm.value = {
    decree_number: item.decree_number,
    region: item.region,
    amount: item.amount,
    effective_from: item.effective_from,
    note: item.note ?? '',
  }
  minimumWageDialogVisible.value = true
}

function resetSeniorityForm() {
  seniorityForm.value = {
    raise_month: senioritySettings.value.current?.raise_month ?? 1,
    raise_day: senioritySettings.value.current?.raise_day ?? 1,
    years_per_grade: senioritySettings.value.current?.years_per_grade ?? 3,
    first_year_cutoff_month: senioritySettings.value.current?.first_year_cutoff_month ?? 4,
    first_year_cutoff_day: senioritySettings.value.current?.first_year_cutoff_day ?? 30,
    effective_from: '',
    note: '',
  }
}

function openCreateSeniorityDialog() {
  editingSeniority.value = null
  resetSeniorityForm()
  seniorityDialogVisible.value = true
}

function openEditSeniorityDialog(item: BhxhSenioritySettingRead) {
  editingSeniority.value = item
  seniorityForm.value = {
    raise_month: item.raise_month,
    raise_day: item.raise_day,
    years_per_grade: item.years_per_grade,
    first_year_cutoff_month: item.first_year_cutoff_month,
    first_year_cutoff_day: item.first_year_cutoff_day,
    effective_from: item.effective_from,
    note: item.note ?? '',
  }
  seniorityDialogVisible.value = true
}

function resetPositionGroupForm() {
  positionGroupForm.value = {
    code: '',
    name: '',
    description: '',
    is_active: true,
    position_ids: [],
    coefficients: buildDefaultPositionGroupCoefficients(),
  }
}

function openCreatePositionGroupDialog() {
  editingPositionGroup.value = null
  resetPositionGroupForm()
  positionGroupDialogVisible.value = true
}

function openEditPositionGroupDialog(item: BhxhPositionGroupRead) {
  editingPositionGroup.value = item
  positionGroupForm.value = {
    code: item.code,
    name: item.name,
    description: item.description ?? '',
    is_active: item.is_active,
    position_ids: item.members.map((member) => member.job_position_id),
    coefficients: item.coefficients.map((coefficient) => ({
      grade_no: coefficient.grade_no,
      coefficient: Number(coefficient.coefficient),
      promotion_months: coefficient.promotion_months,
      criteria: coefficient.criteria ?? '',
    })),
  }
  positionGroupDialogVisible.value = true
}

async function submitPolicy() {
  submitting.value = true
  try {
    const componentsPayload = policyForm.value.components.map((item) => ({
      component_code: item.component_code,
      employee_rate_percent: String(item.employee_rate_percent_n ?? 0),
      employer_rate_percent: String(item.employer_rate_percent_n ?? 0),
      employer_advances_employee_part: item.employer_advances_employee_part,
    }))

    if (editingPolicy.value) {
      const payload: InsurancePolicyVersionUpdate = {
        name: policyForm.value.name,
        legal_basis_summary: policyForm.value.legal_basis_summary || null,
        effective_from: policyForm.value.effective_from,
        company_region: policyForm.value.company_region,
        note: policyForm.value.note || null,
        components: componentsPayload,
      }
      await insuranceService.updatePolicyVersion(editingPolicy.value.id, payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật policy version', life: 3000 })
    } else {
      const payload: InsurancePolicyVersionCreate = {
        code: policyForm.value.code,
        name: policyForm.value.name,
        legal_basis_summary: policyForm.value.legal_basis_summary || null,
        effective_from: policyForm.value.effective_from,
        company_region: policyForm.value.company_region,
        note: policyForm.value.note || null,
        components: componentsPayload,
      }
      await insuranceService.createPolicyVersion(payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã tạo policy version mới', life: 3000 })
    }

    policyDialogVisible.value = false
    await loadAll()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  } finally {
    submitting.value = false
  }
}

async function activatePolicy(policy: InsurancePolicyVersionRead) {
  activatingPolicyId.value = policy.id
  try {
    await insuranceService.activatePolicyVersion(policy.id)
    toast.add({ severity: 'success', summary: 'Thành công', detail: `Đã activate ${policy.code}`, life: 3000 })
    await loadAll()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  } finally {
    activatingPolicyId.value = null
  }
}

function confirmDeletePolicy(policy: InsurancePolicyVersionRead) {
  confirm.require({
    message: `Hủy nháp policy ${policy.code}? Thao tác này sẽ xóa toàn bộ component rates của bản nháp này.`,
    header: 'Xác nhận hủy nháp',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Không',
      severity: 'secondary',
      outlined: true,
    },
    acceptProps: {
      label: 'Hủy nháp',
      severity: 'danger',
    },
    accept: async () => {
      try {
        await insuranceService.deletePolicyVersion(policy.id)
        toast.add({ severity: 'success', summary: 'Thành công', detail: `Đã hủy nháp ${policy.code}`, life: 3000 })
        await loadAll()
      } catch (error) {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
      }
    },
  })
}

async function checkEffectiveConfig() {
  if (!checkDate.value) return
  checkingDate.value = true
  checkResult.value = null
  checkError.value = ''
  try {
    const resp = await insuranceService.getEffectiveConfig(checkDate.value)
    checkResult.value = resp.data
  } catch (error) {
    const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
    checkError.value = typeof detail === 'string' ? detail : 'Không tìm thấy cấu hình cho ngày này'
  } finally {
    checkingDate.value = false
  }
}

async function submitRegion() {
  submittingRegion.value = true
  try {
    await insuranceService.updateCompanyRegion({
      region: regionForm.value.region,
      effective_from: regionForm.value.effective_from,
      note: regionForm.value.note || null,
    })
    toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật vùng BHXH công ty', life: 3000 })
    regionDialogVisible.value = false
    await loadAll()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  } finally {
    submittingRegion.value = false
  }
}

async function submitMinimumWage() {
  submittingMinimumWage.value = true
  try {
    if (editingMinimumWage.value) {
      const payload: RegionalMinimumWageUpdate = {
        decree_number: minimumWageForm.value.decree_number,
        amount: minimumWageForm.value.amount,
        note: minimumWageForm.value.note || null,
      }
      await insuranceService.updateMinimumWage(editingMinimumWage.value.id, payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật lương tối thiểu vùng', life: 3000 })
    } else {
      const payload: RegionalMinimumWageCreate = {
        decree_number: minimumWageForm.value.decree_number,
        region: minimumWageForm.value.region,
        amount: minimumWageForm.value.amount,
        effective_from: minimumWageForm.value.effective_from,
        note: minimumWageForm.value.note || null,
      }
      await insuranceService.createMinimumWage(payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã thêm cấu hình lương tối thiểu vùng', life: 3000 })
    }
    minimumWageDialogVisible.value = false
    await loadAll()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  } finally {
    submittingMinimumWage.value = false
  }
}

function confirmDeleteMinimumWage(item: RegionalMinimumWageRead) {
  confirm.require({
    message: `Xóa cấu hình LTTV ${regionLabel(item.region)} · ${formatDate(item.effective_from)}?`,
    header: 'Xác nhận xóa LTTV',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Không',
      severity: 'secondary',
      outlined: true,
    },
    acceptProps: {
      label: 'Xóa',
      severity: 'danger',
    },
    accept: async () => {
      try {
        await insuranceService.deleteMinimumWage(item.id)
        toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã xóa cấu hình lương tối thiểu vùng', life: 3000 })
        await loadAll()
      } catch (error) {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
      }
    },
  })
}

async function submitSeniority() {
  submittingSeniority.value = true
  try {
    if (editingSeniority.value) {
      const payload: BhxhSenioritySettingUpdate = {
        raise_month: seniorityForm.value.raise_month,
        raise_day: seniorityForm.value.raise_day,
        years_per_grade: seniorityForm.value.years_per_grade,
        first_year_cutoff_month: seniorityForm.value.first_year_cutoff_month,
        first_year_cutoff_day: seniorityForm.value.first_year_cutoff_day,
        note: seniorityForm.value.note || null,
      }
      await insuranceService.updateSenioritySetting(editingSeniority.value.id, payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật rule thâm niên BHXH', life: 3000 })
    } else {
      const payload: BhxhSenioritySettingCreate = {
        raise_month: seniorityForm.value.raise_month,
        raise_day: seniorityForm.value.raise_day,
        years_per_grade: seniorityForm.value.years_per_grade,
        first_year_cutoff_month: seniorityForm.value.first_year_cutoff_month,
        first_year_cutoff_day: seniorityForm.value.first_year_cutoff_day,
        effective_from: seniorityForm.value.effective_from,
        note: seniorityForm.value.note || null,
      }
      await insuranceService.createSenioritySetting(payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã thêm rule thâm niên BHXH', life: 3000 })
    }
    seniorityDialogVisible.value = false
    await loadAll()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  } finally {
    submittingSeniority.value = false
  }
}

function confirmDeleteSeniority(item: BhxhSenioritySettingRead) {
  confirm.require({
    message: `Xóa rule thâm niên hiệu lực từ ${formatDate(item.effective_from)}?`,
    header: 'Xác nhận xóa rule thâm niên',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Không',
      severity: 'secondary',
      outlined: true,
    },
    acceptProps: {
      label: 'Xóa',
      severity: 'danger',
    },
    accept: async () => {
      try {
        await insuranceService.deleteSenioritySetting(item.id)
        toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã xóa rule thâm niên BHXH', life: 3000 })
        await loadAll()
      } catch (error) {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
      }
    },
  })
}

async function submitPositionGroup() {
  submittingPositionGroup.value = true
  try {
    const payload = {
      code: positionGroupForm.value.code,
      name: positionGroupForm.value.name,
      description: positionGroupForm.value.description || null,
      is_active: positionGroupForm.value.is_active,
      position_ids: positionGroupForm.value.position_ids,
      coefficients: positionGroupForm.value.coefficients.map((item) => ({
        grade_no: item.grade_no,
        coefficient: String(item.coefficient),
        promotion_months: item.promotion_months,
        criteria: item.criteria || null,
      })),
    }
    if (editingPositionGroup.value) {
      await insuranceService.updatePositionGroup(editingPositionGroup.value.id, payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật nhóm vị trí BHXH', life: 3000 })
    } else {
      await insuranceService.createPositionGroup(payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã thêm nhóm vị trí BHXH', life: 3000 })
    }
    positionGroupDialogVisible.value = false
    await loadAll()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  } finally {
    submittingPositionGroup.value = false
  }
}

function confirmDeletePositionGroup(item: BhxhPositionGroupRead) {
  confirm.require({
    message: `Xóa nhóm vị trí BHXH ${item.code}? Thao tác này sẽ xóa mapping vị trí và 7 bậc hệ số của nhóm này trong scale hiện hành.`,
    header: 'Xác nhận xóa nhóm vị trí BHXH',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Không',
      severity: 'secondary',
      outlined: true,
    },
    acceptProps: {
      label: 'Xóa',
      severity: 'danger',
    },
    accept: async () => {
      try {
        await insuranceService.deletePositionGroup(item.id)
        toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã xóa nhóm vị trí BHXH', life: 3000 })
        await loadAll()
      } catch (error) {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
      }
    },
  })
}

// --- Salary Scales Functions ---

function resetSalaryScaleForm() {
  salaryScaleForm.value = {
    name: '',
    effective_from: '',
    note: '',
  }
}

function openCreateSalaryScaleDialog() {
  editingSalaryScale.value = null
  resetSalaryScaleForm()
  salaryScaleDialogVisible.value = true
}

function openEditSalaryScaleDialog(scale: SalaryScaleRead) {
  editingSalaryScale.value = scale
  salaryScaleForm.value = {
    name: scale.name,
    effective_from: scale.effective_from,
    note: scale.note ?? '',
  }
  salaryScaleDialogVisible.value = true
}

async function submitSalaryScale() {
  submittingSalaryScale.value = true
  try {
    if (editingSalaryScale.value) {
      await insuranceService.updateSalaryScale(editingSalaryScale.value.id, {
        name: salaryScaleForm.value.name,
        effective_from: salaryScaleForm.value.effective_from,
        note: salaryScaleForm.value.note || null,
      })
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật thông tin thang bảng lương', life: 3000 })
    } else {
      await insuranceService.createSalaryScale({
        name: salaryScaleForm.value.name,
        effective_from: salaryScaleForm.value.effective_from,
        note: salaryScaleForm.value.note || null,
      })
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã tạo thang bảng lương nháp mới', life: 3000 })
    }
    salaryScaleDialogVisible.value = false
    await loadAll()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  } finally {
    submittingSalaryScale.value = false
  }
}

async function activateSalaryScale(scale: SalaryScaleRead) {
  confirm.require({
    message: `Kích hoạt thang bảng lương "${scale.name}" hiệu lực từ ${formatDate(scale.effective_from)}? Thang bảng lương hiện hành khác sẽ tự động hết hiệu lực vào ngày hôm trước.`,
    header: 'Xác nhận kích hoạt',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Hủy',
      severity: 'secondary',
      outlined: true,
    },
    acceptProps: {
      label: 'Kích hoạt',
      severity: 'success',
    },
    accept: async () => {
      activatingScaleId.value = scale.id
      try {
        await insuranceService.activateSalaryScale(scale.id)
        toast.add({ severity: 'success', summary: 'Thành công', detail: `Đã kích hoạt thang bảng lương "${scale.name}"`, life: 3000 })
        await loadAll()
      } catch (error) {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
      } finally {
        activatingScaleId.value = null
      }
    },
  })
}

function openCloneSalaryScaleDialog(scale: SalaryScaleRead) {
  cloneSourceScale.value = scale
  cloneForm.value = {
    source_scale_id: scale.id,
    name: `[Bản sao] ${scale.name}`,
    effective_from: '',
    note: `Sao chép hệ số từ ${scale.name}`,
  }
  salaryScaleCloneDialogVisible.value = true
}

async function submitCloneSalaryScale() {
  if (!cloneForm.value.source_scale_id) return
  submittingSalaryScale.value = true
  try {
    const createResp = await insuranceService.createSalaryScale({
      name: cloneForm.value.name,
      effective_from: cloneForm.value.effective_from,
      note: cloneForm.value.note || null,
    })
    await insuranceService.cloneSalaryScale(createResp.data.id, cloneForm.value.source_scale_id)
    toast.add({ severity: 'success', summary: 'Thành công', detail: 'Nhân bản thang bảng lương và hệ số thành công', life: 3000 })
    salaryScaleCloneDialogVisible.value = false
    await loadAll()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  } finally {
    submittingSalaryScale.value = false
  }
}

function confirmDeleteSalaryScale(scale: SalaryScaleRead) {
  confirm.require({
    message: `Xóa thang bảng lương "${scale.name}"? Thao tác này sẽ xóa toàn bộ hệ số cấu hình của thang lương này.`,
    header: 'Xác nhận xóa thang bảng lương',
    icon: 'pi pi-trash',
    rejectProps: {
      label: 'Không',
      severity: 'secondary',
      outlined: true,
    },
    acceptProps: {
      label: 'Xóa',
      severity: 'danger',
    },
    accept: async () => {
      try {
        await insuranceService.deleteSalaryScale(scale.id)
        toast.add({ severity: 'success', summary: 'Thành công', detail: `Đã xóa thang bảng lương "${scale.name}"`, life: 3000 })
        await loadAll()
      } catch (error) {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
      }
    },
  })
}

async function openCoefficientsDialog(scale: SalaryScaleRead) {
  configuringScale.value = null
  try {
    const resp = await insuranceService.getSalaryScaleDetail(scale.id)
    configuringScale.value = resp.data
    coefficientsForm.value = resp.data.groups.map(group => {
      const coeffs = Array.from({ length: 7 }, (_, i) => {
        const grade = i + 1
        const existing = group.coefficients.find(c => c.grade_no === grade)
        return {
          grade_no: grade,
          coefficient: existing ? Number(existing.coefficient) : 1.0,
          promotion_months: existing ? existing.promotion_months : 12,
          criteria: existing?.criteria || '',
        }
      })
      return {
        bhxh_position_group_id: group.id,
        code: group.code,
        name: group.name,
        coefficients: coeffs,
      }
    })
    activeTabGroupIndex.value = 0
    coefficientsDialogVisible.value = true
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  }
}

async function submitScaleCoefficients() {
  if (!configuringScale.value) return
  submittingCoefficients.value = true
  try {
    const payload: SalaryScaleCoefficientsUpdateInput = {
      groups: coefficientsForm.value.map(group => ({
        bhxh_position_group_id: group.bhxh_position_group_id,
        coefficients: group.coefficients.map(c => ({
          grade_no: c.grade_no,
          coefficient: String(c.coefficient),
          promotion_months: c.promotion_months,
          criteria: c.criteria || null
        }))
      }))
    }
    await insuranceService.updateScaleCoefficients(configuringScale.value.id, payload)
    toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật hệ số thang bảng lương', life: 3000 })
    coefficientsDialogVisible.value = false
    await loadAll()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  } finally {
    submittingCoefficients.value = false
  }
}

onMounted(async () => {
  await loadAll()
})
</script>

<style scoped lang="scss">
.scale-coefficients-editor {
  display: flex;
  gap: 1.5rem;
  min-height: 400px;
}

.scale-groups-sidebar {
  width: 260px;
  border-right: 1px solid var(--p-content-border-color);
  padding-right: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 480px;
  overflow-y: auto;
}

.scale-group-item {
  padding: 0.75rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;

  &:hover {
    background: color-mix(in srgb, var(--p-primary-50) 40%, var(--p-content-background));
  }

  &.active {
    background: var(--p-primary-50);
    border-color: var(--p-primary-200);
    color: var(--p-primary-900);
    font-weight: 600;
  }
}

.scale-coefficients-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-height: 480px;
  overflow-y: auto;
}

.scale-group-name {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--p-text-color);
}
</style>
