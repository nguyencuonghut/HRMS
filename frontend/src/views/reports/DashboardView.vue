<template>
  <div class="dashboard-view">
    <div class="page-header">
      <div>
        <h2>Dashboard tổng quan</h2>
        <div class="subtitle">
          Tổng hợp headcount, biến động nhân sự và cơ cấu nhân sự theo bộ lọc đã
          chọn.
        </div>
      </div>
    </div>

    <div class="toolbar dashboard-toolbar">
      <Select
        v-model="filters.year"
        :options="yearOptions"
        option-label="label"
        option-value="value"
        class="toolbar-filter-sm"
        placeholder="Năm"
      />
      <Select
        v-model="filters.month"
        :options="monthOptions"
        option-label="label"
        option-value="value"
        class="toolbar-filter-sm"
        placeholder="Tháng"
      />
      <Select
        v-model="filters.department_id"
        :options="departmentOptions"
        option-label="name"
        option-value="id"
        class="toolbar-filter"
        placeholder="Phòng ban"
        filter
        show-clear
      />
      <Button
        label="Xem báo cáo"
        icon="pi pi-chart-line"
        :loading="loading"
        @click="loadDashboard"
      />
    </div>

    <div v-if="errorMessage" class="dashboard-error">
      <i class="pi pi-exclamation-triangle" />
      <span>{{ errorMessage }}</span>
    </div>

    <section class="dashboard-section">
      <div class="dashboard-section-head">
        <h3>{{ summaryHeading }}</h3>
        <span v-if="summary" class="dashboard-meta"
          >As of {{ formatDate(summary.as_of_date) }}</span
        >
      </div>

      <div v-if="loading" class="dashboard-kpis">
        <Skeleton
          v-for="index in 4"
          :key="index"
          height="132px"
          border-radius="16px"
        />
      </div>
      <div v-else class="dashboard-kpis">
        <article
          v-for="card in kpiCards"
          :key="card.label"
          class="dashboard-kpi-card"
        >
          <div class="dashboard-kpi-icon" :class="card.iconClass">
            <i :class="['pi', card.icon]" />
          </div>
          <div class="dashboard-kpi-content">
            <div class="dashboard-kpi-label">{{ card.label }}</div>
            <div class="dashboard-kpi-value">{{ card.value }}</div>
            <div class="dashboard-kpi-sub">{{ card.subtext }}</div>
          </div>
        </article>
      </div>
    </section>

    <section class="dashboard-section">
      <div class="dashboard-section-head">
        <h3>Headcount theo phòng ban</h3>
        <span class="dashboard-meta">{{ headcountMeta }}</span>
      </div>
      <div class="card dashboard-card">
        <div v-if="loading" class="dashboard-chart-skeleton">
          <Skeleton height="280px" border-radius="12px" />
        </div>
        <EmptyState
          v-else-if="headcountByDepartment.length === 0"
          title="Không có dữ liệu"
          subtitle="Chưa có headcount phù hợp với bộ lọc hiện tại."
        />
        <HeadcountHierarchyChart
          v-else
          :items="headcountByDepartment"
          :total-headcount="summary?.total_headcount ?? 0"
        />
      </div>
    </section>

    <section class="dashboard-section">
      <div class="dashboard-section-head">
        <h3>Biến động 12 tháng</h3>
      </div>
      <div class="card dashboard-card">
        <div v-if="loading" class="dashboard-chart-skeleton">
          <Skeleton height="320px" border-radius="12px" />
        </div>
        <EmptyState
          v-else-if="monthlyTrend.monthly.length === 0"
          title="Không có dữ liệu"
          subtitle="Chưa có dữ liệu biến động nhân sự trong năm đã chọn."
        />
        <LineTrendChart v-else :items="monthlyTrend.monthly" />
      </div>
    </section>

    <section class="dashboard-section">
      <div class="dashboard-section-head">
        <h3>Cơ cấu nhân sự</h3>
      </div>
      <div class="dashboard-structure-grid">
        <div class="card dashboard-card">
          <div class="dashboard-structure-head">Giới tính</div>
          <div v-if="loading" class="dashboard-chart-skeleton">
            <Skeleton height="260px" border-radius="12px" />
          </div>
          <EmptyState
            v-else-if="structure.gender.length === 0"
            title="Không có dữ liệu"
            subtitle="Chưa có dữ liệu giới tính trong phạm vi lọc."
          />
          <PieSummaryChart v-else :items="structure.gender" />
        </div>

        <div class="card dashboard-card">
          <div class="dashboard-structure-head">Độ tuổi</div>
          <div v-if="loading" class="dashboard-chart-skeleton">
            <Skeleton height="260px" border-radius="12px" />
          </div>
          <EmptyState
            v-else-if="structure.age_group.length === 0"
            title="Không có dữ liệu"
            subtitle="Chưa có dữ liệu độ tuổi trong phạm vi lọc."
          />
          <HorizontalBarChart
            v-else
            :items="structure.age_group"
            value-key="count"
            value-suffix=" người"
            bar-color="var(--dashboard-age-bar)"
            denominator-mode="total"
          />
        </div>

        <div class="card dashboard-card">
          <div class="dashboard-structure-head">Trình độ học vấn</div>
          <div v-if="loading" class="dashboard-chart-skeleton">
            <Skeleton height="260px" border-radius="12px" />
          </div>
          <EmptyState
            v-else-if="structure.education_level.length === 0"
            title="Không có dữ liệu"
            subtitle="Chưa có dữ liệu học vấn trong phạm vi lọc."
          />
          <HorizontalBarChart
            v-else
            :items="structure.education_level"
            value-key="count"
            value-suffix=" người"
            bar-color="var(--dashboard-education-bar)"
            denominator-mode="total"
          />
        </div>

        <div class="card dashboard-card">
          <div class="dashboard-structure-head">Thâm niên</div>
          <div v-if="loading" class="dashboard-chart-skeleton">
            <Skeleton height="260px" border-radius="12px" />
          </div>
          <EmptyState
            v-else-if="structure.tenure_group.length === 0"
            title="Không có dữ liệu"
            subtitle="Chưa có dữ liệu thâm niên trong phạm vi lọc."
          />
          <HorizontalBarChart
            v-else
            :items="structure.tenure_group"
            value-key="count"
            value-suffix=" người"
            bar-color="var(--dashboard-tenure-bar)"
            denominator-mode="total"
          />
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  defineComponent,
  h,
  onMounted,
  reactive,
  ref,
  type PropType,
} from "vue";
import Button from "primevue/button";
import Select from "primevue/select";
import Skeleton from "primevue/skeleton";

