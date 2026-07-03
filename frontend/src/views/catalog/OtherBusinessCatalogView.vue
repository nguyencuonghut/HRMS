<template>
  <div class="other-business-catalog">
    <section class="hero-panel">
      <div class="hero-copy">
        <span class="eyebrow">Operations Catalog Workspace</span>
        <h1>Danh mục nghiệp vụ khác</h1>
        <p class="hero-text">
          Chuẩn hóa danh mục nền cho hồ sơ nhân sự, nghỉ phép và hợp đồng lao động; đồng thời
          chuẩn bị metadata cho mẫu hợp đồng, phụ lục và cơ chế auto-fill ở phase sau.
        </p>
        <div class="hero-actions">
          <Button v-can:create="'catalog'" :label="primaryCreateLabel" icon="pi pi-plus" @click="openCreateForActiveTab" />
          <Button label="Về tổng quan danh mục" icon="pi pi-th-large" severity="secondary" outlined @click="router.push('/catalog')" />
          <Button label="Xem nhật ký hệ thống" icon="pi pi-list" severity="contrast" outlined @click="router.push('/admin/audit-logs')" />
        </div>
      </div>

      <div class="hero-side">
        <article class="signal-card">
          <div class="signal-head">
            <span class="signal-label">Nhóm đang quản trị</span>
            <Tag :value="activeTabLabel" severity="info" rounded />
          </div>
          <p class="signal-value">{{ activeHeadline }}</p>
          <p class="signal-note">{{ activeSubline }}</p>
        </article>

        <article class="signal-card muted">
          <div class="signal-head">
            <span class="signal-label">Điểm dùng lại</span>
          </div>
          <ul class="scope-list">
            <li>Danh mục nhân thân cho hồ sơ nhân sự</li>
            <li>Loại nghỉ phép và ngân hàng cho vận hành HR</li>
            <li>Kỹ năng, chứng chỉ cho hồ sơ năng lực</li>
            <li>Checklist hồ sơ pháp lý để HR chủ động thay đổi về sau</li>
            <li>Metadata mẫu hợp đồng/phụ lục cho phase auto-fill</li>
          </ul>
        </article>
      </div>
    </section>

    <section class="stats-grid">
      <article class="stat-card">
        <div class="stat-icon tone-teal"><i class="pi pi-file-edit" /></div>
        <div class="stat-body">
          <span class="stat-label">Loại hợp đồng</span>
          <strong class="stat-value">{{ formatNumber(contractCategoryState.total) }}</strong>
          <span class="stat-footnote">HĐLĐ và nhóm phụ lục đang có</span>
        </div>
      </article>
      <article class="stat-card">
        <div class="stat-icon tone-amber"><i class="pi pi-id-card" /></div>
        <div class="stat-body">
          <span class="stat-label">Danh mục nhân thân</span>
          <strong class="stat-value">{{ formatNumber(nationalityState.total + ethnicityState.total + religionState.total) }}</strong>
          <span class="stat-footnote">Quốc tịch, dân tộc, tôn giáo</span>
        </div>
      </article>
      <article class="stat-card">
        <div class="stat-icon tone-slate"><i class="pi pi-briefcase" /></div>
        <div class="stat-body">
          <span class="stat-label">Năng lực & chứng chỉ</span>
          <strong class="stat-value">{{ formatNumber(skillState.total + certificateState.total) }}</strong>
          <span class="stat-footnote">Kỹ năng và chứng chỉ phục vụ nhân sự</span>
        </div>
      </article>
      <article class="stat-card">
        <div class="stat-icon tone-rose"><i class="pi pi-file-word" /></div>
        <div class="stat-body">
          <span class="stat-label">Mẫu hợp đồng</span>
          <strong class="stat-value">{{ formatNumber(templateState.total) }}</strong>
          <span class="stat-footnote">Metadata mẫu và placeholder đã khai báo</span>
        </div>
      </article>
    </section>

    <div v-if="errorBanner" class="status-banner danger">
      <i class="pi pi-exclamation-triangle" />
      <span>{{ errorBanner }}</span>
    </div>

    <div class="card workspace-card">
      <Tabs v-model:value="activeTab">
        <div class="workspace-head">
          <div>
            <span class="section-kicker">Quản trị trực tiếp</span>
            <h2>{{ activeHeadline }}</h2>
          </div>
          <div class="tabs-scroll">
            <TabList>
              <Tab value="contracts">Loại hợp đồng</Tab>
              <Tab value="identity">Nhân thân</Tab>
              <Tab value="banks">Ngân hàng</Tab>
              <Tab value="competency">Kỹ năng & chứng chỉ</Tab>
              <Tab value="leaves">Loại nghỉ phép</Tab>
              <Tab value="documentChecklist">Checklist hồ sơ</Tab>
              <Tab value="templates">Mẫu hợp đồng</Tab>
            </TabList>
          </div>
        </div>

        <TabPanels>
          <TabPanel value="contracts">
            <div class="toolbar">
              <Select v-model="contractCategoryState.isActive" :options="activeFilterOptions" option-label="label" option-value="value" placeholder="Tất cả trạng thái" show-clear filter class="toolbar-filter" @change="loadContractCategories" />
              <Select v-model="contractCategoryState.documentKind" :options="documentKindOptions" option-label="label" option-value="value" placeholder="Tất cả nhóm" show-clear filter class="toolbar-filter" @change="loadContractCategories" />
              <IconField class="toolbar-search">
                <InputIcon class="pi pi-search" />
                <InputText v-model="contractCategoryState.keyword" class="w-full" placeholder="Tìm theo mã hoặc tên loại hợp đồng..." @input="debounce(loadContractCategories)" />
              </IconField>
              <Button v-can:create="'catalog'" icon="pi pi-plus" severity="secondary" text rounded @click="openCreateContractCategory" />
              <Button icon="pi pi-refresh" severity="secondary" text rounded :loading="contractCategoryState.loading" @click="loadContractCategories" />
            </div>

            <DataTable :value="contractCategoryState.items" :loading="contractCategoryState.loading" stripedRows paginator lazy responsive-layout="scroll"
              :rows="contractCategoryState.pageSize" :first="(contractCategoryState.page - 1) * contractCategoryState.pageSize"
              :total-records="contractCategoryState.total" :rows-per-page-options="[10,20,50]" paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
              current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
              @page="onPage(contractCategoryState, $event, loadContractCategories)">
              <template #empty><div class="empty-state"><i class="pi pi-inbox" /><span>Không có dữ liệu loại hợp đồng</span></div></template>
              <Column field="name" header="Tên loại" style="min-width: 260px" />
              <Column field="code" header="Mã" style="width: 170px" />
              <Column field="document_kind" header="Nhóm" style="width: 170px"><template #body="{ data }">{{ documentKindLabel(data.document_kind) }}</template></Column>
              <Column field="legal_contract_type" header="Pháp lý" style="width: 170px"><template #body="{ data }">{{ legalTypeLabel(data.legal_contract_type) }}</template></Column>
              <Column field="is_active" header="Trạng thái" style="width: 120px"><template #body="{ data }"><Tag :value="data.is_active ? 'Hoạt động' : 'Đã khóa'" :severity="data.is_active ? 'success' : 'danger'" /></template></Column>
              <Column header="" style="width: 110px"><template #body="{ data }"><div class="action-cell"><Button v-can:edit="'catalog'" icon="pi pi-pencil" severity="secondary" text rounded size="small" @click="openEditContractCategory(data)" /><Button v-can:delete="'catalog'" icon="pi pi-trash" severity="danger" text rounded size="small" @click="confirmDelete('contractCategory', data)" /></div></template></Column>
            </DataTable>
          </TabPanel>

          <TabPanel value="identity">
            <div class="triple-grid">
              <article class="mini-card">
                <div class="mini-head">
                  <div><span class="section-kicker">Nhân thân</span><h3>Quốc tịch</h3></div>
                  <Button v-can:create="'catalog'" icon="pi pi-plus" text rounded @click="openCreateIdentity('nationality')" />
                </div>
                <div class="toolbar compact">
                  <InputText v-model="nationalityState.keyword" class="w-full" placeholder="Tìm quốc tịch..." @input="debounce(loadNationalities)" />
                </div>
                <DataTable :value="nationalityState.items" :loading="nationalityState.loading" stripedRows responsive-layout="scroll">
                  <template #empty><div class="empty-state compact"><i class="pi pi-inbox" /><span>Không có dữ liệu</span></div></template>
                  <Column field="name" header="Tên" />
                  <Column field="code" header="Mã" style="width: 90px" />
                  <Column header="" style="width: 90px"><template #body="{ data }"><div class="action-cell"><Button v-can:edit="'catalog'" icon="pi pi-pencil" text rounded size="small" @click="openEditIdentity('nationality', data)" /><Button v-can:delete="'catalog'" icon="pi pi-trash" severity="danger" text rounded size="small" @click="confirmDelete('nationality', data)" /></div></template></Column>
                </DataTable>
              </article>

              <article class="mini-card">
                <div class="mini-head">
                  <div><span class="section-kicker">Nhân thân</span><h3>Dân tộc</h3></div>
                  <Button v-can:create="'catalog'" icon="pi pi-plus" text rounded @click="openCreateIdentity('ethnicity')" />
                </div>
                <div class="toolbar compact">
                  <InputText v-model="ethnicityState.keyword" class="w-full" placeholder="Tìm dân tộc..." @input="debounce(loadEthnicities)" />
                </div>
                <DataTable :value="ethnicityState.items" :loading="ethnicityState.loading" stripedRows responsive-layout="scroll">
                  <template #empty><div class="empty-state compact"><i class="pi pi-inbox" /><span>Không có dữ liệu</span></div></template>
                  <Column field="name" header="Tên" />
                  <Column field="code" header="Mã" style="width: 90px" />
                  <Column header="" style="width: 90px"><template #body="{ data }"><div class="action-cell"><Button v-can:edit="'catalog'" icon="pi pi-pencil" text rounded size="small" @click="openEditIdentity('ethnicity', data)" /><Button v-can:delete="'catalog'" icon="pi pi-trash" severity="danger" text rounded size="small" @click="confirmDelete('ethnicity', data)" /></div></template></Column>
                </DataTable>
              </article>

              <article class="mini-card">
                <div class="mini-head">
                  <div><span class="section-kicker">Nhân thân</span><h3>Tôn giáo</h3></div>
                  <Button v-can:create="'catalog'" icon="pi pi-plus" text rounded @click="openCreateIdentity('religion')" />
                </div>
                <div class="toolbar compact">
                  <InputText v-model="religionState.keyword" class="w-full" placeholder="Tìm tôn giáo..." @input="debounce(loadReligions)" />
                </div>
                <DataTable :value="religionState.items" :loading="religionState.loading" stripedRows responsive-layout="scroll">
                  <template #empty><div class="empty-state compact"><i class="pi pi-inbox" /><span>Không có dữ liệu</span></div></template>
                  <Column field="name" header="Tên" />
                  <Column field="code" header="Mã" style="width: 90px" />
                  <Column header="" style="width: 90px"><template #body="{ data }"><div class="action-cell"><Button v-can:edit="'catalog'" icon="pi pi-pencil" text rounded size="small" @click="openEditIdentity('religion', data)" /><Button v-can:delete="'catalog'" icon="pi pi-trash" severity="danger" text rounded size="small" @click="confirmDelete('religion', data)" /></div></template></Column>
                </DataTable>
              </article>
            </div>
          </TabPanel>

          <TabPanel value="banks">
            <div class="toolbar">
              <Select v-model="bankState.isActive" :options="activeFilterOptions" option-label="label" option-value="value" placeholder="Tất cả trạng thái" show-clear filter class="toolbar-filter" @change="loadBanks" />
              <IconField class="toolbar-search">
                <InputIcon class="pi pi-search" />
                <InputText v-model="bankState.keyword" class="w-full" placeholder="Tìm theo tên, mã, short name, BIN..." @input="debounce(loadBanks)" />
              </IconField>
              <Button v-can:create="'catalog'" icon="pi pi-plus" severity="secondary" text rounded @click="openCreateBank" />
              <Button icon="pi pi-refresh" severity="secondary" text rounded :loading="bankState.loading" @click="loadBanks" />
            </div>
            <DataTable :value="bankState.items" :loading="bankState.loading" stripedRows paginator lazy responsive-layout="scroll"
              :rows="bankState.pageSize" :first="(bankState.page - 1) * bankState.pageSize" :total-records="bankState.total" :rows-per-page-options="[10,20,50]"
              paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
              current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
              @page="onPage(bankState, $event, loadBanks)">
              <template #empty><div class="empty-state"><i class="pi pi-inbox" /><span>Không có dữ liệu ngân hàng</span></div></template>
              <Column field="name" header="Ngân hàng" style="min-width: 250px"><template #body="{ data }"><div class="stacked-cell"><strong>{{ data.name }}</strong><small>{{ data.short_name || '—' }}</small></div></template></Column>
              <Column field="code" header="Mã" style="width: 120px" />
              <Column field="bin_code" header="BIN" style="width: 110px"><template #body="{ data }">{{ data.bin_code || '—' }}</template></Column>
              <Column field="swift_code" header="SWIFT" style="width: 120px"><template #body="{ data }">{{ data.swift_code || '—' }}</template></Column>
              <Column field="is_active" header="Trạng thái" style="width: 120px"><template #body="{ data }"><Tag :value="data.is_active ? 'Hoạt động' : 'Đã khóa'" :severity="data.is_active ? 'success' : 'danger'" /></template></Column>
              <Column header="" style="width: 110px"><template #body="{ data }"><div class="action-cell"><Button v-can:edit="'catalog'" icon="pi pi-pencil" text rounded size="small" @click="openEditBank(data)" /><Button v-can:delete="'catalog'" icon="pi pi-trash" severity="danger" text rounded size="small" @click="confirmDelete('bank', data)" /></div></template></Column>
            </DataTable>
          </TabPanel>

          <TabPanel value="competency">
            <div class="dual-grid">
              <article class="mini-card">
                <div class="mini-head">
                  <div><span class="section-kicker">Năng lực</span><h3>Kỹ năng</h3></div>
                  <Button v-can:create="'catalog'" icon="pi pi-plus" text rounded @click="openCreateSkill" />
                </div>
                <div class="toolbar compact">
                  <InputText v-model="skillState.keyword" class="w-full" placeholder="Tìm kỹ năng..." @input="debounce(loadSkills)" />
                </div>
                <DataTable :value="skillState.items" :loading="skillState.loading" stripedRows responsive-layout="scroll">
                  <template #empty><div class="empty-state compact"><i class="pi pi-inbox" /><span>Không có dữ liệu</span></div></template>
                  <Column field="name" header="Tên" />
                  <Column field="skill_group" header="Nhóm" style="width: 130px"><template #body="{ data }">{{ data.skill_group || '—' }}</template></Column>
                  <Column header="" style="width: 90px"><template #body="{ data }"><div class="action-cell"><Button v-can:edit="'catalog'" icon="pi pi-pencil" text rounded size="small" @click="openEditSkill(data)" /><Button v-can:delete="'catalog'" icon="pi pi-trash" severity="danger" text rounded size="small" @click="confirmDelete('skill', data)" /></div></template></Column>
                </DataTable>
              </article>

              <article class="mini-card">
                <div class="mini-head">
                  <div><span class="section-kicker">Năng lực</span><h3>Chứng chỉ</h3></div>
                  <Button v-can:create="'catalog'" icon="pi pi-plus" text rounded @click="openCreateCertificate" />
                </div>
                <div class="toolbar compact">
                  <InputText v-model="certificateState.keyword" class="w-full" placeholder="Tìm chứng chỉ..." @input="debounce(loadCertificates)" />
                </div>
                <DataTable :value="certificateState.items" :loading="certificateState.loading" stripedRows responsive-layout="scroll">
                  <template #empty><div class="empty-state compact"><i class="pi pi-inbox" /><span>Không có dữ liệu</span></div></template>
                  <Column field="name" header="Tên" />
                  <Column field="certificate_group" header="Nhóm" style="width: 130px"><template #body="{ data }">{{ data.certificate_group || '—' }}</template></Column>
                  <Column header="" style="width: 90px"><template #body="{ data }"><div class="action-cell"><Button v-can:edit="'catalog'" icon="pi pi-pencil" text rounded size="small" @click="openEditCertificate(data)" /><Button v-can:delete="'catalog'" icon="pi pi-trash" severity="danger" text rounded size="small" @click="confirmDelete('certificate', data)" /></div></template></Column>
                </DataTable>
              </article>
            </div>
          </TabPanel>

          <TabPanel value="leaves">
            <div class="toolbar">
              <Select v-model="leaveTypeState.isActive" :options="activeFilterOptions" option-label="label" option-value="value" placeholder="Tất cả trạng thái" show-clear filter class="toolbar-filter" @change="loadLeaveTypes" />
              <IconField class="toolbar-search">
                <InputIcon class="pi pi-search" />
                <InputText v-model="leaveTypeState.keyword" class="w-full" placeholder="Tìm loại nghỉ phép..." @input="debounce(loadLeaveTypes)" />
              </IconField>
              <Button v-can:create="'catalog'" icon="pi pi-plus" severity="secondary" text rounded @click="openCreateLeaveType" />
              <Button icon="pi pi-refresh" severity="secondary" text rounded :loading="leaveTypeState.loading" @click="loadLeaveTypes" />
            </div>
            <DataTable :value="leaveTypeState.items" :loading="leaveTypeState.loading" stripedRows paginator lazy responsive-layout="scroll"
              :rows="leaveTypeState.pageSize" :first="(leaveTypeState.page - 1) * leaveTypeState.pageSize" :total-records="leaveTypeState.total" :rows-per-page-options="[10,20,50]"
              paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
              current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
              @page="onPage(leaveTypeState, $event, loadLeaveTypes)">
              <template #empty><div class="empty-state"><i class="pi pi-inbox" /><span>Không có dữ liệu loại nghỉ</span></div></template>
              <Column field="name" header="Tên loại nghỉ" style="min-width: 220px" />
              <Column field="code" header="Mã" style="width: 150px" />
              <Column field="is_paid_leave" header="Hưởng lương" style="width: 115px"><template #body="{ data }"><Tag :value="data.is_paid_leave ? 'Có' : 'Không'" :severity="data.is_paid_leave ? 'success' : 'contrast'" /></template></Column>
              <Column header="Quy tắc" style="min-width:210px;">
                <template #body="{ data }">
                  <div class="leave-rule-chips">
                    <Tag v-if="data.allow_half_day"         value="½ ngày"      severity="info" />
                    <Tag v-if="data.carryover_allowed"      value="Chuyển phép" severity="warning" />
                    <Tag v-if="!data.count_public_holidays" value="Trừ ngày lễ" severity="secondary" />
                    <span v-if="data.max_days_per_year"   class="rule-limit">Max {{ data.max_days_per_year }} ng/năm</span>
                    <span v-if="data.min_advance_days"    class="rule-limit">Báo trước {{ data.min_advance_days }}ng</span>
                  </div>
                </template>
              </Column>
              <Column field="is_active" header="Trạng thái" style="width: 115px"><template #body="{ data }"><Tag :value="data.is_active ? 'Hoạt động' : 'Đã khóa'" :severity="data.is_active ? 'success' : 'danger'" /></template></Column>
              <Column header="" style="width: 110px"><template #body="{ data }"><div class="action-cell"><Button v-can:edit="'catalog'" icon="pi pi-pencil" text rounded size="small" @click="openEditLeaveType(data)" /><Button v-can:delete="'catalog'" icon="pi pi-trash" severity="danger" text rounded size="small" @click="confirmDelete('leaveType', data)" /></div></template></Column>
            </DataTable>
          </TabPanel>

          <TabPanel value="templates">
            <div class="toolbar">
              <Select v-model="templateState.isActive" :options="activeFilterOptions" option-label="label" option-value="value" placeholder="Tất cả trạng thái" show-clear filter class="toolbar-filter" @change="loadTemplates" />
              <Select v-model="templateState.documentKind" :options="documentKindOptions" option-label="label" option-value="value" placeholder="Tất cả nhóm" show-clear filter class="toolbar-filter" @change="loadTemplates" />
              <IconField class="toolbar-search">
                <InputIcon class="pi pi-search" />
                <InputText v-model="templateState.keyword" class="w-full" placeholder="Tìm mẫu hợp đồng/phụ lục..." @input="debounce(loadTemplates)" />
              </IconField>
              <Button v-can:create="'catalog'" icon="pi pi-plus" severity="secondary" text rounded @click="openCreateTemplate" />
              <Button icon="pi pi-refresh" severity="secondary" text rounded :loading="templateState.loading" @click="loadTemplates" />
            </div>
            <div v-if="templateHealthItems.length" class="health-panel">
              <div class="health-panel-header">
                <i class="pi pi-exclamation-triangle" />
                <strong>Cảnh báo sức khoẻ mẫu hợp đồng ({{ templateHealthItems.length }} mẫu cần kiểm tra)</strong>
                <Button label="Xem audit log" icon="pi pi-list" text size="small" class="ml-auto" @click="router.push({ path: '/admin/audit-logs', query: { entity_type: 'contract_template' } })" />
              </div>
              <ul class="health-list">
                <li v-for="item in templateHealthItems" :key="item.id" class="health-item">
                  <span class="health-name">{{ item.name }} <code>{{ item.code }}</code></span>
                  <ul class="health-warnings">
                    <li v-for="(w, i) in item.health_warnings" :key="i">{{ w }}</li>
                  </ul>
                </li>
              </ul>
            </div>
            <DataTable :value="templateState.items" :loading="templateState.loading" stripedRows paginator lazy responsive-layout="scroll"
              :rows="templateState.pageSize" :first="(templateState.page - 1) * templateState.pageSize" :total-records="templateState.total" :rows-per-page-options="[10,20,50]"
              paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
              current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
              @page="onPage(templateState, $event, loadTemplates)">
              <template #empty><div class="empty-state"><i class="pi pi-inbox" /><span>Không có dữ liệu mẫu hợp đồng</span></div></template>
              <Column field="name" header="Tên mẫu" style="min-width: 260px"><template #body="{ data }"><div class="stacked-cell"><strong>{{ data.name }}</strong><small>{{ data.file_name }}</small></div></template></Column>
              <Column field="code" header="Mã" style="width: 150px" />
              <Column field="version_no" header="Version" style="width: 90px" />
              <Column field="document_kind" header="Nhóm" style="width: 150px"><template #body="{ data }">{{ documentKindLabel(data.document_kind) }}</template></Column>
              <Column field="is_active" header="Trạng thái" style="width: 120px"><template #body="{ data }"><Tag :value="data.is_active ? 'Hoạt động' : 'Đã khóa'" :severity="data.is_active ? 'success' : 'danger'" /></template></Column>
              <Column header="" style="width: 240px">
                <template #body="{ data }">
                  <div class="action-cell">
                    <Button v-can:edit="'catalog'" icon="pi pi-list" severity="secondary" text rounded size="small" aria-label="Quản lý placeholder" v-tooltip.top="'Quản lý placeholder'" @click="openTemplatePlaceholders(data)" />
                    <Button v-can:edit="'catalog'" icon="pi pi-search" severity="secondary" text rounded size="small" aria-label="Quét placeholder từ DOCX" v-tooltip.top="'Quét placeholder từ DOCX'" @click="openTemplatePlaceholders(data, true)" />
                    <Button v-can:edit="'catalog'" icon="pi pi-pencil" text rounded size="small" aria-label="Chỉnh sửa mẫu hợp đồng" v-tooltip.top="'Chỉnh sửa'" @click="openEditTemplate(data)" />
                    <Button
                      v-if="data.is_active"
                      icon="pi pi-lock"
                      severity="warn"
                      text
                      rounded
                      size="small"
                      aria-label="Khóa mẫu hợp đồng"
                      v-tooltip.top="'Khóa mẫu hợp đồng'"
                      v-can:edit="'catalog'"
                      @click="confirmToggleTemplateActive(data, false)"
                    />
                    <Button
                      v-else
                      icon="pi pi-lock-open"
                      severity="success"
                      text
                      rounded
                      size="small"
                      aria-label="Mở khóa mẫu hợp đồng"
                      v-tooltip.top="'Mở khóa mẫu hợp đồng'"
                      v-can:edit="'catalog'"
                      @click="confirmToggleTemplateActive(data, true)"
                    />
                    <Button
                      v-if="isSuperuser"
                      v-can:delete="'catalog'"
                      icon="pi pi-trash"
                      severity="danger"
                      text
                      rounded
                      size="small"
                      aria-label="Xóa hẳn mẫu hợp đồng"
                      v-tooltip.top="'Xóa hẳn mẫu hợp đồng'"
                      @click="confirmHardDeleteTemplate(data)"
                    />
                  </div>
                </template>
              </Column>
            </DataTable>
          </TabPanel>

          <TabPanel value="documentChecklist">
            <div class="toolbar">
              <Select v-model="documentChecklistTypeState.isActive" :options="activeFilterOptions" option-label="label" option-value="value" placeholder="Tất cả trạng thái" show-clear filter class="toolbar-filter" @change="loadDocumentChecklistTypes" />
              <Select v-model="documentChecklistTypeState.appliesTo" :options="documentChecklistAppliesToOptions" option-label="label" option-value="value" placeholder="Tất cả đối tượng" show-clear filter class="toolbar-filter" @change="loadDocumentChecklistTypes" />
              <IconField class="toolbar-search">
                <InputIcon class="pi pi-search" />
                <InputText v-model="documentChecklistTypeState.keyword" class="w-full" placeholder="Tìm loại checklist hồ sơ..." @input="debounce(loadDocumentChecklistTypes)" />
              </IconField>
              <Button v-can:create="'catalog'" icon="pi pi-plus" severity="secondary" text rounded @click="openCreateDocumentChecklistType" />
              <Button icon="pi pi-refresh" severity="secondary" text rounded :loading="documentChecklistTypeState.loading" @click="loadDocumentChecklistTypes" />
            </div>
            <DataTable
              :value="documentChecklistTypeState.items"
              :loading="documentChecklistTypeState.loading"
              stripedRows
              paginator
              lazy
              responsive-layout="scroll"
              :rows="documentChecklistTypeState.pageSize"
              :first="(documentChecklistTypeState.page - 1) * documentChecklistTypeState.pageSize"
              :total-records="documentChecklistTypeState.total"
              :rows-per-page-options="[10,20,50]"
              paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
              current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
              @page="onPage(documentChecklistTypeState, $event, loadDocumentChecklistTypes)"
            >
              <template #empty><div class="empty-state"><i class="pi pi-inbox" /><span>Không có dữ liệu checklist hồ sơ</span></div></template>
              <Column field="name" header="Tên loại hồ sơ" style="min-width: 260px">
                <template #body="{ data }">
                  <div class="stacked-cell">
                    <strong>{{ data.name }}</strong>
                    <small>{{ data.description || '—' }}</small>
                  </div>
                </template>
              </Column>
              <Column field="code" header="Mã" style="width: 220px" />
              <Column field="applies_to" header="Áp dụng cho" style="width: 180px">
                <template #body="{ data }">{{ documentChecklistAppliesToLabel(data.applies_to) }}</template>
              </Column>
              <Column field="sort_order" header="Thứ tự" style="width: 100px" />
              <Column field="is_required" header="Bắt buộc" style="width: 120px">
                <template #body="{ data }"><Tag :value="data.is_required ? 'Có' : 'Không'" :severity="data.is_required ? 'success' : 'contrast'" /></template>
              </Column>
              <Column field="has_expiry" header="Có hạn" style="width: 120px">
                <template #body="{ data }"><Tag :value="data.has_expiry ? 'Có' : 'Không'" :severity="data.has_expiry ? 'warning' : 'contrast'" /></template>
              </Column>
              <Column field="is_active" header="Trạng thái" style="width: 120px">
                <template #body="{ data }"><Tag :value="data.is_active ? 'Hoạt động' : 'Đã khóa'" :severity="data.is_active ? 'success' : 'danger'" /></template>
              </Column>
              <Column header="" style="width: 110px">
                <template #body="{ data }">
                  <div class="action-cell">
                    <Button v-can:edit="'catalog'" icon="pi pi-pencil" text rounded size="small" @click="openEditDocumentChecklistType(data)" />
                    <Button v-can:delete="'catalog'" icon="pi pi-trash" severity="danger" text rounded size="small" @click="confirmDelete('documentChecklistType', data)" />
                  </div>
                </template>
              </Column>
            </DataTable>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>

    <Dialog
      v-model:visible="dialogVisible"
      class="other-business-edit-dialog"
      :header="dialogHeader"
      :style="{ width: dialogWidth, maxWidth: '96vw' }"
      :breakpoints="{ '1200px': '84vw', '960px': '92vw', '640px': '96vw' }"
      modal
      :closable="!submitting"
    >
      <form class="form-shell" @submit.prevent="submitActiveDialog">
        <template v-if="dialogKind === 'contractCategory'">
          <div v-if="!editingContractCategory" class="field"><label>Mã <span class="req">*</span></label><InputText v-model="contractCategoryForm.code" class="w-full" /></div>
          <div class="field"><label>Tên <span class="req">*</span></label><InputText v-model="contractCategoryForm.name" class="w-full" /></div>
          <div class="field-row">
            <div class="field"><label>Nhóm tài liệu</label><Select v-model="contractCategoryForm.document_kind" :options="documentKindOptions" option-label="label" option-value="value" filter class="w-full" /></div>
            <div class="field"><label>Loại pháp lý</label><Select v-model="contractCategoryForm.legal_contract_type" :options="legalTypeOptions" option-label="label" option-value="value" filter class="w-full" show-clear /></div>
          </div>
          <div class="field-row">
            <div class="field"><label>Nhóm nghiệp vụ</label><InputText v-model="contractCategoryForm.business_group" class="w-full" /></div>
            <div class="field"><label>Thời hạn mặc định (tháng)</label><InputNumber v-model="contractCategoryForm.default_term_months" :min="1" :max-fraction-digits="0" class="w-full" /></div>
          </div>
          <div class="field"><label>Mô tả</label><Textarea v-model="contractCategoryForm.description" rows="3" class="w-full" auto-resize /></div>
          <div v-if="editingContractCategory" class="field field-switch"><label>Trạng thái</label><div class="switch-row"><ToggleSwitch v-model="contractCategoryForm.is_active" /><span :class="contractCategoryForm.is_active ? 'active-label' : 'inactive-label'">{{ contractCategoryForm.is_active ? 'Hoạt động' : 'Đã khóa' }}</span></div></div>
        </template>

        <template v-else-if="dialogKind === 'identity'">
          <div v-if="!editingIdentity" class="field"><label>Mã <span class="req">*</span></label><InputText v-model="identityForm.code" class="w-full" /></div>
          <div class="field"><label>Tên <span class="req">*</span></label><InputText v-model="identityForm.name" class="w-full" /></div>
          <div v-if="identityType === 'nationality'" class="field-row">
            <div class="field"><label>ISO2</label><InputText v-model="identityForm.iso2_code" class="w-full" /></div>
            <div class="field"><label>ISO3</label><InputText v-model="identityForm.iso3_code" class="w-full" /></div>
          </div>
          <div v-if="editingIdentity" class="field field-switch"><label>Trạng thái</label><div class="switch-row"><ToggleSwitch v-model="identityForm.is_active" /><span :class="identityForm.is_active ? 'active-label' : 'inactive-label'">{{ identityForm.is_active ? 'Hoạt động' : 'Đã khóa' }}</span></div></div>
        </template>

        <template v-else-if="dialogKind === 'bank'">
          <div v-if="!editingBank" class="field"><label>Mã <span class="req">*</span></label><InputText v-model="bankForm.code" class="w-full" /></div>
          <div class="field"><label>Tên <span class="req">*</span></label><InputText v-model="bankForm.name" class="w-full" /></div>
          <div class="field"><label>Tên ngắn</label><InputText v-model="bankForm.short_name" class="w-full" /></div>
          <div class="field-row">
            <div class="field"><label>BIN</label><InputText v-model="bankForm.bin_code" class="w-full" /></div>
            <div class="field"><label>SWIFT</label><InputText v-model="bankForm.swift_code" class="w-full" /></div>
          </div>
          <div v-if="editingBank" class="field field-switch"><label>Trạng thái</label><div class="switch-row"><ToggleSwitch v-model="bankForm.is_active" /><span :class="bankForm.is_active ? 'active-label' : 'inactive-label'">{{ bankForm.is_active ? 'Hoạt động' : 'Đã khóa' }}</span></div></div>
        </template>

        <template v-else-if="dialogKind === 'skill'">
          <div v-if="!editingSkill" class="field"><label>Mã <span class="req">*</span></label><InputText v-model="skillForm.code" class="w-full" /></div>
          <div class="field"><label>Tên <span class="req">*</span></label><InputText v-model="skillForm.name" class="w-full" /></div>
          <div class="field"><label>Nhóm kỹ năng</label><InputText v-model="skillForm.skill_group" class="w-full" /></div>
          <div v-if="editingSkill" class="field field-switch"><label>Trạng thái</label><div class="switch-row"><ToggleSwitch v-model="skillForm.is_active" /><span :class="skillForm.is_active ? 'active-label' : 'inactive-label'">{{ skillForm.is_active ? 'Hoạt động' : 'Đã khóa' }}</span></div></div>
        </template>

        <template v-else-if="dialogKind === 'certificate'">
          <div v-if="!editingCertificate" class="field"><label>Mã <span class="req">*</span></label><InputText v-model="certificateForm.code" class="w-full" /></div>
          <div class="field"><label>Tên <span class="req">*</span></label><InputText v-model="certificateForm.name" class="w-full" /></div>
          <div class="field-row">
            <div class="field"><label>Nhóm</label><InputText v-model="certificateForm.certificate_group" class="w-full" /></div>
            <div class="field"><label>Đơn vị cấp</label><InputText v-model="certificateForm.issuer_name" class="w-full" /></div>
          </div>
          <div class="field-row">
            <div class="field"><label>Chính sách hết hạn</label><Select v-model="certificateForm.expiry_policy" :options="expiryPolicyOptions" option-label="label" option-value="value" filter class="w-full" show-clear /></div>
            <div class="field"><label>Số tháng hiệu lực</label><InputNumber v-model="certificateForm.default_valid_months" :min="1" :max-fraction-digits="0" class="w-full" /></div>
          </div>
          <div v-if="editingCertificate" class="field field-switch"><label>Trạng thái</label><div class="switch-row"><ToggleSwitch v-model="certificateForm.is_active" /><span :class="certificateForm.is_active ? 'active-label' : 'inactive-label'">{{ certificateForm.is_active ? 'Hoạt động' : 'Đã khóa' }}</span></div></div>
        </template>

        <template v-else-if="dialogKind === 'leaveType'">
          <div v-if="!editingLeaveType" class="field"><label>Mã <span class="req">*</span></label><InputText v-model="leaveTypeForm.code" class="w-full" /></div>
          <div class="field"><label>Tên <span class="req">*</span></label><InputText v-model="leaveTypeForm.name" class="w-full" /></div>
          <div class="checkbox-grid">
            <label class="check-item"><Checkbox v-model="leaveTypeForm.is_paid_leave" binary /><span>Hưởng lương</span></label>
            <label class="check-item"><Checkbox v-model="leaveTypeForm.affects_annual_leave" binary /><span>Trừ phép năm</span></label>
            <label class="check-item"><Checkbox v-model="leaveTypeForm.allow_half_day" binary /><span>Cho phép nửa ngày</span></label>
            <label class="check-item"><Checkbox v-model="leaveTypeForm.requires_attachment" binary /><span>Yêu cầu đính kèm</span></label>
          </div>

          <p class="form-section-label">Quy tắc nghỉ</p>
          <div class="field-row-3">
            <div class="field">
              <label>Số ngày tối đa / năm</label>
              <InputNumber v-model="leaveTypeForm.max_days_per_year" :min="1" :max-fraction-digits="0" placeholder="Không giới hạn" class="w-full" show-buttons />
            </div>
            <div class="field">
              <label>Ngày liên tiếp tối đa / đơn</label>
              <InputNumber v-model="leaveTypeForm.max_consecutive_days" :min="1" :max-fraction-digits="0" placeholder="Không giới hạn" class="w-full" show-buttons />
            </div>
            <div class="field">
              <label>Báo trước tối thiểu (ngày)</label>
              <InputNumber v-model="leaveTypeForm.min_advance_days" :min="0" :max-fraction-digits="0" class="w-full" show-buttons />
            </div>
          </div>
          <div class="checkbox-grid">
            <label class="check-item">
              <Checkbox v-model="leaveTypeForm.count_public_holidays" binary />
              <span>Tính ngày lễ vào quota phép</span>
            </label>
            <label class="check-item">
              <Checkbox v-model="leaveTypeForm.carryover_allowed" binary />
              <span>Cho phép chuyển phép dư sang năm sau</span>
            </label>
          </div>
          <div v-if="leaveTypeForm.carryover_allowed" class="field" style="max-width:220px;">
            <label>Hết hạn chuyển (tháng) <span class="req">*</span></label>
            <InputNumber v-model="leaveTypeForm.carryover_cutoff_month" :min="1" :max="12" :max-fraction-digits="0" class="w-full" show-buttons />
            <small class="field-hint">3 = hết Quý I (31/03)</small>
          </div>

          <div class="field-row">
            <div class="field"><label>Màu nhãn</label><InputText v-model="leaveTypeForm.color_tag" class="w-full" /></div>
          </div>
          <div class="field"><label>Mô tả</label><Textarea v-model="leaveTypeForm.description" rows="2" class="w-full" auto-resize /></div>
          <div v-if="editingLeaveType" class="field field-switch"><label>Trạng thái</label><div class="switch-row"><ToggleSwitch v-model="leaveTypeForm.is_active" /><span :class="leaveTypeForm.is_active ? 'active-label' : 'inactive-label'">{{ leaveTypeForm.is_active ? 'Hoạt động' : 'Đã khóa' }}</span></div></div>
        </template>

        <template v-else-if="dialogKind === 'documentChecklistType'">
          <div v-if="!editingDocumentChecklistType" class="field"><label>Mã <span class="req">*</span></label><InputText v-model="documentChecklistTypeForm.code" class="w-full" /></div>
          <div class="field"><label>Tên <span class="req">*</span></label><InputText v-model="documentChecklistTypeForm.name" class="w-full" /></div>
          <div class="field-row">
            <div class="field"><label>Áp dụng cho</label><Select v-model="documentChecklistTypeForm.applies_to" :options="documentChecklistAppliesToOptions" option-label="label" option-value="value" filter class="w-full" /></div>
            <div class="field"><label>Thứ tự</label><InputNumber v-model="documentChecklistTypeForm.sort_order" :min="0" :max-fraction-digits="0" class="w-full" /></div>
          </div>
          <div class="checkbox-grid">
            <label class="check-item"><Checkbox v-model="documentChecklistTypeForm.is_required" binary /><span>Bắt buộc</span></label>
            <label class="check-item"><Checkbox v-model="documentChecklistTypeForm.has_expiry" binary /><span>Có ngày hết hạn</span></label>
          </div>
          <div class="field"><label>Mô tả</label><Textarea v-model="documentChecklistTypeForm.description" rows="3" class="w-full" auto-resize /></div>
          <div v-if="editingDocumentChecklistType" class="field field-switch"><label>Trạng thái</label><div class="switch-row"><ToggleSwitch v-model="documentChecklistTypeForm.is_active" /><span :class="documentChecklistTypeForm.is_active ? 'active-label' : 'inactive-label'">{{ documentChecklistTypeForm.is_active ? 'Hoạt động' : 'Đã khóa' }}</span></div></div>
        </template>

        <template v-else-if="dialogKind === 'template'">
          <div v-if="!editingTemplate" class="field"><label>Mã <span class="req">*</span></label><InputText v-model="templateForm.code" class="w-full" /></div>
          <div class="field"><label>Tên mẫu <span class="req">*</span></label><InputText v-model="templateForm.name" class="w-full" /></div>
          <div class="field-row">
            <div class="field"><label>Loại hợp đồng <span class="req">*</span></label><Select v-model="templateForm.contract_category_id" :options="contractCategoryLookup" option-label="name" option-value="id" filter class="w-full" /></div>
            <div class="field"><label>Nhóm tài liệu</label><Select v-model="templateForm.document_kind" :options="documentKindOptions" option-label="label" option-value="value" filter class="w-full" /></div>
          </div>
          <div class="field">
            <label>File mẫu DOCX</label>
            <FileUpload
              mode="basic"
              :auto="false"
              accept=".docx"
              :max-file-size="5242880"
              choose-label="Chọn file DOCX"
              @select="onTemplateFileSelect"
            />
            <small class="field-hint">Chỉ nhận file .docx, tối đa 5 MB. Có thể upload ngay khi tạo mới hoặc khi chỉnh sửa mẫu.</small>
            <small v-if="selectedTemplateFileName" class="field-hint">Đã chọn: {{ selectedTemplateFileName }}</small>
            <small v-else-if="editingTemplate?.file_name" class="field-hint">File hiện tại: {{ editingTemplate.file_name }}</small>
          </div>
          <div class="field-row">
            <div class="field"><label>Tên file <span class="req">*</span></label><InputText v-model="templateForm.file_name" class="w-full" /></div>
            <div class="field"><label>MIME type <span class="req">*</span></label><InputText v-model="templateForm.mime_type" class="w-full" /></div>
          </div>
          <div class="field-row">
            <div class="field"><label>Version</label><InputNumber v-model="templateForm.version_no" :min="1" :max-fraction-digits="0" class="w-full" /></div>
            <div class="field"><label>Storage path</label><InputText v-model="templateForm.storage_path" class="w-full" readonly placeholder="Tự cập nhật sau khi upload" /></div>
          </div>
          <div class="field"><label>Ghi chú</label><Textarea v-model="templateForm.note" rows="3" class="w-full" auto-resize /></div>
          <div v-if="editingTemplate" class="field field-switch"><label>Trạng thái</label><div class="switch-row"><ToggleSwitch v-model="templateForm.is_active" /><span :class="templateForm.is_active ? 'active-label' : 'inactive-label'">{{ templateForm.is_active ? 'Hoạt động' : 'Đã khóa' }}</span></div></div>
        </template>
      </form>
      <template #footer>
        <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="dialogVisible = false" />
        <Button v-can="editingMode ? 'catalog:edit' : 'catalog:create'" :label="editingMode ? 'Lưu thay đổi' : 'Tạo mới'" icon="pi pi-check" :loading="submitting" @click="submitActiveDialog" />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="placeholderDialogVisible"
      class="other-business-placeholder-dialog"
      header="Placeholder của mẫu hợp đồng"
      :style="{ width: '1440px', maxWidth: '98vw' }"
      :breakpoints="{ '1600px': '96vw', '1200px': '97vw', '960px': '98vw', '640px': '99vw' }"
      :pt="{ content: { style: 'padding-bottom: 1.5rem' } }"
      modal
      :closable="!submittingPlaceholders"
    >
      <div class="placeholder-shell">
        <div class="placeholder-toolbar">
          <div class="placeholder-meta">
            <strong>{{ editingPlaceholderTemplate?.name }}</strong>
            <p class="placeholder-note">Quản trị bộ biến metadata dùng cho phase auto-fill hợp đồng/phụ lục. Chọn trường dữ liệu nghiệp vụ, hệ thống sẽ tự điền phạm vi và đường dẫn logic nội bộ.</p>
            <p class="placeholder-note placeholder-note-subtle">`Đường dẫn logic` không phải tên cột DB. Nguồn dữ liệu thật của từng field sẽ hiển thị ngay dưới ô đường dẫn.</p>
          </div>
          <div class="placeholder-actions">
            <Button
              v-can:edit="'catalog'"
              v-if="editingPlaceholderTemplate?.storage_path"
              label="Quét từ DOCX"
              icon="pi pi-search"
              severity="secondary"
              outlined
              :loading="inspectingTemplateDocx"
              @click="inspectTemplateDocx"
            />
            <Button v-can:edit="'catalog'" label="Thêm placeholder" icon="pi pi-plus" @click="addPlaceholderRow" />
          </div>
        </div>

        <div v-if="templateDocxSummary" class="docx-summary">
          <div class="docx-summary-head">
            <strong>Phân tích file mẫu</strong>
            <span>{{ mappedPlaceholderCount }}/{{ detectedPlaceholderCount }} placeholder đã auto-map vào bảng bên dưới</span>
          </div>
          <div class="docx-summary-metrics">
            <span><strong>{{ detectedPlaceholderCount }}</strong> placeholder phát hiện trong file</span>
            <span><strong>{{ templateDocxSummary.supported_count }}</strong> placeholder có thể map tự động</span>
            <span><strong>{{ templateDocxSummary.unsupported_count }}</strong> placeholder cần xử lý tay</span>
          </div>
          <ul v-if="templateDocxSummary.warnings.length" class="docx-warning-list">
            <li v-for="warning in templateDocxSummary.warnings" :key="warning">{{ warning }}</li>
          </ul>
        </div>

        <div v-if="placeholderRegistryWarning" class="docx-summary registry-warning">
          <div class="docx-summary-head">
            <strong>Placeholder ngoài registry</strong>
            <span>{{ placeholderRegistryWarning }}</span>
          </div>
        </div>

        <DataTable :value="placeholderRows" responsive-layout="scroll" stripedRows>
          <template #empty><div class="empty-state"><i class="pi pi-inbox" /><span>Chưa có placeholder nào</span></div></template>
          <Column header="Khóa" style="min-width: 220px"><template #body="{ index }"><InputText v-model="placeholderRows[index].placeholder_key" class="w-full" /></template></Column>
          <Column header="Nhãn" style="min-width: 220px"><template #body="{ index }"><InputText v-model="placeholderRows[index].label" class="w-full" /></template></Column>
          <Column header="Trường dữ liệu" style="min-width: 380px">
            <template #body="{ index }">
              <Select
                v-model="placeholderRows[index].field_registry_token"
                :options="placeholderFieldOptions"
                option-label="display_label"
                option-value="token"
                filter
                class="w-full"
                @change="onPlaceholderFieldChange(index)"
              />
            </template>
          </Column>
          <Column header="Phạm vi" style="min-width: 160px">
            <template #body="{ index }">
              <InputText :model-value="scopeLabel(placeholderRows[index].source_scope)" class="w-full" readonly />
            </template>
          </Column>
          <Column header="Đường dẫn logic" style="min-width: 340px">
            <template #body="{ index }">
              <div class="placeholder-cell-stack">
                <InputText v-model="placeholderRows[index].source_path" class="w-full" readonly />
                <small v-if="sourceOriginLabel(placeholderRows[index])" class="placeholder-origin">{{ sourceOriginLabel(placeholderRows[index]) }}</small>
              </div>
            </template>
          </Column>
          <Column header="Kiểu" style="min-width: 160px">
            <template #body="{ index }">
              <InputText :model-value="typeLabel(placeholderRows[index].data_type)" class="w-full" readonly />
            </template>
          </Column>
          <Column header="Bắt buộc" style="width: 110px"><template #body="{ index }"><Checkbox v-model="placeholderRows[index].is_required" binary /></template></Column>
          <Column header="" style="width: 70px"><template #body="{ index }"><Button v-can:edit="'catalog'" icon="pi pi-times" severity="danger" text rounded @click="removePlaceholderRow(index)" /></template></Column>
        </DataTable>
      </div>
      <template #footer>
        <div class="placeholder-dialog-footer">
          <Button label="Đóng" severity="secondary" outlined :disabled="submittingPlaceholders" @click="placeholderDialogVisible = false" />
          <Button v-can:edit="'catalog'" label="Lưu placeholder" icon="pi pi-save" :loading="submittingPlaceholders" @click="savePlaceholders" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import FileUpload from 'primevue/fileupload'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import { useAuthStore } from '@/stores/auth'

