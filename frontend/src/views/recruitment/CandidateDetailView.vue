<template>
  <div class="rc-detail" v-if="candidate">
    <!-- Header -->
    <div class="rc-detail-header">
      <div class="rc-header-left">
        <Button
          icon="pi pi-arrow-left"
          text
          rounded
          severity="secondary"
          @click="router.push('/recruitment?tab=candidates')"
        />
        <div>
          <div
            style="
              display: flex;
              align-items: center;
              gap: 0.6rem;
              flex-wrap: wrap;
            "
          >
            <span class="rc-jr-code">{{ candidate.full_name }}</span>
            <Tag
              v-if="candidate.gender_label"
              :value="candidate.gender_label"
              severity="secondary"
            />
            <Tag
              :value="candidate.identity_strength_label"
              :severity="identityStrengthSeverity(candidate.identity_strength)"
            />
          </div>
          <div class="rc-meta-row" style="margin-top: 0.2rem">
            <span v-if="candidate.personal_email">{{
              candidate.personal_email
            }}</span>
            <span v-if="candidate.personal_email && candidate.phone_number"
              >·</span
            >
            <span v-if="candidate.phone_number">{{
              candidate.phone_number
            }}</span>
            <span
              v-if="
                (candidate.personal_email || candidate.phone_number) &&
                candidate.source_channel_name
              "
              >·</span
            >
            <span v-if="candidate.source_channel_name">{{
              candidate.source_channel_name
            }}</span>
          </div>
        </div>
      </div>
      <div class="rc-header-right">
        <Button
          label="Gắn vào JR"
          icon="pi pi-link"
          severity="info"
          outlined
          @click="showApplyDialog = true"
        />
        <Button
          label="Sửa"
          icon="pi pi-pencil"
          severity="secondary"
          outlined
          @click="openEdit"
        />
      </div>
    </div>

    <!-- Tabs -->
    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="info">Thông tin</Tab>
        <Tab value="education">Học vấn & Kinh nghiệm</Tab>
        <Tab value="skills">Kỹ năng</Tab>
        <Tab value="attachments">Hồ sơ đính kèm</Tab>
        <Tab value="applications"
          >Ứng tuyển ({{ candidate.active_applications }})</Tab
        >
        <Tab value="communications">Giao tiếp</Tab>
      </TabList>

      <TabPanels>
        <!-- TAB: Thông tin -->
        <TabPanel value="info">
          <div class="section-stack" style="padding-top: 0.75rem">
            <div class="section-card">
              <div class="section-header">
                <span class="section-title">Độ mạnh định danh</span>
              </div>
              <div
                style="
                  display: flex;
                  align-items: center;
                  gap: 0.75rem;
                  flex-wrap: wrap;
                "
              >
                <Tag
                  :value="candidate.identity_strength_label"
                  :severity="
                    identityStrengthSeverity(candidate.identity_strength)
                  "
                />
                <span
                  class="rc-muted"
                  v-if="candidate.identity_strength === 'weak'"
                >
                  Hồ sơ chưa có email, SĐT, CCCD/CMND hoặc hộ chiếu để đối chiếu
                  trùng hiệu quả.
                </span>
              </div>
            </div>

            <div class="section-card">
              <div class="section-header">
                <span class="section-title">Trạng thái chuyển đổi</span>
              </div>
              <div
                v-if="candidate.conversion_ready"
                class="rc-conversion-ready"
              >
                Hồ sơ đã đủ dữ liệu cốt lõi để convert sang nhân viên ở bước
                13.5.
              </div>
              <div v-else class="rc-conversion-missing">
                <span>Thiếu dữ liệu cốt lõi:</span>
                <strong>{{
                  formatMissingFields(candidate.conversion_missing_fields)
                }}</strong>
              </div>
            </div>

            <div class="section-card">
              <div class="section-header">
                <span class="section-title">Thông tin cá nhân</span>
              </div>
              <div class="info-grid">
                <div class="info-row" v-if="candidate.date_of_birth">
                  <span class="info-label">Ngày sinh</span>
                  <span class="info-value">{{
                    formatDate(candidate.date_of_birth)
                  }}</span>
                </div>
                <div
                  class="info-row"
                  v-if="
                    candidate.nationality_name || candidate.raw_nationality_text
                  "
                >
                  <span class="info-label">Quốc tịch</span>
                  <span class="info-value">{{
                    candidate.nationality_name ?? candidate.raw_nationality_text
                  }}</span>
                </div>
                <div class="info-row" v-if="candidate.ethnicity_name">
                  <span class="info-label">Dân tộc</span>
                  <span class="info-value">{{ candidate.ethnicity_name }}</span>
                </div>
                <div class="info-row" v-if="candidate.religion_name">
                  <span class="info-label">Tôn giáo</span>
                  <span class="info-value">{{ candidate.religion_name }}</span>
                </div>
                <div class="info-row" v-if="candidate.id_number">
                  <span class="info-label">CCCD / Hộ chiếu</span>
                  <span class="info-value">{{ candidate.id_number }}</span>
                </div>
                <div class="info-row" v-if="candidate.id_issued_on">
                  <span class="info-label">Ngày cấp giấy tờ</span>
                  <span class="info-value">{{
                    formatDate(candidate.id_issued_on)
                  }}</span>
                </div>
                <div class="info-row" v-if="candidate.id_issued_by">
                  <span class="info-label">Nơi cấp giấy tờ</span>
                  <span class="info-value">{{ candidate.id_issued_by }}</span>
                </div>
                <div class="info-row" v-if="candidate.personal_tax_code">
                  <span class="info-label">Mã số thuế cá nhân</span>
                  <span class="info-value">{{
                    candidate.personal_tax_code
                  }}</span>
                </div>
                <div class="info-row" v-if="candidate.bhxh_code">
                  <span class="info-label">Mã số BHXH</span>
                  <span class="info-value">{{ candidate.bhxh_code }}</span>
                </div>
                <div class="info-row" v-if="candidate.address">
                  <span class="info-label">Địa chỉ</span>
                  <span class="info-value">{{ candidate.address }}</span>
                </div>
              </div>
            </div>

            <div class="section-card">
              <div class="section-header">
                <span class="section-title">Nghề nghiệp</span>
              </div>
              <div class="info-grid">
                <div class="info-row" v-if="candidate.current_position">
                  <span class="info-label">Vị trí hiện tại</span>
                  <span class="info-value">{{
                    candidate.current_position
                  }}</span>
                </div>
                <div class="info-row" v-if="candidate.current_company">
                  <span class="info-label">Công ty hiện tại</span>
                  <span class="info-value">{{
                    candidate.current_company
                  }}</span>
                </div>
                <div class="info-row" v-if="candidate.expected_salary">
                  <span class="info-label">Lương kỳ vọng</span>
                  <span class="info-value">{{
                    formatSalary(candidate.expected_salary)
                  }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">Kênh nguồn</span>
                  <span class="info-value">{{
                    candidate.source_channel_name ?? "—"
                  }}</span>
                </div>
                <div class="info-row" v-if="candidate.source_note">
                  <span class="info-label">Ghi chú nguồn</span>
                  <span class="info-value">{{ candidate.source_note }}</span>
                </div>
              </div>
            </div>

            <div
              class="section-card"
              v-if="
                candidate.passport_number ||
                candidate.passport_issued_on ||
                candidate.passport_expires_on ||
                candidate.work_permit_number
              "
            >
              <div class="section-header">
                <span class="section-title">Giấy tờ nước ngoài</span>
              </div>
              <div class="info-grid">
                <div class="info-row" v-if="candidate.passport_number">
                  <span class="info-label">Số hộ chiếu</span>
                  <span class="info-value">{{
                    candidate.passport_number
                  }}</span>
                </div>
                <div class="info-row" v-if="candidate.passport_issued_on">
                  <span class="info-label">Ngày cấp hộ chiếu</span>
                  <span class="info-value">{{
                    formatDate(candidate.passport_issued_on)
                  }}</span>
                </div>
                <div class="info-row" v-if="candidate.passport_expires_on">
                  <span class="info-label">Ngày hết hạn hộ chiếu</span>
                  <span class="info-value">{{
                    formatDate(candidate.passport_expires_on)
                  }}</span>
                </div>
                <div class="info-row" v-if="candidate.work_permit_number">
                  <span class="info-label">Giấy phép lao động</span>
                  <span class="info-value">{{
                    candidate.work_permit_number
                  }}</span>
                </div>
                <div class="info-row" v-if="candidate.work_permit_issued_on">
                  <span class="info-label">Ngày cấp GPLĐ</span>
                  <span class="info-value">{{
                    formatDate(candidate.work_permit_issued_on)
                  }}</span>
                </div>
                <div class="info-row" v-if="candidate.work_permit_expires_on">
                  <span class="info-label">Ngày hết hạn GPLĐ</span>
                  <span class="info-value">{{
                    formatDate(candidate.work_permit_expires_on)
                  }}</span>
                </div>
              </div>
            </div>

            <div class="section-card" v-if="candidate.tags?.length">
              <div class="section-header">
                <span class="section-title">Tags</span>
              </div>
              <div
                style="
                  display: flex;
                  flex-wrap: wrap;
                  gap: 0.4rem;
                  padding-top: 0.25rem;
                "
              >
                <Tag
                  v-for="tag in candidate.tags"
                  :key="tag"
                  :value="tag"
                  severity="secondary"
                />
              </div>
            </div>

            <div class="section-card" v-if="candidate.internal_note">
              <div class="section-header">
                <span class="section-title">Ghi chú nội bộ</span>
              </div>
              <div style="white-space: pre-wrap; font-size: 0.875rem">
                {{ candidate.internal_note }}
              </div>
            </div>
          </div>
        </TabPanel>

        <!-- TAB: Học vấn & Kinh nghiệm -->
        <TabPanel value="education">
          <div class="section-stack" style="padding-top: 0.75rem">
            <div class="section-card">
              <div class="section-header">
                <span class="section-title">Học vấn</span>
                <Button
                  icon="pi pi-plus"
                  text
                  rounded
                  size="small"
                  @click="openAddEdu"
                  v-tooltip.top="'Thêm'"
                />
              </div>
              <div
                v-if="!candidate.educations.length"
                class="rc-jd-empty"
                style="padding: 0.5rem 0"
              >
                Chưa có thông tin
              </div>
              <div
                v-for="edu in candidate.educations"
                :key="edu.id"
                class="cand-sub-row"
              >
                <div class="cand-sub-main">
                  <span class="cand-sub-title">{{
                    edu.institution_name ?? "—"
                  }}</span>
                  <span v-if="edu.is_main_education">
                    <Tag
                      value="Chính"
                      severity="info"
                      style="font-size: 0.72rem"
                  /></span>
                  <div class="rc-muted" style="font-size: 0.8rem">
                    {{ edu.major_name ?? "" }}
                    <span v-if="edu.graduation_year">
                      · {{ edu.graduation_year }}</span
                    >
                    <span v-if="edu.education_level_name">
                      · {{ edu.education_level_name }}</span
                    >
                  </div>
                  <div
                    v-if="edu.note"
                    class="rc-muted"
                    style="font-size: 0.78rem"
                  >
                    {{ edu.note }}
                  </div>
                </div>
                <div class="cand-sub-actions">
                  <Button
                    icon="pi pi-pencil"
                    text
                    rounded
                    size="small"
                    severity="secondary"
                    @click="openEditEdu(edu)"
                  />
                  <Button
                    icon="pi pi-trash"
                    text
                    rounded
                    size="small"
                    severity="danger"
                    @click="confirmDeleteEdu(edu)"
                  />
                </div>
              </div>
            </div>

            <div class="section-card">
              <div class="section-header">
                <span class="section-title">Kinh nghiệm làm việc</span>
                <Button
                  icon="pi pi-plus"
                  text
                  rounded
                  size="small"
                  @click="openAddExp"
                  v-tooltip.top="'Thêm'"
                />
              </div>
              <div
                v-if="!candidate.work_experiences.length"
                class="rc-jd-empty"
                style="padding: 0.5rem 0"
              >
                Chưa có thông tin
              </div>
              <div
                v-for="exp in candidate.work_experiences"
                :key="exp.id"
                class="cand-sub-row"
              >
                <div class="cand-sub-main">
                  <span class="cand-sub-title">{{ exp.company_name }}</span>
                  <div class="rc-muted" style="font-size: 0.8rem">
                    {{ exp.position_name ?? "" }}
                    <span v-if="exp.start_date">
                      · {{ formatDate(exp.start_date) }} –
                      {{
                        exp.end_date ? formatDate(exp.end_date) : "Hiện tại"
                      }}</span
                    >
                  </div>
                  <div
                    v-if="exp.description"
                    class="rc-muted"
                    style="font-size: 0.78rem; white-space: pre-wrap"
                  >
                    {{ exp.description }}
                  </div>
                </div>
                <div class="cand-sub-actions">
                  <Button
                    icon="pi pi-pencil"
                    text
                    rounded
                    size="small"
                    severity="secondary"
                    @click="openEditExp(exp)"
                  />
                  <Button
                    icon="pi pi-trash"
                    text
                    rounded
                    size="small"
                    severity="danger"
                    @click="confirmDeleteExp(exp)"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Education Dialog -->
          <Dialog
            v-model:visible="showEduDialog"
            :header="editingEdu ? 'Sửa học vấn' : 'Thêm học vấn'"
            modal
            style="width: 460px"
          >
            <div class="rc-form">
              <div class="rc-field">
                <label class="rc-label"
                  >Trường / Cơ sở đào tạo <span class="rc-req">*</span></label
                >
                <AutoComplete
                  v-model="selectedInstitution"
                  :suggestions="institutionSuggestions"
                  option-label="name"
                  dropdown
                  force-selection
                  @complete="searchInstitutions"
                  :invalid="!!eduErrors.institution_id"
                >
                  <template #option="{ option }">
                    <div>
                      <div>{{ option.name }}</div>
                      <small class="rc-muted">{{
                        option.short_name || option.code || ""
                      }}</small>
                    </div>
                  </template>
                </AutoComplete>
                <small v-if="eduErrors.institution_id" class="rc-api-error">{{
                  eduErrors.institution_id
                }}</small>
              </div>
              <div class="rc-field">
                <label class="rc-label">Chuyên ngành</label>
                <AutoComplete
                  v-model="selectedMajor"
                  :suggestions="majorSuggestions"
                  option-label="name"
                  dropdown
                  force-selection
                  @complete="searchMajors"
                >
                  <template #option="{ option }">
                    <div>
                      <div>{{ option.name }}</div>
                      <small class="rc-muted">{{
                        option.major_group || option.code || ""
                      }}</small>
                    </div>
                  </template>
                </AutoComplete>
              </div>
              <div class="rc-field">
                <label class="rc-label"
                  >Trình độ <span class="rc-req">*</span></label
                >
                <Select
                  v-model="eduForm.education_level_id"
                  :options="educationLevelOptions"
                  option-label="label"
                  option-value="value"
                  :invalid="!!eduErrors.education_level_id"
                />
                <small
                  v-if="eduErrors.education_level_id"
                  class="rc-api-error"
                  >{{ eduErrors.education_level_id }}</small
                >
              </div>
              <div class="rc-row">
                <div class="rc-field">
                  <label class="rc-label">Năm tốt nghiệp</label>
                  <InputNumber
                    v-model="eduForm.graduation_year"
                    :use-grouping="false"
                    :min="1950"
                    :max="2100"
                  />
                </div>
                <div class="rc-field">
                  <label class="rc-label">Loại bằng</label>
                  <InputText v-model="eduForm.diploma_type" />
                </div>
              </div>
              <div class="rc-row">
                <div
                  class="rc-field"
                  style="justify-content: flex-end; padding-top: 1.5rem"
                >
                  <label
                    style="
                      display: flex;
                      align-items: center;
                      gap: 0.5rem;
                      cursor: pointer;
                      font-size: 0.875rem;
                    "
                  >
                    <ToggleSwitch v-model="eduForm.is_main_education" />
                    Học vấn chính
                  </label>
                </div>
              </div>
              <div class="rc-field">
                <label class="rc-label">Ghi chú</label>
                <InputText v-model="eduForm.note" />
              </div>
            </div>
            <template #footer>
              <Button
                label="Hủy"
                severity="secondary"
                text
                @click="showEduDialog = false"
              />
              <Button label="Lưu" :loading="saving" @click="saveEdu" />
            </template>
          </Dialog>

          <!-- Work Exp Dialog -->
          <Dialog
            v-model:visible="showExpDialog"
            :header="editingExp ? 'Sửa kinh nghiệm' : 'Thêm kinh nghiệm'"
            modal
            style="width: 460px"
          >
            <div class="rc-form">
              <div class="rc-field">
                <label class="rc-label"
                  >Công ty <span class="rc-req">*</span></label
                >
                <InputText v-model="expForm.company_name" />
              </div>
              <div class="rc-field">
                <label class="rc-label">Vị trí</label>
                <InputText v-model="expForm.position_name" />
              </div>
              <div class="rc-row">
                <div class="rc-field">
                  <label class="rc-label">Từ ngày</label>
                  <DatePicker
                    v-model="expStartDate"
                    date-format="dd/mm/yy"
                    show-button-bar
                  />
                </div>
                <div class="rc-field">
                  <label class="rc-label"
                    >Đến ngày
                    <span class="rc-optional">(trống = hiện tại)</span></label
                  >
                  <DatePicker
                    v-model="expEndDate"
                    date-format="dd/mm/yy"
                    show-button-bar
                  />
                </div>
              </div>
              <div class="rc-field">
                <label class="rc-label">Mô tả</label>
                <Textarea v-model="expForm.description" rows="2" auto-resize />
              </div>
            </div>
            <template #footer>
              <Button
                label="Hủy"
                severity="secondary"
                text
                @click="showExpDialog = false"
              />
              <Button label="Lưu" :loading="saving" @click="saveExp" />
            </template>
          </Dialog>
        </TabPanel>

        <!-- TAB: Kỹ năng -->
        <TabPanel value="skills">
          <div class="section-card" style="margin-top: 0.75rem">
            <div class="section-header">
              <span class="section-title">Kỹ năng</span>
              <Button
                icon="pi pi-plus"
                text
                rounded
                size="small"
                @click="openAddSkill"
                v-tooltip.top="'Thêm kỹ năng'"
              />
            </div>
            <div
              style="
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                padding-top: 0.5rem;
              "
            >
              <div
                v-for="sk in candidate.skills"
                :key="sk.id"
                class="cand-skill-chip"
                :title="sk.note || ''"
              >
                <span>{{ sk.skill_name }}</span>
                <span
                  v-if="sk.proficiency_level"
                  class="rc-muted"
                  style="font-size: 0.75rem"
                  >·{{ proficiencyLabel(sk.proficiency_level) }}</span
                >
                <span
                  v-if="sk.skill_group"
                  class="rc-muted"
                  style="font-size: 0.75rem"
                  >·{{ sk.skill_group }}</span
                >
                <Button
                  icon="pi pi-times"
                  text
                  rounded
                  size="small"
                  severity="secondary"
                  style="width: 1.25rem; height: 1.25rem; padding: 0"
                  @click="confirmDeleteSkill(sk)"
                />
              </div>
            </div>
            <div
              v-if="!candidate.skills.length"
              class="rc-jd-empty"
              style="padding: 0.5rem 0"
            >
              Chưa có kỹ năng
            </div>
          </div>

          <Dialog
            v-model:visible="showSkillDialog"
            header="Thêm kỹ năng"
            modal
            style="width: 380px"
          >
            <div class="rc-form">
              <div class="rc-field">
                <label class="rc-label"
                  >Kỹ năng <span class="rc-req">*</span></label
                >
                <Select
                  v-model="skillForm.skill_id"
                  :options="skillOptions"
                  option-label="label"
                  option-value="value"
                  placeholder="Chọn kỹ năng"
                  filter
                  :invalid="!!skillErrors.skill_id"
                />
                <small v-if="skillErrors.skill_id" class="rc-api-error">{{
                  skillErrors.skill_id
                }}</small>
              </div>
              <div class="rc-field">
                <label class="rc-label"
                  >Mức độ <span class="rc-req">*</span></label
                >
                <Select
                  v-model="skillForm.proficiency_level"
                  :options="proficiencyOptions"
                  option-label="label"
                  option-value="value"
                  placeholder="Chọn mức độ"
                  :invalid="!!skillErrors.proficiency_level"
                />
                <small
                  v-if="skillErrors.proficiency_level"
                  class="rc-api-error"
                  >{{ skillErrors.proficiency_level }}</small
                >
              </div>
              <div class="rc-field">
                <label class="rc-label">Ghi chú</label>
                <Textarea v-model="skillForm.note" rows="2" auto-resize />
              </div>
            </div>
            <template #footer>
              <Button
                label="Hủy"
                severity="secondary"
                text
                @click="showSkillDialog = false"
              />
              <Button label="Thêm" :loading="saving" @click="saveSkill" />
            </template>
          </Dialog>
        </TabPanel>

        <!-- TAB: Hồ sơ đính kèm -->
        <TabPanel value="attachments">
          <div class="section-card" style="margin-top: 0.75rem">
            <div class="section-header">
              <span class="section-title">Tài liệu đính kèm</span>
              <Button
                icon="pi pi-upload"
                text
                rounded
                size="small"
                @click="showUploadDialog = true"
                v-tooltip.top="'Upload file'"
              />
            </div>
            <div
              v-if="!candidate.attachments.length"
              class="rc-jd-empty"
              style="padding: 0.5rem 0"
            >
              Chưa có tài liệu đính kèm
            </div>
            <div
              v-for="att in candidate.attachments"
              :key="att.id"
              class="cand-sub-row"
            >
              <div class="cand-sub-main">
                <span class="cand-sub-title">{{ att.file_name }}</span>
                <div class="rc-muted" style="font-size: 0.78rem">
                  {{ att.attachment_type_label }}
                  <span v-if="att.file_size">
                    · {{ formatFileSize(att.file_size) }}</span
                  >
                  <span> · {{ formatDatetime(att.uploaded_at) }}</span>
                </div>
                <div
                  v-if="att.note"
                  class="rc-muted"
                  style="font-size: 0.78rem"
                >
                  {{ att.note }}
                </div>
              </div>
              <div class="cand-sub-actions">
                <a :href="downloadUrl(att)" target="_blank">
                  <Button
                    icon="pi pi-download"
                    text
                    rounded
                    size="small"
                    severity="info"
                    v-tooltip.top="'Tải xuống'"
                  />
                </a>
                <Button
                  icon="pi pi-trash"
                  text
                  rounded
                  size="small"
                  severity="danger"
                  @click="confirmDeleteAtt(att)"
                />
              </div>
            </div>
          </div>

          <Dialog
            v-model:visible="showUploadDialog"
            header="Upload tài liệu"
            modal
            style="width: 420px"
          >
            <div class="rc-form">
              <div class="rc-field">
                <label class="rc-label"
                  >Loại tài liệu <span class="rc-req">*</span></label
                >
                <Select
                  v-model="uploadForm.attachment_type"
                  :options="attachmentTypeOptions"
                  option-label="label"
                  option-value="value"
                  placeholder="Chọn loại"
                />
              </div>
              <div class="rc-field">
                <label class="rc-label"
                  >File <span class="rc-req">*</span></label
                >
                <FileUpload
                  mode="basic"
                  :auto="false"
                  accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                  :max-file-size="20971520"
                  choose-label="Chọn file"
                  @select="onFileSelect"
                />
                <small class="rc-muted"
                  >PDF, Word, JPG, PNG — tối đa 20MB</small
                >
              </div>
              <div class="rc-field">
                <label class="rc-label">Ghi chú</label>
                <InputText v-model="uploadForm.note" />
              </div>
              <p v-if="uploadError" class="rc-api-error">
                <i class="pi pi-exclamation-circle" />{{ uploadError }}
              </p>
            </div>
            <template #footer>
              <Button
                label="Hủy"
                severity="secondary"
                text
                @click="showUploadDialog = false"
              />
              <Button label="Upload" :loading="uploading" @click="doUpload" />
            </template>
          </Dialog>
        </TabPanel>

        <!-- TAB: Giao tiếp -->
        <TabPanel value="communications">
          <CommunicationTab :candidate-id="candidateId" />
        </TabPanel>

        <!-- TAB: Ứng tuyển -->
        <TabPanel value="applications">
          <div class="section-card" style="margin-top: 0.75rem">
            <div class="section-header">
              <span class="section-title">Danh sách JR đã ứng tuyển</span>
            </div>
            <DataTable
              :value="applications"
              size="small"
              :loading="appsLoading"
            >
              <template #empty
                ><div class="rc-empty">Chưa ứng tuyển vào JR nào</div></template
              >
              <Column header="Mã JR" style="width: 120px">
                <template #body="{ data }: { data: ApplicationRead }">
                  <RouterLink
                    :to="`/recruitment/applications/${data.id}`"
                    class="rc-code-link"
                  >
                    {{ data.job_requisition_code }}
                  </RouterLink>
                </template>
              </Column>
              <Column header="Vị trí / Phòng ban">
                <template #body="{ data }: { data: ApplicationRead }">
                  <span>{{ data.job_position_name }}</span>
                  <div class="rc-muted" style="font-size: 0.78rem">
                    {{ data.department_name }}
                  </div>
                </template>
              </Column>
              <Column header="Giai đoạn" style="width: 130px">
                <template #body="{ data }: { data: ApplicationRead }">
                  <Tag
                    :value="stageLabel(data.current_stage)"
                    :severity="stageSeverity(data.current_stage)"
                  />
                </template>
              </Column>
              <Column header="Ngày nộp" style="width: 110px">
                <template #body="{ data }: { data: ApplicationRead }">
                  {{ formatDate(data.applied_date) }}
                </template>
              </Column>
              <Column header="" style="width: 72px; text-align: right">
                <template #body="{ data }: { data: ApplicationRead }">
                  <RouterLink :to="`/recruitment/applications/${data.id}`">
                    <Button
                      icon="pi pi-eye"
                      text
                      rounded
                      size="small"
                      severity="secondary"
                      v-tooltip.top="'Xem quy trình'"
                    />
                  </RouterLink>
                </template>
              </Column>
            </DataTable>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <!-- Apply to JR dialog -->
    <Dialog
      v-model:visible="showApplyDialog"
      header="Gắn vào Yêu cầu tuyển dụng"
      modal
      style="width: 440px"
    >
      <div class="rc-form">
        <div class="rc-field">
          <label class="rc-label"
            >Yêu cầu tuyển dụng (JR) <span class="rc-req">*</span></label
          >
          <Select
            v-model="applyForm.job_requisition_id"
            :options="activeJRs"
            option-label="label"
            option-value="value"
            placeholder="Chọn JR"
            filter
          />
        </div>
        <div class="rc-field">
          <label class="rc-label">Ngày ứng tuyển</label>
          <DatePicker
            v-model="applyDate"
            date-format="dd/mm/yy"
            show-button-bar
          />
        </div>
        <div class="rc-field">
          <label class="rc-label">Kênh</label>
          <Select
            v-model="applyForm.source_channel_id"
            :options="channels"
            option-label="name"
            option-value="id"
            placeholder="Chọn kênh"
            show-clear
          />
        </div>
        <div class="rc-field">
          <label class="rc-label">Ghi chú nội bộ</label>
          <Textarea v-model="applyForm.internal_note" rows="2" auto-resize />
        </div>
        <p v-if="applyError" class="rc-api-error">
          <i class="pi pi-exclamation-circle" />{{ applyError }}
        </p>
      </div>
      <template #footer>
        <Button
          label="Hủy"
          severity="secondary"
          text
          @click="showApplyDialog = false"
        />
        <Button label="Gắn" :loading="saving" @click="doApply" />
      </template>
    </Dialog>

    <!-- Edit dialog -->
    <CandidateFormDialog
      v-model:visible="showEditDialog"
      :editing="candidate"
      @saved="onEdited"
    />
  </div>

  <div v-else-if="pageLoading" class="loading-state">
    <i class="pi pi-spin pi-spinner" /><span>Đang tải...</span>
  </div>
  <div v-else class="error-state">
    <i class="pi pi-exclamation-triangle" /><span>Không tìm thấy ứng viên</span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import AutoComplete from "primevue/autocomplete";
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import DatePicker from "primevue/datepicker";
import Dialog from "primevue/dialog";
import FileUpload from "primevue/fileupload";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Tab from "primevue/tab";
import TabList from "primevue/tablist";
import TabPanel from "primevue/tabpanel";
import TabPanels from "primevue/tabpanels";
import Tabs from "primevue/tabs";
import Tag from "primevue/tag";
import Textarea from "primevue/textarea";
import ToggleSwitch from "primevue/toggleswitch";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import educationCatalogService, {
  type EducationalInstitutionRead,
  type EducationMajorRead,
} from "@/services/educationCatalogService";
import otherBusinessCatalogService from "@/services/otherBusinessCatalogService";
import recruitmentService, {
  type ApplicationRead,
  type CandidateAttachmentRead,
  type CandidateEducationRead,
  type CandidateRead,
  type CandidateSkillCreate,
  type CandidateSkillRead,
  type CandidateWorkExpRead,
  type RecruitmentChannelRead,
} from "@/services/recruitmentService";
import CandidateFormDialog from "./components/CandidateFormDialog.vue";
import CommunicationTab from "./components/CommunicationTab.vue";

const route = useRoute();
const router = useRouter();
const confirm = useConfirm();
const toast = useToast();

const candidateId = computed(() => Number(route.params.id));
const candidate = ref<CandidateRead | null>(null);
const pageLoading = ref(true);
const activeTab = ref("info");
const saving = ref(false);
const channels = ref<RecruitmentChannelRead[]>([]);

// Applications
const applications = ref<ApplicationRead[]>([]);
const appsLoading = ref(false);

// Edit dialog
const showEditDialog = ref(false);

// ── Education ─────────────────────────────────────────────────────────────────
const showEduDialog = ref(false);
const editingEdu = ref<CandidateEducationRead | null>(null);
const eduForm = ref({
  education_level_id: null as number | null,
  graduation_year: null as number | null,
  diploma_type: "",
  is_main_education: false,
  note: "",
});
const eduErrors = ref<Record<string, string>>({});
const educationLevelOptions = ref<{ label: string; value: number }[]>([]);
const selectedInstitution = ref<EducationalInstitutionRead | null>(null);
const selectedMajor = ref<EducationMajorRead | null>(null);
const institutionSuggestions = ref<EducationalInstitutionRead[]>([]);
const majorSuggestions = ref<EducationMajorRead[]>([]);

// ── Work Exp ──────────────────────────────────────────────────────────────────
const showExpDialog = ref(false);
const editingExp = ref<CandidateWorkExpRead | null>(null);
const expForm = ref({ company_name: "", position_name: "", description: "" });
const expStartDate = ref<Date | null>(null);
const expEndDate = ref<Date | null>(null);

// ── Skills ────────────────────────────────────────────────────────────────────
const showSkillDialog = ref(false);
const skillForm = ref({
  skill_id: null as number | null,
  proficiency_level: null as string | null,
  note: "",
});
const skillErrors = ref<Record<string, string>>({});
const skillOptions = ref<{ label: string; value: number }[]>([]);

const proficiencyOptions = [
  { label: "Cơ bản", value: "beginner" },
  { label: "Trung bình", value: "intermediate" },
  { label: "Tốt", value: "advanced" },
  { label: "Chuyên gia", value: "expert" },
];

// ── Attachments ───────────────────────────────────────────────────────────────
const showUploadDialog = ref(false);
const uploading = ref(false);
const uploadError = ref("");
const uploadForm = ref({ attachment_type: "", note: "" });
const selectedFile = ref<File | null>(null);
const attachmentTypeOptions = [
  { label: "CV / Hồ sơ", value: "cv" },
  { label: "Bằng cấp / Chứng chỉ", value: "degree" },
  { label: "CCCD / Hộ chiếu", value: "id_card" },
  { label: "Ảnh", value: "photo" },
  { label: "Khác", value: "other" },
];

// ── Apply ─────────────────────────────────────────────────────────────────────
const showApplyDialog = ref(false);
const applyForm = ref({
  job_requisition_id: null as number | null,
  source_channel_id: null as number | null,
  internal_note: "",
});
const applyDate = ref<Date | null>(new Date());
const applyError = ref("");
const activeJRs = ref<{ label: string; value: number }[]>([]);

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(d: string) {
  return new Date(d).toLocaleDateString("vi-VN");
}
function formatDatetime(d: string) {
  return new Date(d).toLocaleString("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
  });
}
function formatSalary(n: number) {
  return n.toLocaleString("vi-VN") + " ₫";
}
function formatFileSize(bytes: number) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}
function downloadUrl(att: CandidateAttachmentRead) {
  return `/api/v1${att.download_url.replace("/api/v1", "")}`;
}
function proficiencyLabel(level: string) {
  return proficiencyOptions.find((o) => o.value === level)?.label ?? level;
}
function stageLabel(stage: string) {
  const map: Record<string, string> = {
    new: "Mới",
    screening: "Sàng lọc",
    test: "Kiểm tra",
    interview: "Phỏng vấn",
    offer: "Đề nghị",
    hired: "Tuyển",
    rejected: "Từ chối",
    withdrawn: "Rút",
  };
  return map[stage] ?? stage;
}
function stageSeverity(stage: string) {
  const map: Record<string, string> = {
    new: "info",
    screening: "secondary",
    test: "secondary",
    interview: "warn",
    offer: "contrast",
    hired: "success",
    rejected: "danger",
    withdrawn: "secondary",
  };
  return map[stage] ?? "secondary";
}
function identityStrengthSeverity(
  strength: CandidateRead["identity_strength"],
) {
  const map = {
    strong: "success",
    medium: "warn",
    weak: "danger",
  } as const;
  return map[strength] ?? "secondary";
}
function formatMissingFields(fields: string[]) {
  const labels: Record<string, string> = {
    last_name: "Họ",
    first_name: "Tên",
    date_of_birth: "Ngày sinh",
    gender: "Giới tính",
    nationality_id: "Quốc tịch",
    id_number: "Số CCCD/Hộ chiếu",
    id_issued_on: "Ngày cấp giấy tờ",
    id_issued_by: "Nơi cấp giấy tờ",
  };
  return fields.map((field) => labels[field] ?? field).join(", ");
}