import dashboardService, {
  type DashboardFilterParams,
  type DashboardSummary,
  type GenderStructureItem,
  type HeadcountByDepartmentItem,
  type MonthlyTrendItem,
  type MonthlyTrendReport,
  type StructureMetricItem,
  type StructureReport,
} from "@/services/dashboardService";
import departmentService, {
  type DepartmentRead,
} from "@/services/departmentService";

const now = new Date();
const currentYear = now.getFullYear();
const currentMonth = now.getMonth() + 1;

const filters = reactive<DashboardFilterParams>({
  year: currentYear,
  month: currentMonth,
  department_id: null,
});

const loading = ref(false);
const errorMessage = ref("");
const departments = ref<DepartmentRead[]>([]);
const summary = ref<DashboardSummary | null>(null);
const headcountByDepartment = ref<HeadcountByDepartmentItem[]>([]);
const monthlyTrend = ref<MonthlyTrendReport>({
  year: currentYear,
  department_id: null,
  monthly: [],
});
const structure = ref<StructureReport>({
  gender: [],
  age_group: [],
  education_level: [],
  tenure_group: [],
});

const yearOptions = computed(() =>
  Array.from({ length: 7 }, (_, index) => {
    const year = currentYear - 3 + index;
    return { label: `Năm ${year}`, value: year };
  }),
);

const monthOptions = computed(() =>
  [
    { label: "Toàn năm", value: null },
    ...Array.from({ length: 12 }, (_, index) => ({
      label: `Tháng ${index + 1}`,
      value: index + 1,
    })),
  ],
);

const departmentOptions = computed(() => departments.value);
const selectedDepartment = computed(
  () =>
    departments.value.find((department) => department.id === filters.department_id) ??
    null,
);
const headcountMeta = computed(() => {
  if (filters.department_id && selectedDepartment.value) {
    return `Hiển thị các đơn vị trực thuộc ${selectedDepartment.value.name}`;
  }
  return "Gộp theo phòng/ban cấp gốc";
});