import otherBusinessCatalogService, {
  type BankRead,
  type CertificateRead,
  type ContractCategoryRead,
  type DocumentChecklistAppliesToOption,
  type DocumentChecklistTypeRead,
  type ContractTemplateFieldRegistryRead,
  type ContractTemplateDocxInspectionRead,
  type ContractTemplateHealthRead,
  type ContractTemplatePlaceholderWrite,
  type ContractTemplateRead,
  type EthnicityRead,
  type LeaveTypeRead,
  type NationalityRead,
  type ReligionRead,
  type SkillRead,
} from '@/services/otherBusinessCatalogService'

type ActiveTab = 'contracts' | 'identity' | 'banks' | 'competency' | 'leaves' | 'documentChecklist' | 'templates'
type DialogKind = 'contractCategory' | 'identity' | 'bank' | 'skill' | 'certificate' | 'leaveType' | 'documentChecklistType' | 'template'
type IdentityKind = 'nationality' | 'ethnicity' | 'religion'
type PlaceholderRow = ContractTemplatePlaceholderWrite & { field_registry_token: string | null }
type PlaceholderFieldOption = ContractTemplateFieldRegistryRead & { display_label: string }

interface ListState<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  keyword: string
  isActive: boolean | null
  loading: boolean
}

function makeListState<T>(): ListState<T> {
  return { items: [], total: 0, page: 1, pageSize: 10, keyword: '', isActive: true, loading: false }
}