// ── Load ──────────────────────────────────────────────────────────────────────

async function load() {
  pageLoading.value = true;
  try {
    const res = await recruitmentService.getCandidate(candidateId.value);
    candidate.value = res.data;
  } catch {
    candidate.value = null;
  } finally {
    pageLoading.value = false;
  }
}

async function loadApps() {
  appsLoading.value = true;
  applications.value = [];
  try {
    const response = await recruitmentService.listCandidateApplications(
      candidateId.value,
      { page_size: 100 },
    );
    applications.value = response.data.items;
  } catch {
  } finally {
    appsLoading.value = false;
  }
}

async function loadChannelsAndJRs() {
  try {
    const [chRes, jrRes] = await Promise.all([
      recruitmentService.listChannels(),
      recruitmentService.listJR({ page_size: 200, status: "approved" }),
    ]);
    channels.value = (chRes.data as unknown as RecruitmentChannelRead[]).filter(
      (c) => c.is_active,
    );
    activeJRs.value = jrRes.data.items.map((jr) => ({
      label: `${jr.code} — ${jr.job_position_name}`,
      value: jr.id,
    }));
    // Also load in_progress JRs
    const jrRes2 = await recruitmentService.listJR({
      page_size: 200,
      status: "in_progress",
    });
    activeJRs.value.push(
      ...jrRes2.data.items.map((jr) => ({
        label: `${jr.code} — ${jr.job_position_name}`,
        value: jr.id,
      })),
    );
  } catch {}
}

