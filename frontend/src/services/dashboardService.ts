import api from "./api";

export interface DashboardFilterParams {
  year: number;
  month?: number | null;
  department_id?: number | null;
}

export interface DashboardSummary {
  total_headcount: number;
  new_hires_this_month: number;
  resigned_this_month: number;
  turnover_rate: number;
  headcount_start_of_month: number;
  as_of_date: string;
}

export interface HeadcountByDepartmentItem {
  department_id: number;
  department_name: string;
  headcount: number;
  direct_headcount: number;
  child_department_count: number;
  parent_department_id?: number | null;
}

export interface MonthlyTrendItem {
  month: number;
  new_hires: number;
  resigned_count: number;
  net_change: number;
}

export interface MonthlyTrendReport {
  year: number;
  department_id?: number | null;
  monthly: MonthlyTrendItem[];
}

export interface StructureMetricItem {
  label: string;
  count: number;
}

export interface GenderStructureItem extends StructureMetricItem {
  percentage: number;
}

export interface StructureReport {
  gender: GenderStructureItem[];
  age_group: StructureMetricItem[];
  education_level: StructureMetricItem[];
  tenure_group: StructureMetricItem[];
}

function cleanParams(
  params: DashboardFilterParams,
): Record<string, string | number> {
  return Object.fromEntries(
    Object.entries(params).filter(
      ([, value]) => value !== null && value !== undefined && value !== "",
    ),
  ) as Record<string, string | number>;
}

export default {
  getSummary: (params: DashboardFilterParams) =>
    api.get<DashboardSummary>("/reports/dashboard/summary", {
      params: cleanParams(params),
    }),

  getHeadcountByDepartment: (params: DashboardFilterParams) =>
    api.get<HeadcountByDepartmentItem[]>(
      "/reports/dashboard/headcount-by-dept",
      {
        params: cleanParams(params),
      },
    ),

  getMonthlyTrend: (params: Omit<DashboardFilterParams, "month">) =>
    api.get<MonthlyTrendReport>("/reports/dashboard/monthly-trend", {
      params: cleanParams(params),
    }),

  getStructure: (params: Omit<DashboardFilterParams, "month">) =>
    api.get<StructureReport>("/reports/dashboard/structure", {
      params: cleanParams(params),
    }),
};