const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const auth = useAuthStore()

const activeTab = ref<ActiveTab>('contracts')
const errorBanner = ref('')
const submitting = ref(false)
const dialogVisible = ref(false)
const dialogKind = ref<DialogKind>('contractCategory')

const contractCategoryState = ref(makeListState<ContractCategoryRead>() as ListState<ContractCategoryRead> & { documentKind: string | null })
contractCategoryState.value.documentKind = null
const nationalityState = ref(makeListState<NationalityRead>())
const ethnicityState = ref(makeListState<EthnicityRead>())
const religionState = ref(makeListState<ReligionRead>())
const bankState = ref(makeListState<BankRead>())
const skillState = ref(makeListState<SkillRead>())
const certificateState = ref(makeListState<CertificateRead>())
const leaveTypeState = ref(makeListState<LeaveTypeRead>())
const documentChecklistTypeState = ref(makeListState<DocumentChecklistTypeRead>() as ListState<DocumentChecklistTypeRead> & { appliesTo: 'all' | 'foreign_worker' | null })
documentChecklistTypeState.value.appliesTo = null
const templateState = ref(makeListState<ContractTemplateRead>() as ListState<ContractTemplateRead> & { documentKind: string | null })
templateState.value.documentKind = null
const templateHealthItems = ref<ContractTemplateHealthRead[]>([])
const documentChecklistAppliesToOptions = ref<DocumentChecklistAppliesToOption[]>([])