async function loadEducationCatalogs() {
  const [levelsResult, skillsResult] = await Promise.allSettled([
    educationCatalogService.lookupEducationLevels({
      limit: 100,
    }),
    otherBusinessCatalogService.lookupSkills({ limit: 100 }),
  ]);

  educationLevelOptions.value =
    levelsResult.status === "fulfilled"
      ? levelsResult.value.data.map((level) => ({
          value: level.id,
          label: `${level.rank_no}. ${level.name}`,
        }))
      : [];

  skillOptions.value =
    skillsResult.status === "fulfilled"
      ? skillsResult.value.data.map((skill) => ({
          value: skill.id,
          label: skill.name,
        }))
      : [];
}

async function searchInstitutions(event: { query: string }) {
  const response = await educationCatalogService.lookupEducationalInstitutions({
    keyword: event.query || null,
    limit: 20,
  });
  institutionSuggestions.value = response.data;
}

async function searchMajors(event: { query: string }) {
  const response = await educationCatalogService.lookupEducationMajors({
    keyword: event.query || null,
    limit: 20,
  });
  majorSuggestions.value = response.data;
}

function openEdit() {
  showEditDialog.value = true;
}
async function onEdited() {
  showEditDialog.value = false;
  await load();
}

// ── Education ops ─────────────────────────────────────────────────────────────