const kpiCards = computed(() => {
  const data = summary.value;
  const annualMode = filters.month == null;
  return [
    {
      label: "Tổng nhân viên",
      value: formatInteger(data?.total_headcount ?? 0),
      subtext: data
        ? `${annualMode ? "Đầu năm" : "Đầu tháng"}: ${formatInteger(data.headcount_start_of_month)}`
        : "Chưa có dữ liệu",
      icon: "pi-users",
      iconClass: "is-primary",
    },
    {
      label: annualMode ? "Mới trong năm" : "Mới trong tháng",
      value: formatInteger(data?.new_hires_this_month ?? 0),
      subtext: annualMode
        ? "Nhân sự bắt đầu làm việc trong năm"
        : "Nhân sự bắt đầu làm việc",
      icon: "pi-user-plus",
      iconClass: "is-green",
    },
    {
      label: annualMode ? "Nghỉ việc trong năm" : "Nghỉ việc trong tháng",
      value: formatInteger(data?.resigned_this_month ?? 0),
      subtext: annualMode
        ? "Nhân sự kết thúc làm việc trong năm"
        : "Nhân sự kết thúc làm việc",
      icon: "pi-user-minus",
      iconClass: "is-red",
    },
    {
      label: "Turnover Rate",
      value: `${formatDecimal(data?.turnover_rate ?? 0)}%`,
      subtext: annualMode
        ? "Tỷ lệ nghỉ việc theo headcount đầu năm"
        : "Tỷ lệ nghỉ việc theo headcount đầu tháng",
      icon: "pi-chart-line",
      iconClass: "is-amber",
    },
  ];
});

const summaryHeading = computed(() =>
  filters.month == null
    ? `KPI năm ${filters.year}`
    : `KPI tháng ${filters.month}/${filters.year}`,
);

const EmptyState = defineComponent({
  name: "DashboardEmptyState",
  props: {
    title: { type: String, required: true },
    subtitle: { type: String, required: true },
  },
  setup(props) {
    return () =>
      h("div", { class: "empty-state dashboard-empty" }, [
        h("i", { class: "pi pi-inbox" }),
        h("strong", props.title),
        h("span", props.subtitle),
      ]);
  },
});

const HorizontalBarChart = defineComponent({
  name: "DashboardHorizontalBarChart",
  props: {
    items: {
      type: Array as PropType<
        Array<HeadcountByDepartmentItem | StructureMetricItem>
      >,
      required: true,
    },
    valueKey: {
      type: String as PropType<"headcount" | "count">,
      required: true,
    },
    valueSuffix: { type: String, default: "" },
    barColor: { type: String, required: true },
    denominatorMode: {
      type: String as PropType<"max" | "total">,
      default: "max",
    },
    layout: {
      type: String as PropType<"stacked" | "grid">,
      default: "stacked",
    },
  },
  setup(props) {
    function getItemLabel(item: HeadcountByDepartmentItem | StructureMetricItem) {
      return "department_name" in item ? item.department_name : item.label;
    }

    function getItemCaption(item: HeadcountByDepartmentItem | StructureMetricItem) {
      if (!("department_name" in item)) return null;
      const details = [`Trực tiếp ${formatInteger(item.direct_headcount)}`];
      if (item.child_department_count > 0) {
        details.push(`${formatInteger(item.child_department_count)} đơn vị con`);
      }
      return details.join(" • ");
    }

    function getItemValue(
      item: HeadcountByDepartmentItem | StructureMetricItem,
      key: "headcount" | "count",
    ) {
      return key === "headcount"
        ? ("headcount" in item ? item.headcount : 0)
        : "count" in item
          ? item.count
          : 0;
    }

    const maxValue = computed(() =>
      props.items.reduce(
        (max, item) => Math.max(max, Number(getItemValue(item, props.valueKey))),
        0,
      ),
    );
    const totalValue = computed(() =>
      props.items.reduce(
        (sum, item) => sum + Number(getItemValue(item, props.valueKey)),
        0,
      ),
    );
    const denominator = computed(() =>
      props.denominatorMode === "total" ? totalValue.value : maxValue.value,
    );

    return () =>
      h(
        "div",
        {
          class: ["bar-chart", props.layout === "grid" && "is-grid"],
        },
        props.items.map((item) => {
          const value = Number(getItemValue(item, props.valueKey));
          const label = getItemLabel(item);
          const width =
            denominator.value === 0
              ? 0
              : Math.max((value / denominator.value) * 100, value > 0 ? 8 : 0);
          return h(
            "div",
            {
              class: "bar-chart-row",
              key: `${label}-${value}`,
            },
            [
              (() => {
                const caption = getItemCaption(item);
                return h(
                  "div",
                  {
                    class: "bar-chart-label",
                    title: label,
                  },
                  caption
                    ? [
                        h("strong", { class: "bar-chart-label-text" }, label),
                        h("span", { class: "bar-chart-caption" }, caption),
                      ]
                    : [h("strong", { class: "bar-chart-label-text" }, label)],
                );
              })(),
              h("div", { class: "bar-chart-track" }, [
                h("div", {
                  class: "bar-chart-fill",
                  style: {
                    width: `${width}%`,
                    background: props.barColor,
                  },
                }),
              ]),
              h(
                "div",
                { class: "bar-chart-value" },
                `${formatInteger(value)}${props.valueSuffix}`,
              ),
            ],
          );
        }),
      );
  },
});