const activeFilterOptions = [
  { label: 'Đang hoạt động', value: true },
  { label: 'Đã khóa', value: false },
]
const documentKindOptions = [
  { label: 'Hợp đồng lao động', value: 'labor_contract' },
  { label: 'Phụ lục hợp đồng', value: 'contract_appendix' },
]
const legalTypeOptions = [
  { label: 'Không xác định thời hạn', value: 'indefinite_term' },
  { label: 'Xác định thời hạn', value: 'definite_term' },
]
const expiryPolicyOptions = [
  { label: 'Không hết hạn', value: 'none' },
  { label: 'Ngày cố định', value: 'fixed_date' },
  { label: 'Theo số tháng sau ngày cấp', value: 'months_after_issue' },
]
const placeholderScopeOptions = [
  { label: 'Nhân viên', value: 'employee' },
  { label: 'Tổ chức', value: 'organization' },
  { label: 'Hợp đồng', value: 'contract_draft' },
  { label: 'Người ký', value: 'signer' },
  { label: 'Hệ thống', value: 'system' },
]
const placeholderTypeOptions = [
  { label: 'Văn bản', value: 'text' },
  { label: 'Ngày tháng', value: 'date' },
  { label: 'Số', value: 'number' },
  { label: 'Tiền tệ', value: 'currency' },
  { label: 'Đúng/Sai', value: 'boolean' },
]