function openAddEdu() {
  editingEdu.value = null;
  eduForm.value = {
    education_level_id: null,
    graduation_year: null,
    diploma_type: "",
    is_main_education: false,
    note: "",
  };
  eduErrors.value = {};
  selectedInstitution.value = null;
  selectedMajor.value = null;
  showEduDialog.value = true;
}
function openEditEdu(edu: CandidateEducationRead) {
  editingEdu.value = edu;
  eduForm.value = {
    education_level_id: edu.education_level_id,
    graduation_year: edu.graduation_year ?? null,
    diploma_type: edu.diploma_type ?? "",
    is_main_education: edu.is_main_education,
    note: edu.note ?? "",
  };
  eduErrors.value = {};
  selectedInstitution.value = edu.institution_id
    ? ({
        id: edu.institution_id,
        name: edu.institution_name ?? "",
      } as EducationalInstitutionRead)
    : null;
  selectedMajor.value = edu.major_id
    ? ({ id: edu.major_id, name: edu.major_name ?? "" } as EducationMajorRead)
    : null;
  showEduDialog.value = true;
}

function validateEdu() {
  const errors: Record<string, string> = {};
  if (!selectedInstitution.value?.id) {
    errors.institution_id = "Chọn trường từ danh mục";
  }
  if (!eduForm.value.education_level_id) {
    errors.education_level_id = "Chọn trình độ";
  }
  eduErrors.value = errors;
  return Object.keys(errors).length === 0;
}