const HeadcountHierarchyChart = defineComponent({
  name: "DashboardHeadcountHierarchyChart",
  props: {
    items: {
      type: Array as PropType<HeadcountByDepartmentItem[]>,
      required: true,
    },
    totalHeadcount: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const denominator = computed(() =>
      Math.max(
        props.totalHeadcount,
        1,
        ...props.items.map((item) => item.headcount),
      ),
    );

    function progressWidth(headcount: number): string {
      return `${Math.max((headcount / denominator.value) * 100, headcount > 0 ? 8 : 0)}%`;
    }

    function childUnitLabel(count: number): string {
      return `${formatInteger(count)} đơn vị con`;
    }

    function shareLabel(headcount: number): string {
      return `${formatDecimal((headcount / denominator.value) * 100)}% quy mô`;
    }

    return () =>
      h(
        "div",
        { class: "headcount-grid" },
        props.items.map((item) =>
          h(
            "article",
            {
              class: [
                "headcount-card",
                item.headcount === 0 && "is-empty",
              ],
              key: item.department_id,
            },
            [
              h("div", { class: "headcount-card-copy" }, [
                h("div", { class: "headcount-card-name", title: item.department_name }, item.department_name),
                h("div", { class: "headcount-card-metric" }, [
                  h("strong", formatInteger(item.headcount)),
                  h("span", "nhân sự"),
                ]),
              ]),
              h("div", { class: "headcount-card-body" }, [
                h("div", { class: "headcount-card-progress-meta" }, [
                  h("span", "Tỷ trọng"),
                  h("strong", shareLabel(item.headcount)),
                ]),
                h("div", { class: "headcount-card-track" }, [
                  h("div", {
                    class: "headcount-card-fill",
                    style: { width: progressWidth(item.headcount) },
                  }),
                ]),
              ]),
              item.headcount > 0
                ? h("div", { class: "headcount-card-detail" }, [
                    h("span", { class: "headcount-card-detail-item" }, [
                      h("i", { class: "pi pi-users" }),
                      `Trực tiếp ${formatInteger(item.direct_headcount)}`,
                    ]),
                    item.child_department_count > 0
                      ? h("span", { class: "headcount-card-detail-item" }, [
                          h("i", { class: "pi pi-sitemap" }),
                          childUnitLabel(item.child_department_count),
                        ])
                      : null,
                  ])
                : h("div", { class: "headcount-card-empty" }, "Chưa có nhân sự"),
            ],
          ),
        ),
      );
  },
});

const PieSummaryChart = defineComponent({
  name: "DashboardPieSummaryChart",
  props: {
    items: { type: Array as PropType<GenderStructureItem[]>, required: true },
  },
  setup(props) {
    const fallbackColors = [
      "var(--dashboard-pie-3)",
      "var(--dashboard-pie-4)",
      "var(--dashboard-pie-5)",
    ];
    const total = computed(() =>
      props.items.reduce((sum, item) => sum + item.count, 0),
    );

    function genderColor(label: string, index: number): string {
      const normalized = label.trim().toLowerCase();
      if (normalized === "nam") return "var(--dashboard-gender-male)";
      if (normalized === "nữ" || normalized === "nu") return "var(--dashboard-gender-female)";
      return fallbackColors[index % fallbackColors.length];
    }

    const segments = computed(() => {
      let offset = 0;
      return props.items.map((item, index) => {
        const portion = total.value === 0 ? 0 : item.count / total.value;
        const dash = `${portion * 100} ${100 - portion * 100}`;
        const color = genderColor(item.label, index);
        const segment = {
          label: item.label,
          count: item.count,
          percentage: item.percentage,
          color,
          style: {
            stroke: color,
            strokeDasharray: dash,
            strokeDashoffset: `${25 - offset}`,
          },
        };
        offset += portion * 100;
        return segment;
      });
    });

    return () =>
      h("div", { class: "pie-summary" }, [
        h(
          "svg",
          {
            viewBox: "0 0 42 42",
            class: "pie-summary-chart",
            "aria-label": "Cơ cấu giới tính",
          },
          [
            h("circle", {
              cx: "21",
              cy: "21",
              r: "15.9155",
              fill: "transparent",
              stroke: "var(--p-surface-200)",
              strokeWidth: "6",
            }),
            ...segments.value.map((segment) =>
              h("circle", {
                cx: "21",
                cy: "21",
                r: "15.9155",
                fill: "transparent",
                strokeWidth: "6",
                style: segment.style,
              }),
            ),
          ],
        ),
        h(
          "div",
          { class: "pie-summary-legend" },
          segments.value.map((segment) =>
            h("div", { class: "pie-summary-legend-item", key: segment.label }, [
              h("span", {
                class: "pie-summary-legend-dot",
                style: { background: segment.color },
              }),
              h("div", { class: "pie-summary-legend-copy" }, [
                h("strong", segment.label),
                h(
                  "span",
                  `${formatInteger(segment.count)} người • ${formatDecimal(segment.percentage)}%`,
                ),
              ]),
            ]),
          ),
        ),
      ]);
  },
});