const templateFieldRegistry = ref<ContractTemplateFieldRegistryRead[]>([])
const placeholderFieldOptions = computed<PlaceholderFieldOption[]>(() => {
  const base = templateFieldRegistry.value.map((field) => ({
    ...field,
    display_label: `${field.label} (${field.token})`,
  }))
  const extras = placeholderRows.value
    .filter((row) => row.field_registry_token?.startsWith('__unresolved__:'))
    .map((row) => ({
      token: row.field_registry_token as string,
      label: row.label || row.placeholder_key || 'Placeholder ngoài registry',
      source_scope: row.source_scope,
      source_path: row.source_path,
      source_origin: null,
      data_type: row.data_type,
      formatter: row.formatter ?? null,
      is_required: row.is_required ?? false,
      recommended_token: null,
      display_label: `Ngoài registry: ${row.label || row.placeholder_key || row.source_path}`,
    }))
  return [...base, ...extras]
})

const placeholderRegistryWarning = computed(() => {
  const count = placeholderRows.value.filter((row) => row.field_registry_token?.startsWith('__unresolved__:')).length
  if (!count) return ''
  return `${count} placeholder hiện tại chưa khớp field registry. Bạn vẫn xem được chúng, nhưng placeholder mới nên chọn từ danh sách chuẩn.`
})

const detectedPlaceholderCount = computed(() => templateDocxSummary.value?.detected_placeholders.length ?? 0)
const mappedPlaceholderCount = computed(() => templateDocxSummary.value?.suggested_rows.length ?? 0)

const contractCategoryLookup = ref<ContractCategoryRead[]>([])

const editingContractCategory = ref<ContractCategoryRead | null>(null)
const contractCategoryForm = ref({
  code: '',
  name: '',
  document_kind: 'labor_contract' as 'labor_contract' | 'contract_appendix',
  legal_contract_type: null as 'indefinite_term' | 'definite_term' | null,
  business_group: '',
  default_term_months: null as number | null,
  sort_order: 0,
  is_active: true,
  description: '',
})

const identityType = ref<IdentityKind>('nationality')
const editingIdentity = ref<NationalityRead | EthnicityRead | ReligionRead | null>(null)
const identityForm = ref({
  code: '',
  name: '',
  iso2_code: '',
  iso3_code: '',
  is_active: true,
})

const editingBank = ref<BankRead | null>(null)
const bankForm = ref({ code: '', name: '', short_name: '', bin_code: '', swift_code: '', is_active: true })

const editingSkill = ref<SkillRead | null>(null)
const skillForm = ref({ code: '', name: '', skill_group: '', is_active: true })

const editingCertificate = ref<CertificateRead | null>(null)
const certificateForm = ref({
  code: '', name: '', certificate_group: '', issuer_name: '', expiry_policy: null as 'none' | 'fixed_date' | 'months_after_issue' | null, default_valid_months: null as number | null, is_active: true,
})

const editingLeaveType = ref<LeaveTypeRead | null>(null)
const leaveTypeForm = ref({
  code: '', name: '',
  is_paid_leave: false, affects_annual_leave: false, allow_half_day: false, requires_attachment: false,
  color_tag: '', is_active: true, description: '',
  count_public_holidays: true,
  max_days_per_year: null as number | null,
  max_consecutive_days: null as number | null,
  min_advance_days: 0,
  carryover_allowed: false,
  carryover_cutoff_month: 3,
})
const editingDocumentChecklistType = ref<DocumentChecklistTypeRead | null>(null)
const documentChecklistTypeForm = ref({
  code: '',
  name: '',
  description: '',
  is_required: true,
  has_expiry: false,
  applies_to: 'all' as 'all' | 'foreign_worker',
  sort_order: 0,
  is_active: true,
})

const editingTemplate = ref<ContractTemplateRead | null>(null)
const templateForm = ref({
  code: '', name: '', contract_category_id: null as number | null, document_kind: 'labor_contract' as 'labor_contract' | 'contract_appendix', file_name: '', mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', storage_path: '', version_no: 1, is_active: true, note: '',
})
const selectedTemplateFile = ref<File | null>(null)

const placeholderDialogVisible = ref(false)
const submittingPlaceholders = ref(false)
const inspectingTemplateDocx = ref(false)
const editingPlaceholderTemplate = ref<ContractTemplateRead | null>(null)
const placeholderRows = ref<PlaceholderRow[]>([])
const templateDocxSummary = ref<ContractTemplateDocxInspectionRead | null>(null)
const selectedTemplateFileName = computed(() => selectedTemplateFile.value?.name || '')
const isSuperuser = computed(() => auth.user?.is_superuser === true)

let debounceTimer: ReturnType<typeof setTimeout> | undefined
function debounce(fn: () => void) {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => fn(), 300)
}

function scopeLabel(scope: PlaceholderRow['source_scope']) {
  return placeholderScopeOptions.find((option) => option.value === scope)?.label || scope
}

function typeLabel(type: PlaceholderRow['data_type']) {
  return placeholderTypeOptions.find((option) => option.value === type)?.label || type
}

function unresolvedFieldToken(row: Pick<PlaceholderRow, 'source_scope' | 'source_path' | 'data_type' | 'formatter'>) {
  return `__unresolved__:${row.source_scope}:${row.source_path}:${row.data_type}:${row.formatter ?? ''}`
}

function resolveRegistryToken(row: Pick<PlaceholderRow, 'source_scope' | 'source_path' | 'data_type' | 'formatter'>) {
  const matched = templateFieldRegistry.value.find(
    (field) =>
      field.source_scope === row.source_scope &&
      field.source_path === row.source_path &&
      field.data_type === row.data_type &&
      (field.formatter ?? null) === (row.formatter ?? null),
  )
  return matched?.token || unresolvedFieldToken(row)
}

function applyFieldRegistrySelection(row: PlaceholderRow, token: string | null) {
  if (!token) return
  if (token.startsWith('__unresolved__:')) {
    row.field_registry_token = token
    return
  }
  const matched = templateFieldRegistry.value.find((field) => field.token === token)
  if (!matched) return
  const isNewField = !row.source_path
  row.field_registry_token = matched.token
  row.source_scope = matched.source_scope
  row.source_path = matched.source_path
  row.data_type = matched.data_type
  row.formatter = matched.formatter
  if (!row.placeholder_key) row.placeholder_key = matched.token
  if (!row.label) row.label = matched.label
  if (isNewField) row.is_required = matched.is_required
}

function onPlaceholderFieldChange(index: number) {
  const row = placeholderRows.value[index]
  if (!row) return
  applyFieldRegistrySelection(row, row.field_registry_token)
}

const activeTabLabel = computed(() => ({
  contracts: 'Loại hợp đồng',
  identity: 'Nhân thân',
  banks: 'Ngân hàng',
  competency: 'Kỹ năng & chứng chỉ',
  leaves: 'Loại nghỉ phép',
  documentChecklist: 'Checklist hồ sơ',
  templates: 'Mẫu hợp đồng',
}[activeTab.value]))