async function saveEdu() {
  if (!validateEdu()) return;
  saving.value = true;
  try {
    const payload = {
      institution_id: selectedInstitution.value!.id,
      major_id: selectedMajor.value?.id ?? null,
      education_level_id: eduForm.value.education_level_id!,
      graduation_year: eduForm.value.graduation_year,
      diploma_type: eduForm.value.diploma_type || null,
      is_main_education: eduForm.value.is_main_education,
      note: eduForm.value.note || null,
    };
    if (editingEdu.value) {
      await recruitmentService.updateEducation(
        candidateId.value,
        editingEdu.value.id,
        payload,
      );
    } else {
      await recruitmentService.addEducation(candidateId.value, payload);
    }
    showEduDialog.value = false;
    await load();
  } catch {
    toast.add({ severity: "error", summary: "Lỗi", life: 3000 });
  } finally {
    saving.value = false;
  }
}
function confirmDeleteEdu(edu: CandidateEducationRead) {
  confirm.require({
    message: "Xóa thông tin học vấn này?",
    header: "Xác nhận",
    acceptLabel: "Xóa",
    rejectLabel: "Hủy",
    accept: async () => {
      await recruitmentService.deleteEducation(candidateId.value, edu.id);
      await load();
    },
  });
}

// ── Work Exp ops ──────────────────────────────────────────────────────────────