const LineTrendChart = defineComponent({
  name: "DashboardLineTrendChart",
  props: {
    items: { type: Array as PropType<MonthlyTrendItem[]>, required: true },
  },
  setup(props) {
    const width = 720;
    const height = 260;
    const padding = { top: 20, right: 28, bottom: 38, left: 28 };

    const maxValue = computed(() =>
      Math.max(
        1,
        ...props.items.flatMap((item) => [item.new_hires, item.resigned_count]),
      ),
    );

    function xAt(index: number): number {
      const innerWidth = width - padding.left - padding.right;
      return (
        padding.left +
        (innerWidth * index) / Math.max(props.items.length - 1, 1)
      );
    }

    function yAt(value: number): number {
      const innerHeight = height - padding.top - padding.bottom;
      return padding.top + innerHeight - (value / maxValue.value) * innerHeight;
    }

    function toPath(values: number[]): string {
      return values
        .map(
          (value, index) =>
            `${index === 0 ? "M" : "L"} ${xAt(index)} ${yAt(value)}`,
        )
        .join(" ");
    }

    const hiresPath = computed(() =>
      toPath(props.items.map((item) => item.new_hires)),
    );
    const resignedPath = computed(() =>
      toPath(props.items.map((item) => item.resigned_count)),
    );

    return () =>
      h("div", { class: "line-chart" }, [
        h(
          "svg",
          {
            viewBox: `0 0 ${width} ${height}`,
            class: "line-chart-svg",
            "aria-label": "Biến động nhân sự 12 tháng",
          },
          [
            ...Array.from({ length: 5 }, (_, index) => {
              const value = (maxValue.value / 4) * index;
              const y = yAt(value);
              return h("g", { key: `grid-${index}` }, [
                h("line", {
                  x1: padding.left,
                  y1: y,
                  x2: width - padding.right,
                  y2: y,
                  class: "line-chart-grid",
                }),
                h(
                  "text",
                  { x: 0, y: y + 4, class: "line-chart-axis-label" },
                  formatInteger(Math.round(value)),
                ),
              ]);
            }),
            h("path", {
              d: hiresPath.value,
              class: "line-chart-path is-hires",
            }),
            h("path", {
              d: resignedPath.value,
              class: "line-chart-path is-resigned",
            }),
            ...props.items.flatMap((item, index) => [
              h("circle", {
                cx: xAt(index),
                cy: yAt(item.new_hires),
                r: 4,
                class: "line-chart-point is-hires",
              }),
              h("circle", {
                cx: xAt(index),
                cy: yAt(item.resigned_count),
                r: 4,
                class: "line-chart-point is-resigned",
              }),
              h(
                "text",
                {
                  x: xAt(index),
                  y: height - 10,
                  class: "line-chart-axis-label is-bottom",
                },
                `T${item.month}`,
              ),
            ]),
          ],
        ),
        h("div", { class: "line-chart-legend" }, [
          h("div", { class: "line-chart-legend-item" }, [
            h("span", { class: "line-chart-legend-dot is-hires" }),
            h("span", "Tuyển mới"),
          ]),
          h("div", { class: "line-chart-legend-item" }, [
            h("span", { class: "line-chart-legend-dot is-resigned" }),
            h("span", "Nghỉ việc"),
          ]),
        ]),
      ]);
  },
});

async function loadDepartments() {
  try {
    const res = await departmentService.getList(true);
    departments.value = res.data;
  } catch {
    departments.value = [];
  }
}