const activeHeadline = computed(() => ({
  contracts: 'Chuẩn hóa loại hợp đồng và nhóm phụ lục',
  identity: 'Danh mục nhân thân dùng lại cho hồ sơ nhân sự',
  banks: 'Ngân hàng dùng cho thông tin thanh toán nhân viên',
  competency: 'Kỹ năng và chứng chỉ phục vụ hồ sơ năng lực',
  leaves: 'Loại nghỉ phép và quy tắc nhân sự nền',
  documentChecklist: 'Checklist hồ sơ pháp lý và điều kiện áp dụng',
  templates: 'Metadata mẫu hợp đồng/phụ lục cho phase auto-fill',
}[activeTab.value]))

const activeSubline = computed(() => ({
  contracts: 'Phân biệt lớp pháp lý và lớp nghiệp vụ nội bộ để không khóa sai thiết kế hợp đồng.',
  identity: 'Giảm nhập tay và chuẩn hóa lookup cho quốc tịch, dân tộc, tôn giáo.',
  banks: 'Dùng chung cho tài khoản ngân hàng nhân viên và các mẫu biểu nghiệp vụ.',
  competency: 'Chuẩn hóa kỹ năng/chứng chỉ cho đào tạo, đánh giá và hồ sơ nhân sự.',
  leaves: 'Làm nền cho module nghỉ phép và quy tắc hiển thị trên báo cáo HR.',
  documentChecklist: 'Cho phép HR đổi loại giấy tờ, tính bắt buộc và phạm vi áp dụng ngay trên UI.',
  templates: 'Khai báo tên file, version, loại hợp đồng và placeholder cần render về sau.',
}[activeTab.value]))

const primaryCreateLabel = computed(() => ({
  contracts: 'Thêm loại hợp đồng',
  identity: 'Thêm danh mục nhân thân',
  banks: 'Thêm ngân hàng',
  competency: 'Thêm kỹ năng',
  leaves: 'Thêm loại nghỉ',
  documentChecklist: 'Thêm checklist hồ sơ',
  templates: 'Thêm mẫu hợp đồng',
}[activeTab.value]))

const editingMode = computed(() => {
  switch (dialogKind.value) {
    case 'contractCategory': return !!editingContractCategory.value
    case 'identity': return !!editingIdentity.value
    case 'bank': return !!editingBank.value
    case 'skill': return !!editingSkill.value
    case 'certificate': return !!editingCertificate.value
    case 'leaveType': return !!editingLeaveType.value
    case 'documentChecklistType': return !!editingDocumentChecklistType.value
    case 'template': return !!editingTemplate.value
  }
})

const dialogHeader = computed(() => {
  if (dialogKind.value === 'contractCategory') return editingContractCategory.value ? 'Chỉnh sửa loại hợp đồng' : 'Thêm loại hợp đồng'
  if (dialogKind.value === 'identity') return editingIdentity.value ? `Chỉnh sửa ${identityTypeLabel(identityType.value)}` : `Thêm ${identityTypeLabel(identityType.value)}`
  if (dialogKind.value === 'bank') return editingBank.value ? 'Chỉnh sửa ngân hàng' : 'Thêm ngân hàng'
  if (dialogKind.value === 'skill') return editingSkill.value ? 'Chỉnh sửa kỹ năng' : 'Thêm kỹ năng'
  if (dialogKind.value === 'certificate') return editingCertificate.value ? 'Chỉnh sửa chứng chỉ' : 'Thêm chứng chỉ'
  if (dialogKind.value === 'leaveType') return editingLeaveType.value ? 'Chỉnh sửa loại nghỉ phép' : 'Thêm loại nghỉ phép'
  if (dialogKind.value === 'documentChecklistType') return editingDocumentChecklistType.value ? 'Chỉnh sửa checklist hồ sơ' : 'Thêm checklist hồ sơ'
  return editingTemplate.value ? 'Chỉnh sửa mẫu hợp đồng' : 'Thêm mẫu hợp đồng'
})

const dialogWidth = computed(() => ['template', 'contractCategory', 'certificate', 'leaveType', 'documentChecklistType'].includes(dialogKind.value) ? '720px' : '580px')

function identityTypeLabel(kind: IdentityKind) {
  return kind === 'nationality' ? 'quốc tịch' : kind === 'ethnicity' ? 'dân tộc' : 'tôn giáo'
}
function documentKindLabel(value: string | null) {
  return documentKindOptions.find((item) => item.value === value)?.label ?? '—'
}
function legalTypeLabel(value: string | null) {
  return legalTypeOptions.find((item) => item.value === value)?.label ?? '—'
}
function documentChecklistAppliesToLabel(value: string | null) {
  return documentChecklistAppliesToOptions.value.find((item) => item.value === value)?.label ?? value ?? '—'
}
function formatNumber(value: number) {
  return new Intl.NumberFormat('vi-VN').format(value)
}
function apiError(error: unknown): string {
  const err = error as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((item: { msg: string }) => item.msg).join('; ')
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi, vui lòng thử lại'
}
function onPage(state: ListState<unknown>, event: { page: number; rows: number }, loader: () => void) {
  state.page = event.page + 1
  state.pageSize = event.rows
  loader()
}

async function loadContractCategoryLookup() {
  const res = await otherBusinessCatalogService.lookupContractCategories({ limit: 100 })
  contractCategoryLookup.value = res.data
}
async function loadContractCategories() {
  contractCategoryState.value.loading = true
  try {
    const res = await otherBusinessCatalogService.getContractCategories({ keyword: contractCategoryState.value.keyword || null, is_active: contractCategoryState.value.isActive, document_kind: contractCategoryState.value.documentKind, page: contractCategoryState.value.page, page_size: contractCategoryState.value.pageSize })
    Object.assign(contractCategoryState.value, { items: res.data.items, total: res.data.total, page: res.data.page, pageSize: res.data.page_size })
  } catch (e) { errorBanner.value = apiError(e) } finally { contractCategoryState.value.loading = false }
}
async function loadNationalities() {
  nationalityState.value.loading = true
  try {
    const res = await otherBusinessCatalogService.getNationalities({ keyword: nationalityState.value.keyword || null, is_active: true, page: 1, page_size: 10 })
    Object.assign(nationalityState.value, { items: res.data.items, total: res.data.total })
  } catch (e) { errorBanner.value = apiError(e) } finally { nationalityState.value.loading = false }
}
async function loadEthnicities() {
  ethnicityState.value.loading = true
  try {
    const res = await otherBusinessCatalogService.getEthnicities({ keyword: ethnicityState.value.keyword || null, is_active: true, page: 1, page_size: 10 })
    Object.assign(ethnicityState.value, { items: res.data.items, total: res.data.total })
  } catch (e) { errorBanner.value = apiError(e) } finally { ethnicityState.value.loading = false }
}
async function loadReligions() {
  religionState.value.loading = true
  try {
    const res = await otherBusinessCatalogService.getReligions({ keyword: religionState.value.keyword || null, is_active: true, page: 1, page_size: 10 })
    Object.assign(religionState.value, { items: res.data.items, total: res.data.total })
  } catch (e) { errorBanner.value = apiError(e) } finally { religionState.value.loading = false }
}
async function loadBanks() {
  bankState.value.loading = true
  try {
    const res = await otherBusinessCatalogService.getBanks({ keyword: bankState.value.keyword || null, is_active: bankState.value.isActive, page: bankState.value.page, page_size: bankState.value.pageSize })
    Object.assign(bankState.value, { items: res.data.items, total: res.data.total, page: res.data.page, pageSize: res.data.page_size })
  } catch (e) { errorBanner.value = apiError(e) } finally { bankState.value.loading = false }
}
async function loadSkills() {
  skillState.value.loading = true
  try {
    const res = await otherBusinessCatalogService.getSkills({ keyword: skillState.value.keyword || null, is_active: true, page: 1, page_size: 10 })
    Object.assign(skillState.value, { items: res.data.items, total: res.data.total })
  } catch (e) { errorBanner.value = apiError(e) } finally { skillState.value.loading = false }
}
async function loadCertificates() {
  certificateState.value.loading = true
  try {
    const res = await otherBusinessCatalogService.getCertificates({ keyword: certificateState.value.keyword || null, is_active: true, page: 1, page_size: 10 })
    Object.assign(certificateState.value, { items: res.data.items, total: res.data.total })
  } catch (e) { errorBanner.value = apiError(e) } finally { certificateState.value.loading = false }
}
async function loadLeaveTypes() {
  leaveTypeState.value.loading = true
  try {
    const res = await otherBusinessCatalogService.getLeaveTypes({ keyword: leaveTypeState.value.keyword || null, is_active: leaveTypeState.value.isActive, page: leaveTypeState.value.page, page_size: leaveTypeState.value.pageSize })
    Object.assign(leaveTypeState.value, { items: res.data.items, total: res.data.total, page: res.data.page, pageSize: res.data.page_size })
  } catch (e) { errorBanner.value = apiError(e) } finally { leaveTypeState.value.loading = false }
}
async function loadDocumentChecklistAppliesToOptions() {
  try {
    const res = await otherBusinessCatalogService.getDocumentChecklistAppliesToOptions()
    documentChecklistAppliesToOptions.value = res.data
  } catch (e) { errorBanner.value = apiError(e) }
}
async function loadDocumentChecklistTypes() {
  documentChecklistTypeState.value.loading = true
  try {
    const res = await otherBusinessCatalogService.getDocumentChecklistTypes({
      keyword: documentChecklistTypeState.value.keyword || null,
      is_active: documentChecklistTypeState.value.isActive,
      applies_to: documentChecklistTypeState.value.appliesTo,
      page: documentChecklistTypeState.value.page,
      page_size: documentChecklistTypeState.value.pageSize,
    })
    Object.assign(documentChecklistTypeState.value, { items: res.data.items, total: res.data.total, page: res.data.page, pageSize: res.data.page_size })
  } catch (e) { errorBanner.value = apiError(e) } finally { documentChecklistTypeState.value.loading = false }
}
async function loadTemplates() {
  templateState.value.loading = true
  try {
    const [listRes, healthRes] = await Promise.all([
      otherBusinessCatalogService.getContractTemplates({ keyword: templateState.value.keyword || null, is_active: templateState.value.isActive, document_kind: templateState.value.documentKind, page: templateState.value.page, page_size: templateState.value.pageSize }),
      otherBusinessCatalogService.getContractTemplateHealthSummary(),
    ])
    Object.assign(templateState.value, { items: listRes.data.items, total: listRes.data.total, page: listRes.data.page, pageSize: listRes.data.page_size })
    templateHealthItems.value = healthRes.data
  } catch (e) { errorBanner.value = apiError(e) } finally { templateState.value.loading = false }
}

async function loadContractTemplateFieldRegistry() {
  try {
    const res = await otherBusinessCatalogService.lookupContractTemplateFields()
    templateFieldRegistry.value = res.data
  } catch (e) {
    errorBanner.value = apiError(e)
  }
}