function openAddExp() {
  editingExp.value = null;
  expForm.value = { company_name: "", position_name: "", description: "" };
  expStartDate.value = null;
  expEndDate.value = null;
  showExpDialog.value = true;
}
function openEditExp(exp: CandidateWorkExpRead) {
  editingExp.value = exp;
  expForm.value = {
    company_name: exp.company_name,
    position_name: exp.position_name ?? "",
    description: exp.description ?? "",
  };
  expStartDate.value = exp.start_date ? new Date(exp.start_date) : null;
  expEndDate.value = exp.end_date ? new Date(exp.end_date) : null;
  showExpDialog.value = true;
}
async function saveExp() {
  if (!expForm.value.company_name.trim()) {
    toast.add({
      severity: "warn",
      summary: "Tên công ty không được để trống",
      life: 3000,
    });
    return;
  }
  saving.value = true;
  try {
    const payload = {
      company_name: expForm.value.company_name,
      position_name: expForm.value.position_name || null,
      start_date: expStartDate.value
        ? expStartDate.value.toISOString().slice(0, 10)
        : null,
      end_date: expEndDate.value
        ? expEndDate.value.toISOString().slice(0, 10)
        : null,
      description: expForm.value.description || null,
    };
    if (editingExp.value) {
      await recruitmentService.updateWorkExperience(
        candidateId.value,
        editingExp.value.id,
        payload,
      );
    } else {
      await recruitmentService.addWorkExperience(candidateId.value, payload);
    }
    showExpDialog.value = false;
    await load();
  } catch {
    toast.add({ severity: "error", summary: "Lỗi", life: 3000 });
  } finally {
    saving.value = false;
  }
}
function confirmDeleteExp(exp: CandidateWorkExpRead) {
  confirm.require({
    message: `Xóa kinh nghiệm tại "${exp.company_name}"?`,
    header: "Xác nhận",
    acceptLabel: "Xóa",
    rejectLabel: "Hủy",
    accept: async () => {
      await recruitmentService.deleteWorkExperience(candidateId.value, exp.id);
      await load();
    },
  });
}