async function loadDashboard() {
  loading.value = true;
  errorMessage.value = "";

  const summaryParams: DashboardFilterParams = {
    year: filters.year,
    month: filters.month ?? null,
    department_id: filters.department_id ?? null,
  };
  const yearlyParams = {
    year: filters.year,
    department_id: filters.department_id ?? null,
  };

  try {
    const [summaryRes, headcountRes, trendRes, structureRes] =
      await Promise.all([
        dashboardService.getSummary(summaryParams),
        dashboardService.getHeadcountByDepartment(summaryParams),
        dashboardService.getMonthlyTrend(yearlyParams),
        dashboardService.getStructure(yearlyParams),
      ]);

    summary.value = summaryRes.data;
    headcountByDepartment.value = [...headcountRes.data].sort(
      (a, b) => b.headcount - a.headcount,
    );
    monthlyTrend.value = trendRes.data;
    structure.value = structureRes.data;
  } catch {
    summary.value = null;
    headcountByDepartment.value = [];
    monthlyTrend.value = {
      year: filters.year,
      department_id: filters.department_id ?? null,
      monthly: [],
    };
    structure.value = {
      gender: [],
      age_group: [],
      education_level: [],
      tenure_group: [],
    };
    errorMessage.value = "Không thể tải dashboard. Vui lòng thử lại.";
  } finally {
    loading.value = false;
  }
}

function formatInteger(value: number): string {
  return new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 }).format(
    value,
  );
}

function formatDecimal(value: number): string {
  return new Intl.NumberFormat("vi-VN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  }).format(value);
}

function formatDate(value: string): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("vi-VN").format(date);
}

onMounted(async () => {
  await loadDepartments();
  await loadDashboard();
});
</script>