function resetContractCategoryForm() {
  editingContractCategory.value = null
  contractCategoryForm.value = { code: '', name: '', document_kind: 'labor_contract', legal_contract_type: null, business_group: '', default_term_months: null, sort_order: 0, is_active: true, description: '' }
}
function resetIdentityForm(kind: IdentityKind) {
  identityType.value = kind
  editingIdentity.value = null
  identityForm.value = { code: '', name: '', iso2_code: '', iso3_code: '', is_active: true }
}
function resetBankForm() { editingBank.value = null; bankForm.value = { code: '', name: '', short_name: '', bin_code: '', swift_code: '', is_active: true } }
function resetSkillForm() { editingSkill.value = null; skillForm.value = { code: '', name: '', skill_group: '', is_active: true } }
function resetCertificateForm() { editingCertificate.value = null; certificateForm.value = { code: '', name: '', certificate_group: '', issuer_name: '', expiry_policy: null, default_valid_months: null, is_active: true } }
function resetLeaveTypeForm() {
  editingLeaveType.value = null
  leaveTypeForm.value = {
    code: '', name: '',
    is_paid_leave: false, affects_annual_leave: false, allow_half_day: false, requires_attachment: false,
    color_tag: '', is_active: true, description: '',
    count_public_holidays: true,
    max_days_per_year: null, max_consecutive_days: null, min_advance_days: 0,
    carryover_allowed: false, carryover_cutoff_month: 3,
  }
}
function resetDocumentChecklistTypeForm() {
  editingDocumentChecklistType.value = null
  documentChecklistTypeForm.value = {
    code: '',
    name: '',
    description: '',
    is_required: true,
    has_expiry: false,
    applies_to: 'all',
    sort_order: 0,
    is_active: true,
  }
}
function resetTemplateForm() {
  editingTemplate.value = null
  selectedTemplateFile.value = null
  templateForm.value = { code: '', name: '', contract_category_id: null, document_kind: 'labor_contract', file_name: '', mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', storage_path: '', version_no: 1, is_active: true, note: '' }
}

function openCreateForActiveTab() {
  if (activeTab.value === 'contracts') return openCreateContractCategory()
  if (activeTab.value === 'identity') return openCreateIdentity('nationality')
  if (activeTab.value === 'banks') return openCreateBank()
  if (activeTab.value === 'competency') return openCreateSkill()
  if (activeTab.value === 'leaves') return openCreateLeaveType()
  if (activeTab.value === 'documentChecklist') return openCreateDocumentChecklistType()
  return openCreateTemplate()
}
function openCreateContractCategory() { dialogKind.value = 'contractCategory'; resetContractCategoryForm(); dialogVisible.value = true }
function openEditContractCategory(row: ContractCategoryRead) { dialogKind.value = 'contractCategory'; editingContractCategory.value = row; contractCategoryForm.value = { code: row.code, name: row.name, document_kind: row.document_kind, legal_contract_type: row.legal_contract_type, business_group: row.business_group || '', default_term_months: row.default_term_months, sort_order: row.sort_order, is_active: row.is_active, description: row.description || '' }; dialogVisible.value = true }
function openCreateIdentity(kind: IdentityKind) { dialogKind.value = 'identity'; resetIdentityForm(kind); dialogVisible.value = true }
function openEditIdentity(kind: IdentityKind, row: NationalityRead | EthnicityRead | ReligionRead) { dialogKind.value = 'identity'; identityType.value = kind; editingIdentity.value = row; identityForm.value = { code: row.code, name: row.name, iso2_code: 'iso2_code' in row ? (row.iso2_code || '') : '', iso3_code: 'iso3_code' in row ? (row.iso3_code || '') : '', is_active: row.is_active }; dialogVisible.value = true }
function openCreateBank() { dialogKind.value = 'bank'; resetBankForm(); dialogVisible.value = true }
function openEditBank(row: BankRead) { dialogKind.value = 'bank'; editingBank.value = row; bankForm.value = { code: row.code, name: row.name, short_name: row.short_name || '', bin_code: row.bin_code || '', swift_code: row.swift_code || '', is_active: row.is_active }; dialogVisible.value = true }
function openCreateSkill() { dialogKind.value = 'skill'; resetSkillForm(); dialogVisible.value = true }
function openEditSkill(row: SkillRead) { dialogKind.value = 'skill'; editingSkill.value = row; skillForm.value = { code: row.code, name: row.name, skill_group: row.skill_group || '', is_active: row.is_active }; dialogVisible.value = true }
function openCreateCertificate() { dialogKind.value = 'certificate'; resetCertificateForm(); dialogVisible.value = true }
function openEditCertificate(row: CertificateRead) { dialogKind.value = 'certificate'; editingCertificate.value = row; certificateForm.value = { code: row.code, name: row.name, certificate_group: row.certificate_group || '', issuer_name: row.issuer_name || '', expiry_policy: row.expiry_policy, default_valid_months: row.default_valid_months, is_active: row.is_active }; dialogVisible.value = true }
function openCreateLeaveType() { dialogKind.value = 'leaveType'; resetLeaveTypeForm(); dialogVisible.value = true }
function openEditLeaveType(row: LeaveTypeRead) {
  dialogKind.value = 'leaveType'
  editingLeaveType.value = row
  leaveTypeForm.value = {
    code: row.code, name: row.name,
    is_paid_leave: row.is_paid_leave, affects_annual_leave: row.affects_annual_leave,
    allow_half_day: row.allow_half_day, requires_attachment: row.requires_attachment,
    color_tag: row.color_tag || '', is_active: row.is_active, description: row.description || '',
    count_public_holidays: row.count_public_holidays,
    max_days_per_year: row.max_days_per_year ?? null,
    max_consecutive_days: row.max_consecutive_days ?? null,
    min_advance_days: row.min_advance_days,
    carryover_allowed: row.carryover_allowed,
    carryover_cutoff_month: row.carryover_cutoff_month,
  }
  dialogVisible.value = true
}
function openCreateDocumentChecklistType() { dialogKind.value = 'documentChecklistType'; resetDocumentChecklistTypeForm(); dialogVisible.value = true }
function openEditDocumentChecklistType(row: DocumentChecklistTypeRead) {
  dialogKind.value = 'documentChecklistType'
  editingDocumentChecklistType.value = row
  documentChecklistTypeForm.value = {
    code: row.code,
    name: row.name,
    description: row.description || '',
    is_required: row.is_required,
    has_expiry: row.has_expiry,
    applies_to: row.applies_to,
    sort_order: row.sort_order,
    is_active: row.is_active,
  }
  dialogVisible.value = true
}
function openCreateTemplate() { dialogKind.value = 'template'; resetTemplateForm(); dialogVisible.value = true }
function openEditTemplate(row: ContractTemplateRead) {
  dialogKind.value = 'template'
  editingTemplate.value = row
  selectedTemplateFile.value = null
  templateForm.value = { code: row.code, name: row.name, contract_category_id: row.contract_category_id, document_kind: row.document_kind, file_name: row.file_name, mime_type: row.mime_type, storage_path: row.storage_path || '', version_no: row.version_no, is_active: row.is_active, note: row.note || '' }
  dialogVisible.value = true
}

function onTemplateFileSelect(event: { files?: File[] }) {
  const file = event.files?.[0] || null
  selectedTemplateFile.value = file
  if (!file) return
  templateForm.value.file_name = file.name
  templateForm.value.mime_type = file.type || 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}

async function submitActiveDialog() {
  submitting.value = true
  try {
    if (dialogKind.value === 'contractCategory') {
      if (editingContractCategory.value) await otherBusinessCatalogService.updateContractCategory(editingContractCategory.value.id, { name: contractCategoryForm.value.name, document_kind: contractCategoryForm.value.document_kind, legal_contract_type: contractCategoryForm.value.legal_contract_type, business_group: contractCategoryForm.value.business_group || null, default_term_months: contractCategoryForm.value.default_term_months, sort_order: contractCategoryForm.value.sort_order, is_active: contractCategoryForm.value.is_active, description: contractCategoryForm.value.description || null })
      else await otherBusinessCatalogService.createContractCategory({ ...contractCategoryForm.value, business_group: contractCategoryForm.value.business_group || null, description: contractCategoryForm.value.description || null })
      await loadContractCategories()
    } else if (dialogKind.value === 'identity') {
      if (identityType.value === 'nationality') {
        if (editingIdentity.value) await otherBusinessCatalogService.updateNationality(editingIdentity.value.id, { name: identityForm.value.name, iso2_code: identityForm.value.iso2_code || null, iso3_code: identityForm.value.iso3_code || null, is_active: identityForm.value.is_active })
        else await otherBusinessCatalogService.createNationality({ code: identityForm.value.code, name: identityForm.value.name, iso2_code: identityForm.value.iso2_code || null, iso3_code: identityForm.value.iso3_code || null })
        await loadNationalities()
      } else if (identityType.value === 'ethnicity') {
        if (editingIdentity.value) await otherBusinessCatalogService.updateEthnicity(editingIdentity.value.id, { name: identityForm.value.name, is_active: identityForm.value.is_active })
        else await otherBusinessCatalogService.createEthnicity({ code: identityForm.value.code, name: identityForm.value.name })
        await loadEthnicities()
      } else {
        if (editingIdentity.value) await otherBusinessCatalogService.updateReligion(editingIdentity.value.id, { name: identityForm.value.name, is_active: identityForm.value.is_active })
        else await otherBusinessCatalogService.createReligion({ code: identityForm.value.code, name: identityForm.value.name })
        await loadReligions()
      }
    } else if (dialogKind.value === 'bank') {
      if (editingBank.value) await otherBusinessCatalogService.updateBank(editingBank.value.id, { name: bankForm.value.name, short_name: bankForm.value.short_name || null, bin_code: bankForm.value.bin_code || null, swift_code: bankForm.value.swift_code || null, is_active: bankForm.value.is_active })
      else await otherBusinessCatalogService.createBank({ ...bankForm.value, short_name: bankForm.value.short_name || null, bin_code: bankForm.value.bin_code || null, swift_code: bankForm.value.swift_code || null })
      await loadBanks()
    } else if (dialogKind.value === 'skill') {
      if (editingSkill.value) await otherBusinessCatalogService.updateSkill(editingSkill.value.id, { name: skillForm.value.name, skill_group: skillForm.value.skill_group || null, is_active: skillForm.value.is_active })
      else await otherBusinessCatalogService.createSkill({ code: skillForm.value.code, name: skillForm.value.name, skill_group: skillForm.value.skill_group || null })
      await loadSkills()
    } else if (dialogKind.value === 'certificate') {
      if (editingCertificate.value) await otherBusinessCatalogService.updateCertificate(editingCertificate.value.id, { name: certificateForm.value.name, certificate_group: certificateForm.value.certificate_group || null, issuer_name: certificateForm.value.issuer_name || null, expiry_policy: certificateForm.value.expiry_policy, default_valid_months: certificateForm.value.default_valid_months, is_active: certificateForm.value.is_active })
      else await otherBusinessCatalogService.createCertificate({ code: certificateForm.value.code, name: certificateForm.value.name, certificate_group: certificateForm.value.certificate_group || null, issuer_name: certificateForm.value.issuer_name || null, expiry_policy: certificateForm.value.expiry_policy, default_valid_months: certificateForm.value.default_valid_months })
      await loadCertificates()
    } else if (dialogKind.value === 'leaveType') {
      const leaveRuleFields = {
        count_public_holidays:  leaveTypeForm.value.count_public_holidays,
        max_days_per_year:      leaveTypeForm.value.max_days_per_year,
        max_consecutive_days:   leaveTypeForm.value.max_consecutive_days,
        min_advance_days:       leaveTypeForm.value.min_advance_days,
        carryover_allowed:      leaveTypeForm.value.carryover_allowed,
        carryover_cutoff_month: leaveTypeForm.value.carryover_cutoff_month,
      }
      if (editingLeaveType.value) await otherBusinessCatalogService.updateLeaveType(editingLeaveType.value.id, {
        name: leaveTypeForm.value.name, is_paid_leave: leaveTypeForm.value.is_paid_leave,
        affects_annual_leave: leaveTypeForm.value.affects_annual_leave, allow_half_day: leaveTypeForm.value.allow_half_day,
        requires_attachment: leaveTypeForm.value.requires_attachment, color_tag: leaveTypeForm.value.color_tag || null,
        is_active: leaveTypeForm.value.is_active, description: leaveTypeForm.value.description || null,
        ...leaveRuleFields,
      })
      else await otherBusinessCatalogService.createLeaveType({
        code: leaveTypeForm.value.code, name: leaveTypeForm.value.name,
        is_paid_leave: leaveTypeForm.value.is_paid_leave, affects_annual_leave: leaveTypeForm.value.affects_annual_leave,
        allow_half_day: leaveTypeForm.value.allow_half_day, requires_attachment: leaveTypeForm.value.requires_attachment,
        color_tag: leaveTypeForm.value.color_tag || null, description: leaveTypeForm.value.description || null,
        ...leaveRuleFields,
      })
      await loadLeaveTypes()
    } else if (dialogKind.value === 'documentChecklistType') {
      if (editingDocumentChecklistType.value) {
        await otherBusinessCatalogService.updateDocumentChecklistType(editingDocumentChecklistType.value.id, {
          name: documentChecklistTypeForm.value.name,
          description: documentChecklistTypeForm.value.description || null,
          is_required: documentChecklistTypeForm.value.is_required,
          has_expiry: documentChecklistTypeForm.value.has_expiry,
          applies_to: documentChecklistTypeForm.value.applies_to,
          sort_order: documentChecklistTypeForm.value.sort_order,
          is_active: documentChecklistTypeForm.value.is_active,
        })
      } else {
        await otherBusinessCatalogService.createDocumentChecklistType({
          code: documentChecklistTypeForm.value.code,
          name: documentChecklistTypeForm.value.name,
          description: documentChecklistTypeForm.value.description || null,
          is_required: documentChecklistTypeForm.value.is_required,
          has_expiry: documentChecklistTypeForm.value.has_expiry,
          applies_to: documentChecklistTypeForm.value.applies_to,
          sort_order: documentChecklistTypeForm.value.sort_order,
        })
      }
      await loadDocumentChecklistTypes()
    } else {
      if (!templateForm.value.contract_category_id) throw new Error('Chọn loại hợp đồng trước khi lưu mẫu')
      let templateRow: ContractTemplateRead
      if (editingTemplate.value) {
        const res = await otherBusinessCatalogService.updateContractTemplate(editingTemplate.value.id, { name: templateForm.value.name, contract_category_id: templateForm.value.contract_category_id, document_kind: templateForm.value.document_kind, file_name: templateForm.value.file_name, mime_type: templateForm.value.mime_type, storage_path: templateForm.value.storage_path || null, is_active: templateForm.value.is_active, note: templateForm.value.note || null })
        templateRow = res.data
      } else {
        const res = await otherBusinessCatalogService.createContractTemplate({ code: templateForm.value.code, name: templateForm.value.name, contract_category_id: templateForm.value.contract_category_id, document_kind: templateForm.value.document_kind, file_name: templateForm.value.file_name, mime_type: templateForm.value.mime_type, storage_path: templateForm.value.storage_path || null, version_no: templateForm.value.version_no, note: templateForm.value.note || null })
        templateRow = res.data
      }
      if (selectedTemplateFile.value) {
        const uploadRes = await otherBusinessCatalogService.uploadContractTemplateFile(templateRow.id, selectedTemplateFile.value)
        templateRow = uploadRes.data
        templateForm.value.storage_path = templateRow.storage_path || ''
        selectedTemplateFile.value = null
      }
      await loadTemplates()
    }
    toast.add({ severity: 'success', summary: 'Thành công', detail: editingMode.value ? 'Đã cập nhật dữ liệu' : 'Đã tạo dữ liệu mới', life: 2500 })
    dialogVisible.value = false
    errorBanner.value = ''
  } catch (e) {
    errorBanner.value = apiError(e)
    toast.add({ severity: 'error', summary: 'Không thể lưu dữ liệu', detail: errorBanner.value, life: 4000 })
  } finally {
    submitting.value = false
  }
}

async function openTemplatePlaceholders(row: ContractTemplateRead, inspectAfterOpen = false) {
  editingPlaceholderTemplate.value = row
  templateDocxSummary.value = null
  if (!templateFieldRegistry.value.length) {
    await loadContractTemplateFieldRegistry()
  }
  const res = await otherBusinessCatalogService.getContractTemplatePlaceholders(row.id)
  placeholderRows.value = res.data.map((item) => ({
    placeholder_key: item.placeholder_key,
    label: item.label,
    source_scope: item.source_scope,
    source_path: item.source_path,
    data_type: item.data_type,
    formatter: item.formatter,
    is_required: item.is_required,
    default_value: item.default_value,
    sort_order: item.sort_order,
    field_registry_token: resolveRegistryToken({
      source_scope: item.source_scope,
      source_path: item.source_path,
      data_type: item.data_type,
      formatter: item.formatter,
    }),
  }))
  placeholderDialogVisible.value = true
  if (inspectAfterOpen) {
    await inspectTemplateDocx()
  }
}
function addPlaceholderRow() {
  placeholderRows.value.push({
    placeholder_key: '',
    label: '',
    source_scope: 'employee',
    source_path: '',
    data_type: 'text',
    formatter: null,
    is_required: false,
    default_value: null,
    sort_order: placeholderRows.value.length * 10 + 10,
    field_registry_token: null,
  })
}
function removePlaceholderRow(index: number) {
  placeholderRows.value.splice(index, 1)
}

function sourceOriginLabel(row: PlaceholderRow): string {
  const token = row.field_registry_token
  if (!token) return ''
  const field = placeholderFieldOptions.value.find((item) => item.token === token)
  return field?.source_origin ?? ''
}

async function savePlaceholders() {
  if (!editingPlaceholderTemplate.value) return
  submittingPlaceholders.value = true
  try {
    const incompleteIndex = placeholderRows.value.findIndex((row) => !row.source_path || !row.source_scope || !row.data_type)
    if (incompleteIndex >= 0) {
      throw new Error(`Placeholder dòng ${incompleteIndex + 1} chưa chọn trường dữ liệu hợp lệ`)
    }
    await otherBusinessCatalogService.replaceContractTemplatePlaceholders(
      editingPlaceholderTemplate.value.id,
      placeholderRows.value.map(({ field_registry_token: _fieldRegistryToken, ...row }, index) => ({
        ...row,
        sort_order: (index + 1) * 10,
      })),
    )
    await loadTemplates()
    toast.add({ severity: 'success', summary: 'Đã lưu placeholder', detail: editingPlaceholderTemplate.value.name, life: 2500 })
    placeholderDialogVisible.value = false
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Không thể lưu placeholder', detail: apiError(e), life: 4000 })
  } finally {
    submittingPlaceholders.value = false
  }
}

async function inspectTemplateDocx() {
  if (!editingPlaceholderTemplate.value) return
  inspectingTemplateDocx.value = true
  try {
    const res = await otherBusinessCatalogService.inspectContractTemplateDocx(editingPlaceholderTemplate.value.id)
    templateDocxSummary.value = res.data
    placeholderRows.value = res.data.suggested_rows.map((item) => ({
      ...item,
      field_registry_token: resolveRegistryToken({
        source_scope: item.source_scope,
        source_path: item.source_path,
        data_type: item.data_type,
        formatter: item.formatter ?? null,
      }),
    }))
    toast.add({
      severity: 'success',
      summary: 'Đã quét DOCX',
      detail: `${res.data.supported_count} token có thể map tự động${res.data.unsupported_count ? `, ${res.data.unsupported_count} token cần xử lý tay` : ''}`,
      life: 3500,
    })
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Không thể quét DOCX', detail: apiError(e), life: 4000 })
  } finally {
    inspectingTemplateDocx.value = false
  }
}

function confirmDelete(kind: string, row: { id: number; name: string }) {
  confirm.require({
    message: `Khóa '${row.name}'?`,
    header: 'Xác nhận',
    acceptLabel: 'Khóa',
    rejectLabel: 'Hủy',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        if (kind === 'contractCategory') await otherBusinessCatalogService.deleteContractCategory(row.id)
        else if (kind === 'nationality') await otherBusinessCatalogService.deleteNationality(row.id)
        else if (kind === 'ethnicity') await otherBusinessCatalogService.deleteEthnicity(row.id)
        else if (kind === 'religion') await otherBusinessCatalogService.deleteReligion(row.id)
        else if (kind === 'bank') await otherBusinessCatalogService.deleteBank(row.id)
        else if (kind === 'skill') await otherBusinessCatalogService.deleteSkill(row.id)
        else if (kind === 'certificate') await otherBusinessCatalogService.deleteCertificate(row.id)
        else if (kind === 'leaveType') await otherBusinessCatalogService.deleteLeaveType(row.id)
        else if (kind === 'documentChecklistType') await otherBusinessCatalogService.deleteDocumentChecklistType(row.id)
        else if (kind === 'template') await otherBusinessCatalogService.deleteContractTemplate(row.id)

        if (kind === 'contractCategory') await loadContractCategories()
        else if (kind === 'nationality') await loadNationalities()
        else if (kind === 'ethnicity') await loadEthnicities()
        else if (kind === 'religion') await loadReligions()
        else if (kind === 'bank') await loadBanks()
        else if (kind === 'skill') await loadSkills()
        else if (kind === 'certificate') await loadCertificates()
        else if (kind === 'leaveType') await loadLeaveTypes()
        else if (kind === 'documentChecklistType') await loadDocumentChecklistTypes()
        else if (kind === 'template') await loadTemplates()
        toast.add({ severity: 'success', summary: 'Đã khóa dữ liệu', detail: row.name, life: 2500 })
      } catch (e) {
        toast.add({ severity: 'error', summary: 'Không thể khóa dữ liệu', detail: apiError(e), life: 4000 })
      }
    },
  })
}