// ── Skill ops ─────────────────────────────────────────────────────────────────

async function saveSkill() {
  const errors: Record<string, string> = {};
  if (!skillForm.value.skill_id) {
    errors.skill_id = "Chọn kỹ năng";
  }
  if (!skillForm.value.proficiency_level) {
    errors.proficiency_level = "Chọn mức độ thành thạo";
  }
  skillErrors.value = errors;
  if (Object.keys(errors).length) return;
  saving.value = true;
  try {
    const payload: CandidateSkillCreate = {
      skill_id: skillForm.value.skill_id!,
      proficiency_level: skillForm.value.proficiency_level,
      note: skillForm.value.note || null,
    };
    await recruitmentService.addSkill(candidateId.value, payload);
    showSkillDialog.value = false;
    skillForm.value = { skill_id: null, proficiency_level: null, note: "" };
    skillErrors.value = {};
    await load();
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })
      ?.response?.data?.detail;
    toast.add({
      severity: "error",
      summary: "Lỗi",
      detail: typeof detail === "string" ? detail : "Không thể thêm kỹ năng",
      life: 3000,
    });
  } finally {
    saving.value = false;
  }
}

function openAddSkill() {
  skillForm.value = { skill_id: null, proficiency_level: null, note: "" };
  skillErrors.value = {};
  showSkillDialog.value = true;
}