<style>
.dashboard-view {
  --dashboard-headcount-bar: linear-gradient(
    90deg,
    color-mix(in srgb, var(--p-primary-400) 88%, white),
    var(--p-primary-600)
  );
  --dashboard-age-bar: linear-gradient(90deg, #38bdf8, #0284c7);
  --dashboard-education-bar: linear-gradient(90deg, #fbbf24, #d97706);
  --dashboard-tenure-bar: linear-gradient(90deg, #34d399, #059669);
  --dashboard-hires-color: #16a34a;
  --dashboard-resigned-color: #dc2626;
  --dashboard-gender-male: #2563eb;
  --dashboard-gender-female: #f97316;
  --dashboard-pie-1: #14b8a6;
  --dashboard-pie-2: #38bdf8;
  --dashboard-pie-3: #f59e0b;
  --dashboard-pie-4: #f87171;
  --dashboard-pie-5: #a78bfa;
  --dashboard-base-bg: var(--l-surface);
  --dashboard-surface-soft: var(--l-surface-variant);
  --dashboard-track-bg: color-mix(
    in srgb,
    var(--l-border) 65%,
    transparent
  );
  --dashboard-grid-line: color-mix(
    in srgb,
    var(--l-border) 70%,
    transparent
  );
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

html.dark-mode .dashboard-view {
  --dashboard-headcount-bar: linear-gradient(
    90deg,
    color-mix(in srgb, var(--p-primary-300) 85%, white),
    var(--p-primary-500)
  );
  --dashboard-age-bar: linear-gradient(90deg, #7dd3fc, #0ea5e9);
  --dashboard-education-bar: linear-gradient(90deg, #fcd34d, #f59e0b);
  --dashboard-tenure-bar: linear-gradient(90deg, #6ee7b7, #10b981);
  --dashboard-hires-color: #4ade80;
  --dashboard-resigned-color: #f87171;
  --dashboard-gender-male: #60a5fa;
  --dashboard-gender-female: #fb7185;
  --dashboard-pie-1: #5eead4;
  --dashboard-pie-2: #7dd3fc;
  --dashboard-pie-3: #fcd34d;
  --dashboard-pie-4: #fca5a5;
  --dashboard-pie-5: #c4b5fd;
  --dashboard-base-bg: var(--l-surface);
  --dashboard-surface-soft: var(--l-surface-variant);
  --dashboard-track-bg: color-mix(
    in srgb,
    var(--l-border) 85%,
    transparent
  );
  --dashboard-grid-line: color-mix(
    in srgb,
    var(--l-border) 85%,
    transparent
  );
}

.dashboard-toolbar {
  margin-bottom: 0;
}

.dashboard-error {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.875rem 1rem;
  border: 1px solid color-mix(in srgb, var(--p-red-500) 28%, transparent);
  background: color-mix(in srgb, var(--p-red-500) 10%, var(--p-surface-0));
  color: var(--p-red-700);
  border-radius: 12px;
}

html.dark-mode .dashboard-error {
  color: var(--p-red-300);
}

.dashboard-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.dashboard-section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
}

.dashboard-section-head h3 {
  margin: 0;
  font-size: 1.05rem;
  color: var(--l-text);
}

.dashboard-meta {
  color: var(--l-text-muted);
  font-size: 0.875rem;
}

.dashboard-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
}

.dashboard-kpi-card {
  display: flex;
  gap: 0.875rem;
  padding: var(--hh-card-content-padding);
  border: 1px solid var(--l-border);
  border-radius: 12px;
  background-color: var(--dashboard-base-bg);
  color: var(--l-text);
  box-shadow: var(--l-shadow);
}

.dashboard-kpi-icon {
  width: 3rem;
  height: 3rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  font-size: 1.15rem;
  color: white;
  flex-shrink: 0;
}

.dashboard-kpi-icon.is-primary {
  background: linear-gradient(
    135deg,
    var(--p-primary-500),
    var(--p-primary-700)
  );
}
.dashboard-kpi-icon.is-green {
  background: linear-gradient(135deg, #22c55e, #15803d);
}
.dashboard-kpi-icon.is-red {
  background: linear-gradient(135deg, #ef4444, #b91c1c);
}
.dashboard-kpi-icon.is-amber {
  background: linear-gradient(135deg, #f59e0b, #d97706);
}

.dashboard-kpi-content {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 0;
}

.dashboard-kpi-label {
  color: var(--l-text-muted);
  font-size: 0.82rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.dashboard-kpi-value {
  font-size: 1.95rem;
  line-height: 1;
  font-weight: 800;
  color: var(--l-text);
}

.dashboard-kpi-sub {
  color: var(--l-text-muted);
  font-size: 0.875rem;
}

.dashboard-card {
  padding: var(--hh-card-content-padding);
  background-color: var(--dashboard-base-bg);
  border: 1px solid var(--l-border);
  border-radius: 0.5rem;
  color: var(--l-text);
  box-shadow: var(--l-shadow);
}

.dashboard-chart-skeleton {
  padding: 0.25rem 0;
}

.dashboard-structure-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.dashboard-structure-head {
  margin-bottom: 0.875rem;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--l-text);
}

.dashboard-empty {
  min-height: 240px;
  justify-content: center;
  text-align: center;
}

.dashboard-empty strong {
  font-size: 0.95rem;
}

.dashboard-view .headcount-grid {
  display: grid;
  grid-template-columns: repeat(1, minmax(0, 1fr));
  gap: 1rem;
}

.dashboard-view .headcount-card {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  min-height: 13.25rem;
  padding: 1.05rem 1rem;
  border: 1px solid color-mix(in srgb, var(--l-border) 88%, transparent);
  border-radius: 12px;
  background: color-mix(
    in srgb,
    var(--dashboard-base-bg) 88%,
    var(--dashboard-surface-soft)
  );
}

.dashboard-view .headcount-card-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.dashboard-view .headcount-card-name {
  font-size: 0.96rem;
  font-weight: 600;
  color: var(--l-text);
  line-height: 1.35;
  min-height: 2.75rem;
}

.dashboard-view .headcount-card-metric {
  display: flex;
  align-items: flex-end;
  gap: 0.45rem;
  flex-shrink: 0;
}

.dashboard-view .headcount-card-metric strong {
  font-size: 2.35rem;
  line-height: 1;
  font-weight: 800;
  color: var(--l-text);
  font-variant-numeric: tabular-nums;
}

.dashboard-view .headcount-card-metric span {
  font-size: 0.88rem;
  color: var(--l-text-muted);
  margin-bottom: 0.2rem;
}

.dashboard-view .headcount-card-body {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.dashboard-view .headcount-card-progress-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  font-size: 0.76rem;
  color: var(--l-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.dashboard-view .headcount-card-progress-meta strong {
  color: var(--l-text);
  font-size: 0.8rem;
  font-weight: 700;
}

.dashboard-view .headcount-card-track {
  position: relative;
  height: 0.65rem;
  border-radius: 999px;
  overflow: hidden;
  background: var(--dashboard-track-bg);
}

.dashboard-view .headcount-card-fill {
  height: 100%;
  border-radius: inherit;
  background: var(--dashboard-headcount-bar);
}

.dashboard-view .headcount-card-detail {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-top: auto;
  padding-top: 0.45rem;
  border-top: 1px solid color-mix(in srgb, var(--l-border) 75%, transparent);
}

.dashboard-view .headcount-card-detail-item {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: var(--l-text-muted);
}

.dashboard-view .headcount-card-detail-item i {
  font-size: 0.72rem;
  color: var(--p-primary-color);
}

.dashboard-view .headcount-card-empty {
  margin-top: auto;
  padding-top: 0.45rem;
  border-top: 1px solid color-mix(in srgb, var(--l-border) 75%, transparent);
  font-size: 0.78rem;
  color: var(--l-text-muted);
}

.dashboard-view .headcount-card.is-empty {
  opacity: 0.58;
}

html.dark-mode .dashboard-view .headcount-card.is-empty {
  opacity: 0.72;
}

.bar-chart {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.bar-chart.is-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.875rem 1rem;
}

.bar-chart-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.bar-chart.is-grid .bar-chart-row {
  grid-template-columns: minmax(0, 1fr);
  gap: 0.5rem;
  align-items: stretch;
  padding: 0.875rem 0.95rem;
  border-radius: 10px;
  background: var(--dashboard-surface-soft);
  border: 1px solid color-mix(in srgb, var(--l-border) 85%, transparent);
}

.bar-chart.is-grid .bar-chart-label {
  font-size: 0.92rem;
}

.bar-chart.is-grid .bar-chart-value {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--l-text);
}

.bar-chart-label,
.bar-chart-value {
  font-size: 0.88rem;
}

.bar-chart-label {
  display: flex;
  flex-direction: column;
  flex: 0 0 110px;
  gap: 0.15rem;
  line-height: 1.35;
  color: var(--l-text);
}

.bar-chart-label-text {
  font-weight: 600;
}

.bar-chart-caption {
  color: var(--l-text-muted);
  font-size: 0.78rem;
}

.bar-chart-track {
  position: relative;
  flex: 1 1 auto;
  height: 1.25rem;
  border-radius: 999px;
  background: var(--dashboard-track-bg);
  overflow: hidden;
}

.bar-chart-fill {
  height: 100%;
  border-radius: inherit;
  min-width: 0;
}

.bar-chart-value {
  color: var(--l-text-muted);
  flex: 0 0 4.5rem;
  text-align: right;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.pie-summary {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 1rem;
  align-items: center;
  min-height: 240px;
}

.pie-summary-chart {
  width: 100%;
  max-width: 180px;
  transform: rotate(-90deg);
}

.pie-summary-legend {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.pie-summary-legend-item {
  display: flex;
  align-items: flex-start;
  gap: 0.625rem;
}

.pie-summary-legend-dot {
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 999px;
  margin-top: 0.25rem;
  flex-shrink: 0;
}

.pie-summary-legend-copy {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.pie-summary-legend-copy strong {
  font-size: 0.92rem;
}

.pie-summary-legend-copy span {
  color: var(--l-text-muted);
  font-size: 0.85rem;
}

.line-chart {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.line-chart-svg {
  width: 100%;
  height: auto;
  overflow: visible;
}

.line-chart-grid {
  stroke: var(--dashboard-grid-line);
  stroke-width: 1;
}

.line-chart-axis-label {
  fill: var(--l-text-muted);
  font-size: 11px;
}

.line-chart-axis-label.is-bottom {
  text-anchor: middle;
}

.line-chart-path {
  fill: none;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.line-chart-path.is-hires,
.line-chart-point.is-hires,
.line-chart-legend-dot.is-hires {
  stroke: var(--dashboard-hires-color);
  background: var(--dashboard-hires-color);
  fill: var(--dashboard-hires-color);
}

.line-chart-path.is-resigned,
.line-chart-point.is-resigned,
.line-chart-legend-dot.is-resigned {
  stroke: var(--dashboard-resigned-color);
  background: var(--dashboard-resigned-color);
  fill: var(--dashboard-resigned-color);
}

.line-chart-legend {
  display: flex;
  justify-content: center;
  gap: 1rem;
  flex-wrap: wrap;
  color: var(--l-text-muted);
  font-size: 0.875rem;
}

.line-chart-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.line-chart-legend-dot {
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 999px;
}

@media (max-width: 1024px) {
  .dashboard-kpis,
  .dashboard-structure-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .bar-chart.is-grid {
    grid-template-columns: 1fr;
  }
}

@media (min-width: 900px) {
  .dashboard-view .headcount-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (min-width: 1320px) {
  .dashboard-view .headcount-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .dashboard-section-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .bar-chart-row {
    flex-direction: column;
    align-items: stretch;
    gap: 0.375rem;
  }

  .bar-chart-label,
  .bar-chart-value {
    flex-basis: auto;
  }

  .bar-chart-value {
    text-align: left;
  }

  .pie-summary {
    grid-template-columns: 1fr;
    justify-items: center;
    text-align: center;
  }

  .pie-summary-legend {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .dashboard-kpis,
  .dashboard-structure-grid {
    grid-template-columns: 1fr;
  }

  .dashboard-kpi-value {
    font-size: 1.7rem;
  }
}
</style>