function confirmToggleTemplateActive(row: ContractTemplateRead, nextState: boolean) {
  const verb = nextState ? 'mở khóa' : 'khóa'
  confirm.require({
    message: nextState
      ? `Mở khóa mẫu '${row.name}' để tiếp tục dùng cho các lần generate mới?`
      : `Khóa mẫu '${row.name}'? Mẫu đã khóa sẽ không dùng được cho các lần generate mới nhưng vẫn giữ lại để tra cứu lịch sử.`,
    header: nextState ? 'Mở khóa mẫu hợp đồng' : 'Khóa mẫu hợp đồng',
    acceptLabel: nextState ? 'Mở khóa' : 'Khóa',
    rejectLabel: 'Hủy',
    acceptClass: nextState ? 'p-button-success' : 'p-button-warning',
    accept: async () => {
      try {
        await otherBusinessCatalogService.updateContractTemplate(row.id, { is_active: nextState })
        await loadTemplates()
        toast.add({
          severity: 'success',
          summary: nextState ? 'Đã mở khóa mẫu' : 'Đã khóa mẫu',
          detail: row.name,
          life: 2500,
        })
      } catch (e) {
        toast.add({
          severity: 'error',
          summary: `Không thể ${verb} mẫu`,
          detail: apiError(e),
          life: 4000,
        })
      }
    },
  })
}

function confirmHardDeleteTemplate(row: ContractTemplateRead) {
  confirm.require({
    message:
      `Xóa hẳn mẫu '${row.name}'? Hành động này không thể hoàn tác. ` +
      `Hệ thống sẽ xóa metadata, placeholder và file DOCX của mẫu. ` +
      `Các hợp đồng đã xuất trước đó không bị xóa, nhưng sẽ không thể generate lại từ mẫu này.`,
    header: 'Xóa hẳn mẫu hợp đồng',
    acceptLabel: 'Xóa hẳn',
    rejectLabel: 'Hủy',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await otherBusinessCatalogService.hardDeleteContractTemplate(row.id)
        await loadTemplates()
        toast.add({
          severity: 'success',
          summary: 'Đã xóa hẳn mẫu',
          detail: row.name,
          life: 2500,
        })
      } catch (e) {
        toast.add({
          severity: 'error',
          summary: 'Không thể xóa hẳn mẫu',
          detail: apiError(e),
          life: 4500,
        })
      }
    },
  })
}

onMounted(async () => {
  await Promise.all([
    loadContractCategories(),
    loadNationalities(),
    loadEthnicities(),
    loadReligions(),
    loadBanks(),
    loadSkills(),
    loadCertificates(),
    loadLeaveTypes(),
    loadDocumentChecklistAppliesToOptions(),
    loadDocumentChecklistTypes(),
    loadTemplates(),
    loadContractTemplateFieldRegistry(),
    loadContractCategoryLookup(),
  ])
})
</script>