function confirmDeleteSkill(sk: CandidateSkillRead) {
  confirm.require({
    message: `Xóa kỹ năng "${sk.skill_name}"?`,
    header: "Xác nhận",
    acceptLabel: "Xóa",
    rejectLabel: "Hủy",
    accept: async () => {
      await recruitmentService.deleteSkill(candidateId.value, sk.id);
      await load();
    },
  });
}

// ── Attachment ops ────────────────────────────────────────────────────────────

function onFileSelect(event: { files: File[] }) {
  selectedFile.value = event.files[0] ?? null;
}
async function doUpload() {
  if (!uploadForm.value.attachment_type) {
    uploadError.value = "Chọn loại tài liệu";
    return;
  }
  if (!selectedFile.value) {
    uploadError.value = "Chọn file cần upload";
    return;
  }
  uploading.value = true;
  uploadError.value = "";
  try {
    const fd = new FormData();
    fd.append("attachment_type", uploadForm.value.attachment_type);
    if (uploadForm.value.note) fd.append("note", uploadForm.value.note);
    fd.append("file", selectedFile.value);
    await recruitmentService.uploadAttachment(candidateId.value, fd);
    showUploadDialog.value = false;
    uploadForm.value = { attachment_type: "", note: "" };
    selectedFile.value = null;
    await load();
    toast.add({
      severity: "success",
      summary: "Upload thành công",
      life: 3000,
    });
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })
      ?.response?.data?.detail;
    uploadError.value = typeof detail === "string" ? detail : "Lỗi upload";
  } finally {
    uploading.value = false;
  }
}
function confirmDeleteAtt(att: CandidateAttachmentRead) {
  confirm.require({
    message: `Xóa file "${att.file_name}"?`,
    header: "Xác nhận",
    acceptLabel: "Xóa",
    rejectLabel: "Hủy",
    accept: async () => {
      await recruitmentService.deleteAttachment(candidateId.value, att.id);
      await load();
    },
  });
}

// ── Apply ops ─────────────────────────────────────────────────────────────────

async function doApply() {
  if (!applyForm.value.job_requisition_id) {
    applyError.value = "Chọn JR";
    return;
  }
  saving.value = true;
  applyError.value = "";
  try {
    await recruitmentService.applyCandidate(candidateId.value, {
      job_requisition_id: applyForm.value.job_requisition_id,
      applied_date: applyDate.value
        ? applyDate.value.toISOString().slice(0, 10)
        : undefined,
      source_channel_id: applyForm.value.source_channel_id ?? undefined,
      internal_note: applyForm.value.internal_note || undefined,
    });
    showApplyDialog.value = false;
    applyForm.value = {
      job_requisition_id: null,
      source_channel_id: null,
      internal_note: "",
    };
    toast.add({
      severity: "success",
      summary: "Đã gắn ứng viên vào JR",
      life: 3000,
    });
    await load();
    applications.value = [];
    await loadApps();
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })
      ?.response?.data?.detail;
    applyError.value =
      typeof detail === "string" ? detail : "Lỗi gắn ứng tuyển";
  } finally {
    saving.value = false;
  }
}

onMounted(async () => {
  await Promise.all([load(), loadChannelsAndJRs(), loadEducationCatalogs()]);
  await loadApps();
});
</script>
